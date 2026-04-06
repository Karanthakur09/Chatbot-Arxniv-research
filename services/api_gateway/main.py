from fastapi import FastAPI
from services.api_gateway.routes.chat import router as chat_router
from services.api_gateway.routes.auth import router as auth_router
from services.api_gateway.routes.conversations import router as conv_router
from infra.event_bus.kafka_producer import KafkaProducerService

app = FastAPI(title="Enterprise Chatbot")

#Kafka integeration 
kafka_producer = KafkaProducerService()

@app.on_event("startup")
async def startup():
    await kafka_producer.start()

@app.on_event("shutdown")
async def shutdown():
    await kafka_producer.stop()


# app.include_router(search_router)
app.include_router(chat_router)
app.include_router(auth_router)
app.include_router(conv_router)