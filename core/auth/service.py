# from sqlalchemy.orm import Session

# from infra.db.models.user import User
# from infra.auth.password import hash_password, verify_password


# class AuthService:

#     def __init__(self, db: Session):
#         self.db = db

#     def signup(self, email: str, password: str):

#         existing = self.db.query(User).filter(User.email == email).first()
#         if existing:
#             return None, "User already exists"

#         user = User(
#             email=email,
#             hashed_password=hash_password(password)
#         )

#         self.db.add(user)
#         self.db.commit()

#         return user, None

#     def login(self, email: str, password: str):

#         user = self.db.query(User).filter(User.email == email).first()
#         if not user:
#             return None

#         if not verify_password(password, user.hashed_password):
#             return None

#         return user

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infra.db.models.user import User
from infra.auth.password import hash_password, verify_password

class AuthService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def signup(self, email: str, password: str):
        # 1. New Async Select Style
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        existing = result.scalars().first()

        if existing:
            return None, "User already exists"

        # 2. Create User
        user = User(
            email=email,
            hashed_password=hash_password(password)
        )

        # 3. Async Save
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user) # Important: Refresh to get the user ID/created_at

        return user, None

    async def login(self, email: str, password: str):
        # 4. Async Fetch User
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        user = result.scalars().first()

        if not user:
            return None

        # 5. Verify (Password hashing is usually sync/CPU bound, so no await needed here)
        if not verify_password(password, user.hashed_password):
            return None

        return user
