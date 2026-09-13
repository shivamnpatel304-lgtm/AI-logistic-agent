"""
Base Model Definition for all SQLAlchemy entities in the AI Logistics Agent system.
Applies:
- Inheritance: All concrete models inherit common attributes (id, timestamps) and utility methods.
- Encapsulation: Protects internal dictionary conversion and provides domain validation hooks.
- Abstraction: Defines abstract entity contract and serialization interface.
"""
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import Column, Integer, DateTime
from app.database.connection import Base


class BaseEntity(Base):
    """
    Abstract declarative base entity providing common identity and auditing fields.
    Inherited by all domain models (Order, Product, Warehouse, Distributor, Inventory, Vehicle).
    """
    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self, exclude: Optional[set] = None) -> Dict[str, Any]:
        """
        Encapsulates object state serialization into a standard Python dictionary.
        """
        exclude_set = exclude or set()
        result = {}
        for column in self.__table__.columns:
            if column.name not in exclude_set:
                val = getattr(self, column.name)
                if isinstance(val, datetime):
                    val = val.isoformat()
                result[column.name] = val
        return result

    def validate(self) -> None:
        """
        Domain validation hook to be optionally overridden by subclasses.
        Ensures entity state consistency before persistence.
        """
        pass

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id})>"
