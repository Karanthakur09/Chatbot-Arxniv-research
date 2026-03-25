import uuid
from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func

from infra.db.models.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())