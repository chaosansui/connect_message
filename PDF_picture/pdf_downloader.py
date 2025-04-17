import requests
import os
import logging

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PDFDownloader:
    def download_pdf(self, pdf_url: str, temp_dir: str) -> str:
        """
        从指定URL下载PDF文件到临时目录。

        Args:
            pdf_url (str): PDF文件的URL。
            temp_dir (str): 临时目录路径，用于存储下载的PDF。

        Returns:
            str: 下载的PDF文件路径。

        Raises:
            requests.RequestException: 如果下载失败。
        """
        try:
            response = requests.get(pdf_url, stream=True)
            response.raise_for_status()
            pdf_path = os.path.join(temp_dir, "input.pdf")
            with open(pdf_path, 'wb') as f:
                f.write(response.content)
            logger.info(f"PDF下载到: {pdf_path}")
            return pdf_path
        except requests.RequestException as e:
            logger.error(f"PDF下载失败: {e}")
            raise