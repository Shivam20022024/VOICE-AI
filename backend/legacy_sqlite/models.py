from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.sql import func
from .db import Base

class Call(Base):
    __tablename__ = "calls"

    call_id = Column(String, primary_key=True, index=True)
    customer_id = Column(String)
    sentiment = Column(String)
    emotion = Column(String)
    summary = Column(Text)
    transcript = Column(Text)
    tags = Column(Text)       # JSON stored as text
    analysis = Column(Text)   # JSON stored as text
    created_at = Column(DateTime, server_default=func.now())
