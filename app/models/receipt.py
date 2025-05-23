from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from .user import Base
from datetime import datetime

class Receipt(Base):
    __tablename__ = "receipts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Receipt Details
    store_name = Column(String, nullable=True)
    store_address = Column(String, nullable=True)
    receipt_number = Column(String, nullable=True)
    
    # Financial Info
    total_amount = Column(Float, nullable=False)
    tax_amount = Column(Float, nullable=True)
    currency = Column(String, default="USD")
    
    # Processing Info
    ocr_confidence = Column(Float, nullable=True)
    processing_status = Column(String, default="pending")
    raw_text = Column(Text, nullable=True)
    
    # Timestamps
    purchase_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="receipts")
    items = relationship("ReceiptItem", back_populates="receipt", cascade="all, delete-orphan")

class ReceiptItem(Base):
    __tablename__ = "receipt_items"
    
    id = Column(Integer, primary_key=True, index=True)
    receipt_id = Column(Integer, ForeignKey("receipts.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    
    # Item Details
    item_name = Column(String, nullable=False)
    quantity = Column(Float, default=1.0)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    
    # Processing Info
    confidence_score = Column(Float, nullable=True)
    
    # Relationships
    receipt = relationship("Receipt", back_populates="items")
    product = relationship("Product", back_populates="receipt_items")
