import os

from fastapi import FastAPI
import pandas as pd
from config import DATA_PATH
from models import Submission
from bkt_engine import audit_mastery
from ai_engine import get_hybrid_mcq, get_dual_feedback

app = FastAPI()

@app.get("/mastery/report/{user_id}")
async def mastery_report(user_id: int):
    skills = ["Verbal Ability", "Aptitude", "Data Structures"]
    return {s: await audit_mastery(user_id, s) for s in skills}

@app.get("/recommend/{user_id}")
async def recommend(user_id: int):
    skills = ["Verbal Ability", "Aptitude", "Data Structures"]
    report = {s: await audit_mastery(user_id, s) for s in skills}
    weakest = min(report, key=report.get)
    score = report[weakest]
    
    difficulty = "Easy" if score < 0.4 else "Hard" if score < 0.7 else "Expert"
    use_cloud = (difficulty == "Expert") or (weakest == "Data Structures")
    
    mcq = await get_hybrid_mcq(weakest, difficulty, score, use_cloud)
    needs_explanation = not (difficulty == "Easy" and weakest in ["Verbal Ability", "Aptitude"])
    
    return {
        "skill": weakest,
        "mastery": score,
        "difficulty": difficulty,
        "needs_explanation": needs_explanation,
        "question": {
            "question": mcq.get("question", "Question missing?"),
            "options": {
                "A": mcq.get("option_A", "N/A"),
                "B": mcq.get("option_B", "N/A"),
                "C": mcq.get("option_C", "N/A"),
                "D": mcq.get("option_D", "N/A")
            },
            "correct_option": mcq.get("correct_option", "A"),
            "logic_explanation": mcq.get("logic_explanation", "")
        }
    }

@app.post("/submit")
async def submit(sub: Submission):
    is_correct = sub.selected_option.upper() == sub.correct_option.upper()
    df = pd.DataFrame([[sub.user_id, sub.skill, 1 if is_correct else 0]], columns=['user_id','skill_name','correct'])
    should_write_header = not os.path.exists(DATA_PATH) or os.path.getsize(DATA_PATH) == 0
    df.to_csv(DATA_PATH, mode='a', header=should_write_header, index=False)
    
    feedback = await get_dual_feedback(sub)
    return {
        "is_correct": is_correct,
        "new_mastery": await audit_mastery(sub.user_id, sub.skill),
        "mentor_feedback": feedback.get("mentor"),
        "expert_feedback": feedback.get("expert")
    }
