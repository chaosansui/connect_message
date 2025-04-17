PDF 转图片工具包
这是一个 Python 工具包，用于将通过 URL 提供的 PDF 文件转换为单页图片，发送至模型 API 进行处理，并在处理完成后安全删除所有临时文件。该工具包采用模块化设计，具有高扩展性，支持强大的错误处理和日志记录功能。
功能特性

PDF 下载：从指定 URL 下载 PDF 文件。
PDF 转图片：将 PDF 的每一页转换为 PNG 图片。
模型 API 集成：将图片发送至指定的模型 API 进行处理。
安全清理：处理完成后或发生错误时，自动删除临时文件（PDF 和图片）。
模块化设计：功能分模块实现，便于维护和扩展。
日志记录：提供详细的日志记录，便于调试和监控。

安装
前置条件

Python 3.10 或更高版本
Poppler（pdf2image 的依赖）
Windows：通过 poppler-windows 安装。
Linux：运行 sudo apt-get install poppler-utils
macOS：运行 brew install poppler



Python 依赖
安装所需的 Python 包：
pip install requests pdf2image

文件结构
工具包分为五个 Python 模块，每个模块负责特定功能：

utils.py：处理临时目录的创建和清理。
pdf_downloader.py：从 URL 下载 PDF 文件。
pdf_to_image_converter.py：将 PDF 转换为单页 PNG 图片。
image_processor.py：将图片发送至模型 API 进行处理。
pdf_to_image_toolkit.py：协调上述模块，完成整个处理流程。

请将所有文件放置在同一目录下。
使用方法
基本示例

修改 pdf_to_image_toolkit.py 中的 model_api_url 和 pdf_url：model_api_url = "https://your-model-api.com/process"  # 替换为实际的模型 API URL
pdf_url = "https://example.com/sample.pdf"           # 替换为实际的 PDF URL


运行脚本：python pdf_to_image_toolkit.py(记得在里面改url和模型的api)

在这里我编写了一个test测试文件，1、pdf下载 通过 2、pdf转图片 通过 3、测试图片处理功能 （目前没有模型api处理）


工具包将执行以下操作：
下载 PDF 文件。
将 PDF 转换为图片。
将每张图片发送至模型 API。
返回 API 的处理结果。
删除所有临时文件。



代码示例
from pdf_to_image_toolkit import PDFToImageToolkit

# 初始化工具包
toolkit = PDFToImageToolkit(model_api_url="")

# 处理 PDF
results = toolkit.process_pdf(pdf_url="")

# 查看结果
for i, result in enumerate(results):
    print(f"第 {i+1} 页结果: {result}")

预期输出
工具包会将每个步骤（下载、转换、API 处理、清理）的日志记录到控制台。results 变量包含模型 API 返回的 JSON 响应列表，每个响应对应一页图片的处理结果。
扩展性
模块化设计便于自定义和扩展：

支持新文件格式：在 pdf_to_image_converter.py 中添加新方法以支持其他格式（如 DOCX）。
自定义 API 逻辑：修改 image_processor.py，添加认证头或更改请求格式。
调整清理策略：更新 utils.py，实现自定义清理逻辑（如在删除前归档文件）。
增强日志记录：在任意模块中修改日志配置，集成外部日志系统（如将日志发送至服务器）。

安全性和清理

临时文件：所有文件（PDF 和图片）存储在通过 tempfile.mkdtemp() 创建的安全临时目录中。
自动清理：utils.cleanup_temp_dir 函数确保在处理完成或发生错误时删除临时文件。
析构函数：PDFToImageToolkit 类包含 __del__ 方法，确保对象销毁时清理残留文件。
错误处理：每个模块包含完善的异常处理机制，错误信息会记录到日志中，便于调试。

日志记录
工具包使用 Python 的 logging 模块记录以下内容：

每个步骤的开始和完成（下载、转换、API 调用、清理）。
详细的错误信息，便于排查问题。日志默认输出到控制台，可通过修改日志配置将其重定向到文件或外部系统。

故障排除

PDF 下载失败：确保 pdf_url 有效且可访问，检查网络连接。
PDF 转换失败：确认 Poppler 已安装且在系统 PATH 中。
API 错误：验证 model_api_url 正确，且 API 支持 PNG 图片的预期格式。
临时文件未删除：检查临时目录的文件权限，工具包会记录清理操作的日志以供验证。
