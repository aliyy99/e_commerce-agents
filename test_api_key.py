import os
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai

# .env dosyasını backend klasöründen yükle
_BASE_DIR = Path(__file__).resolve().parent / "backend"
load_dotenv(_BASE_DIR / ".env")

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("GEMINI_API_KEY bulunamadı!")
else:
    print(f"API Key bulundu (ilk 4 karakter): {api_key[:4]}...")
    genai.configure(api_key=api_key)
    try:
        print("Kullanılabilir modeller listeleniyor...")
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"- {m.name}")
        
        model_name = 'models/gemini-1.5-flash'
        print(f"Deneme yapılıyor: {model_name}")
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Hello, are you active?")
        print("API Key geçerli!")
        print(f"Yanıt: {response.text}")
    except Exception as e:
        print(f"Hata oluştu: {e}")
