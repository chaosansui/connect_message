import subprocess
import time
import os
import signal
import sys
import argparse
import logging
from logging.handlers import RotatingFileHandler
import requests
import json

# 配置日志，仅写入 test.log
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler('test.log', maxBytes=10*1024*1024, backupCount=5)
    ]
)
logger = logging.getLogger(__name__)
rabbitmq_logger = logging.getLogger('rabbitmq_client')

processes = []
test_results = []

def check_log(expect_received=True, expect_retry=False, expect_api_failure=False):
    try:
        with open('rabbitmq.log', 'r') as f:
            log = f.read()
            logger.debug(f"rabbitmq.log 内容: {log[:500]}...")
            if 'rabbitmq_client - ERROR' in log:
                return False, f"日志包含 ERROR: {log.split('rabbitmq_client - ERROR')[1][:100]}"
            if expect_received and 'Received' not in log:
                return False, "未找到 'Received' 消息"
            if expect_retry and '重试连接' not in log:
                return False, "未找到重试记录"
            if expect_api_failure and '管理 API 请求失败' not in log:
                return False, "未找到 API 失败记录"
            if expect_received:
                received_count = len([line for line in log.splitlines() if 'Received: {' in line])
                logger.info(f"检测到 {received_count} 条 Received 消息")
                if received_count < 1 and not expect_retry:
                    return False, f"Received 消息数量不足，实际 {received_count} 条"
        return True, "日志检查通过"
    except Exception as e:
        return False, f"日志检查失败: {e}"

def run_command(cmd, timeout=30):
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        logger.debug(f"命令 {cmd} 输出: {result.stdout} 错误: {result.stderr}")
        if result.returncode != 0:
            return False, f"命令 {cmd} 失败: {result.stderr}"
        return True, result.stdout
    except subprocess.TimeoutExpired:
        return False, f"命令 {cmd} 超时"
    except Exception as e:
        return False, f"命令 {cmd} 错误: {e}"

def check_rabbitmq_status():
    cmd = ['rabbitmqctl', 'status']
    success, msg = run_command(cmd, timeout=10)
    return success, msg

