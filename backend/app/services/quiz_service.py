import json
import os
from pathlib import Path
from app.core.database import db
import google.generativeai as genai
from dotenv import load_dotenv
from app.services import chapter_service 

# --- SETUP API KEY ---
base_dir = Path(__file__).resolve().parent.parent.parent
load_dotenv(dotenv_path=base_dir / ".env")
API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

if API_KEY:
    genai.configure(api_key=API_KEY)

MODEL_NAME = "gemini-2.0-flash-exp"

# --- 1. CHAT ---
async def chat_with_chapter(chapter_id: str, query: str, user_id: str = "demo-user"):
    if not db.is_connected(): await db.connect()
    
    chapter = await db.chapter.find_unique(where={"id": chapter_id})
    if not chapter: raise Exception("Chapter not found")

    try:
        remote_file = genai.get_file(chapter.gemini_file_id)
    except:
        raise Exception("File Reference lost. Re-upload PDF.")

    model = genai.GenerativeModel(MODEL_NAME)

    final_prompt = f"""
    You are an AI Tutor.
    USER QUESTION: "{query}"
    
    INSTRUCTIONS:
    1. Answer the USER QUESTION directly based on the PDF.
    2. Keep it concise and helpful.
    3. If asked to summarize, provide bullet points.
    """

    try:
        response = model.generate_content([final_prompt, remote_file])
        await chapter_service.update_mastery(chapter_id, user_id, source="chat")
        return {"answer": response.text}
    except Exception as e:
        return {"answer": f"AI Error: {str(e)}"}

# --- 2. QUIZ GENERATION ---
async def generate_quiz(chapter_id: str, req):
    if not db.is_connected(): await db.connect()
    chapter = await db.chapter.find_unique(where={"id": chapter_id})
    
    try:
        remote_file = genai.get_file(chapter.gemini_file_id)
    except:
        raise Exception("File Reference lost.")

    model = genai.GenerativeModel(MODEL_NAME)

    context_instruction = ""
    if hasattr(req, 'chat_history') and req.chat_history:
        relevant_history = [msg for msg in req.chat_history if "Hello!" not in msg.get('text', '')]
        if relevant_history:
            history_text = "\n".join([f"{msg['role']}: {msg['text']}" for msg in relevant_history])
            context_instruction = f"""
            CONTEXT:
            {history_text}
            INSTRUCTION:
            Generate at least 50% of questions based on the topics discussed in the context above.
            """

    final_prompt = f"""
    Create a quiz based on the PDF.
    REQUIREMENTS:
    - {req.num_mcq} MCQs, {req.num_short} Short, {req.num_numerical} Numerical.
    - Output strictly valid JSON array.
    
    {context_instruction}
    
    JSON STRUCTURE:
    {{
        "q_id": "unique_id",
        "type": "mcq" | "short" | "numerical",
        "question": "Question text",
        "options": ["A", "B", "C", "D"], 
        "answer": "Exact Correct Answer Text",
        "topic": "Concept"
    }}
    """

    try:
        response = model.generate_content(
            [final_prompt, remote_file],
            generation_config={"response_mime_type": "application/json"}
        )
        questions_list = json.loads(response.text)
        
        quiz = await db.quiz.create(
            data={
                "chapter_id": chapter_id,
                "questions": json.dumps(questions_list), 
                "difficulty": req.difficulty
            }
        )
        return {"id": quiz.id, "chapter_id": quiz.chapter_id, "questions": questions_list}
    except Exception as e:
        print(f"Error: {e}")
        raise Exception("Quiz Generation Failed")

# --- 3. GRADING ---
async def ai_grade_answer(question, correct, user_ans):
    if not user_ans: return 0.0, "No answer"
    model = genai.GenerativeModel(MODEL_NAME)
    prompt = f"""
    Grade answer (0.0 to 1.0) and brief feedback.
    Q: {question}
    Correct: {correct}
    Student: {user_ans}
    JSON: {{ "score": 0.0, "feedback": "text" }}
    """
    try:
        res = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        d = json.loads(res.text)
        return float(d.get("score", 0)), d.get("feedback", "")
    except: return 0.0, "Error"

async def grade_quiz(quiz_id: str, req):
    if not db.is_connected(): await db.connect()
    quiz = await db.quiz.find_unique(where={"id": quiz_id})
    questions = quiz.questions
    
    total_score = 0
    results = {}
    weak_topics = []
    feedback_map = {}

    for q in questions:
        qid = str(q.get("q_id"))
        user_ans = str(req.answers.get(qid, "")).strip().lower()
        correct = str(q["answer"]).strip().lower()
        score = 0.0
        fb = ""

        if q["type"] == "short":
            score, fb = await ai_grade_answer(q["question"], q["answer"], user_ans)
        elif q["type"] == "numerical":
            if user_ans == correct: score = 1.0; fb = "Correct"
            else: fb = f"Incorrect. Answer: {correct}"
        elif q["type"] == "mcq":
            if user_ans == correct: score = 1.0; fb = "Correct"
            elif user_ans.isdigit():
                opts = q.get("options", [])
                if int(user_ans) < len(opts) and opts[int(user_ans)].lower() == correct:
                    score = 1.0; fb = "Correct"
                else: fb = "Incorrect"
            else: fb = "Incorrect"

        results[qid] = score
        feedback_map[qid] = fb
        total_score += score
        if score < 0.5: weak_topics.append(q.get("topic", "General"))

    pct = total_score / len(questions) if questions else 0
    
    await chapter_service.update_mastery(quiz.chapter_id, req.user_id, "quiz", pct)

    await db.quizattempt.create(
        data={
            "quiz_id": quiz_id,
            "user_id": req.user_id,
            "answers": json.dumps(req.answers),
            "scores": json.dumps(results),
            "total_score": float(total_score),
            "weak_topics": json.dumps(weak_topics)
        }
    )
    
    return {"total_score": total_score, "percentage": pct, "weak_topics": weak_topics, "scores": results, "feedback": feedback_map}

# --- 4. ANALYTICS ---
async def get_user_analytics(user_id: str):
    if not db.is_connected(): await db.connect()
    attempts = await db.quizattempt.find_many(where={"user_id": user_id})
    if not attempts: return {"message": "No data"}
    avg = sum([float(a.total_score) for a in attempts]) / len(attempts)
    return {"user_id": user_id, "quizzes": len(attempts), "avg_score": round(avg, 2)}

async def get_chapter_stats(chapter_id: str):
    if not db.is_connected(): await db.connect()
    quizzes = await db.quiz.find_many(where={"chapter_id": chapter_id})
    quiz_ids = [q.id for q in quizzes]
    attempts = await db.quizattempt.find_many(where={"quiz_id": {"in": quiz_ids}})
    if not attempts: return {"message": "No data"}
    avg = sum([float(a.total_score) for a in attempts]) / len(attempts)
    return {"chapter_id": chapter_id, "attempts": len(attempts), "avg_score": round(avg, 2)}