from infra.db.session import engine
from infra.db.models.base import Base

# import all models (IMPORTANT)
from infra.db.models.user import User
from infra.db.models.conversation import Conversation
from infra.db.models.message import Message


def init_db():
    Base.metadata.create_all(bind=engine)