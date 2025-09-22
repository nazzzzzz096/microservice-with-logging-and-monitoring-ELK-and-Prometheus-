from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)  # reference to user_service
    product = Column(String(255), nullable=False)
    quantity = Column(Integer, nullable=False)
    status = Column(String(50), default="pending")