# server.py
import os
import openpyxl
import time
import subprocess
import wave
from datetime import datetime, timedelta
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from process_audio import process_uploaded_audio, get_weekly_excel_file
import mongodb

# -------------------------------------------------------
# APP
# -------------------------------------------------------
app = FastAPI(
    description="Audio processing backend using FastAPI + MongoDB",
    version="1.0.1"
)
from fastapi.responses import FileResponse
import os

@app.get("/download/overall")
def download_overall_calls():
    file_path = "results/analytics_results.xlsx"
    return FileResponse(
        file_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="overall_calls.xlsx"
    )

@app.get("/download/weekly-calls")
def download_weekly_calls():
    file_path = get_weekly_excel_file()  # your existing helper
    return FileResponse(
        file_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="weekly_calls.xlsx"
    )

@app.get("/download/weekly-sales")
def download_weekly_sales():
    file_path = "results/sales_crm.xlsx"
    return FileResponse(
        file_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="weekly_sales.xlsx"
    )

# -------------------------------------------------------
# CORS
# -------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# -------------------------------------------------------
# STARTUP
# -------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    db = mongodb.get_db()
    try:
        await db.command("ping")
        print("MongoDB Connected")
    except:
        print("MongoDB NOT Connected")

    try:
        await db.calls.create_index("expiresAt", expireAfterSeconds=0)
    except:
        pass

# -------------------------------------------------------
# WEEK START (MONDAY 00:00 UTC)
# -------------------------------------------------------
def start_of_current_week():
    now = datetime.utcnow()
    start = now - timedelta(days=now.weekday())
    return start.replace(hour=0, minute=0, second=0, microsecond=0)


def get_audio_duration_seconds(file_path: str):
    # First try ffprobe for broad format coverage (mp3, m4a, wav, etc.).
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

    # Fallback for WAV if ffprobe is unavailable.
    try:
        with wave.open(file_path, "rb") as wav_file:
            frames = wav_file.getnframes()
            rate = wav_file.getframerate()
            if rate > 0:
                duration = frames / float(rate)
                if duration > 0:
                    return duration
    except Exception:
        pass

    return None

# -------------------------------------------------------
# PROCESS AUDIO
# -------------------------------------------------------
@app.post("/process-audio")
async def process_audio_api(file: UploadFile = File(...)):
    temp_path = None
    try:
        timestamp = int(time.time() * 1000)
        temp_path = f"temp_{timestamp}_{file.filename}"

        with open(temp_path, "wb") as f:
            f.write(await file.read())

        duration_seconds = get_audio_duration_seconds(temp_path)
        result = await run_in_threadpool(process_uploaded_audio, temp_path)

        now = datetime.utcnow()
        unique_call_id = f"call_{timestamp}"

        doc = {
            "call_id": unique_call_id,
            "customer_id": result.get("customer_id", "NA"),
            "sentiment": str(result.get("sentiment", "neutral")).lower(),
            "sentiment_confidence": result.get("sentiment_confidence"),
            "sentiment_reason": result.get("sentiment_reason"),
            "emotion": result.get("emotion"),
            "summary": result.get("summary"),
            "transcript": result.get("transcript"),
            "raw_transcript": result.get("raw_transcript"),
            "refined_transcript": result.get("refined_transcript"),
            "transcript_provider": result.get("transcript_provider"),
            "transcript_refined": result.get("transcript_refined"),
            "transcript_refiner": result.get("transcript_refiner"),
            "analysis_provider": result.get("analysis_provider"),
            "tags": list(set(result.get("intents", []))),   # ⭐ Deduplicate tags
            "analysis": result.get("analysis", {}),
            "analysis_raw": result.get("analysis_raw", ""),
            "duration_seconds": duration_seconds,
            "created_at": now,
            "expiresAt": now + timedelta(days=30)
        }

        db = mongodb.get_db()
        await db.calls.insert_one(doc)

        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

        return {"status": "ok", "call_id": unique_call_id}

    except Exception as e:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(status_code=500, detail=str(e))

# -------------------------------------------------------
# SUMMARY STATS
# -------------------------------------------------------
@app.get("/stats/summary")
async def get_summary():
    db = mongodb.get_db()

    total_calls = await db.calls.count_documents({})
    positive_calls = await db.calls.count_documents({"sentiment": "positive"})

    rate = round((positive_calls / total_calls) * 100, 2) if total_calls > 0 else 0

    return {
        "total_calls": total_calls,
        "positive_calls": positive_calls,
        "conversion_rate": rate
    }

