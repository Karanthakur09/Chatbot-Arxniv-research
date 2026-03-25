import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, Text
from sqlalchemy.sql import func

from infra.db.models.base import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    conversation_id = Column(String, ForeignKey("conversations.id"))
    role = Column(String)  # user / assistant
    content = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())