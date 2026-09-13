"""
Distributor / Client database model.
Applies:
- Inheritance: Inherits common columns and behaviors from BaseEntity.
- Encapsulation: Encapsulates client tier privileges and SLA weights.
"""
from sqlalchemy import Column, String, Float, Boolean
from sqlalchemy.orm import relationship
from app.models.base import BaseEntity


class Distributor(BaseEntity):
    __tablename__ = "distributors"

    code = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    contact_email = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    address = Column(String(500), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    tier = Column(String(50), default="Standard")  # Standard, Gold, VIP
    is_active = Column(Boolean, default=True)

    # Relationships
    orders = relationship("Order", back_populates="distributor")

    @property
    def is_priority_client(self) -> bool:
        """Encapsulated check for VIP or Gold tier standing."""
        return (self.tier or "").strip().upper() in ("VIP", "GOLD")

    @property
    def tier_normalized(self) -> str:
        return (self.tier or "STANDARD").strip().upper()

    def __repr__(self) -> str:
        return f"<Distributor(code='{self.code}', tier='{self.tier}')>"
