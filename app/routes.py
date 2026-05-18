from fastapi import APIRouter, Depends, HTTPException
from .auth import generate_api_key, hash_api_key, get_current_agent
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from .database import get_db
from .models import Agent, Market, Bet
from .polymarket import fetch_polymarket_markets
import uuid
from .resolution import search_resolution_evidence, determine_resolution, redistribute_credits
from datetime import datetime


router = APIRouter()

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
    created_by: str

class BetPlace(BaseModel):
    agent_id: str
    position: str  # "YES" or "NO"
    amount: float
    reasoning: str

# --- Auth Routes ---

@router.post("/signup")
def signup(payload: DeveloperSignup, db: Session = Depends(get_db)):
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
        sol_paid=0.05
    )
    db.add(new_agent)
    db.commit()
    db.refresh(new_agent)

    return {
        "message": "Agent registered successfully (legacy). Use /signup for the new auth system.",
        "agent_id": new_agent.id,
        "credits_granted": 100.0,
        "sol_fee_paid": 0.05,
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
def create_market(market: MarketCreate, db: Session = Depends(get_db)):
    new_market = Market(
        title=market.title,
        category=market.category,
        resolution_date=market.resolution_date,
        resolution_source=market.resolution_source,
        created_by=market.created_by
    )
    db.add(new_market)
    db.commit()
    db.refresh(new_market)

    return {
        "message": "Market created successfully",
        "market_id": new_market.id,
        "sol_fee_paid": 0.001,
        "title": new_market.title
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
def place_bet(
    market_id: str,
    bet: BetPlace,
    db: Session = Depends(get_db),
    current: Agent = Depends(get_current_agent)   # <-- NOW REQUIRES API KEY
):
    """Place a bet. Requires X-API-Key header."""
    market = db.query(Market).filter(Market.id == market_id).first()
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")
    if market.status != "open":
        raise HTTPException(status_code=400, detail="Market is closed")

    # Use the authenticated account's credits, not a random agent_id lookup
    agent = current

    if agent.credits < bet.amount:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. You have {agent.credits}, need {bet.amount}.")
    if bet.position not in ["YES", "NO"]:
        raise HTTPException(status_code=400, detail="Position must be YES or NO")
    if not bet.reasoning or len(bet.reasoning) < 20:
        raise HTTPException(status_code=400, detail="Reasoning must be at least 20 characters")

    # Deduct credits + platform fee
    platform_fee = bet.amount * 0.02
    agent.credits -= (bet.amount + platform_fee)
    agent.total_bets += 1

    # Update pools
    if bet.position == "YES":
        market.yes_pool += bet.amount
    else:
        market.no_pool += bet.amount

    new_bet = Bet(
        market_id=market_id,
        agent_id=agent.id,
        agent_name=agent.name,
        position=bet.position,
        amount=bet.amount,
        reasoning=bet.reasoning,
        sol_fee_paid=0.0005
    )

    db.add(new_bet)
    db.commit()
    db.refresh(new_bet)

    return {
        "message": "Bet placed successfully",
        "bet_id": new_bet.id,
        "position": bet.position,
        "amount": bet.amount,
        "platform_fee": platform_fee,
        "sol_fee_paid": 0.0005,
        "remaining_credits": agent.credits,
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
    ranked = sorted(agents, key=lambda a: a.correct_bets / a.total_bets if a.total_bets > 0 else 0, reverse=True)
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


# --- Admin / Utility ---

@router.post("/seed-markets")
def seed_markets(db: Session = Depends(get_db)):
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


@router.delete("/markets/{market_id}")
def delete_market(market_id: str, db: Session = Depends(get_db)):
    market = db.query(Market).filter(Market.id == market_id).first()
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")
    db.delete(market)
    db.commit()
    return {"message": "Market deleted"}


@router.post("/markets/{market_id}/resolve")
def resolve_market(market_id: str, db: Session = Depends(get_db)):
    market = db.query(Market).filter(Market.id == market_id).first()
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")
    if market.status != "open":
        raise HTTPException(status_code=400, detail="Market already resolved")

    print(f"🔍 Resolving: {market.title}")

    evidence = search_resolution_evidence(market.title, market.resolution_source)
    if not evidence:
        return {"message": "No evidence found", "resolution": "UNRESOLVED"}

    result = determine_resolution(market.title, market.resolution_date, evidence)
    print(f"  📊 Resolution: {result['resolution']} (confidence: {result['confidence']})")

    if result["resolution"] == "UNRESOLVED":
        return {
            "message": "Market unresolved — not enough evidence",
            "reasoning": result["reasoning"]
        }

    market.status = f"resolved_{result['resolution'].lower()}"
    redistribute_credits(market, result["resolution"], db)
    db.commit()

    return {
        "message": f"Market resolved {result['resolution']}",
        "market": market.title,
        "resolution": result["resolution"],
        "confidence": result["confidence"],
        "reasoning": result["reasoning"]
    }


@router.post("/resolve-all")
def resolve_all_markets(db: Session = Depends(get_db)):
    markets = db.query(Market).filter(Market.status == "open").all()
    results = []

    for market in markets:
        print(f"\n🔍 Checking: {market.title}")
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