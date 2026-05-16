import pandas as pd
import os
from config import DATA_PATH

async def audit_mastery(user_id: int, skill: str):
    try:
        if not os.path.exists(DATA_PATH):
            return 0.1
        
        df = pd.read_csv(DATA_PATH)
        user_skill_data = df[(df['user_id'] == user_id) & (df['skill_name'] == skill)]
        
        if user_skill_data.empty:
            return 0.1
        
        p_mastery = 0.1
        p_transit, p_slip, p_guess = 0.2, 0.1, 0.2

        for obs in user_skill_data['correct']:
            if obs == 1:
                p_known = (p_mastery * (1 - p_slip)) / (p_mastery * (1 - p_slip) + (1 - p_mastery) * p_guess)
                p_mastery = p_known + (1 - p_known) * p_transit
            else:
                p_known = (p_mastery * p_slip) / (p_mastery * p_slip + (1 - p_mastery) * (1 - p_guess))
                p_mastery = p_known
            
        return round(float(p_mastery), 3)
    except Exception as e:
        print(f"BKT Error: {e}")
        return 0.1
