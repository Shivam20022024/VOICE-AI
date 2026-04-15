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

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None

# OLLAMA CONFIG
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")
OLLAMA_TIMEOUT = 900

# -----------------------------------------
# CONFIG
# -----------------------------------------
TRANSCRIPT_DIR = "transcripts"
RESULTS_DIR = "results"

EXCEL_FILE = os.path.join(RESULTS_DIR, "analytics_results.xlsx")
CONVERTED_EXCEL_FILE = os.path.join(RESULTS_DIR, "converted_calls.xlsx")
SALES_CRM_FILE = os.path.join(RESULTS_DIR, "sales_crm.xlsx")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

_WHISPER_MODEL_INSTANCE = None

def get_whisper_model():
    global _WHISPER_MODEL_INSTANCE
    if _WHISPER_MODEL_INSTANCE is None:
        if WhisperModel is None:
            raise ImportError("faster-whisper is not installed. Please install it using 'pip install faster-whisper'.")
        print("Loading local Faster-Whisper base model... this may take a few seconds on first run.")
        _WHISPER_MODEL_INSTANCE = WhisperModel("base", device="cpu", compute_type="int8")
    return _WHISPER_MODEL_INSTANCE

def ollama_generate(prompt, enforce_json=False):
    data = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }
    if enforce_json:
        data["format"] = "json"

    try:
        response = requests.post(OLLAMA_API_URL, json=data, timeout=OLLAMA_TIMEOUT)
        response.raise_for_status()
        return response.json().get("response", "")
    except Exception as e:
        print(f"Ollama generation failed: {e}. Is Ollama running on {OLLAMA_API_URL}?")
        return ""


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


def transcribe_file_local(filepath):
    try:
        model = get_whisper_model()
        segments, info = model.transcribe(filepath, beam_size=5)
        text = " ".join([segment.text for segment in segments])
        return _format_transcript_for_display(text)
    except Exception as e:
        print("Local audio transcription failed:", e)
        return ""


def local_refine_transcript(raw_transcript, alt_transcript=""):
    """
    Cleans ASR output using local Ollama model.
    """
    raw_transcript = _format_transcript_for_display(raw_transcript)
    if not raw_transcript:
        return ""

    prompt = f"""
You are a highly accurate ASR cleanup engine.
Return ONLY valid JSON:
{{
  "refined_transcript": "string"
}}

Rules:
- Do NOT add new facts. Preserve the original meaning exactly.
- Fix punctuation, spacing, grammar, and obvious ASR spelling errors to make it highly professional.
- Keep Hinglish/code-mixed words when present.
- Eliminate obvious promo/outro junk unrelated to the actual call.
- Explicitly format the text as a clear two-way conversation. Every turn must start with a speaker label ("Agent:" or "Customer:") on a new line. Infer the speaker from context if missing.
- Do not summarize. Return only the cleaned, well-formatted transcript capturing the accurate dialogue.

Primary transcript:
{raw_transcript}
"""
    try:
        response_text = ollama_generate(prompt, enforce_json=True)
        parsed = _extract_json_object(response_text)
        if not parsed:
            return ""
        return _format_transcript_for_display(parsed.get("refined_transcript", ""))
    except Exception as e:
        print("Local transcript refinement failed:", e)
        return ""


def transcribe_file(filepath):
    # Use Local transcription only.
    local_text = transcribe_file_local(filepath)
    base_text = _normalize_whitespace(local_text)
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
        refined = local_refine_transcript(base_text, "")
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


def local_summary(transcript):
    if not transcript.strip():
        return ""

    prompt = f"""
You are an expert call summarization engine.
Return ONLY valid JSON:
{{
  "summary": "string"
}}

Rules:
- Provide a highly accurate, professional summary of the entire call.
- Format the summary to reflect a two-way conversation narrative (e.g., detailing the back-and-forth flow: what the Customer stated/requested vs. how the Agent responded/resolved it).
- Ensure it reads like a professional interaction report, capturing the core issue, key dialogue exchange, and the final resolution or next steps.
- Focus purely on factual conversational details from the transcript.
- Ignore generic promotional script lines and automated messages.

Transcript:
{transcript}
"""
    try:
        response_text = ollama_generate(prompt, enforce_json=True)
        parsed = _extract_json_object(response_text)
        if not parsed:
            return ""
        return _normalize_whitespace(parsed.get("summary", ""))
    except Exception as e:
        print("Local summary failed:", e)
        return ""


def local_analysis(transcript, fallback_intents):
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
    if not transcript.strip():
        return None

    prompt = f"""
You are an expert call transcript analyst. I need highly accurate and professional insights from the following transcript.
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
1. "summary": Provide a highly accurate, professional summary of the call. Structure the summary to clearly reflect the two-way nature of the conversation—highlighting the back-and-forth dialogue, what the Customer expressed/requested, and exactly how the Agent responded and resolved the situation. Ensure all critical context is captured in a cohesive narrative.
2. "sentiment": Evaluate the overall tone of the customer with high accuracy. Must be exactly one of: "positive", "neutral", or "negative". Focus strictly on the customer's disposition throughout the interaction.
3. "sentiment_confidence": A decimal between 0.0 and 1.0 indicating how confident you are in the sentiment. Be mathematically precise.
4. "sentiment_reason": One concise sentence accurately explaining why you chose this sentiment, citing specific customer phrasing, reactions, or final outcome.
5. "emotion": The primary emotion displayed by the customer (e.g., "frustrated", "satisfied", "confused", "appreciative", "urgent").
6. "intents": 2-5 short tags accurately capturing the topics of the conversation (e.g., "billing_issue", "product_inquiry", "cancellation").

Transcript:
{transcript}
"""
    try:
        response_text = ollama_generate(prompt, enforce_json=True)
        parsed = _extract_json_object(response_text)
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
        print("Local analysis failed:", e)
        return None


# -----------------------------------------
# MAIN
# -----------------------------------------
def process_uploaded_audio(audio_path):
    filename = os.path.basename(audio_path)
    base = os.path.splitext(filename)[0]

    local_text = _normalize_whitespace(transcribe_file_local(audio_path))
    raw_transcript = local_text
    transcript_provider = "faster-whisper" if local_text else "none"

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
            refined_transcript = local_refine_transcript(raw_transcript, "")
            if refined_transcript:
                transcript = refined_transcript
                transcript_refined = True

    safe_write(os.path.join(TRANSCRIPT_DIR, base + ".txt"), transcript)

    normalized = normalize_language(transcript)
    fallback_intents = detect_intents(normalized)
    local_result = local_analysis(transcript, fallback_intents)
    if local_result:
        summary = local_result.get("summary") or ""
        sentiment = local_result["sentiment"]
        sentiment_confidence = local_result["sentiment_confidence"]
        sentiment_reason = local_result.get("sentiment_reason") or ""
        intents = local_result["intents"]
        emotion = local_result["emotion"] or "neutral"
        analysis_provider = OLLAMA_MODEL
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
            OLLAMA_MODEL
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
