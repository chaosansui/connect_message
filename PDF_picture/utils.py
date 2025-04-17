import tempfile
import os
import shutil
import logging

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_temp_dir() -> str:
    """
    创建一个临时目录，用于存储PDF和图片文件。

    Returns:
        str: 临时目录的路径。
    """
    temp_dir = tempfile.mkdtemp()
    logger.info(f"创建临时目录: {temp_dir}")
    return temp_dir

def cleanup_temp_dir(temp_dir: str) -> None:
    """
    清理临时目录及其所有内容。

    Args:
        temp_dir (str): 要清理的临时目录路径。
    """
    if temp_dir and os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
        logger.info(f"删除临时目录: {temp_dir}")