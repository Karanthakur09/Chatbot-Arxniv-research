# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker

# from shared.config import settings

# DATABASE_URL = settings.DATABASE_URL

# engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# SessionLocal = sessionmaker(
#     autocommit=False,
#     autoflush=False,
#     bind=engine
# )

#  Async Session with DB
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from shared.config import settings
import ssl

DATABASE_URL = settings.DATABASE_URL.replace(
    "postgresql://", "postgresql+asyncpg://"
)

# Remove sslmode from URL if present and handle it via connect_args
if "sslmode" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.split("?")[0]

# Configure asyncpg with SSL if needed
connect_args = {}
if settings.DATABASE_URL and "sslmode=require" in settings.DATABASE_URL:
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    connect_args["ssl"] = ssl_context

engine = create_async_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    connect_args=connect_args
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False
)