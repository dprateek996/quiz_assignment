from pydantic import BaseModel, field_validator, Field
from typing import Dict, Optional, List, Any

class QuizGenerateRequest(BaseModel):
    difficulty: str = Field(..., pattern="^(easy|medium|hard)$")
    num_mcq: int = Field(..., ge=0, le=20)
    num_short: int = Field(..., ge=0, le=20)
    num_numerical: int = Field(..., ge=0, le=20)
    chat_history: Optional[List[Dict[str, Any]]] = None 

    @field_validator('num_numerical')
    @classmethod
    def validate_total(cls, v, info):
        data = info.data
        total = data.get('num_mcq', 0) + data.get('num_short', 0) + v
        if total == 0:
            raise ValueError('Total questions must be at least 1')
        if total > 50:
            raise ValueError('Total questions cannot exceed 50')
        return v

class QuizSubmitRequest(BaseModel):
    user_id: str
    answers: Dict[str, str]

class AskChapterRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)