import aio_pika
import asyncio
import logging
import json
from tenacity import retry, stop_after_attempt, wait_exponential

# 自定义日志处理器，过滤 aiormq ERROR
class RabbitMQLogFilter(logging.Filter):
    def filter(self, record):
        if record.name.startswith('aiormq') and record.levelno == logging.ERROR:
            return False
        return True

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
for handler in logging.getLogger().handlers:
    handler.addFilter(RabbitMQLogFilter())
logging.getLogger('aio_pika').setLevel(logging.WARNING)
logging.getLogger('aiormq').setLevel(logging.WARNING)

class AsyncRabbitMQClient:
    def __init__(self, queue='hello', url='amqp://guest:guest@localhost:5672//?heartbeat=30'):
        self.queue = queue
        self.url = url
        self.connection = None
        self.channel = None
        self.queue_obj = None

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def connect(self):
        try:
            logger.info("尝试连接 RabbitMQ...")
            self.connection = await aio_pika.connect_robust(self.url)
            self.channel = await self.connection.channel()
            logger.info("RabbitMQ 连接成功")
        except Exception as e:
            logger.info(f"连接失败，重试中: {e}")
            logger.info("重试连接")
            raise

    async def declare_queue(self, durable=True):
        try:
            self.queue_obj = await self.channel.declare_queue(self.queue, durable=durable)
            logger.info(f"队列 {self.queue} 已声明")
        except Exception as e:
            logger.info(f"声明队列失败: {e}")
            raise

    async def publish_message(self, message):
        try:
            if isinstance(message, dict):
                message = json.dumps(message).encode()
            await self.channel.default_exchange.publish(
                aio_pika.Message(body=message, delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
                routing_key=self.queue
            )
            logger.info(f"Sent: {message.decode()}")
        except Exception as e:
            logger.info(f"发布消息失败: {e}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5))
    async def consume_messages(self, callback):
        try:
            if not self.queue_obj:
                await self.declare_queue(durable=True)
            async with self.queue_obj.iterator() as queue_iter:
                async for message in queue_iter:
                    try:
                        logger.info(f"Received: {message.body.decode()}")
                        await callback(message)
                    except Exception as e:
                        logger.info(f"处理消息失败: {e}")
        except aio_pika.exceptions.AMQPConnectionError as e:
            logger.info(f"连接中断: {e}")
            logger.info("连接已关闭")
            raise
        except Exception as e:
            logger.info(f"消费消息失败: {e}")
            raise

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def monitor_queue(self):
        try:
            while True:
                if not self.queue_obj:
                    await self.declare_queue(durable=True)
                queue_state = await self.queue_obj.get_queue_state()
                logger.debug(f"队列状态: {queue_state}")
                await asyncio.sleep(5)
        except aio_pika.exceptions.AMQPConnectionError as e:
            logger.info(f"监控队列中断: {e}")
            logger.info("重试连接")
            raise
        except Exception as e:
            logger.info(f"监控队列失败: {e}")
            raise

    async def close(self):
        try:
            if self.channel:
                await self.channel.close()
            if self.connection:
                await self.connection.close()
            logger.info("连接已关闭")
            self.channel = None
            self.connection = None
            self.queue_obj = None
        except Exception as e:
            logger.info(f"关闭连接失败: {e}")