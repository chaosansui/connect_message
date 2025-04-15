import asyncio
import json
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

async def callback(message):
    async with message.process():
        body = json.loads(message.body.decode())
        logger.info(f"Received: {body}")

async def main():
    client = AsyncRabbitMQClient(queue='hello')
    try:
        await client.connect()
        await client.declare_queue(durable=True)
        await client.consume_messages(callback)
        monitor_task = asyncio.create_task(client.monitor_queue())
        await asyncio.Event().wait()  # 保持运行
    except Exception as e:
        logger.info(f"操作失败: {e}")
    finally:
        monitor_task.cancel()
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())