from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from infra.db.session import SessionLocal
from infra.db.repositories.conversation_repository import ConversationRepository
from infra.db.repositories.chat_repository import ChatRepository
from services.api_gateway.dependencies.auth import get_current_user

router = APIRouter(prefix="/conversations", tags=["conversations"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("")
def list_conversations(
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    repo = ConversationRepository(db)
    conversations = repo.list_conversations(user_id)

    return [
        {
            "id": c.id,
            "title": c.title,
            "created_at": c.created_at
        }
        for c in conversations
    ]


@router.get("/{conversation_id}/messages")
def get_messages(
    conversation_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    repo = ChatRepository(db)
    messages = repo.get_messages(conversation_id)

    return [
        {
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at
        }
        for m in messages
    ]


@router.patch("/{conversation_id}")
def rename_conversation(
    conversation_id: str,
    title: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    repo = ConversationRepository(db)
    conv = repo.rename_conversation(conversation_id, title)

    return {"id": conv.id, "title": conv.title}


@router.delete("/{conversation_id}")
def delete_conversation(
    conversation_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    repo = ConversationRepository(db)
    repo.delete_conversation(conversation_id)

    return {"message": "Deleted successfully"}