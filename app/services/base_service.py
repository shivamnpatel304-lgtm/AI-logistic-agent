"""
Base Service Definition for Business Logic and Database Persistence.
Applies:
- Abstraction: Abstract base class BaseService[T] defines the standard persistence interface.
- Inheritance: All domain services inherit common CRUD, query, and transaction logic.
- Encapsulation: Protects database session boundaries, commit/rollback, and query construction.
"""
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Type, Optional, List, Any
from sqlalchemy.orm import Session
from app.models.base import BaseEntity

ModelType = TypeVar("ModelType", bound=BaseEntity)


class BaseService(ABC, Generic[ModelType]):
    """
    Abstract generic base service providing standardized data-access and business routines.
    Subclassed by OrderService, InventoryService, ProductService, WarehouseService, LogisticsService.
    """

    def __init__(self, model_class: Type[ModelType]):
        self._model_class = model_class

    @property
    def model_class(self) -> Type[ModelType]:
        """Encapsulated accessor for the underlying entity class."""
        return self._model_class

    def get_by_id(self, db: Session, entity_id: int) -> Optional[ModelType]:
        """Fetches an entity by primary key."""
        return db.query(self._model_class).filter(self._model_class.id == entity_id).first()

    def get_all(self, db: Session, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Fetches all entities with pagination."""
        return db.query(self._model_class).offset(skip).limit(limit).all()

    def count(self, db: Session) -> int:
        """Returns total entity count."""
        return db.query(self._model_class).count()

    def save(self, db: Session, entity: ModelType) -> ModelType:
        """
        Encapsulates persistence, transaction commit, and refresh.
        """
        db.add(entity)
        db.commit()
        db.refresh(entity)
        return entity

    def delete(self, db: Session, entity_id: int) -> bool:
        """
        Safely deletes an entity by primary key.
        """
        entity = self.get_by_id(db, entity_id)
        if not entity:
            return False
        db.delete(entity)
        db.commit()
        return True