# -------------------------------------------------------
# ⭐ WEEKLY STATS + CORRECT TRENDING TOPICS
# -------------------------------------------------------
@app.get("/stats/weekly")
async def get_weekly_stats():
    db = mongodb.get_db()
    start_week = start_of_current_week()
    now = datetime.utcnow()

    # Weekly counts
    total = await db.calls.count_documents({"created_at": {"$gte": start_week}})
    positive = await db.calls.count_documents(
        {"created_at": {"$gte": start_week}, "sentiment": "positive"}
    )

    rate = round((positive / total) * 100, 2) if total > 0 else 0

    # -------------------------------------------------------
    # ⭐ FIX: Count each topic only ONCE per call
    # -------------------------------------------------------
    pipeline = [
        {"$match": {"created_at": {"$gte": start_week}}},
        {"$project": {"tags": 1}},  
        {"$project": {"unique_tags": {"$setUnion": ["$tags", []]}}},  # remove duplicates inside call
        {"$unwind": "$unique_tags"},  
        {"$group": {"_id": "$unique_tags", "count": {"$sum": 1}}},  # count 1 per call
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]

    trending = await db.calls.aggregate(pipeline).to_list(length=10)

    return {
        "period": "current_week",
        "week_start": start_week.isoformat() + "Z",
        "week_end": now.isoformat() + "Z",
        "total_calls": total,
        "positive_calls": positive,
        "conversion_rate": rate,
        "topics": trending
    }

# -------------------------------------------------------
# CALLS (CURRENT WEEK ONLY)
# -------------------------------------------------------
@app.get("/calls")
async def get_calls(limit: int = 50, skip: int = 0):
    db = mongodb.get_db()
    start_week = start_of_current_week()

    cursor = (
        db.calls.find({"created_at": {"$gte": start_week}})
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )

    results = []
    async for d in cursor:
        d["_id"] = None
        if isinstance(d.get("created_at"), datetime):
            d["created_at"] = d["created_at"].isoformat() + "Z"
        results.append(d)

    return results

# -------------------------------------------------------
# SINGLE CALL
# -------------------------------------------------------
@app.get("/calls/{call_id}")
async def get_call(call_id: str):
    db = mongodb.get_db()
    doc = await db.calls.find_one({"call_id": call_id})

    if not doc:
        raise HTTPException(status_code=404, detail="Call not found")

    doc["_id"] = None
    if isinstance(doc.get("created_at"), datetime):
        doc["created_at"] = doc["created_at"].isoformat() + "Z"

    return doc

@app.get("/stats/weekly")
async def get_weekly_stats():
    db = mongodb.get_db()
    start_week = start_of_current_week()
    now = datetime.utcnow()

    # ---------------------------
    # Weekly call counts
    # ---------------------------
    total = await db.calls.count_documents({
        "created_at": {"$gte": start_week}
    })

    positive = await db.calls.count_documents({
        "created_at": {"$gte": start_week},
        "sentiment": "positive"
    })

    rate = round((positive / total) * 100, 2) if total > 0 else 0

    # ---------------------------
    # ⭐ FINAL FIXED TRENDING TOPICS ⭐
    # ---------------------------
    # Guarantee:
    #   - Only calls from this week
    #   - Only unique topics per call
    #   - Total topic count can NEVER exceed total calls
    #
    pipeline = [
        {"$match": {"created_at": {"$gte": start_week}}},
        
        # remove duplicates inside a single call (e.g., ["billing","billing"])
        {"$project": {"unique_tags": {"$setUnion": ["$tags", []]}}},
        
        {"$unwind": "$unique_tags"},

        # group by tag but count only 1 per call
        {"$group": {
            "_id": "$unique_tags",
            "count": {"$sum": 1}
        }},

        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]

    trending = await db.calls.aggregate(pipeline).to_list(length=10)

    # Extra safety: ensure count never exceeds weekly total calls
    for t in trending:
        if t["count"] > total:
            t["count"] = total

    return {
        "period": "current_week",
        "week_start": start_week.isoformat() + "Z",
        "week_end": now.isoformat() + "Z",
        "total_calls": total,
        "positive_calls": positive,
        "conversion_rate": rate,
        "topics": trending
    }
    # -------------------------------------------------------
# NEW API → GET CALLS BY TOPIC
# -------------------------------------------------------
@app.get("/calls/topic/{topic_name}")
async def get_calls_by_topic(topic_name: str):
    db = mongodb.get_db()
    start_week = start_of_current_week()

    cursor = (
        db.calls.find({
            "created_at": {"$gte": start_week},
            "tags": topic_name
        }).sort("created_at", -1)
    )

    results = []
    async for doc in cursor:
        doc["_id"] = None
        if isinstance(doc.get("created_at"), datetime):
            doc["created_at"] = doc["created_at"].isoformat() + "Z"
        results.append(doc)

    return {"topic": topic_name, "count": len(results), "calls": results}

# -------------------------------------------------------
# RUN
# -------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
