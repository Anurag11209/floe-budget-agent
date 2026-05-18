from sqlalchemy import Column, String, Numeric, Text, Integer, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
import uuid, datetime

Base = declarative_base()

class Task(Base):
    __tablename__ = "tasks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    description = Column(Text, nullable=False)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime)
    result = Column(JSON)
    error = Column(Text)

class Loan(Base):
    __tablename__ = "loans"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    floe_loan_id = Column(String(100), unique=True, nullable=False)
    amount_usdc = Column(Numeric(18, 6), nullable=False)
    rate_apr = Column(Numeric(6, 4))
    opened_at = Column(DateTime, default=datetime.datetime.utcnow)
    repaid_at = Column(DateTime)
    status = Column(String(20), default="active")

class ApiCall(Base):
    __tablename__ = "api_calls"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    endpoint = Column(Text, nullable=False)
    cost_usdc = Column(Numeric(18, 6), nullable=False)
    response_status = Column(Integer)
    called_at = Column(DateTime, default=datetime.datetime.utcnow)
    latency_ms = Column(Integer)

class CreditEvent(Base):
    __tablename__ = "credit_events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(50), nullable=False)
    credit_remaining = Column(Numeric(18, 6))
    credit_limit = Column(Numeric(18, 6))
    extra_data = Column(JSON)   # renamed from 'metadata'
    occurred_at = Column(DateTime, default=datetime.datetime.utcnow)