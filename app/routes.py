from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from .database import get_db
from .models import Agent, Market, Bet
from .polymarket import fetch_polymarket_markets
import uuid

router = APIRouter()

# --- Schemas ---

class AgentRegister(BaseModel):
    name: str
    wallet_address: str

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

# --- Routes ---

@router.post("/register")
def register_agent(agent: AgentRegister, db: Session = Depends(get_db)):
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
        "message": "Agent registered successfully",
        "agent_id": new_agent.id,
        "credits_granted": 100.0,
        "sol_fee_paid": 0.05,
        "wallet": agent.wallet_address
    }

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
    markets = db.query(Market).filter(Market.status == "open").all()
    return [
        {
            "id": m.id,
            "title": m.title,
            "category": m.category,
            "resolution_date": m.resolution_date,
            "resolution_source": m.resolution_source,
            "created_by": m.created_by,
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
        "yes_bets": [b for b in bets if b.position == "YES"],
        "no_bets": [b for b in bets if b.position == "NO"]
    }

@router.post("/markets/{market_id}/bet")
def place_bet(market_id: str, bet: BetPlace, db: Session = Depends(get_db)):
    market = db.query(Market).filter(Market.id == market_id).first()
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")
    if market.status != "open":
        raise HTTPException(status_code=400, detail="Market is closed")
    
    agent = db.query(Agent).filter(Agent.id == bet.agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.credits < bet.amount:
        raise HTTPException(status_code=400, detail="Insufficient credits")
    if bet.position not in ["YES", "NO"]:
        raise HTTPException(status_code=400, detail="Position must be YES or NO")
    if not bet.reasoning or len(bet.reasoning) < 20:
        raise HTTPException(status_code=400, detail="Reasoning must be at least 20 characters")

    # deduct credits + platform fee
    platform_fee = bet.amount * 0.02
    agent.credits -= (bet.amount + platform_fee)
    agent.total_bets += 1

    # update pools
    if bet.position == "YES":
        market.yes_pool += bet.amount
    else:
        market.no_pool += bet.amount

    new_bet = Bet(
        market_id=market_id,
        agent_id=bet.agent_id,
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