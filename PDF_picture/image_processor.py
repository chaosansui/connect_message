import requests
import os
import logging
from typing import Dict

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ImageProcessor:
    def __init__(self, model_api_url: str, api_key: str = None):
        """
        初始化图片处理器，设置模型 API 的 URL 和认证密钥。

        Args:
            model_api_url (str): 模型 API 的 URL。
            api_key (str, optional): API 密钥，用于认证。如果不需要认证，可为 None。
        """
        self.model_api_url = model_api_url
        self.api_key = api_key

    def send_to_model(self, image_path: str) -> Dict:
        """
        将图片发送到模型 API 进行处理。

        Args:
            image_path (str): 图片文件路径。

        Returns:
            Dict: 模型 API 的响应结果。

        Raises:
            requests.RequestException: 如果 API 调用失败。
        """
        try:
            with open(image_path, 'rb') as f:
                # 准备文件上传
                files = {'image': (os.path.basename(image_path), f, 'image/png')}
                
                # 设置请求头（如果需要认证）
                headers = {}
                if self.api_key:
                    headers['Authorization'] = f'Bearer {self.api_key}'
                
                # 发送 POST 请求
                response = requests.post(
                    self.model_api_url,
                    files=files,
                    headers=headers,
                    timeout=30  # 设置超时，避免长时间挂起
                )
                response.raise_for_status()
                
                # 解析响应
                result = response.json()
                if result.get('status') == 'error':
                    logger.error(f"API 返回错误: {result.get('message')}")
                    raise ValueError(f"API error: {result.get('message')}")
                
                logger.info(f"图片 {image_path} 已由模型 API 处理")
                return result
        except requests.RequestException as e:
            logger.error(f"发送图片到模型 API 失败: {e}")
            raise
        except ValueError as e:
            logger.error(f"API 响应解析失败: {e}")
            raise