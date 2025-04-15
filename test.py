import subprocess
import time
import os
import signal
import sys
import argparse
import logging
from logging.handlers import RotatingFileHandler

# 配置 test.py 日志，带轮转
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler('test.log', maxBytes=10*1024*1024, backupCount=5)
    ]
)
logger = logging.getLogger(__name__)

# 全局子进程列表
processes = []

# 测试结果
test_results = []

def check_log(expect_received=True, expect_retry=False, expect_api_failure=False):
    """检查 rabbitmq.log，确保无 ERROR，验证特定条件"""
    try:
        with open('rabbitmq.log', 'r') as f:
            log = f.read()
            if 'ERROR' in log:
                return False, f"日志包含 ERROR: {log.split('ERROR')[1][:100]}"
            if expect_received and 'Received' not in log:
                return False, "未找到 'Received' 消息"
            if expect_retry and '重试连接' not in log:
                return False, "未找到重试记录"
            if expect_api_failure and '管理 API 请求失败' not in log:
                return False, "未找到 API 失败记录"
            if '连接已关闭' not in log:
                return False, "未找到 '连接已关闭'"
        return True, "日志检查通过"
    except Exception as e:
        return False, f"日志检查失败: {e}"

def run_command(cmd, timeout=30, use_sudo=False):
    """执行命令，捕获输出"""
    if use_sudo:
        cmd = ['sudo'] + cmd
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
    """检查 RabbitMQ 是否运行"""
    for cmd in [
        ['rabbitmqctl', 'status'],
        ['sudo', 'rabbitmqctl', 'status']
    ]:
        success, msg = run_command(cmd, timeout=10)
        if success:
            return True, msg
    return False, "无法获取 RabbitMQ 状态"

