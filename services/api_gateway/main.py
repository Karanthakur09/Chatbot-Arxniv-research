from fastapi import FastAPI
from services.api_gateway.routes.chat import router as chat_router
from services.api_gateway.routes.auth import router as auth_router
from services.api_gateway.routes.conversations import router as conv_router

app = FastAPI(title="Enterprise Chatbot")

# app.include_router(search_router)
app.include_router(chat_router)
app.include_router(auth_router)
app.include_router(conv_router)