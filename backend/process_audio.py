import json
import mimetypes
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime

import openpyxl
import requests

# -----------------------------------------
# CONFIG
# -----------------------------------------
TRANSCRIPT_DIR = "transcripts"
RESULTS_DIR = "results"

EXCEL_FILE = os.path.join(RESULTS_DIR, "analytics_results.xlsx")
CONVERTED_EXCEL_FILE = os.path.join(RESULTS_DIR, "converted_calls.xlsx")
SALES_CRM_FILE = os.path.join(RESULTS_DIR, "sales_crm.xlsx")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_GEMINI_IMPORT_ERROR_LOGGED = False
_GEMINI_DISABLED_REASON = None


def _bootstrap_local_venv_site_packages():
    """
    If the backend is started with a global Python interpreter, allow imports from the
    bundled backend virtualenv so optional SDKs like Gemini still resolve.
    """
    py_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
    candidate_paths = [
        os.path.join(BASE_DIR, "venv", "Lib", "site-packages"),
        os.path.join(BASE_DIR, "venv", "lib", py_version, "site-packages"),
    ]

    for path in candidate_paths:
        if os.path.isdir(path) and path not in sys.path:
            sys.path.insert(0, path)


def _import_gemini_sdk(log_context):
    global _GEMINI_IMPORT_ERROR_LOGGED

    _bootstrap_local_venv_site_packages()

    try:
        import google.generativeai as genai
        return genai
    except Exception as e:
        if not _GEMINI_IMPORT_ERROR_LOGGED:
            print(
                f"Gemini disabled ({log_context}): {e}. "
                "Start the backend with backend\\venv\\Scripts\\python.exe or install "
                "requirements from voice-ai\\requirements.txt."
            )
            _GEMINI_IMPORT_ERROR_LOGGED = True
        return None


def _import_google_genai_sdk(log_context):
    _bootstrap_local_venv_site_packages()

    try:
        from google import genai
        return genai
    except Exception as e:
        print(f"Google GenAI SDK unavailable for {log_context}: {e}")
        return None


def _get_gemini_api_key():
    global _GEMINI_DISABLED_REASON

    api_key = (os.environ.get("GEMINI_API_KEY") or "").strip()
    if not api_key:
        return ""

    invalid_markers = {
        "placeholder_api_key",
        "your_api_key",
        "your_gemini_api_key",
        "changeme",
    }
    if api_key.lower() in invalid_markers:
        if _GEMINI_DISABLED_REASON != "placeholder":
            print("Gemini disabled: GEMINI_API_KEY is still set to a placeholder value.")
            _GEMINI_DISABLED_REASON = "placeholder"
        return ""

    if _GEMINI_DISABLED_REASON == "invalid_key":
        return ""

    return api_key


# -----------------------------------------
# WEEKLY FILE HELPERS
# -----------------------------------------
def get_weekly_excel_file():
    now = datetime.utcnow()
    year, week_num, _ = now.isocalendar()
    return os.path.join(RESULTS_DIR, f"weekly_calls_{year}_W{week_num}.xlsx")


def get_weekly_sales_file():
    now = datetime.utcnow()
    year, week_num, _ = now.isocalendar()
    return os.path.join(RESULTS_DIR, f"weekly_sales_{year}_W{week_num}.xlsx")


# -----------------------------------------
# HELPERS
# -----------------------------------------
def _now_ts():
    return datetime.utcnow().isoformat() + "Z"


def _env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name, default):
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return float(value)
    except Exception:
        return default


def _extract_json_object(text):
    if not text:
        return None
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    candidate = text[start : end + 1]
    try:
        return json.loads(candidate)
    except Exception:
        return None


def _normalize_whitespace(text):
    return re.sub(r"\s+", " ", (text or "")).strip()


def _split_sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text or "") if s.strip()]


