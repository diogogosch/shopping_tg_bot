from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    
    # User Preferences
    language = Column(String, default="en")
    timezone = Column(String, default="UTC")
    currency = Column(String, default="USD")
    
    # Shopping Preferences
    dietary_preferences = Column(JSON, default=list)
    favorite_stores = Column(JSON, default=list)
    budget_limit = Column(Float, nullable=True)
    
    # AI Settings
    ai_suggestions_enabled = Column(Boolean, default=True)
    price_alerts_enabled = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    shopping_lists = relationship("ShoppingList", back_populates="user")
    receipts = relationship("Receipt", back_populates="user")
    
    def to_dict(self):
        return {
            "id": self.id,
            "telegram_id": self.telegram_id,
            "username": self.username,
            "preferences": {
                "language": self.language,
                "currency": self.currency,
                "dietary_preferences": self.dietary_preferences,
                "ai_suggestions_enabled": self.ai_suggestions_enabled
            }
        }
