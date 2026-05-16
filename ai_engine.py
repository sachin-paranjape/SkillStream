import csv
import json
import os
import random
from typing import Dict, List

from config import cloud_client, local_client

OPTION_KEYS = ("A", "B", "C", "D")
DATA_ROOT = "data"
VERIFIED_PLACEMENT = os.path.join(DATA_ROOT, "verified_placement_questions.jsonl")
VERIFIED_DSA = os.path.join(DATA_ROOT, "verified_dsa_mcqs.jsonl")
VERIFIED_GFG = os.path.join(DATA_ROOT, "verified_gfg_questions.csv")
EXTRA_DSA_JSON = os.path.join(DATA_ROOT, "dsa_easy_mcq_dataset.json")


def _fallback_mcq(skill, difficulty):
    return {
        "question": f"Which option best represents a {difficulty.lower()} concept in {skill}?",
        "option_A": "Identify the core idea before choosing an answer",
        "option_B": "Ignore the question context",
        "option_C": "Choose the longest option automatically",
        "option_D": "Skip checking the answer logic",
        "correct_option": "A",
        "logic_explanation": "The best first step is to understand the concept being tested.",
    }


def _normalize_mcq(raw_data, skill, difficulty):
    if not isinstance(raw_data, dict):
        return _fallback_mcq(skill, difficulty)

    options = raw_data.get("options")
    if isinstance(options, list):
        for index, key in enumerate(OPTION_KEYS):
            raw_data[f"option_{key}"] = options[index] if index < len(options) else "N/A"
    elif isinstance(options, dict):
        for key in OPTION_KEYS:
            raw_data[f"option_{key}"] = options.get(key) or options.get(f"option_{key}") or "N/A"

    # Map alternative rationale/correct_answer keys to the expected field names
    if not raw_data.get("logic_explanation") and raw_data.get("rationale"):
        raw_data["logic_explanation"] = raw_data.get("rationale")

    # If the dataset provides a text 'correct_answer' (value), map it to option key (A/B/C/D)
    if not raw_data.get("correct_option") and raw_data.get("correct_answer"):
        target = str(raw_data.get("correct_answer")).strip()
        for key in OPTION_KEYS:
            val = raw_data.get(f"option_{key}")
            if val and str(val).strip() == target:
                raw_data["correct_option"] = key
                break

    # preserve optional use-case fields so UI can show a badge
    if raw_data.get("use_case"):
        raw_data["use_case"] = raw_data.get("use_case")
    if raw_data.get("use_case_description"):
        raw_data["use_case_description"] = raw_data.get("use_case_description")

    fallback = _fallback_mcq(skill, difficulty)
    for key, value in fallback.items():
        raw_data.setdefault(key, value)

    correct_option = str(raw_data.get("correct_option", "A")).strip().upper()
    if correct_option.startswith("OPTION_"):
        correct_option = correct_option[-1]
    raw_data["correct_option"] = correct_option if correct_option in OPTION_KEYS else "A"

    return raw_data


def _load_jsonl(path: str) -> List[Dict]:
    result = []
    if not os.path.exists(path):
        return result
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                result.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return result


def _load_csv(path: str) -> List[Dict]:
    result = []
    if not os.path.exists(path):
        return result
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for row in reader:
            result.append(row)
    return result


def _load_json(path: str) -> List[Dict]:
    """Load a JSON file containing a top-level array of objects."""
    result = []
    if not os.path.exists(path):
        return result
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            data = json.load(f)
            if isinstance(data, list):
                result.extend(data)
    except Exception:
        pass
    return result


def _load_grounding_rows() -> List[Dict]:
    if hasattr(_load_grounding_rows, "cache"):
        return _load_grounding_rows.cache

    rows = []
    rows.extend(_load_jsonl(VERIFIED_PLACEMENT))
    rows.extend(_load_jsonl(VERIFIED_DSA))
    # also include any additional DSA JSON datasets (top-level list format)
    rows.extend(_load_json(EXTRA_DSA_JSON))
    rows.extend(_load_csv(VERIFIED_GFG))
    _load_grounding_rows.cache = rows
    return rows


SKILL_DATASETS = {
    "Aptitude": VERIFIED_PLACEMENT,
    "Verbal Ability": VERIFIED_PLACEMENT,
    "Data Structures": VERIFIED_DSA,
}


