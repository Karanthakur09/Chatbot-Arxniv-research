import os
from dotenv import load_dotenv

load_dotenv()

class Settings:

    # COURTLISTENER_API = os.getenv(
    #     "COURTLISTENER_API",
    #     "https://www.courtlistener.com/api/rest/v4/opinions/"
    # )

    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

    QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))

    DATA_DIR = os.getenv("DATA_DIR", "data")
    # COURTLISTENER_API_KEY = os.getenv("COURTLISTENER_API_KEY")
    
    # R2 config
    R2_ENDPOINT = os.getenv("R2_ENDPOINT")
    R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY")
    R2_SECRET_KEY = os.getenv("R2_SECRET_KEY")
    R2_BUCKET = os.getenv("R2_BUCKET", "legal-ai")
    
    
    ARXIV_BASE_URL: str = os.getenv("ARXIV_BASE_URL")
    ARXIV_QUERY: str = os.getenv("ARXIV_QUERY", "all:ai")

    ARXIV_BATCH_SIZE: int = int(os.getenv("ARXIV_BATCH_SIZE", 100))

    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", 30))
    ARXIV_RATE_LIMIT_SECONDS: int = int(os.getenv("ARXIV_RATE_LIMIT_SECONDS", 3))
    
    CONTEXT_MAX_TOKENS = int(os.getenv('CONTEXT_MAX_TOKENS', 6000))
    # GOOGLE api key
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    GEMINI_MODEL = os.getenv('GEMINI_MODEL')
    
    LLM_TEMPERATURE = float(os.getenv('LLM_TEMPERATURE', 0.2))
    LLM_MAX_TOKENS = int(os.getenv('LLM_MAX_TOKENS', 500))
    
    # openAI router
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
    OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat")
    
    
settings = Settings()