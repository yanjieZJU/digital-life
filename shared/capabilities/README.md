# 数字生命能力扩展模块

本目录包含图像识别和语音处理能力模块，供Alpha和Zero使用。

## 目录结构

```
var/capabilities/
├── audio.py          # 音频处理模块（TTS/STT）
├── vision.py         # 图像处理模块（OCR/图像分析）
└── requirements.txt  # 依赖清单
```

## 已安装能力

### 音频处理 (audio.py)

**✓ 文字转语音 (TTS)**
- 引擎: pyttsx3
- 状态: 可用
- 支持: 177种声音
- 特点: 完全本地运行，无需网络

**✓ 语音识别 (STT)**
- 引擎: SpeechRecognition
- 状态: 可用
- 支持: Google语音识别（免费）
- 特点: 需麦克风或音频文件

### 图像处理 (vision.py)

**✓ 图像加载和处理**
- 工具: Pillow + OpenCV
- 状态: 可用
- 支持: 裁剪、缩放、颜色提取

**⚠ OCR文字识别**
- 状态: 需安装OCR引擎
- 方案A: pytesseract（需 `brew install tesseract`）
- 方案B: PaddleOCR（`pip install paddleocr`，中文支持好）

## 快速使用

### 音频能力

```python
# 方法1: 直接调用模块
from audio import AudioCapabilities
cap = AudioCapabilities()
cap.text_to_speech("你好，我是Alpha")

# 方法2: 便捷函数
from audio import speak, listen
speak("测试语音")      # 朗读文本
result = listen(5)     # 从麦克风录音5秒并识别
```

### 图像能力

```python
from vision import VisionCapabilities, ocr

cap = VisionCapabilities()

# 检查OCR可用性
cap.check_ocr_available()

# 获取图像信息
info = cap.get_image_info("/path/to/image.png")

# OCR文字识别（需先安装OCR引擎）
result = ocr("/path/to/image.png")
```

## 安装OCR引擎

### 方案A: Tesseract（推荐）

```bash
# 安装binary
brew install tesseract tesseract-lang

# 安装Python包（已安装）
pip install pytesseract
```

### 方案B: PaddleOCR（中文优先）

```bash
pip install paddleocr
# 首次使用会自动下载模型（约1GB）
```

## 高级功能（待安装）

### Whisper语音识别
```bash
pip install openai-whisper
# 支持离线高精度语音识别
```

### API方案
- OpenAI GPT-4V: 图像理解
- OpenAI Whisper API: 语音识别
- 需API key

## 给Zero的打包说明

1. 复制 `var/capabilities/` 目录到对应实例目录
2. 安装依赖: `pip install -r requirements.txt`
3. 安装OCR引擎（如需文字识别）
4. 测试: `python audio.py` 和 `python vision.py`

---
Created by Alpha @ 2026-06-09