def _difficulty_matches(row_diff: str, difficulty: str) -> bool:
    row_diff = row_diff.lower()
    difficulty = difficulty.lower()
    if difficulty == "expert":
        return row_diff in {"hard", "expert"}
    if difficulty == "hard":
        return row_diff in {"hard", "medium"}
    return row_diff == "easy"


def _retrieve_verified_mcq(skill: str, difficulty: str) -> Dict | None:
    paths = SKILL_DATASETS.get(skill)
    if not paths:
        return None
    if not isinstance(paths, list):
        paths = [paths]

    rows: List[Dict] = []
    for path in paths:
        if path.endswith(".jsonl"):
            rows.extend(_load_jsonl(path))
        elif path.endswith(".json"):
            rows.extend(_load_json(path))
        elif path.endswith(".csv"):
            rows.extend(_load_csv(path))

    matching = []
    for row in rows:
        row_skill = str(row.get("skill") or row.get("topic") or "").strip().lower()
        # If row doesn't explicitly state skill but comes from DSA datasets, treat it as Data Structures
        if not row_skill:
            row_skill = "data structures"
        if row_skill == skill.lower() and _difficulty_matches(str(row.get("difficulty", "")), difficulty):
            matching.append(row)

    if not matching:
        matching = [row for row in rows if str(row.get("skill") or row.get("topic") or "").strip().lower() == skill.lower()]

    if not matching:
        return None

    candidate = random.choice(matching)
    return _normalize_mcq(candidate, skill, difficulty)


def _score_grounding_row(row: Dict, skill: str, difficulty: str) -> int:
    score = 0
    row_skill = str(row.get("skill", "")).lower()
    row_diff = str(row.get("difficulty", "")).lower()
    if row_skill == skill.lower():
        score += 3
    if row_diff == difficulty.lower():
        score += 2
    if difficulty.lower() == "hard" and row_diff in {"medium", "easy"}:
        score += 1
    if difficulty.lower() == "easy" and row_diff == "medium":
        score += 1
    return score


def _select_grounding(skill: str, difficulty: str) -> List[Dict]:
    rows = _load_grounding_rows()
    scored = [(_score_grounding_row(row, skill, difficulty), row) for row in rows]
    scored = [item for item in scored if item[0] > 0]
    scored.sort(key=lambda x: (-x[0], random.random()))
    return [row for _, row in scored[:2]]


def _build_context_text(rows: List[Dict]) -> str:
    lines = []
    for row in rows:
        if row.get("question"):
            lines.append(f"Example question: {row.get('question')}")
            for key in OPTION_KEYS:
                answer = row.get(f"option_{key}")
                if answer:
                    lines.append(f"  {key}: {answer}")
            if row.get("correct_option"):
                lines.append(f"Correct answer: {row.get('correct_option')}")
            if row.get("logic_explanation"):
                lines.append(f"Explanation: {row.get('logic_explanation')}")
            if row.get("anchor_fact"):
                lines.append(f"Anchor fact: {row.get('anchor_fact')}")
            # Optional use-case fields may appear in grounding rows; include them so the generator
            # can weave specific scenario context into the question stem when appropriate.
            if row.get("use_case"):
                lines.append(f"Use case: {row.get('use_case')}")
            if row.get("use_case_description"):
                lines.append(f"Use case description: {row.get('use_case_description')}")
        elif row.get("question_name"):
            lines.append(
                f"Verified problem: {row.get('question_name')} ({row.get('topic', 'unknown')} / {row.get('difficulty', 'unknown')}). "
                f"Company tags: {row.get('company_tags', 'n/a')}. Accuracy: {row.get('accuracy', 'n/a')}%."
            )
    return "\n".join(lines)


def _build_grounded_prompt(skill: str, difficulty: str, rows: List[Dict]) -> str:
    context = _build_context_text(rows)
    payload = f"""
Generate a {difficulty} multiple-choice question for {skill}. Use the verified examples below as grounding information. When the grounding examples include an "Use case" or "Anchor fact", weave that scenario into the question stem (for example: "For the following use case: ...") so the question is explicitly contextualized for that use case. The finished output must be valid JSON matching this exact structure.

Grounding examples:
{context}

Return JSON only:
{{
    "question": "...",
    "option_A": "...",
    "option_B": "...",
    "option_C": "...",
    "option_D": "...",
    "correct_option": "A",
    "logic_explanation": "..."
}}
"""
    return payload