def _strip_transcript_noise(text):
    if not text:
        return ""

    noise_patterns = [
        r"^remember to watch our other .*",
        r"^remember to always be a good customer.*",
        r"^watch our other .*",
        r"^subscribe .*",
        r"^like and share .*",
        r"^role play videos?\.?$",
    ]

    kept = []
    for sentence in _split_sentences(text):
        lowered = sentence.lower()
        if any(re.match(pattern, lowered) for pattern in noise_patterns):
            continue
        kept.append(sentence)
    return " ".join(kept).strip()


def _format_transcript_for_display(text):
    cleaned = _strip_transcript_noise(_normalize_whitespace(text))
    if not cleaned:
        return ""

    cleaned = re.sub(
        r"\b(Call center(?:,)? handling rude customers(?: role play)?\.?)",
        r"\n\1",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\b(Call number \w+[^.?!]*[.?!])",
        r"\n\n\1",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\b(Call center agent and customer\.?)",
        r"\n\1\n",
        cleaned,
        flags=re.IGNORECASE,
    )

    speaker_starts = [
        "Thank you for calling",
        "Good afternoon",
        "Good morning",
        "Good evening",
        "Finally",
        "I'm very sorry",
        "I completely understand",
        "I understand",
        "May I",
        "Oh, fine",
        "This is",
        "Whatever",
        "Again, I am sorry",
        "Then why do you",
        "No, I'm done",
        "I do understand",
        "Yeah,",
        "Well,",
    ]
    for marker in speaker_starts:
        cleaned = re.sub(rf"\s+({re.escape(marker)})", r"\n\1", cleaned)

    lines = [line.strip(" -") for line in cleaned.splitlines() if line.strip()]
    return "\n".join(lines)


def safe_write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text or "")
    return path


def write_excel(path, row):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    new_file = not os.path.exists(path)

    wb = openpyxl.Workbook() if new_file else openpyxl.load_workbook(path)
    ws = wb.active

    if new_file:
        ws.append(list(row.keys()))

    ws.append(list(row.values()))
    wb.save(path)


def _convert_audio_to_wav_16k_mono(input_path):
    output_path = os.path.join(
        tempfile.gettempdir(), f"kcc_google_{int(datetime.utcnow().timestamp() * 1000)}.wav"
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        input_path,
        "-ac",
        "1",
        "-ar",
        "16000",
        output_path,
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=90)
    if result.returncode != 0:
        raise RuntimeError("ffmpeg conversion failed")
    return output_path


def _get_audio_duration_seconds(file_path):
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                file_path,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            value = (result.stdout or "").strip()
            duration = float(value)
            if duration > 0:
                return duration
    except Exception:
        pass
    return None


# -----------------------------------------
# TRANSCRIPTION
# -----------------------------------------


def transcribe_file_elevenlabs(filepath):
    api_key = (os.environ.get("ELEVENLABS_API_KEY") or "").strip()
    if not api_key:
        return ""

    url = "https://api.elevenlabs.io/v1/speech-to-text"
    headers = {"xi-api-key": api_key}
    files = {"file": open(filepath, "rb")}
    data = {
        "model_id": "scribe_v2",
        "diarize": "true",
        "timestamps_granularity": "word",
        "tag_audio_events": "false",
    }
    try:
        response = requests.post(url, headers=headers, files=files, data=data, timeout=300)
        if response.status_code != 200:
            print("ElevenLabs transcription failed:", response.status_code, response.text)
            return ""
        payload = response.json()
        text = payload.get("text") or ""
        return _format_transcript_for_display(text)
    except Exception as e:
        print("ElevenLabs transcription failed:", e)
        return ""
    finally:
        try:
            files["file"].close()
        except Exception:
            pass


