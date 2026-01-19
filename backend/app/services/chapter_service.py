import os
import shutil
import fitz  # PyMuPDF
from fastapi import UploadFile
from app.core.database import db
import uuid

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF using PyMuPDF"""
    text = ""
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text += page.get_text()
    return text

async def process_pdf(file: UploadFile, subject: str, title: str):
    # 1. Save Temp
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # 2. Extract text from PDF
        content_text = extract_text_from_pdf(temp_path)
        
        # 3. Generate a unique ID for gemini_file_id (since we're not using Gemini File API anymore)
        unique_id = f"local_{uuid.uuid4().hex[:16]}"
        
        # 4. Save to DB with extracted text
        chapter = await db.chapter.create(
            data={
                "gemini_file_id": unique_id,
                "content_text": content_text,
                "subject": subject,
                "title": title,
                "status": "indexed"
            }
        )
        return chapter
    finally:
        # 5. Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)

async def update_progress(chapter_id: str, user_id: str, time_spent: int, scroll_pct: float):
    ESTIMATED_TIME = 600 
    
    is_completed = False
    if scroll_pct > 0.90 and time_spent > (ESTIMATED_TIME * 0.4):
        is_completed = True

    progress = await db.userprogress.upsert(
        where={
            "id": "temp-id-placeholder" 
        },
        data={
            "create": {
                "user_id": user_id,
                "chapter_id": chapter_id,
                "time_spent": time_spent,
                "scroll_progress": scroll_pct,
                "is_completed": is_completed,
                "completion_method": "time_scroll_algo"
            },
            "update": {
                "time_spent": time_spent,
                "scroll_progress": scroll_pct,
                "is_completed": is_completed
            }
        }
    )
    return progress