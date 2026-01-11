# app/voice/__init__.py
"""
Voice Narration Module for Leading Light.

Provides Text-to-Speech capabilities using OpenAI Audio API.
"""
from app.voice.router import router

__all__ = ["router"]