def transcribe_file_gemini(filepath):
    global _GEMINI_DISABLED_REASON

    api_key = _get_gemini_api_key()
    if not api_key:
        return ""

    genai = _import_google_genai_sdk("audio transcription")
    if genai is None:
        return ""

    model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    mime_type = mimetypes.guess_type(filepath)[0] or "application/octet-stream"
    prompt = """
Generate a verbatim transcript of the speech in this audio.

Rules:
- Return only the transcript text.
- Do not summarize.
- Do not add speaker labels unless they are obvious from the audio.
- Do not include markdown or explanations.
- Remove obvious non-speech promo or outro lines if they are unrelated to the call content.
""".strip()

    client = None
    uploaded_file = None
    try:
        client = genai.Client(api_key=api_key)
        uploaded_file = client.files.upload(file=filepath)
        response = client.models.generate_content(
            model=model_name,
            contents=[prompt, uploaded_file],
        )
        text = getattr(response, "text", "") or ""
        return _format_transcript_for_display(text)
    except Exception as e:
        error_text = str(e)
        if "API_KEY_INVALID" in error_text or "API key not valid" in error_text:
            if _GEMINI_DISABLED_REASON != "invalid_key":
                print("Gemini disabled: GEMINI_API_KEY was rejected by the API.")
                _GEMINI_DISABLED_REASON = "invalid_key"
            return ""
        print("Gemini audio transcription failed:", e)
        return ""
    finally:
        if client is not None and uploaded_file is not None:
            try:
                client.files.delete(name=uploaded_file.name)
            except Exception:
                pass


def gemini_refine_transcript(raw_transcript, alt_transcript=""):
    """
    Cleans ASR output while preserving meaning and factual content.
    """
    global _GEMINI_DISABLED_REASON

    api_key = _get_gemini_api_key()
    if not api_key:
        return ""

    raw_transcript = _format_transcript_for_display(raw_transcript)
    alt_transcript = _format_transcript_for_display(alt_transcript)
    if not raw_transcript:
        return ""

    genai = _import_gemini_sdk("transcript refinement")
    if genai is None:
        return ""

    model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    prompt = f"""
You are an ASR cleanup engine.
Return ONLY valid JSON:
{{
  "refined_transcript": "string"
}}

Rules:
- Do NOT add new facts.
- Preserve original meaning exactly.
- Fix punctuation, spacing, obvious ASR spelling errors.
- Keep Hinglish/code-mixed words when present.
- If uncertain, keep original wording.
- Remove obvious promo/outro junk unrelated to the actual call.
- Break long text into readable paragraphs.
- If the transcript clearly alternates between agent and customer, preserve those turns on separate lines.
- Do not summarize. Return the cleaned transcript only.

Primary transcript:
{raw_transcript}

Secondary transcript (optional):
{alt_transcript}
"""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0.1, "max_output_tokens": 1200},
        )
        parsed = _extract_json_object(getattr(response, "text", "") or "")
        if not parsed:
            return ""
        return _format_transcript_for_display(parsed.get("refined_transcript", ""))
    except Exception as e:
        error_text = str(e)
        if "API_KEY_INVALID" in error_text or "API key not valid" in error_text:
            if _GEMINI_DISABLED_REASON != "invalid_key":
                print("Gemini disabled: GEMINI_API_KEY was rejected by the API.")
                _GEMINI_DISABLED_REASON = "invalid_key"
            return ""
        print("Gemini transcript refinement failed:", e)
        return ""


def transcribe_file(filepath):
    # Use Gemini transcription only.
    gemini_text = transcribe_file_gemini(filepath)
    base_text = _normalize_whitespace(gemini_text)
    if not base_text:
        return ""

    max_refine_minutes = _env_float("TRANSCRIPT_REFINER_MAX_MINUTES", 20.0)
    max_refine_chars = int(_env_float("TRANSCRIPT_REFINER_MAX_CHARS", 30000))
    duration_seconds = _get_audio_duration_seconds(filepath)

    should_refine = _env_bool("ENABLE_TRANSCRIPT_REFINER", True)
    if duration_seconds is not None and duration_seconds > (max_refine_minutes * 60):
        should_refine = False
    if len(base_text) > max_refine_chars:
        should_refine = False

    if should_refine:
        refined = gemini_refine_transcript(base_text, "")
        if refined:
            return refined

    return base_text


