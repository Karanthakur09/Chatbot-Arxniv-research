import uuid
from sqlalchemy.orm import Session

from infra.db.models.conversation import Conversation


class ConversationRepository:

    def __init__(self, db: Session):
        self.db = db

    def create_conversation(self, user_id: str, title: str = None):
        conv = Conversation(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title=title or "New Chat"
        )
        self.db.add(conv)
        self.db.commit()
        return conv

    def get_conversation(self, conversation_id: str):
        return (
            self.db.query(Conversation)
            .filter(Conversation.id == conversation_id)
            .first()
        )