def get_homebrew_prefix():
    """获取 Homebrew 的 RabbitMQ 路径"""
    try:
        result = subprocess.run(
            ['brew', '--prefix', 'rabbitmq'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return os.path.join(result.stdout.strip(), 'sbin')
    except Exception:
        pass
    return None

def ensure_rabbitmq_running():
    """确保 RabbitMQ 运行，适配 macOS Homebrew"""
    success, msg = check_rabbitmq_status()
    if not success:
        logger.info("启动 RabbitMQ...")
        homebrew_path = get_homebrew_prefix()
        commands = [
            ['brew', 'services', 'start', 'rabbitmq'],
            ['sudo', 'brew', 'services', 'start', 'rabbitmq']
        ]
        if homebrew_path:
            commands.append([os.path.join(homebrew_path, 'rabbitmq-server'), '-detached'])
            commands.append(['sudo', os.path.join(homebrew_path, 'rabbitmq-server'), '-detached'])
        commands.extend([
            ['/opt/homebrew/sbin/rabbitmq-server', '-detached'],
            ['sudo', '/opt/homebrew/sbin/rabbitmq-server', '-detached'],
            ['/usr/local/sbin/rabbitmq-server', '-detached'],
            ['sudo', '/usr/local/sbin/rabbitmq-server', '-detached'],
            ['rabbitmq-server', '-detached'],
            ['sudo', 'rabbitmq-server', '-detached']
        ])
        for cmd in commands:
            success, msg = run_command(cmd, timeout=60)
            if success:
                for _ in range(3):  # 多次检查状态
                    time.sleep(20)  # 延长等待
                    if check_rabbitmq_status()[0]:
                        return True, ""
                    logger.warning("RabbitMQ 启动中，等待重试...")
            logger.warning(f"启动命令 {cmd} 失败: {msg}")
        return False, f"无法启动 RabbitMQ: {msg}"
    return True, ""

def stop_rabbitmq():
    """停止 RabbitMQ，强制清理"""
    for cmd in [
        ['brew', 'services', 'stop', 'rabbitmq'],
        ['sudo', 'brew', 'services', 'stop', 'rabbitmq'],
        ['rabbitmqctl', 'stop'],
        ['sudo', 'rabbitmqctl', 'stop'],
        ['pkill', '-u', 'rabbitmq'],
        ['sudo', 'pkill', '-u', 'rabbitmq'],
        ['killall', 'rabbitmq-server'],
        ['sudo', 'killall', 'rabbitmq-server']
    ]:
        success, msg = run_command(cmd)
        if success:
            time.sleep(10)  # 延长等待
            if not check_rabbitmq_status()[0]:
                return True, ""
        logger.warning(f"停止命令 {cmd} 失败: {msg}")
    # 最终检查
    if check_rabbitmq_status()[0]:
        return False, "无法停止 RabbitMQ"
    return True, ""

def cleanup_processes():
    """终止所有子进程"""
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
    """重置测试环境"""
    cleanup_processes()
    if os.path.exists('rabbitmq.log'):
        os.remove('rabbitmq.log')
    if os.path.exists('send_high.py'):
        os.remove('send_high.py')
    # 清理 RabbitMQ 残留进程
    stop_rabbitmq()
    success, msg = ensure_rabbitmq_running()
    if success:
        run_command(['rabbitmqctl', 'delete_queue', 'hello'])
    else:
        logger.error(f"环境重置失败: {msg}")

def signal_handler(sig, frame):
    """处理 Ctrl+C"""
    logger.info("捕获 Ctrl+C，正在清理...")
    cleanup_processes()
    reset_environment()
    logger.info("测试中止")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def run_test(name, func, **check_args):
    """运行单个测试"""
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
    """测试 1：多条消息"""
    receiver = subprocess.Popen(['python', 'receive.py'])
    processes.append(receiver)
    time.sleep(3)
    for i in range(10):
        logger.info(f"发送消息 {i+1}/10")
        success, msg = run_command(['python', 'send.py'])
        if not success:
            return False, f"发送失败: {msg}"
        time.sleep(0.1)
    time.sleep(1)
    return check_log(expect_received=True)

def test_persistence():
    """测试 2：持久化"""
    receiver = subprocess.Popen(['python', 'receive.py'])
    processes.append(receiver)
    time.sleep(3)
    for i in range(5):
        logger.info(f"发送消息 {i+1}/5")
        success, msg = run_command(['python', 'send.py'])
        if not success:
            return False, f"发送失败: {msg}"
    logger.info("停止 RabbitMQ...")
    success, msg = stop_rabbitmq()
    if not success:
        return False, msg
    logger.info("启动 RabbitMQ...")
    success, msg = ensure_rabbitmq_running()
    if not success:
        return False, msg
    time.sleep(5)
    return check_log(expect_received=True)

def test_multiple_consumers():
    """测试 3：多消费者"""
    receiver1 = subprocess.Popen(['python', 'receive.py'])
    receiver2 = subprocess.Popen(['python', 'receive.py'])
    processes.extend([receiver1, receiver2])
    time.sleep(5)
    for i in range(10):
        logger.info(f"发送消息 {i+1}/10")
        success, msg = run_command(['python', 'send.py'])
        if not success:
            return False, f"发送失败: {msg}"
    time.sleep(2)
    return check_log(expect_received=True)

def test_connection_failure():
    """测试 4：连接失败"""
    logger.info("停止 RabbitMQ...")
    success, msg = stop_rabbitmq()
    if not success:
        return False, msg
    time.sleep(10)  # 延长等待
    receiver = subprocess.Popen(['python', 'receive.py'])
    processes.append(receiver)
    time.sleep(3)
    logger.info("尝试在 RabbitMQ 停止时发送消息...")
    success, msg = run_command(['python', 'send.py'], timeout=10)
    if success:
        return False, "发送意外成功"
    cleanup_processes()
    logger.info("启动 RabbitMQ...")
    success, msg = ensure_rabbitmq_running()
    if not success:
        return False, msg
    return check_log(expect_received=False, expect_retry=True)

def test_high_concurrency():
    """测试 5：高并发"""
    with open('send_high.py', 'w') as f:
        f.write('''
import asyncio
from rabbitmq_client import AsyncRabbitMQClient
import logging

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
        tasks = [client.publish_message({'id': i, 'content': f'Message {i}'}) for i in range(500)]
        await asyncio.gather(*tasks)
    except Exception as e:
        logger.info(f"操作失败: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
''')
    receiver = subprocess.Popen(['python', 'receive.py'])
    processes.append(receiver)
    time.sleep(3)
    logger.info("并发发送 500 条消息...")
    success, msg = run_command(['python', 'send_high.py'])
    if not success:
        return False, f"高并发发送失败: {msg}"
    cleanup_processes()
    success, msg = check_log(expect_received=True)
    if success:
        with open('rabbitmq.log', 'r') as f:
            log = f.read()
            received_count = log.count('Received')
            if received_count < 500:
                return False, f"预期 500 条 Received，实际 {received_count} 条"
    return success, msg

def test_management_api_failure():
    """测试 6：管理 API 失败"""
    logger.info("禁用管理插件...")
    success, msg = run_command(['rabbitmq-plugins', 'disable', 'rabbitmq_management'])
    if not success:
        success, msg = run_command(['sudo', 'rabbitmq-plugins', 'disable', 'rabbitmq_management'])
        if not success:
            return False, f"禁用插件失败: {msg}"
    time.sleep(5)
    receiver = subprocess.Popen(['python', 'receive.py'])
    processes.append(receiver)
    time.sleep(5)
    logger.info("在管理 API 禁用时发送消息...")
    success, msg = run_command(['python', 'send.py'])
    if not success:
        return False, f"发送失败: {msg}"
    cleanup_processes()
    logger.info("重新启用管理插件...")
    run_command(['rabbitmq-plugins', 'enable', 'rabbitmq_management'])
    run_command(['sudo', 'rabbitmq-plugins', 'enable', 'rabbitmq_management'])
    time.sleep(5)
    return check_log(expect_received=True, expect_api_failure=True)

def test_log_integrity():
    """测试 7：日志完整性"""
    for i in range(3):
        logger.info(f"运行 {i+1}/3")
        receiver = subprocess.Popen(['python', 'receive.py'])
        processes.append(receiver)
        time.sleep(3)
        success, msg = run_command(['python', 'send.py'])
        if not success:
            return False, f"发送失败: {msg}"
        cleanup_processes()
    return check_log(expect_received=True)

def test_queue_backlog():
    """测试 8：队列积压"""
    logger.info("在无消费者时发送消息...")
    for i in range(50):
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
            received_count = log.count('Received')
            if received_count < 50:
                return False, f"预期 50 条 Received，实际 {received_count} 条"
    return success, msg

def main():
    parser = argparse.ArgumentParser(description="运行 RabbitMQ 测试")
    parser.add_argument('--skip-slow', action='store_true',
                        help="跳过慢速测试（高并发、队列积压）")
    args = parser.parse_args()

    tests = [
        ("多条消息", test_multiple_messages, {}),
        ("持久化", test_persistence, {}),
        ("多消费者", test_multiple_consumers, {}),
        ("连接失败", test_connection_failure, {'expect_received': False, 'expect_retry': True}),
        ("管理 API 失败", test_management_api_failure, {'expect_api_failure': True}),
        ("日志完整性", test_log_integrity, {}),
    ]

    if not args.skip_slow:
        tests.extend([
            ("高并发", test_high_concurrency, {}),
            ("队列积压", test_queue_backlog, {}),
        ])

    success, msg = ensure_rabbitmq_running()
    if not success:
        logger.error(f"无法启动 RabbitMQ: {msg}")
        sys.exit(1)

    for name, func, check_args in tests:
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