# -----------------------------------------
# HINDI NORMALIZATION
# -----------------------------------------
HINDI_MAP = {
    "paisa": "money",
    "refund chahiye": "refund",
    "daam": "price",
    "khareedna": "buy",
    "booking": "booking",
    "delivery": "delivery",
}


def normalize_language(text):
    t = text.lower()
    for hi, en in HINDI_MAP.items():
        t = t.replace(hi, en)
    return t


# -----------------------------------------
# INTENT DETECTION
# -----------------------------------------
INTENTS = {
    "real_estate_sales": ["property", "flat", "villa", "floor plan"],
    "software_sales": ["software", "subscription", "demo"],
    "insurance_sales": ["insurance", "policy", "premium"],
    "automobile_sales": ["car", "vehicle", "test drive"],
    "generic_sales": ["buy", "purchase", "order"],
}


def detect_intents(text):
    scores = {}
    for intent, keywords in INTENTS.items():
        score = sum(1 for keyword in keywords if keyword in text)
        if score > 0:
            scores[intent] = score
    return [max(scores, key=scores.get)] if scores else ["general_call"]


def generate_local_summary(text):
    if not text:
        return "Not stated"
    sentences = _split_sentences(text)
    if len(sentences) <= 3:
        return f"Summary: {text}"
    
    first_few = " ".join(sentences[:2])
    last_few = " ".join(sentences[-2:])
    
    summary = f"Call Initiation: {first_few}\n"
    summary += f"Conversation Length: Approximately {len(sentences)} identifiable sentences.\n"
    summary += f"Conclusion / Resolution: {last_few}"
    return summary


# -----------------------------------------
# SENTIMENT
# -----------------------------------------
def analyze_sentiment(text):
    t = text.lower()
    pos_pattern = r"\b(good|great|happy|resolved|thank|excellent|awesome|perfect|helpful|love)\b"
    neg_pattern = r"\b(bad|angry|problem|issue|refund|terrible|awful|hate|worst|unhelpful|frustrated|cancel|delay|broken)\b"
    pos = len(re.findall(pos_pattern, t))
    neg = len(re.findall(neg_pattern, t))
    if pos > neg:
        return "positive"
    if neg > pos:
        return "negative"
    return "neutral"


def estimate_sentiment_confidence(text):
    t = text.lower()
    pos_pattern = r"\b(good|great|happy|resolved|thank|excellent|awesome|perfect|helpful|love)\b"
    neg_pattern = r"\b(bad|angry|problem|issue|refund|terrible|awful|hate|worst|unhelpful|frustrated|cancel|delay|broken)\b"
    pos = len(re.findall(pos_pattern, t))
    neg = len(re.findall(neg_pattern, t))
    total = pos + neg
    if total == 0:
        return 0.5
    margin = abs(pos - neg) / total
    confidence = 0.5 + (0.5 * margin)
    return max(0.0, min(1.0, round(confidence, 4)))


def _normalize_sentiment_label(value):
    label = str(value or "").strip().lower()
    if "pos" in label:
        return "positive"
    if "neg" in label:
        return "negative"
    return "neutral"


def gemini_summary(transcript):
    global _GEMINI_DISABLED_REASON

    api_key = _get_gemini_api_key()
    if not api_key or not transcript.strip():
        return ""

    genai = _import_gemini_sdk("summary")
    if genai is None:
        return ""

    model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    prompt = f"""
You are an expert call summarization engine.
Return ONLY valid JSON:
{{
  "summary": "string"
}}

Rules:
- Provide a cohesive, well-structured paragraph (4-6 sentences) summarizing the entire call.
- In the summary, specify the reason for the call, key discussions, problems faced, the agent's resolution, and next steps or outcome.
- Use a natural, professional writing style without using rigid section headings like "Call Purpose:" or "Final Outcome:".
- Focus purely on factual conversational details from the transcript.
- Ignore generic promotional script lines and automated messages unless directly relevant to the conversation.

Transcript:
{transcript}
"""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0.1, "max_output_tokens": 500},
        )
        parsed = _extract_json_object(getattr(response, "text", "") or "")
        if not parsed:
            return ""
        return _normalize_whitespace(parsed.get("summary", ""))
    except Exception as e:
        error_text = str(e)
        if "API_KEY_INVALID" in error_text or "API key not valid" in error_text:
            if _GEMINI_DISABLED_REASON != "invalid_key":
                print("Gemini disabled: GEMINI_API_KEY was rejected by the API.")
                _GEMINI_DISABLED_REASON = "invalid_key"
            return ""
        print("Gemini summary failed:", e)
        return ""


