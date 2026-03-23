"""TTS — 使用 edge-tts（微软，免费）"""
import edge_tts

VOICES = {
    "male":     "zh-CN-YunjianNeural",   # 男声，播音腔
    "female":   "zh-CN-XiaoxiaoNeural",  # 女声，亲切
    "news":     "zh-CN-YunxiNeural",     # 男声，新闻风格
    "energetic": "zh-CN-YunfengNeural",  # 男声，活力
}


async def synthesize(text: str, output_path: str, voice: str = "news") -> str:
    """文字 → MP3，返回文件路径"""
    voice_id = VOICES.get(voice, voice)
    communicate = edge_tts.Communicate(text, voice_id, rate="+10%")
    await communicate.save(output_path)
    return output_path