def get_rabbitmq_path():
    possible_paths = [
        '/opt/homebrew/sbin/rabbitmq-server',
        '/usr/local/rabbitmq/sbin/rabbitmq-server',
        '/usr/local/sbin/rabbitmq-server',
        os.path.expanduser('~/rabbitmq/sbin/rabbitmq-server'),
        '/opt/rabbitmq/sbin/rabbitmq-server'
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None

def fix_rabbitmq_permissions():
    possible_dirs = [
        os.path.expanduser('~/.rabbitmq'),
        '/var/lib/rabbitmq',
        '/opt/homebrew/var/lib/rabbitmq'
    ]
    for data_dir in possible_dirs:
        if os.path.exists(data_dir):
            cmd = ['sudo', 'chmod', '-R', 'u+rwX', data_dir]
            success, msg = run_command(cmd)
            if success:
                logger.info(f"已调整权限: {data_dir}")
                return True, ""
            return False, f"权限调整失败: {msg}"
    return False, "未找到 RabbitMQ 数据目录"

def cleanup_rabbitmq_processes():
    commands = [
        ['sudo', 'rabbitmqctl', 'stop'],
        ['pkill', '-u', 'rabbitmq'],
        ['killall', 'rabbitmq-server']
    ]
    for cmd in commands:
        success, msg = run_command(cmd)
        if success:
            logger.info(f"清理进程: {cmd}")
    time.sleep(2)
    return True, ""

def ensure_rabbitmq_running():
    success, msg = check_rabbitmq_status()
    if success:
        return True, ""
    
    logger.info("启动 RabbitMQ，可能需要输入 sudo 密码...")
    cleanup_rabbitmq_processes()
    fix_rabbitmq_permissions()
    
    rabbitmq_server = get_rabbitmq_path()
    commands = []
    if rabbitmq_server:
        commands.append(['sudo', rabbitmq_server, '-detached'])
    commands.append(['sudo', 'rabbitmq-server', '-detached'])
    
    for cmd in commands:
        logger.info(f"尝试启动: {cmd}")
        success, msg = run_command(cmd, timeout=60)
        if success:
            for _ in range(3):
                time.sleep(20)
                success, status_msg = check_rabbitmq_status()
                if success:
                    logger.info("RabbitMQ 启动成功")
                    return True, ""
                logger.warning(f"RabbitMQ 启动中，等待重试... 状态: {status_msg}")
            logger.warning(f"命令 {cmd} 启动后状态检查失败")
        else:
            logger.warning(f"启动命令 {cmd} 失败: {msg}")
    
    possible_logs = [
        '/opt/homebrew/var/log/rabbitmq/rabbit@*.log',
        '/var/log/rabbitmq/rabbit@*.log',
        os.path.expanduser('~/.rabbitmq/log/rabbit@*.log')
    ]
    logger.error(f"请检查 RabbitMQ 日志: {', '.join(possible_logs)}")
    return False, f"无法启动 RabbitMQ: {msg}"

def stop_rabbitmq():
    commands = [
        ['rabbitmq-plugins', 'disable', 'rabbitmq_management'],
        ['sudo', 'rabbitmqctl', 'stop'],
        ['pkill', '-u', 'rabbitmq'],
        ['killall', 'rabbitmq-server']
    ]
    
    for cmd in commands:
        logger.info(f"尝试停止: {cmd}")
        success, msg = run_command(cmd)
        if success:
            time.sleep(10)
            if not check_rabbitmq_status()[0]:
                logger.info("RabbitMQ 已停止")
                return True, ""
        logger.debug(f"停止命令 {cmd} 失败: {msg}")
    
    if check_rabbitmq_status()[0]:
        logger.error("RabbitMQ 未完全停止")
        return False, "无法停止 RabbitMQ"
    return True, ""

def cleanup_processes():
    for proc in processes:
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
        except ProcessLookupError:
            pass
    processes.clear()

def reset_environment():
    cleanup_processes()
    if os.path.exists('rabbitmq.log'):
        os.remove('rabbitmq.log')
    if os.path.exists('send_high.py'):
        os.remove('send_high.py')
    
    stop_rabbitmq()
    success, msg = ensure_rabbitmq_running()
    if success:
        run_command(['rabbitmqctl', 'delete_queue', 'hello'])
    else:
        logger.error(f"环境重置失败: {msg}")

def signal_handler(sig, frame):
    logger.info("捕获 Ctrl+C，正在清理...")
    cleanup_processes()
    reset_environment()
    logger.info("测试中止")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def run_test(name, func, **check_args):
    logger.info(f"\n运行测试：{name}...")
    reset_environment()
    try:
        success, message = func()
        result = f"{name}: {'通过' if success else '失败'} - {message}"
        test_results.append(result)
        logger.info(result)
        return success
    except Exception as e:
        result = f"{name}: 失败 - 意外错误: {e}"
        test_results.append(result)
        logger.error(result)
        return False
    finally:
        cleanup_processes()

def test_multiple_messages():
    receiver = subprocess.Popen(['python', 'receive.py'])
    processes.append(receiver)
    time.sleep(5)
    for i in range(10):
        logger.info(f"发送消息 {i+1}/10")
        success, msg = run_command(['python', 'send.py'])
        if not success:
            return False, f"发送失败: {msg}"
        time.sleep(0.2)
    time.sleep(2)
    return check_log(expect_received=True)

def test_persistence():
    logger.info("检查初始队列状态...")
    success, queue_info = run_command(['rabbitmqctl', 'list_queues', 'name', 'messages'])
    if success and 'hello' in queue_info:
        logger.info(f"队列状态: {queue_info}")
    
    receiver = subprocess.Popen(['python', 'receive.py'])
    processes.append(receiver)
    time.sleep(5)
    
    for i in range(5):
        logger.info(f"发送消息 {i+1}/5")
        success, msg = run_command(['python', 'send.py'])
        if not success:
            return False, f"发送失败: {msg}"
        time.sleep(0.2)
    
    success, queue_info = run_command(['rabbitmqctl', 'list_queues', 'name', 'messages'])
    if success:
        logger.info(f"发送后队列状态: {queue_info}")
    
    logger.info("停止 RabbitMQ...")
    success, msg = stop_rabbitmq()
    if not success:
        return False, msg
    
    logger.info("启动 RabbitMQ...")
    success, msg = ensure_rabbitmq_running()
    if not success:
        return False, msg
    
    success, queue_info = run_command(['rabbitmqctl', 'list_queues', 'name', 'messages'])
    if success:
        logger.info(f"重启后队列状态: {queue_info}")
    
    cleanup_processes()
    receiver = subprocess.Popen(['python', 'receive.py'])
    processes.append(receiver)
    time.sleep(15)
    
    cleanup_processes()
    receiver = subprocess.Popen(['python', 'receive.py'])
    processes.append(receiver)
    time.sleep(15)
    
    return check_log(expect_received=True)

def test_multiple_consumers():
    receiver1 = subprocess.Popen(['python', 'receive.py'])
    receiver2 = subprocess.Popen(['python', 'receive.py'])
    processes.extend([receiver1, receiver2])
    time.sleep(5)
    for i in range(10):
        logger.info(f"发送消息 {i+1}/10")
        success, msg = run_command(['python', 'send.py'])
        if not success:
            return False, f"发送失败: {msg}"
        time.sleep(0.2)
    time.sleep(2)
    return check_log(expect_received=True)

def test_connection_failure():
    logger.info("停止 RabbitMQ...")
    success, msg = stop_rabbitmq()
    if not success:
        return False, msg
    time.sleep(10)
    receiver = subprocess.Popen(['python', 'receive.py'])
    processes.append(receiver)
    time.sleep(5)
    logger.info("尝试在 RabbitMQ 停止时发送消息...")
    success, msg = run_command(['python', 'send.py'], timeout=10)
    if success:
        return False, "发送意外成功"
    cleanup_processes()
    logger.info("启动 RabbitMQ...")
    success, msg = ensure_rabbitmq_running()
    if not success:
        return False, msg
    time.sleep(5)
    return check_log(expect_received=False, expect_retry=True)

def test_high_concurrency():
    # 检查初始队列状态
    success, queue_info = run_command(['rabbitmqctl', 'list_queues', 'name', 'messages'])
    if success:
        logger.info(f"初始队列状态: {queue_info}")
    
    # 启动消费者
    receiver = subprocess.Popen(['python', 'receive.py'])
    processes.append(receiver)
    time.sleep(5)
    
    # 运行高并发发送
    logger.info("开始高并发测试，发送 500 条消息...")
    with open('send_high.py', 'w') as f:
        f.write('''
import asyncio
from rabbitmq_client import AsyncRabbitMQClient
import logging
import json

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
        for batch in range(0, 500, 100):
            tasks = []
            for i in range(batch, min(batch + 100, 500)):
                message = {"id": i, "content": f"Hello, RabbitMQ! {i}"}
                tasks.append(client.publish_message(message))
            await asyncio.gather(*tasks)
            logger.info(f"已发送 {min(batch + 100, 500)}/500 条消息")
            await asyncio.sleep(0.1)
        logger.info("全部 500 条消息发送完成")
    except Exception as e:
        logger.info(f"高并发发送失败: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
''')
    success, msg = run_command(['python', 'send_high.py'])
    if not success:
        return False, f"高并发发送失败: {msg}"
    
    # 等待消费者处理
    time.sleep(10)
    
    # 检查队列状态
    success, queue_info = run_command(['rabbitmqctl', 'list_queues', 'name', 'messages'])
    if success:
        logger.info(f"消费后队列状态: {queue_info}")
    
    cleanup_processes()
    success, msg = check_log(expect_received=True)
    if success:
        with open('rabbitmq.log', 'r') as f:
            log = f.read()
            received_count = len([line for line in log.splitlines() if 'Received: {' in line])
            logger.info(f"高并发测试收到 {received_count}/500 条消息")
            if received_count < 500:
                return False, f"预期 500 条 Received，实际 {received_count} 条"
            received_msgs = [line for line in log.splitlines() if 'Received: {' in line]
            actual_ids = set()
            for msg in received_msgs:
                try:
                    data = json.loads(msg.split('Received: ')[1])
                    id_val = data.get('id')
                    if id_val is not None:
                        actual_ids.add(f'"id": {id_val}')
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
            expected_ids = set(f'"id": {i}' for i in range(500))
            missing_ids = expected_ids - actual_ids
            if missing_ids:
                return False, f"缺少消息 ID: {missing_ids}"
    return success, msg

def test_management_api_failure():
    logger.info("禁用管理插件...")
    success, msg = run_command(['rabbitmq-plugins', 'disable', 'rabbitmq_management'])
    if not success:
        return False, f"禁用插件失败: {msg}"
    time.sleep(5)
    
    try:
        response = requests.get('http://localhost:15672/api/queues', auth=('guest', 'guest'), timeout=5)
        rabbitmq_logger.info(f"管理 API 意外成功: {response.status_code}")
        return False, "管理 API 未被禁用"
    except requests.RequestException as e:
        rabbitmq_logger.info(f"管理 API 请求失败: {e}")
    
    receiver = subprocess.Popen(['python', 'receive.py'])
    processes.append(receiver)
    time.sleep(5)
    
    logger.info("在管理 API 禁用时发送消息...")
    success, msg = run_command(['python', 'send.py'])
    if not success:
        return False, f"发送失败: {msg}"
    
    cleanup_processes()
    logger.info("重新启用管理插件...")
    success, msg = run_command(['rabbitmq-plugins', 'enable', 'rabbitmq_management'])
    if not success:
        logger.warning(f"重新启用插件失败: {msg}")
    
    time.sleep(5)
    try:
        response = requests.get('http://localhost:15672/api/queues', auth=('guest', 'guest'), timeout=5)
        rabbitmq_logger.info(f"管理 API 恢复: {response.status_code}")
    except requests.RequestException as e:
        rabbitmq_logger.warning(f"管理 API 恢复失败: {e}")
    
    return check_log(expect_received=True, expect_api_failure=True)

def test_log_integrity():
    for i in range(3):
        logger.info(f"运行 {i+1}/3")
        receiver = subprocess.Popen(['python', 'receive.py'])
        processes.append(receiver)
        time.sleep(5)
        success, msg = run_command(['python', 'send.py'])
        if not success:
            return False, f"发送失败: {msg}"
        cleanup_processes()
    return check_log(expect_received=True)

def test_queue_backlog():
    logger.info("在无消费者时发送消息...")
    for i in range(50):
        logger.info(f"发送消息 {i+1}/50")
        success, msg = run_command(['python', 'send.py'])
        if not success:
            return False, f"发送失败: {msg}"
    logger.info("启动消费者...")
    receiver = subprocess.Popen(['python', 'receive.py'])
    processes.append(receiver)
    time.sleep(5)
    cleanup_processes()
    success, msg = check_log(expect_received=True)
    if success:
        with open('rabbitmq.log', 'r') as f:
            log = f.read()
            received_count = len([line for line in log.splitlines() if 'Received: {' in line])
            if received_count < 50:
                return False, f"预期 50 条 Received，实际 {received_count} 条"
    return success, msg

def main():
    parser = argparse.ArgumentParser(description="运行 RabbitMQ 测试")
    parser.add_argument('--skip-slow', action='store_true',
                        help="跳过慢速测试（高并发、队列积压）")
    parser.add_argument('--test', type=str,
                        help="运行指定测试（例如 '多条消息'）")
    cmd_args = parser.parse_args()

    tests = {
        "多条消息": (test_multiple_messages, {}),
        "持久化": (test_persistence, {}),
        "多消费者": (test_multiple_consumers, {}),
        "连接失败": (test_connection_failure, {'expect_received': False, 'expect_retry': True}),
        "管理 API 失败": (test_management_api_failure, {'expect_api_failure': True}),
        "日志完整性": (test_log_integrity, {}),
        "高并发": (test_high_concurrency, {}),
        "队列积压": (test_queue_backlog, {})
    }

    selected_tests = []
    if cmd_args.test:
        if cmd_args.test in tests:
            selected_tests.append((cmd_args.test, *tests[cmd_args.test]))
        else:
            logger.error(f"无效测试名称: {cmd_args.test}")
            sys.exit(1)
    else:
        selected_tests = [(name, func, check_args) for name, (func, check_args) in tests.items()
                         if not (cmd_args.skip_slow and name in ["高并发", "队列积压"])]

    success, msg = ensure_rabbitmq_running()
    if not success:
        logger.error(f"无法启动 RabbitMQ: {msg}")
        sys.exit(1)

    for name, func, check_args in selected_tests:
        run_test(name, func, **check_args)

    logger.info("\n测试总结：")
    for result in test_results:
        logger.info(result)
    if all("通过" in result for result in test_results):
        logger.info("\n所有测试通过！")
    else:
        logger.error("\n部分测试失败。")
        sys.exit(1)

    reset_environment()

if __name__ == "__main__":
    main()