def gemini_analysis(transcript, fallback_intents):
    """
    Returns:
    {
      "summary": str,
      "sentiment": "positive|neutral|negative",
      "sentiment_confidence": float,
      "sentiment_reason": str,
      "emotion": str,
      "intents": [str]
    }
    """
    global _GEMINI_DISABLED_REASON

    api_key = _get_gemini_api_key()
    if not api_key or not transcript.strip():
        return None

    genai = _import_gemini_sdk("analysis")
    if genai is None:
        return None

    model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    prompt = f"""
You are an expert call transcript analyst. I need highly accurate insights from the following transcript.
Analyze the transcript and return your response ONLY as a valid JSON object matching this exact schema:

{{
  "summary": "string",
  "sentiment": "positive|neutral|negative",
  "sentiment_confidence": 0.0,
  "sentiment_reason": "string",
  "emotion": "string",
  "intents": ["string", "string"]
}}

Detailed Requirements:
1. "summary": Provide a clear, cohesive, and comprehensive paragraph (around 4-6 sentences) summarizing the call. Cover the reason for the call, key discussion points, customer issues/concerns, the agent's resolution, and any required next steps. Do not use restrictive headings like 'Call Purpose:'—write an effective executive summary.
2. "sentiment": Evaluate the overall tone of the customer. Must be exactly one of: "positive", "neutral", or "negative".
3. "sentiment_confidence": A decimal between 0.0 and 1.0 indicating how confident you are in the sentiment.
4. "sentiment_reason": One concise sentence explaining why you chose this sentiment, citing specific customer reactions or outcomes.
5. "emotion": The primary emotion displayed by the customer (e.g., "frustrated", "satisfied", "confused", "appreciative", "urgent").
6. "intents": 2-5 short tags capturing the topics of the conversation (e.g., "billing_issue", "product_inquiry", "cancellation").

Transcript:
{transcript}
"""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0.2, "max_output_tokens": 700},
        )

        text = getattr(response, "text", "") or ""
        parsed = _extract_json_object(text)
        if not parsed:
            return None

        summary = str(parsed.get("summary", "")).strip()
        sentiment = _normalize_sentiment_label(parsed.get("sentiment"))
        try:
            confidence = float(parsed.get("sentiment_confidence", 0.0))
        except Exception:
            confidence = 0.0
        confidence = max(0.0, min(1.0, confidence))
        sentiment_reason = _normalize_whitespace(parsed.get("sentiment_reason", ""))
        emotion = str(parsed.get("emotion", "")).strip()
        intents = parsed.get("intents")
        if not isinstance(intents, list):
            intents = fallback_intents
        intents = [str(x).strip() for x in intents if str(x).strip()]
        if not intents:
            intents = fallback_intents

        if not summary:
            return None

        return {
            "summary": summary,
            "sentiment": sentiment,
            "sentiment_confidence": confidence,
            "sentiment_reason": sentiment_reason,
            "emotion": emotion,
            "intents": intents,
        }
    except Exception as e:
        error_text = str(e)
        if "API_KEY_INVALID" in error_text or "API key not valid" in error_text:
            if _GEMINI_DISABLED_REASON != "invalid_key":
                print("Gemini disabled: GEMINI_API_KEY was rejected by the API.")
                _GEMINI_DISABLED_REASON = "invalid_key"
            return None
        print("Gemini analysis failed:", e)
        return None


