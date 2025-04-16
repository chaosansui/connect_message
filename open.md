RabbitMQ 测试框架文档
文档介绍了一个基于 macOS Homebrew 环境的 RabbitMQ 测试框架，包含主测试脚本（test.py）、客户端库（rabbitmq_client.py）、发送脚本（send.py）和接收脚本（receive.py）。框架用于验证 RabbitMQ 的消息发送、接收、持久化、高并发等功能，确保 rabbitmq.log 无 ERROR，仅记录“连接已关闭”日志。
本文档说明了各文件的关系、功能，以及如何修改或接入代码，方便其他开发者使用或扩展。
框架概述
设计目标

自动化测试：无需 sudo 密码，适配 Homebrew 环境，自动管理 RabbitMQ 生命周期。
高可靠性：精准测试消息传递、错误处理和并发场景。
易于扩展：模块化设计，支持添加新测试用例。
清晰日志：生成 test.log 和 rabbitmq.log，便于调试。

测试用例

多条消息：验证发送和接收多条消息。
持久化：测试 RabbitMQ 重启后消息保留。
多消费者：多个消费者处理消息。
连接失败：验证连接错误时的重试机制。
管理 API 失败：测试禁用管理插件时的行为。
日志完整性：确保日志一致性。
高并发：测试大量消息并发发送。
队列积压：验证消息积压处理。

文件关系

test.py：主测试脚本，协调所有测试用例，管理 RabbitMQ 启动/停止，记录结果到 test.log。
rabbitmq_client.py：核心客户端库，提供异步 RabbitMQ 操作（连接、声明队列、发送/接收消息、监控队列）。
send.py：消息发送脚本，使用 rabbitmq_client.py 向队列发送单条消息。
receive.py：消息接收脚本，消费队列消息并记录到 rabbitmq.log。
日志文件：
rabbitmq.log：记录消息发送、接收、连接状态，确保无 ERROR。
test.log：记录测试过程、命令输出，便于调试。


临时文件：
send_high.py：高并发测试生成的临时发送脚本。



关系图：
test.py
├── 调用 rabbitmq_client.py（启动/停止 RabbitMQ，管理队列）
├── 执行 send.py（发送消息）
├── 执行 receive.py（接收消息）
├── 生成 send_high.py（高并发测试）
├── 输出 test.log（测试日志）
└── 输出 rabbitmq.log（消息日志）

文件详情
1. test.py
功能：

定义并运行所有测试用例。
管理 RabbitMQ 生命周期（启动、停止、清理）。
提供命令行参数（--skip-slow、--test）支持灵活测试。
确保无 sudo 依赖，自动调整权限。
记录详细日志到 test.log。

关键特性：

模块化：测试用例存储在字典中，便于添加新测试。
健壮性：动态检测 Homebrew 路径，多次验证 RabbitMQ 状态。
可扩展：支持运行单个测试（--test "多条消息"）。
日志：支持 DEBUG 模式，记录命令输出。

如何修改：

添加测试用例：在 tests 字典中添加新条目，例如：tests["新测试"] = (test_new_feature, {"expect_received": True})

定义对应的测试函数：def test_new_feature():
    # 测试逻辑
    return check_log(expect_received=True)


调整超时：修改 ensure_rabbitmq_running() 或 stop_rabbitmq() 的 time.sleep 值，例如将启动等待从 30 秒改为 20 秒：time.sleep(20)


自定义路径：在 get_homebrew_prefix() 中添加特定路径：commands.append(['/custom/path/rabbitmq-server', '-detached'])



如何接入：

运行完整测试：python test.py


运行单个测试：python test.py --test "持久化"


跳过慢速测试：python test.py --skip-slow


启用调试日志：PYTHON_LOGGING_LEVEL=DEBUG python test.py



2. rabbitmq_client.py
功能：

提供异步 RabbitMQ 客户端，封装连接、队列声明、消息发送/接收、队列监控。
支持重试机制（tenacity），确保连接稳定性。
记录操作到 rabbitmq.log，失败记录为 INFO。

关键特性：

异步操作：基于 aio_pika，支持高并发。
非 SSL 监控：使用 http://localhost:15672 访问管理 API。
无 Prometheus：移除端口依赖，避免冲突。
日志友好：确保无 ERROR，仅记录“连接已关闭”。

如何修改：

更改队列：修改默认队列名称：def __init__(self, queue='new_queue', ...):


调整重试：修改 connect() 的重试策略，例如尝试 10 次：@retry(stop=stop_after_attempt(10), ...)


添加功能：扩展方法，例如批量发送：async def publish_batch(self, messages):
    for msg in messages:
        await self.publish_message(msg)



如何接入：

在新脚本中使用客户端：from rabbitmq_client import AsyncRabbitMQClient
async def main():
    client = AsyncRabbitMQClient(queue='hello')
    await client.connect()
    await client.publish_message({"id": 1, "content": "Test"})
    await client.close()


集成到现有系统：将 rabbitmq_client.py 复制到项目，导入并调用。

3. send.py
功能：

使用 rabbitmq_client.py 发送单条消息到 hello 队列。
记录发送日志到 rabbitmq.log。

关键特性：

简单可靠，适合测试单条消息场景。
支持错误重试，失败记录为 INFO。

