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
    
    def list_conversations(self, user_id: str):
        return (
            self.db.query(Conversation)
            .filter(Conversation.user_id == user_id)
            .order_by(Conversation.created_at.desc())
            .all()
        )


    def delete_conversation(self, conversation_id: str):
        conv = self.get_conversation(conversation_id)
        if conv:
            self.db.delete(conv)
            self.db.commit()


    def rename_conversation(self, conversation_id: str, title: str):
        conv = self.get_conversation(conversation_id)
        if conv:
            conv.title = title
            self.db.commit()
            return conv    