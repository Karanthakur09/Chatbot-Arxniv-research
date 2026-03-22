from fastapi import FastAPI
from services.api_gateway.routes.search import router as search_router
from services.api_gateway.routes.chat import router as chat_router


app = FastAPI(title="Enterprise Chatbot")

app.include_router(search_router)
app.include_router(chat_router)