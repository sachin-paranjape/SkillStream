from pydantic import BaseModel
from typing import Dict, Optional

class Submission(BaseModel):
    user_id: int
    user_name: str
    skill: str
    difficulty: str
    selected_option: str
    correct_option: str
    # Added these to fix the "Template Mentor" issue
    question_text: str
    selected_option_text: str
    correct_option_text: str
    explanation: str

class MCQQuestion(BaseModel):
    question: str
    option_A: str
    option_B: str
    option_C: str
    option_D: str
    correct_option: str
    logic_explanation: str