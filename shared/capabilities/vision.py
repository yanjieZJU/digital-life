#!/usr/bin/env python3
"""
图像识别能力模块
支持OCR文字提取、图像处理
OCR状态：✓ 已安装tesseract 5.5.2，支持163种语言（包括中文chi_sim）

from PIL import Image
import cv2
import numpy as np
from typing import Optional, Dict, Any, List
import os

class VisionCapabilities:
    """图像处理能力集"""
    
    def __init__(self):
        self.ocr_engine = None
    
    # ========== 图像处理基础 ==========
    
    def load_image(self, image_path: str) -> Dict[str, Any]:
        """
        加载图像文件
        
        Args:
            image_path: 图像文件路径
        
        Returns:
            {"success": bool, "size": tuple, "mode": str}
        """
        try:
            img = Image.open(image_path)
            return {
                "success": True,
                "size": img.size,
                "mode": img.mode,
                "format": img.format
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def resize_image(self, image_path: str, output_path: str, 
                     width: int = None, height: int = None, 
                     scale: float = None) -> Dict[str, Any]:
        """
        调整图像大小
        
        Args:
            image_path: 输入图像路径
            output_path: 输出图像路径
            width: 目标宽度
            height: 目标高度
            scale: 缩放比例（若指定则忽略width/height）
        
        Returns:
            {"success": bool, "new_size": tuple}
        """
        try:
            img = Image.open(image_path)
            
            if scale:
                new_size = (int(img.size[0] * scale), int(img.size[1] * scale))
            elif width and height:
                new_size = (width, height)
            elif width:
                ratio = width / img.size[0]
                new_size = (width, int(img.size[1] * ratio))
            elif height:
                ratio = height / img.size[1]
                new_size = (int(img.size[0] * ratio), height)
            else:
                return {"success": False, "error": "需要指定width/height/scale之一"}
            
            img_resized = img.resize(new_size, Image.LANCZOS)
            img_resized.save(output_path)
            
            return {"success": True, "new_size": new_size, "output_path": output_path}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def crop_image(self, image_path: str, output_path: str,
                   left: int, top: int, right: int, bottom: int) -> Dict[str, Any]:
        """
        裁剪图像
        
        Args:
            image_path: 输入图像路径
            output_path: 输出图像路径
            left, top, right, bottom: 裁剪边界
        
        Returns:
            {"success": bool, "crop_size": tuple}
        """
        try:
            img = Image.open(image_path)
            cropped = img.crop((left, top, right, bottom))
            cropped.save(output_path)
            
            return {
                "success": True,
                "crop_size": cropped.size,
                "output_path": output_path
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ========== OCR 文字识别 ==========
    
    def check_ocr_available(self) -> Dict[str, Any]:
        """检查OCR引擎可用性"""
        engines = {}
        
        # 检查pytesseract
        try:
            import pytesseract
            # 检查tesseract binary
            result = os.popen('which tesseract').read().strip()
            if result:
                engines['pytesseract'] = {"available": True, "path": result}
            else:
                engines['pytesseract'] = {"available": False, "reason": "tesseract binary未安装"}
        except ImportError:
            engines['pytesseract'] = {"available": False, "reason": "pytesseract未安装"}
        
        # 检查PaddleOCR
        try:
            from paddleocr import PaddleOCR
            engines['paddleocr'] = {"available": True, "note": "需下载模型（约1GB）"}
        except ImportError:
            engines['paddleocr'] = {"available": False, "reason": "PaddleOCR未安装"}
        
        return {
            "success": True,
            "engines": engines,
            "recommendation": "安装tesseract或PaddleOCR以启用OCR功能"
        }
    
    def ocr_with_tesseract(self, image_path: str, lang: str = 'chi_sim+eng') -> Dict[str, Any]:
        """
        使用Tesseract进行OCR（需先安装tesseract binary）
        
        Args:
            image_path: 图像文件路径
            lang: 语言（chi_sim=简体中文, eng=英文）
        
        Returns:
            {"success": bool, "text": str}
        """
        try:
            import pytesseract
            
            img = Image.open(image_path)
            text = pytesseract.image_to_string(img, lang=lang)
            
            return {
                "success": True,
                "text": text.strip(),
                "engine": "tesseract"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def ocr_with_paddle(self, image_path: str) -> Dict[str, Any]:
        """
        使用PaddleOCR进行OCR（需先安装paddleocr）
        
        Args:
            image_path: 图像文件路径
        
        Returns:
            {"success": bool, "text": str, "boxes": list}
        """
        try:
            from paddleocr import PaddleOCR
            
            ocr = PaddleOCR(use_angle_cls=True, lang='ch')
            result = ocr.ocr(image_path, cls=True)
            
            texts = []
            boxes = []
            for line in result:
                for item in line:
                    boxes.append(item[0])
                    texts.append(item[1][0])
            
            return {
                "success": True,
                "text": '\n'.join(texts),
                "boxes": boxes,
                "engine": "paddleocr"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ========== 图像分析 ==========
    
    def get_image_info(self, image_path: str) -> Dict[str, Any]:
        """
        获取图像详细信息
        
        Returns:
            {"success": bool, "info": dict}
        """
        try:
            img = Image.open(image_path)
            
            # 使用OpenCV读取以获取更多信息
            cv_img = cv2.imread(image_path)
            
            info = {
                "file_path": image_path,
                "size": img.size,
                "width": img.size[0],
                "height": img.size[1],
                "mode": img.mode,
                "format": img.format,
                "channels": cv_img.shape[2] if len(cv_img.shape) == 3 else 1,
                "file_size_kb": os.path.getsize(image_path) / 1024
            }
            
            return {"success": True, "info": info}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def extract_colors(self, image_path: str, top_n: int = 5) -> Dict[str, Any]:
        """
        提取图像主要颜色
        
        Args:
            image_path: 图像路径
            top_n: 返回前N种主要颜色
        
        Returns:
            {"success": bool, "colors": list}
        """
        try:
            img = cv2.imread(image_path)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # 重塑为像素列表
            pixels = img.reshape(-1, 3)
            
            # 简单的颜色统计（实际可用K-means聚类）
            from collections import Counter
            color_counts = Counter(tuple(pixel) for pixel in pixels)
            top_colors = color_counts.most_common(top_n)
            
            colors = [
                {
                    "rgb": color,
                    "count": count,
                    "hex": '#{:02x}{:02x}{:02x}'.format(*color)
                }
                for color, count in top_colors
            ]
            
            return {"success": True, "colors": colors}
        except Exception as e:
            return {"success": False, "error": str(e)}


# 便捷函数
def ocr(image_path: str, engine: str = 'auto') -> Dict[str, Any]:
    """
    快速OCR文字识别
    
    Args:
        image_path: 图像路径
        engine: 'auto', 'tesseract', 'paddle'
    """
    cap = VisionCapabilities()
    
    if engine == 'auto':
        # 先尝试tesseract
        result = cap.ocr_with_tesseract(image_path)
        if result.get('success'):
            return result
        # 再尝试paddle
        return cap.ocr_with_paddle(image_path)
    elif engine == 'tesseract':
        return cap.ocr_with_tesseract(image_path)
    elif engine == 'paddle':
        return cap.ocr_with_paddle(image_path)
    else:
        return {"success": False, "error": f"未知引擎: {engine}"}


if __name__ == "__main__":
    # 测试
    cap = VisionCapabilities()
    
    # 检查OCR可用性
    print("OCR引擎状态:", cap.check_ocr_available())
    
    print("\n图像能力模块加载成功")
