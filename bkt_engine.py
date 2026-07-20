import sqlite3
from config import DB_PATH

BKT_PARAMS = {
    # Conservative initial mastery so new users are treated as beginners.
    "p_init": 0.2,
    # Slow knowledge growth after each correct response.
    "p_transit": 0.03,
    # Higher slip and guess rates to reflect realistic student uncertainty.
    "p_slip": 0.20,
    "p_guess": 0.40,
}

LEVEL_THRESHOLDS = [
    (0.75, "Expert"),
    (0.5, "Advanced"),
    (0.25, "Intermediate"),
    (0.0, "Beginner"),
]


def _get_bkt_connection():
    return sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)


def _bkt_update(p_known: float, correct: bool) -> float:
    slip = BKT_PARAMS["p_slip"]
    guess = BKT_PARAMS["p_guess"]
    transit = BKT_PARAMS["p_transit"]

    if correct:
        p_known_given = (
            p_known * (1 - slip)
        ) / (p_known * (1 - slip) + (1 - p_known) * guess)
        return p_known_given + (1 - p_known_given) * transit
    else:
        p_known_given = (
            p_known * slip
        ) / (p_known * slip + (1 - p_known) * (1 - guess))
        return p_known_given


def _mastery_to_level(mastery: float) -> str:
    for threshold, label in LEVEL_THRESHOLDS:
        if mastery >= threshold:
            return label
    return "Beginner"


def get_bkt_state(user_id: int, skill: str) -> dict:
    try:
        conn = _get_bkt_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT is_correct FROM submissions WHERE user_id = ? AND skill_name = ? ORDER BY submitted_at",
            (user_id, skill),
        )
        rows = cursor.fetchall()
        conn.close()

        p_known = BKT_PARAMS["p_init"]
        attempts = len(rows)
        correct_count = 0

        for (is_correct,) in rows:
            is_correct_bool = bool(is_correct)
            if is_correct_bool:
                correct_count += 1
            p_known = _bkt_update(p_known, is_correct_bool)

        p_correct = p_known * (1 - BKT_PARAMS["p_slip"]) + (1 - p_known) * BKT_PARAMS["p_guess"]
        return {
            "attempts": attempts,
            "correct_count": correct_count,
            "mastery": round(float(min(0.99, p_known)), 3),
            "level": _mastery_to_level(p_known),
            "p_known": round(float(p_known), 3),
            "p_correct": round(float(p_correct), 3),
            "p_known_and_correct": round(float(p_known * (1 - BKT_PARAMS["p_slip"])), 3),
            "p_known_but_missed": round(float(p_known * BKT_PARAMS["p_slip"]), 3),
            "p_guessed": round(float((1 - p_known) * BKT_PARAMS["p_guess"]), 3),
            "p_unknown_and_wrong": round(float((1 - p_known) * (1 - BKT_PARAMS["p_guess"])), 3),
        }
    except Exception as e:
        print(f"BKT Error: {e}")
        return {
            "attempts": 0,
            "correct_count": 0,
            "mastery": round(float(BKT_PARAMS["p_init"]), 3),
            "level": "Beginner",
            "p_known": round(float(BKT_PARAMS["p_init"]), 3),
            "p_correct": round(float(BKT_PARAMS["p_init"] * (1 - BKT_PARAMS["p_slip"]) + (1 - BKT_PARAMS["p_init"]) * BKT_PARAMS["p_guess"]), 3),
            "p_known_and_correct": round(float(BKT_PARAMS["p_init"] * (1 - BKT_PARAMS["p_slip"])), 3),
            "p_known_but_missed": round(float(BKT_PARAMS["p_init"] * BKT_PARAMS["p_slip"]), 3),
            "p_guessed": round(float((1 - BKT_PARAMS["p_init"]) * BKT_PARAMS["p_guess"]), 3),
            "p_unknown_and_wrong": round(float((1 - BKT_PARAMS["p_init"]) * (1 - BKT_PARAMS["p_guess"])), 3),
        }


async def audit_mastery(user_id: int, skill: str):
    state = get_bkt_state(user_id, skill)
    return state["mastery"]
