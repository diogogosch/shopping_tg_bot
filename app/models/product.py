from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
from .user import Base
from datetime import datetime

class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    category = Column(String, nullable=False, index=True)
    subcategory = Column(String, nullable=True)
    
    # Product Details
    brand = Column(String, nullable=True)
    unit = Column(String, default="piece")
    barcode = Column(String, nullable=True, unique=True)
    
    # Nutritional Info
    nutritional_info = Column(JSON, nullable=True)
    
    # Price Tracking
    average_price = Column(Float, nullable=True)
    last_price = Column(Float, nullable=True)
    price_trend = Column(String, default="stable")
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    shopping_list_items = relationship("ShoppingListItem", back_populates="product")
    receipt_items = relationship("ReceiptItem", back_populates="product")

class ShoppingList(Base):
    __tablename__ = "shopping_lists"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, default="My Shopping List")
    
    # List Status
    is_active = Column(Boolean, default=True)
    is_completed = Column(Boolean, default=False)
    
    # Smart Features
    estimated_total = Column(Float, nullable=True)
    suggested_store = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="shopping_lists")
    items = relationship("ShoppingListItem", back_populates="shopping_list", cascade="all, delete-orphan")

class ShoppingListItem(Base):
    __tablename__ = "shopping_list_items"
    
    id = Column(Integer, primary_key=True, index=True)
    shopping_list_id = Column(Integer, ForeignKey("shopping_lists.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    
    # Item Details
    quantity = Column(Float, default=1.0)
    unit = Column(String, default="piece")
    notes = Column(String, nullable=True)
    
    # Status
    is_purchased = Column(Boolean, default=False)
    priority = Column(Integer, default=1)
    
    # AI Suggestions
    is_ai_suggested = Column(Boolean, default=False)
    suggestion_reason = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    purchased_at = Column(DateTime, nullable=True)
    
    # Relationships
    shopping_list = relationship("ShoppingList", back_populates="items")
    product = relationship("Product", back_populates="shopping_list_items")