如何修改：

自定义消息：修改发送内容：message = {"id": 1, "content": "Custom Message"}


批量发送：添加循环：for i in range(10):
    await client.publish_message({"id": i, "content": f"Message {i}"})



如何接入：

直接运行：python send.py


嵌入其他脚本：复制 main() 逻辑，调用 AsyncRabbitMQClient。

4. receive.py
功能：

消费 hello 队列的消息，记录到 rabbitmq.log。
异步监控队列状态（消息数、消费者数）。

关键特性：

稳定消费，处理消息持久化。
监控日志为 INFO，避免 ERROR。

如何修改：

自定义回调：修改 callback() 处理逻辑：async def callback(message):
    async with message.process():
        body = json.loads(message.body.decode())
        logger.info(f"Processed: {body['content']}")


调整监控：更改 monitor_queue() 间隔：await asyncio.sleep(5)  # 从 10 秒改为 5 秒



如何接入：

运行消费者：python receive.py


集成到服务：复制 main() 逻辑，运行在异步环境中。

修改与接入指南
前提条件

环境：
macOS，安装 Homebrew。
RabbitMQ（建议 4.0.8+）：brew install rabbitmq


Python 3.9+，安装依赖：pip install aio-pika aiohttp tenacity




权限：
确保 RabbitMQ 数据目录可写：chmod -R u+rwX /opt/homebrew/var/lib/rabbitmq


或根据实际路径：brew --prefix rabbitmq




管理插件：
启用管理 API：rabbitmq-plugins enable rabbitmq_management





修改代码

添加新测试：
在 test.py 的 tests 字典中添加：tests["自定义测试"] = (test_custom, {"expect_received": True})


定义测试函数：def test_custom():
    receiver = subprocess.Popen(['python', 'receive.py'])
    processes.append(receiver)
    time.sleep(3)
    success, msg = run_command(['python', 'send.py'])
    if not success:
        return False, msg
    return check_log(expect_received=True)




调整参数：
修改超时（test.py）：success, msg = run_command(cmd, timeout=30)  # 改为 20 秒


更改队列（rabbitmq_client.py）：self.queue = 'custom_queue'




自定义日志：
在 rabbitmq_client.py 中添加日志：logger.info(f"队列操作: {operation}")


修改 test.py 日志格式：format='%(asctime)s - [%(levelname)s] - %(message)s'





接入代码

独立运行：
克隆项目目录，包含所有文件。
运行测试：python test.py


运行单个脚本：python send.py
python receive.py




集成到项目：
客户端库：
复制 rabbitmq_client.py 到项目。
示例：from rabbitmq_client import AsyncRabbitMQClient
import asyncio
async def send_message():
    client = AsyncRabbitMQClient(queue='hello')
    await client.connect()
    await client.publish_message({"id": 1, "content": "Test"})
    await client.close()
asyncio.run(send_message())




发送/接收：
复制 send.py 或 receive.py，调整消息或回调。
示例：async def custom_receive():
    client = AsyncRabbitMQClient(queue='hello')
    await client.connect()
    async def callback(message):
        async with message.process():
            print(message.body.decode())
    await client.consume_messages(callback)






扩展测试：
使用 test.py 框架：
复制 test.py，添加新测试。
运行：python test.py --test "新测试"




自定义日志路径：RotatingFileHandler('custom_test.log', ...)





注意事项

环境检查：
验证 RabbitMQ：rabbitmqctl status


检查管理 API：curl http://guest:guest@localhost:15672/api/queues




调试：
查看日志：cat test.log
cat rabbitmq.log


启用 DEBUG：PYTHON_LOGGING_LEVEL=DEBUG python test.py




权限问题：
若仍需 sudo，手动调整：sudo chown $USER /opt/homebrew/var/lib/rabbitmq




进程清理：
终止残留进程：killall rabbitmq-server





运行步骤

准备环境：brew install rabbitmq
pip install aio-pika aiohttp tenacity
chmod -R u+rwX /opt/homebrew/var/lib/rabbitmq
rabbitmq-plugins enable rabbitmq_management
brew services start rabbitmq


运行测试：python test.py


验证结果：
检查 test.log：命令执行详情。
检查 rabbitmq.log：消息和连接日志，无 ERROR。
预期输出：2025-04-15 16:00:00,000 - INFO - 运行测试：多条消息...
...
2025-04-15 16:00:30,000 - INFO - 所有测试通过！





常见问题

启动失败：
检查路径：brew --prefix rabbitmq


清理进程：killall rabbitmq-server




日志包含 ERROR：
验证 rabbitmq_client.py 是否记录 INFO：logger.info(f"操作失败: {e}")




需要 sudo：
调整权限：chmod -R u+rwX /opt/homebrew/var/lib/rabbitmq


使用非 sudo 命令：/opt/homebrew/sbin/rabbitmq-server -detached





总结
本框架提供了一个高效、可靠的 RabbitMQ 测试环境，适配 macOS Homebrew，无需 sudo。通过模块化的 test.py 和 rabbitmq_client.py，开发者可以轻松修改测试用例、调整参数或集成到其他项目。send.py 和 receive.py 提供简单示例，便于快速上手。
