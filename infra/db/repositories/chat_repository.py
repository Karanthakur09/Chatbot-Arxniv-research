# from sqlalchemy.orm import Session

# from infra.db.models.message import Message


# class ChatRepository:

#     def __init__(self, db: Session):
#         self.db = db

#     def save_message(self, conversation_id: str, role: str, content: str):
#         msg = Message(
#             conversation_id=conversation_id,
#             role=role,
#             content=content
#         )
#         self.db.add(msg)
#         self.db.commit()

#     def get_last_messages(self, conversation_id: str, limit: int = 5):
#         messages = (
#             self.db.query(Message)
#             .filter(Message.conversation_id == conversation_id)
#             .order_by(Message.created_at.desc())
#             .limit(limit)
#             .all()
#         )

#         # convert to dict format (VERY IMPORTANT)
#         return [
#             {
#                 "query": m.content if m.role == "user" else "",
#                 "answer": m.content if m.role == "assistant" else ""
#             }
#             for m in reversed(messages)
#         ]
        
#     def get_messages(self, conversation_id: str):
#         return (
#             self.db.query(Message)
#             .filter(Message.conversation_id == conversation_id)
#             .order_by(Message.created_at.asc())
#             .all()
#         )

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from infra.db.models.message import Message

class ChatRepository:

    def __init__(self, db: AsyncSession):
        """Initialise with an AsyncSession instead of a Sync Session"""
        self.db = db

    async def save_message(self, conversation_id: str, role: str, content: str):
        """
        Creates and persists a new message asynchronously.
        """
        msg = Message(
            conversation_id=conversation_id,
            role=role,
            content=content
        )
        
        # 1. Add to the session
        self.db.add(msg)
        
        # 2. Await the commit (This is the 'BEFORE/AFTER' change)
        await self.db.commit()
        
        # 3. Refresh if you need to access 'msg.id' or 'msg.created_at' immediately
        await self.db.refresh(msg)
        return msg

    async def get_messages(self, conversation_id: str, limit: int = 20):
        """
        Retrieves message history for a specific conversation.
        Returns Message objects.
        """
        # 1. Create the select statement
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
        )

        # 2. Execute and get scalars (The 'BEFORE/AFTER' change)
        result = await self.db.execute(stmt)
        messages = result.scalars().all()

        return messages

    async def get_last_message(self, conversation_id: str):
        """
        Example of how to handle .first() in Async
        """
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
        )
        
        # BEFORE: .first() 
        # AFTER: execute -> scalars -> first
        result = await self.db.execute(stmt)
        return result.scalars().first()
