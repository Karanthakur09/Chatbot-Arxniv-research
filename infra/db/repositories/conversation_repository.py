# import uuid
# from sqlalchemy.orm import Session

# from infra.db.models.conversation import Conversation


# class ConversationRepository:

#     def __init__(self, db: Session):
#         self.db = db

#     def create_conversation(self, user_id: str, title: str = None):
#         conv = Conversation(
#             id=str(uuid.uuid4()),
#             user_id=user_id,
#             title=title or "New Chat"
#         )
#         self.db.add(conv)
#         self.db.commit()
#         return conv

#     def get_conversation(self, conversation_id: str):
#         return (
#             self.db.query(Conversation)
#             .filter(Conversation.id == conversation_id)
#             .first()
#         )
    
#     def list_conversations(self, user_id: str):
#         return (
#             self.db.query(Conversation)
#             .filter(Conversation.user_id == user_id)
#             .order_by(Conversation.created_at.desc())
#             .all()
#         )


#     def delete_conversation(self, conversation_id: str):
#         conv = self.get_conversation(conversation_id)
#         if conv:
#             self.db.delete(conv)
#             self.db.commit()


#     def rename_conversation(self, conversation_id: str, title: str):
#         conv = self.get_conversation(conversation_id)
#         if conv:
#             conv.title = title
#             self.db.commit()
#             return conv    

import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from infra.db.models.conversation import Conversation

class ConversationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_conversation(self, user_id: str, title: str = None):
        conv = Conversation(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title=title or "New Chat"
        )
        self.db.add(conv)
        await self.db.commit()      # <--- Await the "Save"
        await self.db.refresh(conv) # <--- Await the "Update"
        return conv

    async def get_conversation(self, conversation_id: str):
        # 1. Create the "Order Form" (stmt)
        stmt = select(Conversation).where(Conversation.id == conversation_id)
        
        # 2. Send the order and wait (execute)
        result = await self.db.execute(stmt)
        
        # 3. Open the delivery box (scalars) and take the first item
        return result.scalars().first()
    
    async def list_conversations(self, user_id: str):
        stmt = (
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def delete_conversation(self, conversation_id: str):
        conv = await self.get_conversation(conversation_id)
        if conv:
            await self.db.delete(conv)
            await self.db.commit()

    async def rename_conversation(self, conversation_id: str, title: str):
        conv = await self.get_conversation(conversation_id)
        if conv:
            conv.title = title
            await self.db.commit()
            await self.db.refresh(conv)
            return conv
