from fastapi import FastAPI, Query
from database import (
    init_db,
    record_submission,
    get_leaderboard,
    get_user_points,
    get_user_rank,
    get_seen_question_texts,
)
from models import Submission
from bkt_engine import audit_mastery, get_bkt_state
from ai_engine import get_hybrid_mcq, get_dual_feedback

app = FastAPI()
init_db()

@app.get("/mastery/report/{user_id}")
async def mastery_report(user_id: int):
    valid_skills = ["Verbal Ability", "Aptitude", "Data Structures"]
    report = {}
    for skill in valid_skills:
        state = get_bkt_state(user_id, skill)
        report[skill] = {
            "mastery": state["mastery"],
            "level": state["level"],
            "attempts": state["attempts"],
        }
    return report

@app.get("/recommend/{user_id}")
async def recommend(user_id: int, skill: str | None = None):
    valid_skills = ["Verbal Ability", "Aptitude", "Data Structures"]
    states = {s: get_bkt_state(user_id, s) for s in valid_skills}

    if skill and skill in valid_skills:
        chosen_skill = skill
    else:
        chosen_skill = min(states, key=lambda s: states[s]["mastery"])

    state = states[chosen_skill]
    score = state["mastery"]
    attempts = state["attempts"]

    if score < 0.35:
        difficulty = "Easy"
    elif score < 0.55:
        difficulty = "Medium"
    elif score < 0.80:
        difficulty = "Hard"
    else:
        difficulty = "Expert"

    use_cloud = difficulty == "Expert" or chosen_skill == "Data Structures"
    seen_question_texts = get_seen_question_texts(user_id, chosen_skill)
    mcq = await get_hybrid_mcq(chosen_skill, difficulty, score, use_cloud, seen_question_texts)
    needs_explanation = difficulty in ["Hard", "Expert"]

    return {
        "skill": chosen_skill,
        "mastery": score,
        "user_level": state["level"],
        "difficulty": difficulty,
        "needs_explanation": needs_explanation,
        "probabilities": {
            "knows": state["p_known"],
            "answers_correct": state["p_correct"],
            "knows_but_missed": state["p_known_but_missed"],
            "guessed": state["p_guessed"],
            "unknown_and_wrong": state["p_unknown_and_wrong"],
        },
        "question": {
            "question": mcq.get("question", "Question missing?"),
            "options": {
                "A": mcq.get("option_A", "N/A"),
                "B": mcq.get("option_B", "N/A"),
                "C": mcq.get("option_C", "N/A"),
                "D": mcq.get("option_D", "N/A")
            },
            "correct_option": mcq.get("correct_option", "A"),
            "logic_explanation": mcq.get("logic_explanation", ""),
            "context": mcq.get("context", ""),
            "anchor_fact": mcq.get("anchor_fact", ""),
            "use_case": mcq.get("use_case", ""),
            "use_case_description": mcq.get("use_case_description", "")
        }
    }

@app.post("/submit")
async def submit(sub: Submission):
    is_correct = sub.selected_option.upper() == sub.correct_option.upper()
    previous_mastery = get_bkt_state(sub.user_id, sub.skill)["mastery"]
    record_submission(
        user_id=sub.user_id,
        user_name=sub.user_name,
        skill_name=sub.skill,
        difficulty=sub.difficulty,
        question_text=sub.question_text,
        selected_option=sub.selected_option,
        selected_option_text=sub.selected_option_text,
        correct_option=sub.correct_option,
        correct_option_text=sub.correct_option_text,
        explanation_text=sub.explanation,
        is_correct=is_correct,
    )

    feedback = await get_dual_feedback(sub)
    new_mastery = await audit_mastery(sub.user_id, sub.skill)
    return {
        "is_correct": is_correct,
        "previous_mastery": previous_mastery,
        "new_mastery": new_mastery,
        "mastery_delta": round(new_mastery - previous_mastery, 3),
        "difficulty": sub.difficulty,
        "points": get_user_points(sub.user_id),
        "correct_option": sub.correct_option,
        "correct_option_text": sub.correct_option_text,
        "mentor_feedback": feedback.get("mentor"),
        "expert_feedback": feedback.get("expert")
    }

@app.get("/leaderboard")
async def leaderboard(
    limit: int = Query(10, ge=1, le=50),
    user_id: int | None = None,
    skill: str | None = None,
):
    board = get_leaderboard(limit, skill_name=skill)
    response = {"leaderboard": board}
    if user_id is not None:
        response["user_rank"] = get_user_rank(user_id)
    return response
