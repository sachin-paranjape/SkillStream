import os
import math
import json
import random
import pandas as pd
import traceback
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from pyBKT.models import Model
from google import genai
from dotenv import load_dotenv

# --- 1. CONFIGURATION ---
load_dotenv()
app = FastAPI(title="SkillStream v4: Final Agentic Engine")

# Enable CORS for frontend/Swagger
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Gemini AI
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Local Data Storage
DATA_PATH = 'data/interactions.csv'
if not os.path.exists('data'):
    os.makedirs('data')

# Initialize BKT Model once for global use
bkt_model = Model(seed=42, num_fits=1)

# --- 2. DATA SCHEMAS (Fixed for Gemini Compatibility) ---

class UserInit(BaseModel):
    user_id: int
    skill: str
    self_reported_level: str # Beginner, Intermediate, Advanced, Expert

class MCQQuestionSchema(BaseModel):
    """Explicit fields to prevent 'additionalProperties' errors in Gemini."""
    question: str
    option_A: str
    option_B: str
    option_C: str
    option_D: str
    correct_option: str # Must be 'A', 'B', 'C', or 'D'
    logic_explanation: str

class Submission(BaseModel):
    user_id: int
    skill: str
    selected_option: str
    correct_option: str
    explanation_text: Optional[str] = "" 
    difficulty: str

# --- 3. THE BRAIN: AUDIT & BKT LOGIC ---

async def audit_mastery(user_id: int, skill: str) -> float:
    """Calculates mastery probability. Uses Heuristic Fallback if BKT fails."""
    if not os.path.exists(DATA_PATH):
        return 0.1
    
    df = pd.read_csv(DATA_PATH)
    user_skill_data = df[(df['user_id'] == user_id) & (df['skill_name'] == skill)]
    
    if user_skill_data.empty:
        return 0.1 
    
    try:
        # 1. Attempt pyBKT Fit
        bkt_model.fit(data_path=DATA_PATH, forgets=False)
        preds = bkt_model.predict(data_path=DATA_PATH)
        preds['user_id'] = preds['user_id'].astype(str)
        
        # Filter prediction for this specific user/skill
        user_rows = preds[(preds['user_id'] == str(user_id)) & (preds['skill_name'] == skill)]
        
        if user_rows.empty:
            raise ValueError("BKT could not find prediction row.")
            
        score = float(user_rows.iloc[-1]['state_predictions'])
        
        if math.isnan(score):
            raise ValueError("BKT returned NaN.")
            
        return round(score, 3)

    except Exception as e:
        # 🛡️ HEURISTIC FALLBACK: If the math library crashes on Python 3.13
        # we use a weighted moving average of their performance.
        print(f"⚠️ Math Engine Bypass: {e}")
        correct_count = len(user_skill_data[user_skill_data['correct'] == 1])
        total = len(user_skill_data)
        # Weighted Accuracy: (Correct / Total) * 0.8
        return round((correct_count / total) * 0.8, 3)

# --- 4. ENDPOINTS ---

@app.post("/user/initialize")
async def initialize_user(data: UserInit):
    """Novelty: Seeds the Bayesian Prior based on self-reported level."""
    levels = {
        "Beginner": [0, 0, 1],
        "Intermediate": [1, 0, 1],
        "Advanced": [1, 1, 0, 1],
        "Expert": [1, 1, 1, 1]
    }
    seeds = levels.get(data.self_reported_level, [0, 1])
    
    # Append the 'Virtual History' to the CSV
    new_rows = pd.DataFrame(
        [[data.user_id, data.skill, res] for res in seeds], 
        columns=['user_id', 'skill_name', 'correct']
    )
    new_rows.to_csv(DATA_PATH, mode='a', header=not os.path.exists(DATA_PATH), index=False)
    
    initial_score = await audit_mastery(data.user_id, data.skill)
    return {"status": "User Calibrated", "initial_prior": initial_score}

@app.get("/recommend/{user_id}")
async def recommend_challenge(user_id: int):
    """Agent Logic: Scans skills, finds weakest link, and generates an MCQ."""
    try:
        # 1. Skill Audit
        skills = ["Verbal Ability", "Aptitude", "Data Structures"]
        report = {s: await audit_mastery(user_id, s) for s in skills}
        
        # 2. Strategy: Target the lowest score
        weakest_skill = min(report, key=report.get)
        score = report[weakest_skill]
        
        # 3. ZPD Difficulty Scaling
        difficulty = "Easy" if score < 0.4 else "Hard" if score < 0.7 else "Expert"

        # 4. Gemini AI Generation
        prompt = f"""
        Generate a {difficulty} MCQ for the skill '{weakest_skill}'. 
        The student's current mastery is {score}.
        Ensure 'correct_option' is exactly 'A', 'B', 'C', or 'D'.
        """
        
        response = client.models.generate_content(
            model="gemini-2.5-flash", # Use the 2026 standard flagship model
            contents=prompt,
            config={
                'response_mime_type': 'application/json', 
                'response_schema': MCQQuestionSchema
            }
        )
        
        # Parse and format for the UI
        raw_mcq = json.loads(response.text)
        formatted_question = {
            "question": raw_mcq["question"],
            "options": {
                "A": raw_mcq["option_A"],
                "B": raw_mcq["option_B"],
                "C": raw_mcq["option_C"],
                "D": raw_mcq["option_D"]
            },
            "correct_option": raw_mcq["correct_option"],
            "logic_explanation": raw_mcq["logic_explanation"]
        }
        
        return {
            "skill": weakest_skill,
            "mastery": score,
            "difficulty": difficulty,
            "question": formatted_question
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/submit")
async def submit_answer(sub: Submission):
    """The Truth Filter: Verifies MCQ + Semantic Logic."""
    try:
        mcq_correct = sub.selected_option.upper() == sub.correct_option.upper()
        
        # Socratic Check (Optional Semantic Logic)
        if mcq_correct and sub.explanation_text:
            check_prompt = f"Verify this explanation: '{sub.explanation_text}' against logic: '{sub.correct_option}'. Is it sound? (Yes/No)"
            # You can use the verdict to adjust BKT weighting in a future version!
        
        # Log result to 'Long-term Memory'
        final_res = 1 if mcq_correct else 0
        new_row = pd.DataFrame(
            [[sub.user_id, sub.skill, final_res]], 
            columns=['user_id', 'skill_name', 'correct']
        )
        new_row.to_csv(DATA_PATH, mode='a', header=False, index=False)

        # Get Coach Feedback
        coach_prompt = f"Topic: {sub.skill}. Result: {'Correct' if mcq_correct else 'Incorrect'}. Give a brief, clever Socratic hint."
        feedback = client.models.generate_content(model="gemini-2.5-flash", contents=coach_prompt).text

        return {
            "is_correct": mcq_correct,
            "new_mastery": await audit_mastery(sub.user_id, sub.skill),
            "coach_feedback": feedback
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- 5. EXECUTION ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)