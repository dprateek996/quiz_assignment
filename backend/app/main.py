from fastapi import FastAPI, UploadFile, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.database import connect_db, disconnect_db, db
from app.services import chapter_service, quiz_service
from app.schemas.quiz import QuizGenerateRequest, QuizSubmitRequest, AskChapterRequest

# --- RATE LIMITER SETUP ---
limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await disconnect_db()

app = FastAPI(title="ChapterIQ API", lifespan=lifespan)

# Add Rate Limit Error Handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 1. HEALTH CHECK ---
@app.get("/health")
async def health_check():
    return {"status": "ok", "db_connected": db.is_connected()}

# --- 2. CHAPTER ENDPOINTS ---
@app.post("/api/chapters")
@limiter.limit("5/minute") 
async def upload_chapter(request: Request, file: UploadFile, subject: str = Form(...), title: str = Form(...)):
    return await chapter_service.process_pdf(file, subject, title)

@app.get("/api/dashboard/{user_id}")
async def get_dashboard_endpoint(user_id: str):
    return await chapter_service.get_user_dashboard(user_id)

@app.delete("/api/chapters/{chapter_id}")
async def delete_chapter_endpoint(chapter_id: str):
    return await chapter_service.delete_chapter(chapter_id)

@app.put("/api/chapters/{chapter_id}/progress")
async def track_progress(chapter_id: str, user_id: str, time_spent: int, scroll_pct: float):
    return await chapter_service.update_progress(chapter_id, user_id, time_spent, scroll_pct)

# --- 3. TUTOR ENDPOINT ---
@app.post("/api/chapters/{chapter_id}/ask")
@limiter.limit("20/minute") 
async def ask_chapter_endpoint(request: Request, chapter_id: str, req: AskChapterRequest):
    return await quiz_service.chat_with_chapter(chapter_id, req.query)

# --- 4. QUIZ ENDPOINTS ---
@app.post("/api/quizzes/generate/{chapter_id}")
@limiter.limit("10/minute")
async def generate_quiz_endpoint(request: Request, chapter_id: str, req: QuizGenerateRequest):
    return await quiz_service.generate_quiz(chapter_id, req)

@app.post("/api/quizzes/{quiz_id}/submit")
async def submit_quiz_endpoint(quiz_id: str, req: QuizSubmitRequest):
    return await quiz_service.grade_quiz(quiz_id, req)

# --- 5. ANALYTICS ---
@app.get("/api/users/{user_id}/performance")
async def get_user_performance_endpoint(user_id: str):
    return await quiz_service.get_user_analytics(user_id)

@app.get("/api/chapters/{chapter_id}/analytics")
async def get_chapter_analytics_endpoint(chapter_id: str):
    return await quiz_service.get_chapter_stats(chapter_id)