import pandas as pd
import os

DATA_PATH = "data/interactions.csv"

async def audit_mastery(user_id: int, skill: str):
    if not os.path.exists(DATA_PATH): return 0.1
    df = pd.read_csv(DATA_PATH)
    data = df[(df['user_id'] == user_id) & (df['skill_name'] == skill)]
    if data.empty: return 0.1
    # Simple logic: each correct answer adds 0.2 to the base 0.1
    score = 0.1 + (len(data[data['correct'] == 1]) * 0.15)
    return round(min(0.95, score), 2)

def get_aptitude_hint():
    return "Focus on Quantitative logic like Ratios, Percentages, and Speed. Avoid CS jargon."