# -----------------------------------------
# MAIN
# -----------------------------------------
def process_uploaded_audio(audio_path):
    filename = os.path.basename(audio_path)
    base = os.path.splitext(filename)[0]

    gemini_text = _normalize_whitespace(transcribe_file_gemini(audio_path))
    raw_transcript = gemini_text
    transcript_provider = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash") if gemini_text else "none"

    transcript = raw_transcript
    refined_transcript = ""
    transcript_refined = False

    if raw_transcript:
        max_refine_minutes = _env_float("TRANSCRIPT_REFINER_MAX_MINUTES", 20.0)
        max_refine_chars = int(_env_float("TRANSCRIPT_REFINER_MAX_CHARS", 30000))
        duration_seconds = _get_audio_duration_seconds(audio_path)

        should_refine = _env_bool("ENABLE_TRANSCRIPT_REFINER", True)
        if duration_seconds is not None and duration_seconds > (max_refine_minutes * 60):
            should_refine = False
        if len(raw_transcript) > max_refine_chars:
            should_refine = False

        if should_refine:
            refined_transcript = gemini_refine_transcript(raw_transcript, "")
            if refined_transcript:
                transcript = refined_transcript
                transcript_refined = True

    safe_write(os.path.join(TRANSCRIPT_DIR, base + ".txt"), transcript)

    normalized = normalize_language(transcript)
    fallback_intents = detect_intents(normalized)
    gemini_result = gemini_analysis(transcript, fallback_intents)
    if gemini_result:
        summary = gemini_result.get("summary") or ""
        sentiment = gemini_result["sentiment"]
        sentiment_confidence = gemini_result["sentiment_confidence"]
        sentiment_reason = gemini_result.get("sentiment_reason") or ""
        intents = gemini_result["intents"]
        emotion = gemini_result["emotion"] or "neutral"
        analysis_provider = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    else:
        summary = generate_local_summary(transcript)
        sentiment = analyze_sentiment(transcript)
        sentiment_confidence = estimate_sentiment_confidence(transcript)
        sentiment_reason = "Determined by local keyword analysis."
        intents = fallback_intents
        emotion = sentiment
        analysis_provider = "local-rule-based"

    conversion_words = ["purchase", "order", "buy", "confirmed"]
    is_converted = any(word in normalized for word in conversion_words)
    is_sales_call = any(intent.endswith("_sales") for intent in intents)

    row = {
        "file": filename,
        "call_id": base,
        "processed_at": _now_ts(),
        "summary": summary,
        "sentiment": sentiment,
        "sentiment_confidence": sentiment_confidence,
        "sentiment_reason": sentiment_reason,
        "intents": json.dumps(intents),
        "converted": is_converted,
    }

    write_excel(EXCEL_FILE, row)
    if is_converted:
        write_excel(CONVERTED_EXCEL_FILE, row)
    if is_sales_call:
        write_excel(SALES_CRM_FILE, row)

    write_excel(get_weekly_excel_file(), row)
    if is_sales_call:
        write_excel(get_weekly_sales_file(), row)

    return {
        "call_id": base,
        "transcript": transcript,
        "raw_transcript": raw_transcript,
        "refined_transcript": refined_transcript or transcript,
        "transcript_provider": transcript_provider,
        "transcript_refined": transcript_refined,
        "transcript_refiner": (
            os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
            if transcript_refined
            else ""
        ),
        "summary": summary,
        "sentiment": sentiment,
        "sentiment_confidence": sentiment_confidence,
        "sentiment_reason": sentiment_reason,
        "emotion": emotion,
        "intents": intents,
        "analysis_provider": analysis_provider,
        "converted": is_converted,
        "sales_call": is_sales_call,
    }


if __name__ == "__main__":
    print("process_audio.py ready")
