from dotenv import load_dotenv
load_dotenv('.env.local')
import process_audio
import traceback

transcript = "Hello, I'm calling about an overcharge in my last bill. Please check the invoice and help me resolve this issue."

try:
    print("Testing gemini_analysis...")
    res = process_audio.gemini_analysis(transcript, ['billing'])
    print("Result:", res)
except Exception as e:
    traceback.print_exc()
