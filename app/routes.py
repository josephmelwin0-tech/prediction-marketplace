from fastapi import APIRouter, Depends, HTTPException, Header, Request
from .auth import generate_api_key, hash_api_key, get_current_agent
from sqlalchemy.orm import Session
from sqlalchemy import update
from pydantic import BaseModel
from typing import Optional
from .database import get_db
from .models import Agent, Market, Bet
from .polymarket import fetch_polymarket_markets
from .email import send_welcome, send_low_credit_alert, send_market_resolved
from slowapi import Limiter
from slowapi.util import get_remote_address
import uuid, os
from .resolution import search_resolution_evidence, determine_resolution, redistribute_credits
from datetime import datetime


router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

ADMIN_SECRET = os.getenv("ADMIN_SECRET_KEY", "change-me-in-env")

# --- Schemas ---

class AgentRegister(BaseModel):
    name: str
    wallet_address: str

class DeveloperSignup(BaseModel):
    name: str
    email: str

class MarketCreate(BaseModel):
    title: str
    category: str
    resolution_date: str
    resolution_source: str

class BetPlace(BaseModel):
    position: str  # "YES" or "NO"
    amount: float
    reasoning: str

# --- Auth Routes ---

@router.post("/signup")
@limiter.limit("5/minute")
def signup(request: Request, payload: DeveloperSignup, db: Session = Depends(get_db)):
    """
    Create a developer account and get your API key.
    The key is shown ONCE — save it immediately.
    """
    existing = db.query(Agent).filter(Agent.developer_email == payload.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered.")

    raw_key = generate_api_key()
    key_hash = hash_api_key(raw_key)

    account = Agent(
        name=payload.name,
        developer_email=payload.email,
        api_key_hash=key_hash,
        credits=1000.0,
        wallet_address=None,
    )
    db.add(account)
    db.commit()
    db.refresh(account)

    try:
        send_welcome(
            to_email=payload.email,
            name=payload.name,
            api_key=raw_key,
            account_id=account.id
        )
    except Exception:
        pass

    return {
        "message": "Account created. Save your API key — it will NOT be shown again.",
        "api_key": raw_key,
        "account_id": account.id,
        "credits": 1000,
        "next_step": "Use this key as X-API-Key header in all requests"
    }


@router.get("/me")
def get_me(current: Agent = Depends(get_current_agent)):
    """Check your account details. Requires X-API-Key header."""
    return {
        "name": current.name,
        "email": current.developer_email,
        "account_id": current.id,
        "credits": current.credits,
        "total_bets": current.total_bets,
        "correct_bets": current.correct_bets,
        "accuracy": round((current.correct_bets / current.total_bets * 100), 1) if current.total_bets > 0 else 0
    }


# --- Legacy Route (kept so old agents don't break) ---

@router.post("/register")
def register_agent(agent: AgentRegister, db: Session = Depends(get_db)):
    """Legacy registration via wallet address. Use /signup instead."""
    existing = db.query(Agent).filter(Agent.wallet_address == agent.wallet_address).first()
    if existing:
        raise HTTPException(status_code=400, detail="Agent already registered")

    new_agent = Agent(
        name=agent.name,
        wallet_address=agent.wallet_address,
        credits=100.0,
    )
    db.add(new_agent)
    db.commit()
    db.refresh(new_agent)

    return {
        "message": "Agent registered (legacy). Use /signup for the new auth system.",
        "agent_id": new_agent.id,
        "credits_granted": 100.0,
        "wallet": agent.wallet_address
    }


# --- Agent Routes ---

@router.get("/agents")
def list_agents(db: Session = Depends(get_db)):
    agents = db.query(Agent).all()
    return [
        {
            "id": a.id,
            "name": a.name,
            "credits": a.credits,
            "total_bets": a.total_bets,
            "correct_bets": a.correct_bets,
            "accuracy": round((a.correct_bets / a.total_bets * 100), 1) if a.total_bets > 0 else 0
        }
        for a in agents
    ]


@router.get("/agents/{agent_id}")
def get_agent(agent_id: str, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


# --- Market Routes ---

@router.post("/markets")
def create_market(
    market: MarketCreate,
    db: Session = Depends(get_db),
    current: Agent = Depends(get_current_agent)
):
    """Create a market. Costs 100 credits. Requires X-API-Key header."""
    MARKET_COST = 100

    result = db.execute(
        update(Agent)
        .where(Agent.id == current.id, Agent.credits >= MARKET_COST)
        .values(credits=Agent.credits - MARKET_COST)
        .returning(Agent.credits)
    )
    new_balance = result.scalar()
    if new_balance is None:
        raise HTTPException(status_code=400, detail="Insufficient credits. Market creation costs 100 credits.")

    new_market = Market(
        title=market.title,
        category=market.category,
        resolution_date=market.resolution_date,
        resolution_source=market.resolution_source,
        created_by=current.id
    )
    db.add(new_market)
    db.commit()
    db.refresh(new_market)

    return {
        "message": "Market created successfully",
        "market_id": new_market.id,
        "title": new_market.title,
        "credits_spent": MARKET_COST,
        "remaining_credits": new_balance
    }


@router.get("/markets")
def list_markets(db: Session = Depends(get_db)):
    markets = db.query(Market).all()
    return [
        {
            "id": m.id,
            "title": m.title,
            "category": m.category,
            "resolution_date": m.resolution_date,
            "resolution_source": m.resolution_source,
            "created_by": m.created_by,
            "status": m.status,
            "yes_pool": m.yes_pool,
            "no_pool": m.no_pool,
            "total_pool": m.yes_pool + m.no_pool,
            "created_at": m.created_at
        }
        for m in markets
    ]


@router.get("/markets/{market_id}")
def get_market(market_id: str, db: Session = Depends(get_db)):
    market = db.query(Market).filter(Market.id == market_id).first()
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")

    bets = db.query(Bet).filter(Bet.market_id == market_id).all()

    return {
        "market": {
            "id": market.id,
            "title": market.title,
            "category": market.category,
            "resolution_date": market.resolution_date,
            "yes_pool": market.yes_pool,
            "no_pool": market.no_pool,
        },
        "bets": [
            {
                "agent_name": b.agent_name,
                "position": b.position,
                "amount": b.amount,
                "reasoning": b.reasoning,
                "placed_at": b.placed_at
            }
            for b in bets
        ],
        "yes_bets": [
            {"agent_name": b.agent_name, "amount": b.amount, "reasoning": b.reasoning}
            for b in bets if b.position == "YES"
        ],
        "no_bets": [
            {"agent_name": b.agent_name, "amount": b.amount, "reasoning": b.reasoning}
            for b in bets if b.position == "NO"
        ]
    }


@router.post("/markets/{market_id}/bet")
@limiter.limit("30/minute")
def place_bet(
    request: Request,
    market_id: str,
    bet: BetPlace,
    db: Session = Depends(get_db),
    current: Agent = Depends(get_current_agent)
):
    """Place a bet. Requires X-API-Key header."""
    if bet.position not in ["YES", "NO"]:
        raise HTTPException(status_code=400, detail="Position must be YES or NO")
    if not bet.reasoning or len(bet.reasoning) < 20:
        raise HTTPException(status_code=400, detail="Reasoning must be at least 20 characters")

    market = db.query(Market).filter(Market.id == market_id).first()
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")
    if market.status != "open":
        raise HTTPException(status_code=400, detail="Market is closed")

    platform_fee = round(bet.amount * 0.02, 4)
    total_cost = bet.amount + platform_fee

    result = db.execute(
        update(Agent)
        .where(Agent.id == current.id, Agent.credits >= total_cost)
        .values(credits=Agent.credits - total_cost, total_bets=Agent.total_bets + 1)
        .returning(Agent.credits)
    )
    new_balance = result.scalar()
    if new_balance is None:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient credits. Need {total_cost}, you have {current.credits}."
        )

    if bet.position == "YES":
        market.yes_pool += bet.amount
    else:
        market.no_pool += bet.amount

    new_bet = Bet(
        market_id=market_id,
        agent_id=current.id,
        agent_name=current.name,
        position=bet.position,
        amount=bet.amount,
        reasoning=bet.reasoning,
    )

    db.add(new_bet)
    db.commit()
    db.refresh(new_bet)

    try:
        if new_balance <= 100 and current.developer_email:
            send_low_credit_alert(
                to_email=current.developer_email,
                name=current.name,
                credits_remaining=new_balance
            )
    except Exception:
        pass

    return {
        "message": "Bet placed successfully",
        "bet_id": new_bet.id,
        "position": bet.position,
        "amount": bet.amount,
        "platform_fee": platform_fee,
        "remaining_credits": new_balance,
        "reasoning_logged": True
    }


# --- Feed & Leaderboard ---

@router.get("/feed")
def live_feed(db: Session = Depends(get_db)):
    bets = db.query(Bet).order_by(Bet.placed_at.desc()).limit(50).all()
    return [
        {
            "agent_name": b.agent_name,
            "market_id": b.market_id,
            "position": b.position,
            "amount": b.amount,
            "reasoning": b.reasoning,
            "placed_at": b.placed_at
        }
        for b in bets
    ]


@router.get("/leaderboard")
def leaderboard(db: Session = Depends(get_db)):
    agents = db.query(Agent).filter(Agent.total_bets > 0).all()
    ranked = sorted(
        agents,
        key=lambda a: a.correct_bets / a.total_bets if a.total_bets > 0 else 0,
        reverse=True
    )
    return [
        {
            "rank": i + 1,
            "name": a.name,
            "total_bets": a.total_bets,
            "correct_bets": a.correct_bets,
            "accuracy": round((a.correct_bets / a.total_bets * 100), 1) if a.total_bets > 0 else 0,
            "credits": a.credits
        }
        for i, a in enumerate(ranked)
    ]


# --- Admin / Utility (protected) ---

def verify_admin(x_admin_key: str = Header(...)):
    if x_admin_key != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.post("/seed-markets", dependencies=[Depends(verify_admin)])
def seed_markets(db: Session = Depends(get_db)):
    """Admin only. Requires X-Admin-Key header."""
    markets = fetch_polymarket_markets(limit=10)
    created = []

    for m in markets:
        existing = db.query(Market).filter(Market.title == m["title"]).first()
        if not existing:
            new_market = Market(
                title=m["title"],
                category=m["category"],
                resolution_date=m["resolution_date"],
                resolution_source=m["resolution_source"],
                created_by=m["created_by"]
            )
            db.add(new_market)
            created.append(m["title"])

    db.commit()
    return {
        "message": f"Seeded {len(created)} markets from Polymarket",
        "markets": created
    }


@router.delete("/markets/{market_id}", dependencies=[Depends(verify_admin)])
def delete_market(market_id: str, db: Session = Depends(get_db)):
    """Admin only. Requires X-Admin-Key header."""
    market = db.query(Market).filter(Market.id == market_id).first()
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")
    db.delete(market)
    db.commit()
    return {"message": "Market deleted"}


@router.post("/markets/{market_id}/resolve", dependencies=[Depends(verify_admin)])
def resolve_market(market_id: str, db: Session = Depends(get_db)):
    """Admin only. Requires X-Admin-Key header."""
    market = db.query(Market).filter(Market.id == market_id).first()
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")
    if market.status != "open":
        raise HTTPException(status_code=400, detail="Market already resolved")

    evidence = search_resolution_evidence(market.title, market.resolution_source)
    if not evidence:
        return {"message": "No evidence found", "resolution": "UNRESOLVED"}

    result = determine_resolution(market.title, market.resolution_date, evidence)

    if result["resolution"] == "UNRESOLVED":
        return {
            "message": "Market unresolved — not enough evidence",
            "reasoning": result["reasoning"]
        }

    market.status = f"resolved_{result['resolution'].lower()}"
    redistribute_credits(market, result["resolution"], db)
    db.commit()

    try:
        bets = db.query(Bet).filter(Bet.market_id == market_id).all()
        winning_agent_ids = [b.agent_id for b in bets if b.position == result["resolution"]]
        for agent_id in set(winning_agent_ids):
            agent = db.query(Agent).filter(Agent.id == agent_id).first()
            if agent and agent.developer_email:
                won_bets = [b for b in bets if b.agent_id == agent_id and b.position == result["resolution"]]
                credits_won = sum(b.amount for b in won_bets)
                send_market_resolved(
                    to_email=agent.developer_email,
                    name=agent.name,
                    market_title=market.title,
                    resolution=result["resolution"],
                    credits_won=credits_won
                )
    except Exception:
        pass

    return {
        "message": f"Market resolved {result['resolution']}",
        "market": market.title,
        "resolution": result["resolution"],
        "confidence": result["confidence"],
        "reasoning": result["reasoning"]
    }


@router.post("/resolve-all", dependencies=[Depends(verify_admin)])
def resolve_all_markets(db: Session = Depends(get_db)):
    """Admin only. Requires X-Admin-Key header."""
    markets = db.query(Market).filter(Market.status == "open").all()
    results = []

    for market in markets:
        evidence = search_resolution_evidence(market.title, market.resolution_source)
        if not evidence:
            continue

        result = determine_resolution(market.title, market.resolution_date, evidence)

        if result["resolution"] != "UNRESOLVED" and result["confidence"] > 0.7:
            market.status = f"resolved_{result['resolution'].lower()}"
            redistribute_credits(market, result["resolution"], db)
            db.commit()
            results.append({
                "market": market.title,
                "resolution": result["resolution"],
                "confidence": result["confidence"],
                "reasoning": result["reasoning"]
            })

    return {
        "message": f"Resolved {len(results)} markets",
        "resolved": results
    }
