import asyncio
import json
import logging
from rabbitmq_client import AsyncRabbitMQClient

# 配置日志
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
    try:
        body = message.body.decode()
        logger.info(f"Received: {body}")
        data = json.loads(body)
        logger.debug(f"处理消息 ID: {data.get('id')}")
        await message.ack()  # 手动确认
    except Exception as e:
        logger.info(f"处理消息失败: {e}")
        await message.nack(requeue=False)  # 失败不重入队列

async def main():
    client = AsyncRabbitMQClient(queue='hello')
    try:
        await client.connect()
        await client.declare_queue(durable=True)
        
        # 启动消费者
        consumer_task = asyncio.create_task(client.consume_messages(callback))
        # 启动监控
        monitor_task = asyncio.create_task(client.monitor_queue())
        
        await asyncio.gather(consumer_task, monitor_task)
    except Exception as e:
        logger.info(f"运行失败: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())