import asyncio
import logging
from rabbitmq_client import AsyncRabbitMQClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('rabbitmq.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)

async def main():
    client = AsyncRabbitMQClient(queue='hello')
    try:
        await client.connect()
        await client.declare_queue(durable=True)
        message = {"id": 1, "content": "Hello, RabbitMQ!"}
        await client.publish_message(message)
    except Exception as e:
        logger.info(f"操作失败: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())