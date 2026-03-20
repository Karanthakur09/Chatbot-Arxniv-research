import os
from dotenv import load_dotenv

load_dotenv()

class Settings:

    COURTLISTENER_API = os.getenv(
        "COURTLISTENER_API",
        "https://www.courtlistener.com/api/rest/v4/opinions/"
    )

    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

    QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))

    DATA_DIR = os.getenv("DATA_DIR", "data")
    COURTLISTENER_API_KEY = os.getenv("COURTLISTENER_API_KEY")

settings = Settings()