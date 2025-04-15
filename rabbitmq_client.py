import aio_pika
import aiohttp
import asyncio
import logging
import json
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('rabbitmq.log', mode='a')
    ]
)

class AsyncRabbitMQClient:
    def __init__(self, queue='hello', host='localhost', username='guest', password='guest'):
        self.queue = queue
        self.host = host
        self.username = username
        self.password = password
        self.connection = None
        self.channel = None

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        before_sleep=lambda retry_state: logger.info(
            f"重试连接，第 {retry_state.attempt_number} 次"
        )
    )
    async def connect(self):
        try:
            self.connection = await aio_pika.connect_robust(
                host=self.host,
                login=self.username,
                password=self.password,
                heartbeat=600
            )
            self.channel = await self.connection.channel()
            logger.info("成功连接到 RabbitMQ")
        except Exception as e:
            logger.info(f"连接失败: {e}")
            raise

    async def declare_queue(self, durable=True):
        try:
            await self.channel.declare_queue(self.queue, durable=durable)
            logger.info(f"队列 {self.queue} 已声明")
        except Exception as e:
            logger.info(f"声明队列失败: {e}")
            raise

    async def publish_message(self, message):
        try:
            await self.channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(message).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key=self.queue
            )
            logger.info(f"Sent: {message}")
        except Exception as e:
            logger.info(f"发送消息失败: {e}")
            raise

    async def consume_messages(self, callback):
        try:
            queue = await self.channel.declare_queue(self.queue, durable=True)
            await queue.consume(callback)
            logger.info(f"开始消费队列 {self.queue}")
        except Exception as e:
            logger.info(f"消费消息失败: {e}")
            raise

    async def close(self):
        try:
            if self.channel and not self.channel.is_closed:
                await self.channel.close()
            if self.connection and not self.connection.is_closed:
                await self.connection.close()
        except Exception:
            pass
        logger.info("连接已关闭")

    async def monitor_queue(self):
        async with aiohttp.ClientSession() as session:
            while True:
                try:
                    auth = aiohttp.BasicAuth(self.username, self.password)
                    async with session.get(
                        f"http://{self.host}:15672/api/queues/%2F/{self.queue}",
                        auth=auth
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            logger.info(
                                f"队列 {self.queue}: 消息数={data['messages']}, "
                                f"消费者数={data['consumers']}"
                            )
                        else:
                            logger.info(f"管理 API 请求失败: {response.status}")
                except Exception as e:
                    logger.info(f"管理 API 请求失败: {e}")
                await asyncio.sleep(10)