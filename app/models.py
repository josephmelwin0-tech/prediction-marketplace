from sqlalchemy import Column, String, Float, Integer, DateTime, Text
from sqlalchemy.sql import func
from .database import Base
import uuid

class Agent(Base):
    __tablename__ = "agents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    wallet_address = Column(String, nullable=False, unique=True)
    credits = Column(Float, default=100.0)
    sol_paid = Column(Float, default=0.05)
    registered_at = Column(DateTime, default=func.now())
    total_bets = Column(Integer, default=0)
    correct_bets = Column(Integer, default=0)

class Market(Base):
    __tablename__ = "markets"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    category = Column(String, nullable=False)
    resolution_date = Column(String, nullable=False)
    resolution_source = Column(String, nullable=False)
    created_by = Column(String, nullable=False)
    status = Column(String, default="open")
    created_at = Column(DateTime, default=func.now())
    yes_pool = Column(Float, default=0.0)
    no_pool = Column(Float, default=0.0)

class Bet(Base):
    __tablename__ = "bets"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    market_id = Column(String, nullable=False)
    agent_id = Column(String, nullable=False)
    agent_name = Column(String, nullable=False)
    position = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    reasoning = Column(Text, nullable=False)
    sol_fee_paid = Column(Float, default=0.0005)
    placed_at = Column(DateTime, default=func.now())