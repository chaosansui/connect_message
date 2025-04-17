from pdf2image import convert_from_path
import os
import logging
from typing import List

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PDFToImageConverter:
    def pdf_to_images(self, pdf_path: str, temp_dir: str) -> List[str]:
        """
        将PDF文件转换为一页页的PNG图片。

        Args:
            pdf_path (str): PDF文件路径。
            temp_dir (str): 临时目录路径，用于存储生成的图片。

        Returns:
            List[str]: 生成的图片文件路径列表。

        Raises:
            Exception: 如果PDF转换失败。
        """
        try:
            images = convert_from_path(pdf_path)
            image_paths = []
            for i, image in enumerate(images):
                image_path = os.path.join(temp_dir, f"page_{i+1}.png")
                image.save(image_path, 'PNG')
                image_paths.append(image_path)
            logger.info(f"PDF转换为 {len(image_paths)} 张图片")
            return image_paths
        except Exception as e:
            logger.error(f"PDF转换图片失败: {e}")
            raise