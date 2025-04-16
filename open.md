RabbitMQ 测试项目
这个项目是一个 Python 测试套件，用于验证 RabbitMQ 消息队列的功能。通过简单的脚本，你可以测试消息发送、接收、高并发、管理 API 等场景。目标是帮助开发者快速验证 RabbitMQ 的可靠性和性能。
项目目的

测试 RabbitMQ 的核心功能，如消息持久化、并发处理、管理 API 禁用。
提供可复用的异步 AMQP 客户端（基于 aio-pika）。
适合学习 RabbitMQ 或调试消息队列应用。

文件功能

test.py：
主测试脚本，运行所有测试用例。
测试内容：多条消息、持久化、多消费者、连接失败、管理 API 失败、高并发、日志完整性、队列积压。
使用示例：python test.py --test "高并发"


receive.py：
消息消费者，从 hello 队列异步接收消息。
功能：消费消息、记录日志（rabbitmq.log）、确认消息（ack）。


send.py：
单条消息发送脚本，向 hello 队列发送一条 JSON 消息。
示例消息：{"id": 1, "content": "Hello, RabbitMQ!"}


send_high.py（测试中生成）：
高并发发送脚本，异步发送 500 条消息。
功能：分批发送（50 条/批），降低服务器压力。


rabbitmq_client.py：
异步 RabbitMQ 客户端封装，基于 aio-pika。
功能：连接、声明队列、发送/消费消息、重试机制。



快速开始
1. 环境要求

Python: 3.9+
RabbitMQ: 3.9.x 或更高
macOS 安装：brew install rabbitmq
默认路径：/opt/homebrew/sbin/rabbitmq-server


依赖：pip install aio-pika tenacity requests



2. 设置步骤

安装 RabbitMQ：brew install rabbitmq
export PATH=$PATH:/opt/homebrew/sbin


启动 RabbitMQ：sudo rabbitmq-server -detached


克隆项目：git clone <你的仓库地址>
cd connect_message


安装依赖：pip install -r requirements.txt



3. 运行测试

所有测试：python test.py

输出示例：2025-04-16 13:30:00,000 - INFO - 高并发测试收到 500/500 条消息
2025-04-16 13:30:01,000 - INFO - 所有测试通过！


单个测试：python test.py --test "高并发"
python test.py --test "管理 API 失败"


调试：PYTHON_LOGGING_LEVEL=DEBUG python test.py



4. 查看结果

日志文件：
rabbitmq.log：消息发送/接收记录。
test.log：测试流程和结果。


验证队列：rabbitmqctl list_queues name messages



注意事项

临时文件（无需上传）：
__pycache__：Python 字节码缓存，运行时生成。
erl_crash.dump：RabbitMQ 崩溃转储，仅用于调试。
rabbitmq.log, test.log：日志文件，动态生成。


权限：
测试可能需要 sudo（如启动/停止 RabbitMQ）。
设置目录权限：sudo chmod -R u+rwX ~/.rabbitmq /opt/homebrew/var/lib/rabbitmq




清理：rm -rf __pycache__ *.log erl_crash.dump
sudo rabbitmqctl stop



常见问题

RabbitMQ 未启动：sudo rabbitmq-server -detached
rabbitmqctl status


依赖缺失：pip install -r requirements.txt


测试失败：
检查 test.log 和 rabbitmq.log。
确认 RabbitMQ 端口（5672, 15672）可用。



