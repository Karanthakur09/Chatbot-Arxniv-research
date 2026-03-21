from fastapi import FastAPI
from services.api_gateway.routes.search import router as search_router

app = FastAPI(title="Enterprise Chatbot")

app.include_router(search_router)