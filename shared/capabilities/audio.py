#!/usr/bin/env python3
"""
音频能力模块
支持文字转语音（TTS）和语音识别（STT）
"""

import pyttsx3
import speech_recognition as sr
from typing import Optional, Dict, Any

class AudioCapabilities:
    """音频处理能力集"""
    
    def __init__(self):
        self.tts_engine = None
        self.recognizer = None
    
    # ========== TTS 文字转语音 ==========
    
    def init_tts(self) -> Dict[str, Any]:
        """初始化TTS引擎"""
        try:
            self.tts_engine = pyttsx3.init()
            voices = self.tts_engine.getProperty('voices')
            return {
                "success": True,
                "voice_count": len(voices),
                "message": "TTS引擎初始化成功"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def text_to_speech(self, text: str, rate: int = 200) -> Dict[str, Any]:
        """
        文字转语音（播放）
        
        Args:
            text: 要朗读的文本
            rate: 语速（默认200）
        
        Returns:
            {"success": bool, "message": str}
        """
        try:
            if not self.tts_engine:
                self.init_tts()
            
            self.tts_engine.setProperty('rate', rate)
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
            
            return {"success": True, "message": f"已朗读: {text[:50]}..."}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def save_tts(self, text: str, output_path: str, rate: int = 200) -> Dict[str, Any]:
        """
        文字转语音（保存为文件）
        
        Args:
            text: 要朗读的文本
            output_path: 输出文件路径（.mp3或.wav）
            rate: 语速
        
        Returns:
            {"success": bool, "output_path": str}
        """
        try:
            if not self.tts_engine:
                self.init_tts()
            
            self.tts_engine.setProperty('rate', rate)
            self.tts_engine.save_to_file(text, output_path)
            self.tts_engine.runAndWait()
            
            return {"success": True, "output_path": output_path}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ========== STT 语音识别 ==========
    
    def init_stt(self) -> Dict[str, Any]:
        """初始化语音识别器"""
        try:
            self.recognizer = sr.Recognizer()
            return {"success": True, "message": "语音识别器初始化成功"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def listen_from_mic(self, timeout: int = 5) -> Dict[str, Any]:
        """
        从麦克风录音并识别
        
        Args:
            timeout: 录音超时时间（秒）
        
        Returns:
            {"success": bool, "text": str, "error": str}
        """
        try:
            if not self.recognizer:
                self.init_stt()
            
            with sr.Microphone() as source:
                print("正在听...")
                audio = self.recognizer.listen(source, timeout=timeout)
            
            # 使用Google语音识别（免费，需网络）
            text = self.recognizer.recognize_google(audio, language='zh-CN')
            
            return {"success": True, "text": text}
        except sr.WaitTimeoutError:
            return {"success": False, "error": "录音超时"}
        except sr.UnknownValueError:
            return {"success": False, "error": "无法识别"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def recognize_audio_file(self, audio_path: str) -> Dict[str, Any]:
        """
        识别音频文件
        
        Args:
            audio_path: 音频文件路径（.wav, .flac, .aiff）
        
        Returns:
            {"success": bool, "text": str}
        """
        try:
            if not self.recognizer:
                self.init_stt()
            
            with sr.AudioFile(audio_path) as source:
                audio = self.recognizer.record(source)
            
            text = self.recognizer.recognize_google(audio, language='zh-CN')
            
            return {"success": True, "text": text}
        except Exception as e:
            return {"success": False, "error": str(e)}


# 便捷函数
def speak(text: str, rate: int = 200) -> Dict[str, Any]:
    """快速朗读文本"""
    cap = AudioCapabilities()
    return cap.text_to_speech(text, rate)


def listen(timeout: int = 5) -> Dict[str, Any]:
    """快速监听并识别"""
    cap = AudioCapabilities()
    return cap.listen_from_mic(timeout)


if __name__ == "__main__":
    # 测试
    cap = AudioCapabilities()
    
    # 测试TTS初始化
    print("TTS初始化:", cap.init_tts())
    
    # 测试STT初始化
    print("STT初始化:", cap.init_stt())
    
    print("\n音频能力模块加载成功")
