# 医院票据图片批量生成 Excel

这是一个完全本地运行的 Windows 小应用。它使用 PaddleOCR 识别医院收费票据照片，将印刷金额与手写扣减金额转换成固定 Excel 模板，并按以下格式命名：

```text
原图片名称+交款人+开票日期YYYYMMDD+核对无误或核对有误.xlsx
```

## 功能

- 批量读取 JPG、JPEG、PNG、BMP、TIFF 图片。
- 识别交款人、开票日期、住院时间、病历号、性别、费用项目及金额。
- 费用净额等于印刷金额减手写扣减金额；净额为零时写数值 `0`。
- E12 写普通数值，不写 Excel 公式。
- 自动比较费用明细净额与最终金额并命名为“核对无误”或“核对有误”。
- 每张图片保留 `review/图片名.json`，方便检查 OCR 原文、置信度和警告。
- 每批生成 `summary.json`，记录成功、失败和输出文件。

## Windows 图形界面

建议安装 64 位 Python 3.12，然后依次双击：

1. `setup.bat`：首次安装依赖。
2. `run_gui.bat`：启动应用。
3. 选择图片文件夹和 Excel 输出文件夹，点击“开始批量生成”。

首次识别会自动下载 PaddleOCR 模型，后续可离线运行。

当前 CPU 测试环境中，每张约需几十秒；电脑性能和图片尺寸不同，速度会有差异。

## 免 Python 分发版

开发者可运行 `build_exe.ps1` 构建。输出目录为：

```text
dist/medical-invoice-excel/
```

将整个目录压缩后发给其他人。对方必须完整解压，直接双击
`医院票据识别工具.exe`，不需要安装 Python，也不需要联网下载模型。
不要只单独复制 EXE；`models` 和 `_internal` 目录是运行所必需的。

## 命令行

```powershell
.venv\Scripts\python.exe -m medical_invoice_ocr.cli `
  "D:\发票图片" "D:\发票图片\excel"
```

只测试一张：

```powershell
.venv\Scripts\python.exe -m medical_invoice_ocr.cli `
  "D:\发票图片" "D:\发票图片\excel-test" --limit 1
```

## 识别边界

PaddleOCR 对印刷内容准确率较高，也能识别一部分写在金额旁的手写扣减数字，但手写数字仍可能误识别。程序通过金额合计进行交叉核对；以下情况应人工检查 `review` JSON 和原图：

- 文件名显示“核对有误”；
- `summary.json` 中状态为 `failed`；
- review 文件包含“置信度较低”或金额不一致警告。

票据属于敏感资料。本程序默认只在本机处理，不会主动上传图片。

## 开源许可

本项目代码使用 MIT License。PaddleOCR 与 PaddlePaddle 使用 Apache 2.0 License；发布打包版本时请同时保留其许可证及版权声明。
