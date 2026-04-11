import process_audio

long_transcript = """
Hi, I'm calling about my recent order. It hasn't arrived yet and it's been two weeks.
I am really frustrated by this delay. Can you tell me what's going on?
Let me check that for you. Yes, it seems there was a delay in shipping.
I apologize for the inconvenience. We can expedite this right away.
That would be great, please do that. Thank you very much!
You're welcome. Your tracking number will be updated within 24 hours. Have a great day.
"""

print("--- LOCAL SUMMARY ---")
print(process_audio.generate_local_summary(long_transcript))
print("\n--- LOCAL SENTIMENT ---")
print("Sentiment:", process_audio.analyze_sentiment(long_transcript))
print("Confidence:", process_audio.estimate_sentiment_confidence(long_transcript))
