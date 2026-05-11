"""Gemini client bootstrap helpers."""
import google.generativeai as genai

from ..config import get_gemini_api_key


def configure_gemini_client() -> None:
    """Configure Google Gemini SDK using backend-only environment key."""
    genai.configure(api_key=get_gemini_api_key())
