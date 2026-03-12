from dotenv import load_dotenv
load_dotenv()

import os
api_key = os.getenv("GEMINI_API_KEY", "")

if not api_key:
    print("❌ GEMINI_API_KEY not found in .env")
    exit(1)

print(f"✓ Key found: {api_key[:8]}...{api_key[-4:]}")

try:
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")
    resp = model.generate_content('Reply with just the word "working"')
    print(f"✓ Gemini response: {resp.text.strip()}")
    print("✅ Gemini API is working!")
except Exception as e:
    print(f"❌ Gemini API error: {e}")