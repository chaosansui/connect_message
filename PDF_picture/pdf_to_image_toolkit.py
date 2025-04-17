from typing import List, Dict
import logging
from utils import create_temp_dir, cleanup_temp_dir
from pdf_downloader import PDFDownloader
from pdf_to_image_converter import PDFToImageConverter
from image_processor import ImageProcessor

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PDFToImageToolkit:
    def __init__(self, model_api_url: str, api_key: str = None):
        """
        初始化 PDF 到图片的工具包。

        Args:
            model_api_url (str): 模型 API 的 URL。
            api_key (str, optional): API 密钥，用于认证。如果不需要认证，可为 None。
        """
        self.model_api_url = model_api_url
        self.api_key = api_key
        self.temp_dir = None
        self.downloader = PDFDownloader()
        self.converter = PDFToImageConverter()
        self.processor = ImageProcessor(model_api_url, api_key)

    def process_pdf(self, pdf_url: str) -> List[Dict]:
        """
        处理 PDF 文件：下载、转换为图片、发送到模型 API、清理临时文件。

        Args:
            pdf_url (str): PDF 文件的 URL。

        Returns:
            List[Dict]: 每张图片的模型 API 处理结果列表。

        Raises:
            Exception: 如果处理过程中的任何步骤失败。
        """
        try:
            # 创建临时目录
            self.temp_dir = create_temp_dir()
            
            # 下载 PDF
            pdf_path = self.downloader.download_pdf(pdf_url, self.temp_dir)
            
            # 转换为图片
            image_paths = self.converter.pdf_to_images(pdf_path, self.temp_dir)
            
            # 处理每张图片
            results = []
            for image_path in image_paths:
                result = self.processor.send_to_model(image_path)
                results.append(result)
            
            return results
        
        finally:
            # 清理临时目录
            cleanup_temp_dir(self.temp_dir)
            self.temp_dir = None

    def __del__(self):
        """
        析构函数，确保临时目录在对象销毁时被清理。
        """
        cleanup_temp_dir(self.temp_dir)
        self.temp_dir = None

def main():
    """
    示例：如何使用 PDFToImageToolkit 处理 PDF。
    """
    model_api_url = "https://your-server.com/api"  # 替换模型 API URL
    api_key = "your-api-key"  # 替换 API 密钥
    pdf_url = "pdf"  # 替换 PDF URL
    
    toolkit = PDFToImageToolkit(model_api_url, api_key)
    try:
        results = toolkit.process_pdf(pdf_url)
        for i, result in enumerate(results):
            logger.info(f"第 {i+1} 页的处理结果: {result}")
    except Exception as e:
        logger.error(f"处理失败: {e}")

if __name__ == "__main__":
    main()