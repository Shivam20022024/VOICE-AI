import process_audio

transcript = "I am so angry right now! My issue is not resolved. Give me a refund immediately for this bad product."
fallback_intents = process_audio.detect_intents(process_audio.normalize_language(transcript))

gemini_result = process_audio.gemini_analysis(transcript, fallback_intents)
if gemini_result is None:
    summary = process_audio.generate_local_summary(transcript)
    sentiment = process_audio.analyze_sentiment(transcript)
    conf = process_audio.estimate_sentiment_confidence(transcript)
    print("Fallback activated!")
    print(f"Summary:\n{summary}")
    print(f"\nSentiment: {sentiment} (Confidence: {conf})")
else:
    print("Gemini result: ", gemini_result)
