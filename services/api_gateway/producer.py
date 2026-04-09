"""
Kafka producer instance - shared across API
"""
from infra.event_bus.kafka_producer import KafkaProducerService

kafka_producer = KafkaProducerService()
