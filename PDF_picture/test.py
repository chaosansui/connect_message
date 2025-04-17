import logging
import os
from utils import create_temp_dir, cleanup_temp_dir
from pdf_downloader import PDFDownloader
from pdf_to_image_converter import PDFToImageConverter
from image_processor import ImageProcessor

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_pdf_download():
    """测试 PDF 下载功能"""
    downloader = PDFDownloader()
    temp_dir = create_temp_dir()
    pdf_url = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
    try:
        pdf_path = downloader.download_pdf(pdf_url, temp_dir)
        logger.info(f"PDF 下载成功: {pdf_path}")
    finally:
        cleanup_temp_dir(temp_dir)

def test_pdf_to_images():
    """测试 PDF 转图片功能"""
    downloader = PDFDownloader()
    converter = PDFToImageConverter()
    temp_dir = create_temp_dir()
    pdf_url = ""
    try:
        pdf_path = downloader.download_pdf(pdf_url, temp_dir)
        image_paths = converter.pdf_to_images(pdf_path, temp_dir)
        logger.info(f"图片生成: {image_paths}")
    finally:
        cleanup_temp_dir(temp_dir)

def test_image_processor():
    """测试图片处理功能（使用服务器 API）"""
    processor = ImageProcessor(
        model_api_url=" ",
        api_key="your-api-key"
    )
    # 使用一个现有 PNG 文件进行测试（需提前准备）
    test_image = "test_image.png"  # 替换为实际图片路径
    if not os.path.exists(test_image):
        logger.error("测试图片不存在，请提供一个 PNG 文件")
        return
    try:
        result = processor.send_to_model(test_image)
        logger.info(f"服务器 API 响应: {result}")
    except Exception as e:
        logger.error(f"图片处理失败: {e}")

if __name__ == "__main__":
    logger.info("开始测试模块")
    test_pdf_download()
    test_pdf_to_images()
    test_image_processor()  # 需要服务器 API 和测试图片
    logger.info("测试完成")