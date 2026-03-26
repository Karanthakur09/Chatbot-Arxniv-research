from sqlalchemy.orm import Session

from infra.db.models.user import User
from infra.auth.password import hash_password, verify_password


class AuthService:

    def __init__(self, db: Session):
        self.db = db

    def signup(self, email: str, password: str):

        existing = self.db.query(User).filter(User.email == email).first()
        if existing:
            return None, "User already exists"

        user = User(
            email=email,
            hashed_password=hash_password(password)
        )

        self.db.add(user)
        self.db.commit()

        return user, None

    def login(self, email: str, password: str):

        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            return None

        if not verify_password(password, user.hashed_password):
            return None

        return user