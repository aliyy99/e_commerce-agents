"""List Gemini models accessible to the current API key."""
import google.generativeai as genai
from backend.config import get_gemini_api_key

genai.configure(api_key=get_gemini_api_key())

print("Models supporting generateContent:\n")
for m in genai.list_models():
    if "generateContent" in m.supported_generation_methods:
        print(f"  {m.name}  ({m.display_name})")
