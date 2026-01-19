import json
from app.core.database import db
from app.llm.gemini_client import llm
from app.llm.prompts import QUIZ_GENERATION_PROMPT, GRADING_PROMPT
from langchain_core.messages import HumanMessage
from app.schemas.quiz import QuizGenerateRequest, QuizSubmitRequest

async def generate_quiz(chapter_id: str, req: QuizGenerateRequest):
    # 1. Check DB Cache
    existing = await db.quiz.find_first(
        where={
            "chapter_id": chapter_id, 
            "difficulty": req.difficulty
        }
    )
    if existing:
        return existing

    # 2. Fetch Chapter with content_text
    chapter = await db.chapter.find_unique(where={"id": chapter_id})
    if not chapter:
        raise ValueError("Chapter not found")

    # 3. Generate via Gemini using extracted text
    prompt_text = QUIZ_GENERATION_PROMPT.format(
        difficulty=req.difficulty,
        num_mcq=req.num_mcq,
        num_short=req.num_short,
        num_numerical=req.num_numerical
    )
    
    # Combine prompt with chapter content
    full_prompt = f"""Here is the chapter content:

{chapter.content_text[:15000]}

---

{prompt_text}"""
    
    message = HumanMessage(content=full_prompt)
    
    response = await llm.ainvoke([message])
    
    # Cleaning the response to ensure valid JSON
    content_str = response.content.strip()
    if content_str.startswith("```json"):
        content_str = content_str[7:]
    if content_str.endswith("```"):
        content_str = content_str[:-3]
        
    quiz_json = json.loads(content_str)

    # 4. Store in DB
    quiz = await db.quiz.create(
        data={
            "chapter_id": chapter_id,
            "difficulty": req.difficulty,
            "questions": json.dumps(quiz_json['questions']),
            "variant_hash": "hash_placeholder"
        }
    )
    return quiz

async def grade_quiz(quiz_id: str, req: QuizSubmitRequest):
    quiz = await db.quiz.find_unique(where={"id": quiz_id}, include={"chapter": True})
    questions = json.loads(quiz.questions)
    
    total_score = 0
    results = {}
    weak_topics = []

    for q in questions:
        q_id = q['q_id']
        u_ans = req.answers.get(q_id)
        
        score = 0.0
        
        if q['type'] == 'mcq':
            # Local Grading
            if str(u_ans) == str(q['correct_answer']):
                score = 1.0
            else:
                weak_topics.append(q['topic'])
        else:
            # AI Grading with chapter text as context
            prompt = f"""Here is the chapter content for context:

{quiz.chapter.content_text[:10000]}

---

{GRADING_PROMPT.format(
    question=q['question'],
    correct_answer=q.get('correct_answer', 'Refer to text'),
    user_answer=u_ans
)}"""
            
            message = HumanMessage(content=prompt)
            
            ai_res = await llm.ainvoke([message])
            
            # Clean JSON
            content_str = ai_res.content.strip()
            if content_str.startswith("```json"):
                content_str = content_str[7:]
            if content_str.endswith("```"):
                content_str = content_str[:-3]

            eval_data = json.loads(content_str)
            score = float(eval_data['score'])
            if score < 0.5: weak_topics.append(q['topic'])

        total_score += score
        results[q_id] = score

    # Store Attempt
    attempt = await db.quizattempt.create(
        data={
            "user_id": req.user_id,
            "quiz_id": quiz_id,
            "answers": json.dumps(req.answers),
            "scores": json.dumps(results),
            "total_score": total_score,
            "weak_topics": json.dumps(weak_topics)
        }
    )
    return attempt