from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def transcribe_audio(audio_bytes: bytes, filename: str = "recording.wav") -> str:
    provider = os.getenv("VOICE_STT_PROVIDER", "groq").lower()
    model = os.getenv("VOICE_STT_MODEL", "whisper-large-v3-turbo")
    if provider != "groq":
        raise ValueError(f"Unsupported speech-to-text provider: {provider}")
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is required for voice transcription.")

    from groq import Groq

    client = Groq(api_key=api_key)
    with tempfile.NamedTemporaryFile(suffix=Path(filename).suffix or ".wav") as audio_file:
        audio_file.write(audio_bytes)
        audio_file.flush()
        with open(audio_file.name, "rb") as source:
            result = client.audio.transcriptions.create(model=model, file=source)
    return result.text.strip()


def synthesize_speech(text: str) -> bytes:
    provider = os.getenv("VOICE_TTS_PROVIDER", "edge-tts").lower()
    voice = os.getenv("VOICE_TTS_VOICE", "en-US-JennyNeural")
    if provider != "edge-tts":
        raise ValueError(f"Unsupported text-to-speech provider: {provider}")
    if not text.strip():
        return b""

    import edge_tts

    async def generate() -> bytes:
        communicate = edge_tts.Communicate(text, voice)
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as output:
            output_path = output.name
        try:
            await communicate.save(output_path)
            return Path(output_path).read_bytes()
        finally:
            Path(output_path).unlink(missing_ok=True)

    return asyncio.run(generate())
