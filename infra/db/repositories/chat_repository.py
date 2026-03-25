from sqlalchemy.orm import Session

from infra.db.models.message import Message


class ChatRepository:

    def __init__(self, db: Session):
        self.db = db

    def save_message(self, conversation_id: str, role: str, content: str):
        msg = Message(
            conversation_id=conversation_id,
            role=role,
            content=content
        )
        self.db.add(msg)
        self.db.commit()

    def get_last_messages(self, conversation_id: str, limit: int = 5):
        return (
            self.db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
            .all()
        )