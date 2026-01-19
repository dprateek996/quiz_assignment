from langchain_core.prompts import PromptTemplate

QUIZ_GENERATION_PROMPT = """
You are an expert teacher. Based on the provided document content, generate a quiz.
Context: The document is attached to this request.

Requirements:
- Difficulty: {difficulty}
- {num_mcq} Multiple Choice Questions.
- {num_short} Short Answer Questions.
- {num_numerical} Numerical Problems.

Output STRICT JSON format:
{{
    "questions": [
        {{
            "q_id": "unique_string",
            "type": "mcq|short|numerical",
            "question": "Question text...",
            "options": ["A", "B", "C", "D"], // Only for MCQ
            "correct_answer": "index (0-3) or text answer",
            "topic": "Specific subtopic"
        }}
    ]
}}
"""

GRADING_PROMPT = """
You are a strict grader.
Context: Refer to the uploaded chapter content.

Question: {question}
Correct Answer/Concept: {correct_answer}
Student Answer: {user_answer}

Task:
1. Grade the answer from 0.0 to 1.0.
2. Provide short feedback (max 1 sentence).

Output STRICT JSON:
{{
    "score": 0.0,
    "feedback": "string"
}}
"""