async def get_hybrid_mcq(skill, difficulty, score, use_cloud):
    verified_mcq = _retrieve_verified_mcq(skill, difficulty)
    if verified_mcq is not None:
        return verified_mcq

    grounding_rows = _select_grounding(skill, difficulty)
    prompt = _build_grounded_prompt(skill, difficulty, grounding_rows)

    if use_cloud and cloud_client is not None:
        try:
            res = cloud_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config={"response_mime_type": "application/json"},
            )
            return _normalize_mcq(json.loads(res.text), skill, difficulty)
        except Exception as e:
            print(f"Cloud generation failed. Falling back to local model: {e}")

    if local_client is not None:
        try:
            res = local_client.chat.completions.create(
                model="gemma3:1b",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            return _normalize_mcq(json.loads(res.choices[0].message.content), skill, difficulty)
        except Exception as e:
            print(f"Local generation failed. Using fallback MCQ: {e}")
    else:
        print("No local AI client configured; using fallback MCQ.")

    return _fallback_mcq(skill, difficulty)


async def get_dual_feedback(sub):
    is_correct = sub.selected_option.upper() == sub.correct_option.upper()
    prompt = f"""
You are a learning mentor and industry critic.
Question: {sub.question_text}
Difficulty: {sub.difficulty}
Student selected: {sub.selected_option} - {sub.selected_option_text}
Correct answer: {sub.correct_option} - {sub.correct_option_text}
Student explanation: {sub.explanation}

If the student is incorrect, return JSON with:
  "mentor": "1-sentence explanation why the actual correct option is right, focusing on the key concept behind that option",
  "expert": "1-sentence critique explaining why the student answer was wrong and what logic they missed"

If the student is correct and difficulty is Hard or Expert, return JSON with:
  "mentor": "1-sentence explanation why the answer is correct, including the core idea behind the choice",
  "expert": "1-sentence note on what was missing from the student's explanation or how to make the reasoning stronger"

If the student is correct and difficulty is Easy or Medium, return JSON with:
  "mentor": "1-sentence explanation why the answer is correct",
  "expert": ""

Return only valid JSON.
"""

    if local_client is not None:
        try:
            res = local_client.chat.completions.create(
                model="gemma3:1b",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            raw_feedback = res.choices[0].message.content
            try:
                feedback = json.loads(raw_feedback)
            except Exception:
                feedback = {}

            mentor = feedback.get(
                "mentor",
                f"The correct answer is {sub.correct_option}: {sub.correct_option_text}, because it best matches the underlying concept.",
            )
            expert = feedback.get(
                "expert",
                "" if is_correct and sub.difficulty in ["Easy", "Medium"] else "This answer needs better justification.",
            )

            if isinstance(mentor, str):
                mentor_lower = mentor.strip().lower()
                if "1-sentence" in mentor_lower or "return json" in mentor_lower or "explanation why" in mentor_lower:
                    mentor = f"The correct answer is {sub.correct_option}: {sub.correct_option_text}, because it best matches the underlying concept."
            else:
                mentor = f"The correct answer is {sub.correct_option}: {sub.correct_option_text}, because it best matches the underlying concept."

            if isinstance(expert, str):
                expert_lower = expert.strip().lower()
                if "1-sentence" in expert_lower or "return json" in expert_lower:
                    expert = "The student answer was wrong because it did not align with the key reasoning behind the correct option."
            else:
                expert = "The student answer was wrong because it did not align with the key reasoning behind the correct option."

            if not is_correct and not expert:
                expert = "The student answer was wrong because it did not align with the key reasoning behind the correct option."
            if not is_correct and (not mentor or mentor.strip().lower().startswith("correct")):
                mentor = f"The correct answer is {sub.correct_option}: {sub.correct_option_text}, because it best matches the underlying concept."

            return {
                "mentor": mentor,
                "expert": expert,
            }
        except Exception as e:
            print(f"Feedback generation failed. Using fallback feedback: {e}")
    else:
        print("No local AI client configured; using fallback feedback.")

    if is_correct:
        mentor = "Correct — this answer is right because it matches the required concept."
        expert = "" if sub.difficulty in ["Easy", "Medium"] else "The answer is correct, but your reasoning should include the core principle behind the choice."
    else:
        mentor = f"The correct answer is {sub.correct_option}: {sub.correct_option_text}, because it best matches the problem statement."
        expert = f"The student answer was wrong because it did not align with the key reasoning behind the correct option."

    return {
        "mentor": mentor,
        "expert": expert,
    }
