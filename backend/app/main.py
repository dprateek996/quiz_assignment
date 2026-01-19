from fastapi import FastAPI, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import connect_db, disconnect_db
from app.services import chapter_service, quiz_service
from app.schemas.quiz import QuizGenerateRequest, QuizSubmitRequest

app = FastAPI(title="Quiz Backend API")

# --- FORCE CORS ---
app.add_middleware(
    CORSMiddleware,
    # Explicitly list the frontend URL instead of "*"
    allow_origins=["http://127.0.0.1:5501", "http://localhost:5501"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ------------------

@app.on_event("startup")
async def startup():
    await connect_db()

@app.on_event("shutdown")
async def shutdown():
    await disconnect_db()

@app.post("/api/chapters")
async def upload_chapter(
    file: UploadFile, 
    subject: str = Form(...), 
    title: str = Form(...)
):
    return await chapter_service.process_pdf(file, subject, title)

@app.put("/api/chapters/{chapter_id}/progress")
async def track_progress(chapter_id: str, user_id: str, time_spent: int, scroll_pct: float):
    return await chapter_service.update_progress(chapter_id, user_id, time_spent, scroll_pct)

@app.post("/api/quizzes/generate/{chapter_id}")
async def generate_quiz_endpoint(chapter_id: str, req: QuizGenerateRequest):
    return await quiz_service.generate_quiz(chapter_id, req)

@app.post("/api/quizzes/{quiz_id}/submit")
async def submit_quiz_endpoint(quiz_id: str, req: QuizSubmitRequest):
    return await quiz_service.grade_quiz(quiz_id, req)