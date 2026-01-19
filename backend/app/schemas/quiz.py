from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class QuizGenerateRequest(BaseModel):
    difficulty: str = "medium"
    num_mcq: int = 5
    num_short: int = 3
    num_numerical: int = 2

class QuizSubmitRequest(BaseModel):
    user_id: str
    answers: Dict[str, Any]  # { "q1": 0, "q2": "Answer text" } 