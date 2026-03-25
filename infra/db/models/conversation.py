import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime
from sqlalchemy.sql import func

from infra.db.models.base import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))

    title = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())