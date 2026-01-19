import os
import shutil
import tempfile
import time
import hashlib
from fastapi import UploadFile
from app.core.database import db
import google.generativeai as genai
from dotenv import load_dotenv
from pathlib import Path

base_dir = Path(__file__).resolve().parent.parent.parent
load_dotenv(dotenv_path=base_dir / ".env")
API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

if API_KEY:
    genai.configure(api_key=API_KEY)

# --- IDEMPOTENCY HELPER ---
def calculate_file_hash(file_path: str) -> str:
    """Calculates SHA256 hash of a file to detect duplicates."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

# --- 1. UPLOAD & PROCESS (With Idempotency & Gemini RAG) ---
async def process_pdf(file: UploadFile, subject: str, title: str):
    # Save to Temp File
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        shutil.copyfileobj(file.file, tmp)
        temp_path = tmp.name

    try:
        # A. IDEMPOTENCY CHECK
        file_hash = calculate_file_hash(temp_path)
        
        if not db.is_connected(): await db.connect()

        # Check if file already exists in DB
        existing_chapter = await db.chapter.find_unique(where={"content_hash": file_hash})
        if existing_chapter:
            print(f"♻️ Idempotency Hit: File '{file.filename}' already exists. Returning cached version.")
            return existing_chapter

        # B. UPLOAD TO GEMINI (If new)
        print(f"Uploading {file.filename} to Gemini 2.0 Files...")
        gemini_file = genai.upload_file(path=temp_path, mime_type="application/pdf")
        
        # Wait for Processing
        print(f"Waiting for processing: {gemini_file.name}")
        while gemini_file.state.name == "PROCESSING":
            time.sleep(1)
            gemini_file = genai.get_file(gemini_file.name)

        if gemini_file.state.name != "ACTIVE":
            raise Exception(f"File indexing failed: {gemini_file.state.name}")

        print(f"File Ready! ID: {gemini_file.name}")

        # C. SAVE TO DB
        chapter = await db.chapter.create(
            data={
                "gemini_file_id": gemini_file.name, 
                "content_text": "Stored in Gemini RAG", 
                "content_hash": file_hash, # Save hash for next time
                "subject": subject,
                "title": title,
                "status": "indexed"
            }
        )
        return chapter

    except Exception as e:
        print(f"Error: {e}")
        raise e
    finally:
        if os.path.exists(temp_path): os.remove(temp_path)

# --- 2. DASHBOARD DATA ---
async def get_user_dashboard(user_id: str):
    if not db.is_connected(): await db.connect()
    
    chapters = await db.chapter.find_many(order={"created_at": "desc"})
    progress_records = await db.userprogress.find_many(where={"user_id": user_id})
    progress_map = {p.chapter_id: p for p in progress_records}

    dashboard_data = []
    for chap in chapters:
        prog = progress_map.get(chap.id)
        completion_pct = float(prog.scroll_progress or 0) * 100 if prog else 0.0
        dashboard_data.append({
            "chapter_id": chap.id,
            "title": chap.title,
            "subject": chap.subject,
            "progress": round(completion_pct),
            "is_completed": prog.is_completed if prog else False
        })
    return dashboard_data

# --- 3. DELETE LOGIC (With Cascade Fix) ---
async def delete_chapter(chapter_id: str):
    if not db.is_connected(): await db.connect()
    
    chapter = await db.chapter.find_unique(where={"id": chapter_id})
    if not chapter: raise Exception("Chapter not found")
        
    # Delete from Google Cloud
    try:
        if chapter.gemini_file_id:
            genai.delete_file(chapter.gemini_file_id)
            print(f"Deleted remote file: {chapter.gemini_file_id}")
    except Exception as e:
        print(f"Warning: Remote delete failed (might be already gone): {e}")

    # Cascade Delete from DB
    quizzes = await db.quiz.find_many(where={"chapter_id": chapter_id})
    quiz_ids = [q.id for q in quizzes]
    
    if quiz_ids:
        # Delete attempts first (Foreign Key Constraint)
        await db.quizattempt.delete_many(where={"quiz_id": {"in": quiz_ids}})
        # Then quizzes
        await db.quiz.delete_many(where={"chapter_id": chapter_id})
    
    # Delete progress
    await db.userprogress.delete_many(where={"chapter_id": chapter_id})
    
    # Finally delete chapter
    await db.chapter.delete(where={"id": chapter_id})
    return {"message": "Deleted successfully"}

# --- 4. MASTERY / PROGRESS LOGIC ---
async def update_progress(chapter_id: str, user_id: str, time_spent: int, scroll_pct: float):
    # This is for manual scroll updates if you implement them in frontend later
    return await update_mastery(chapter_id, user_id, "scroll", 0)

async def update_mastery(chapter_id: str, user_id: str, source: str, score_pct: float = 0):
    if not db.is_connected(): await db.connect()

    current = await db.userprogress.find_first(
        where={"user_id": user_id, "chapter_id": chapter_id}
    )
    current_val = float(current.scroll_progress) if current else 0.0
    is_completed = current.is_completed if current else False
    new_val = current_val

    # Logic:
    if source == 'chat':
        # Chatting boosts progress up to 80%
        if current_val < 0.8: 
            new_val = min(0.8, current_val + 0.05)
            
    elif source == 'quiz':
        # Quiz is the authority
        if score_pct == 1.0: 
            new_val = 1.0
            is_completed = True
        elif score_pct < 0.4:
            # Penalty: If they fail quiz, drop progress to match quiz score
            if current_val > score_pct: new_val = score_pct 
        else:
            # Improve progress if quiz score is higher
            new_val = max(current_val, score_pct)

    if current:
        await db.userprogress.update(
            where={"id": current.id},
            data={"scroll_progress": new_val, "is_completed": is_completed}
        )
    else:
        await db.userprogress.create(
            data={
                "user_id": user_id,
                "chapter_id": chapter_id,
                "scroll_progress": new_val,
                "is_completed": is_completed,
                "completion_method": source
            }
        )