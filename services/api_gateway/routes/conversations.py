# from fastapi import APIRouter, Depends
# from sqlalchemy.orm import Session

# from infra.db.session import SessionLocal
# from infra.db.repositories.conversation_repository import ConversationRepository
# from infra.db.repositories.chat_repository import ChatRepository
# from services.api_gateway.dependencies.auth import get_current_user
# from services.api_gateway.dependencies.db import get_db

# router = APIRouter(prefix="/conversations", tags=["conversations"])




# @router.get("")
# async def list_conversations(
#     user_id: str = Depends(get_current_user),
#     db: AsyncSession = Depends(get_db)
# ):
#     repo = ConversationRepository(db)
#     conversations = repo.list_conversations(user_id)

#     return [
#         {
#             "id": c.id,
#             "title": c.title,
#             "created_at": c.created_at
#         }
#         for c in conversations
#     ]


# @router.get("/{conversation_id}/messages")
# def get_messages(
#     conversation_id: str,
#     user_id: str = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     repo = ChatRepository(db)
#     messages = repo.get_messages(conversation_id)

#     return [
#         {
#             "role": m.role,
#             "content": m.content,
#             "created_at": m.created_at
#         }
#         for m in messages
#     ]


# @router.patch("/{conversation_id}")
# def rename_conversation(
#     conversation_id: str,
#     title: str,
#     user_id: str = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     repo = ConversationRepository(db)
#     conv = repo.rename_conversation(conversation_id, title)

#     return {"id": conv.id, "title": conv.title}


# @router.delete("/{conversation_id}")
# def delete_conversation(
#     conversation_id: str,
#     user_id: str = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     repo = ConversationRepository(db)
#     repo.delete_conversation(conversation_id)

#     return {"message": "Deleted successfully"}


from fastapi import APIRouter, Depends
# 1. Import AsyncSession instead of Session
from sqlalchemy.ext.asyncio import AsyncSession 

# 2. Update your repository imports
from infra.db.repositories.conversation_repository import ConversationRepository
from infra.db.repositories.chat_repository import ChatRepository
from services.api_gateway.dependencies.auth import get_current_user
from services.api_gateway.dependencies.db import get_db

router = APIRouter(prefix="/conversations", tags=["conversations"])

@router.get("")
async def list_conversations(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db) # Updated to Async
):
    repo = ConversationRepository(db)
    # 3. Add 'await' (Your repository methods must now be 'async def')
    conversations = await repo.list_conversations(user_id)

    return [
        {
            "id": c.id,
            "title": c.title,
            "created_at": c.created_at
        }
        for c in conversations
    ]

@router.get("/{conversation_id}/messages")
async def get_messages( # Changed to 'async def'
    conversation_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    repo = ChatRepository(db)
    # 4. Add 'await'
    messages = await repo.get_messages(conversation_id)

    return [
        {
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at
        }
        for m in messages
    ]

@router.patch("/{conversation_id}")
async def rename_conversation( # Changed to 'async def'
    conversation_id: str,
    title: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    repo = ConversationRepository(db)
    # 5. Add 'await'
    conv = await repo.rename_conversation(conversation_id, title)

    return {"id": conv.id, "title": conv.title}


@router.delete("/{conversation_id}")
async def delete_conversation( # Changed to 'async def'
    conversation_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    repo = ConversationRepository(db)
    # 6. Add 'await'
    await repo.delete_conversation(conversation_id)

    return {"message": "Deleted successfully"}
