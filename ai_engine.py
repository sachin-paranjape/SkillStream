import csv
import json
import os
import random
import re
from typing import Dict, List, Set

from config import cloud_client, local_client

OPTION_KEYS = ("A", "B", "C", "D")
DATA_ROOT = "data"
VERIFIED_PLACEMENT = os.path.join(DATA_ROOT, "verified_placement_questions.jsonl")
VERIFIED_DSA = os.path.join(DATA_ROOT, "verified_dsa_mcqs.jsonl")
VERIFIED_GFG = os.path.join(DATA_ROOT, "verified_gfg_questions.csv")
EXTRA_DSA_JSON = os.path.join(DATA_ROOT, "dsa_easy_mcq_dataset.json")
DSA_TOPICS = {
    "array",
    "arrays",
    "linked list",
    "linked lists",
    "stack",
    "stacks",
    "queue",
    "queues",
    "tree",
    "trees",
    "string",
    "strings",
    "sorting",
    "sorting algorithms",
    "time complexity",
    "graph",
    "graphs",
    "hashing",
    "heap",
    "heaps",
}
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "be",
    "by",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "what",
    "when",
    "where",
    "which",
    "why",
    "with",
    "would",
}
CONTEXT_REQUIRED_MARKERS = (
    "this specific use case",
    "this use case",
    "this scenario",
    "the scenario",
    "given scenario",
    "following scenario",
    "this situation",
)
MIN_PASSAGE_WORDS = 55
MIN_PASSAGE_SENTENCES = 3


def _fallback_mcq(skill, difficulty):
    if skill == "Verbal Ability":
        return {
            "question": f"Choose the best word to complete the sentence: The manager gave a _____ explanation so everyone understood the new policy.",
            "option_A": "clear",
            "option_B": "confusing",
            "option_C": "irrelevant",
            "option_D": "careless",
            "correct_option": "A",
            "logic_explanation": "A clear explanation is easy to understand, which matches the result described in the sentence.",
        }

    return {
        "question": f"Which option best represents a {difficulty.lower()} concept in {skill}?",
        "option_A": "Identify the core idea before choosing an answer",
        "option_B": "Ignore the question context",
        "option_C": "Choose the longest option automatically",
        "option_D": "Skip checking the answer logic",
        "correct_option": "A",
        "logic_explanation": "The best first step is to understand the concept being tested.",
    }


def _row_skill(row: Dict) -> str:
    return str(row.get("skill") or row.get("topic") or "").strip().lower()


def _row_matches_skill(row: Dict, skill: str) -> bool:
    row_skill = _row_skill(row)
    target = skill.lower()
    if row_skill == target:
        return True
    if target == "data structures":
        return not row_skill or row_skill in DSA_TOPICS
    return False


def _context_text(raw_data: Dict) -> str:
    return str(
        raw_data.get("use_case_description")
        or raw_data.get("use_case")
        or raw_data.get("anchor_fact")
        or ""
    ).strip()


def _question_needs_context(question: str) -> bool:
    lowered = question.lower()
    return any(marker in lowered for marker in CONTEXT_REQUIRED_MARKERS)


def _split_passage_question(question: str) -> tuple[str, str]:
    if not question.startswith("PASSAGE:"):
        return "", question
    body = question.removeprefix("PASSAGE:").strip()
    match = re.search(r"\bQ:\s*", body)
    if not match:
        return body, ""
    return body[: match.start()].strip(), body[match.end() :].strip()


def _sentence_count(text: str) -> int:
    return len(re.findall(r"[.!?](?:\s|$)", text))


def _is_bad_passage_row(row: Dict) -> bool:
    question = _question_text(row)
    if not question.startswith("PASSAGE:"):
        return False

    passage, prompt = _split_passage_question(question)
    correct_option = str(row.get("correct_option") or "").strip().upper()
    correct_text = str(row.get(f"option_{correct_option}") or row.get("correct_answer") or "").strip()

    if "..." in passage:
        return True
    if len(passage.split()) < MIN_PASSAGE_WORDS:
        return True
    if _sentence_count(passage) < MIN_PASSAGE_SENTENCES:
        return True
    if correct_text and len(correct_text.split()) <= 3 and correct_text.lower() in passage.lower():
        return True
    if prompt and prompt.lower() in passage.lower():
        return True

    return False


def _row_is_usable(row: Dict) -> bool:
    return not _is_bad_passage_row(row)


def _add_context_to_question(raw_data: Dict) -> None:
    question = str(raw_data.get("question") or "").strip()
    context = _context_text(raw_data)
    if not question or not context:
        return
    if _question_needs_context(question) and context.lower() not in question.lower():
        raw_data["question"] = f"Context: {context}\n\n{question}"


def _normalize_mcq(raw_data, skill, difficulty):
    if not isinstance(raw_data, dict):
        return _fallback_mcq(skill, difficulty)
    raw_data = dict(raw_data)

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
    if raw_data.get("anchor_fact"):
        raw_data["anchor_fact"] = raw_data.get("anchor_fact")
    if _context_text(raw_data):
        raw_data["context"] = _context_text(raw_data)

    fallback = _fallback_mcq(skill, difficulty)
    for key, value in fallback.items():
        raw_data.setdefault(key, value)

    _add_context_to_question(raw_data)

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
    if difficulty == "medium":
        return row_diff == "medium"
    if difficulty == "expert":
        return row_diff in {"hard", "expert"}
    if difficulty == "hard":
        return row_diff in {"hard", "medium"}
    return row_diff == "easy"


def _question_text(row: Dict) -> str:
    return str(row.get("question") or "").strip()


def _tokenize(text: str) -> Set[str]:
    tokens = set(re.findall(r"[a-zA-Z][a-zA-Z0-9_+#-]*", text.lower()))
    return {token for token in tokens if token not in STOPWORDS and len(token) > 1}


def _row_retrieval_text(row: Dict) -> str:
    parts = [
        str(row.get("skill") or ""),
        str(row.get("topic") or ""),
        str(row.get("difficulty") or ""),
        str(row.get("question") or ""),
        str(row.get("logic_explanation") or row.get("rationale") or ""),
        str(row.get("anchor_fact") or ""),
        str(row.get("use_case") or ""),
        str(row.get("use_case_description") or ""),
        str(row.get("question_name") or ""),
        str(row.get("company_tags") or ""),
    ]
    for key in OPTION_KEYS:
        parts.append(str(row.get(f"option_{key}") or ""))
    return " ".join(parts)


def _retrieval_query(skill: str, difficulty: str, score: float | None = None) -> str:
    level_hint = ""
    if score is not None:
        if score < 0.35:
            level_hint = "fundamentals definitions basic operations"
        elif score < 0.55:
            level_hint = "application reasoning common cases"
        elif score < 0.80:
            level_hint = "edge cases performance tradeoffs"
        else:
            level_hint = "advanced design constraints optimization"
    return f"{skill} {difficulty} {level_hint}"


def _retrieval_score(row: Dict, query_tokens: Set[str], skill: str, difficulty: str) -> float:
    row_tokens = _tokenize(_row_retrieval_text(row))
    overlap = len(query_tokens & row_tokens)
    score = overlap * 2.0

    if _row_matches_skill(row, skill):
        score += 8.0

    row_diff = str(row.get("difficulty") or "").strip()
    if row_diff and _difficulty_matches(row_diff, difficulty):
        score += 4.0
    elif not row_diff and skill.lower() == "data structures":
        score += 1.5

    if _context_text(row):
        score += 1.25
    if row.get("correct_option") or row.get("correct_answer"):
        score += 1.0
    if row.get("logic_explanation") or row.get("rationale"):
        score += 0.75

    return score + random.random() * 0.001


def _retrieve_rag_rows(
    skill: str,
    difficulty: str,
    seen_question_texts: Set[str] | None = None,
    score: float | None = None,
    limit: int = 4,
) -> List[Dict]:
    rows = [row for row in _load_grounding_rows() if _row_is_usable(row)]
    rows = _without_seen_questions(rows, seen_question_texts or set())
    query_tokens = _tokenize(_retrieval_query(skill, difficulty, score))
    candidates = [row for row in rows if _row_matches_skill(row, skill)]
    if not candidates:
        candidates = rows
    ranked = sorted(
        candidates,
        key=lambda row: _retrieval_score(row, query_tokens, skill, difficulty),
        reverse=True,
    )
    return ranked[:limit]


def _without_seen_questions(rows: List[Dict], seen_question_texts: Set[str]) -> List[Dict]:
    if not seen_question_texts:
        return rows
    seen = {text.strip().lower() for text in seen_question_texts if text.strip()}
    fresh_rows = [row for row in rows if _question_text(row).lower() not in seen]
    return fresh_rows


def _retrieve_verified_mcq(
    skill: str,
    difficulty: str,
    seen_question_texts: Set[str] | None = None,
    mastery_score: float | None = None,
) -> Dict | None:
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

    usable_rows = [row for row in rows if _row_is_usable(row)]
    matching = []
    for row in usable_rows:
        if _row_matches_skill(row, skill) and _difficulty_matches(str(row.get("difficulty", "")), difficulty):
            matching.append(row)

    if not matching:
        matching = [row for row in usable_rows if _row_matches_skill(row, skill)]

    matching = _without_seen_questions(matching, seen_question_texts or set())

    if not matching:
        return None

    query_tokens = _tokenize(_retrieval_query(skill, difficulty, mastery_score))
    ranked = sorted(
        matching,
        key=lambda row: _retrieval_score(row, query_tokens, skill, difficulty),
        reverse=True,
    )
    candidate_window = ranked[: min(25, len(ranked))]
    candidate = random.choice(candidate_window)
    return _normalize_mcq(candidate, skill, difficulty)


def _score_grounding_row(row: Dict, skill: str, difficulty: str) -> int:
    score = 0
    row_skill = _row_skill(row)
    row_diff = str(row.get("difficulty", "")).lower()
    if _row_matches_skill(row, skill):
        score += 3
    if row_diff == difficulty.lower():
        score += 2
    if difficulty.lower() == "hard" and row_diff in {"medium", "easy"}:
        score += 1
    if difficulty.lower() == "easy" and row_diff == "medium":
        score += 1
    return score


def _select_grounding(
    skill: str,
    difficulty: str,
    seen_question_texts: Set[str] | None = None,
    score: float | None = None,
) -> List[Dict]:
    retrieved = _retrieve_rag_rows(skill, difficulty, seen_question_texts, score, limit=4)
    if retrieved:
        return retrieved

    rows = _load_grounding_rows()
    scored = [(_score_grounding_row(row, skill, difficulty), row) for row in rows]
    scored = [item for item in scored if item[0] > 0]
    scored.sort(key=lambda x: (-x[0], random.random()))
    return [row for _, row in scored[:4]]


def _build_context_text(rows: List[Dict]) -> str:
    lines = []
    for index, row in enumerate(rows, start=1):
        lines.append(f"Retrieved source {index}:")
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
        lines.append("")
    return "\n".join(lines)


def _build_grounded_prompt(
    skill: str,
    difficulty: str,
    rows: List[Dict],
    seen_question_texts: Set[str] | None = None,
) -> str:
    context = _build_context_text(rows)
    avoided = "\n".join(f"- {text}" for text in list(seen_question_texts or set())[:10])
    avoid_instruction = (
        f"\nQuestions this user has already seen; do not repeat or closely paraphrase these:\n{avoided}\n"
        if avoided
        else ""
    )
    verbal_instruction = ""
    if skill == "Verbal Ability":
        verbal_instruction = """
For Verbal Ability:
- If you create a reading-comprehension item, write an original 90-140 word passage with at least 4 sentences.
- Do not use a one-sentence passage.
- Do not truncate the passage with "...".
- Do not place the exact correct answer phrase in the passage when the question only asks for direct recall.
- Prefer vocabulary, grammar, sentence improvement, analogy, or inference questions when the retrieved sources do not contain a complete passage.
"""
    payload = f"""
Generate a {difficulty} multiple-choice question for {skill}.

Use only the retrieved sources below as grounding. If a source includes an Anchor fact, Use case, or Use case description, include the needed context inside the question stem so the learner can answer without hidden information. Do not write phrases like "this specific use case" unless the use case is explicitly included in the same question. Keep the correct option verifiable from the retrieved sources.
{verbal_instruction}

Grounding examples:
{context}
{avoid_instruction}

Return JSON only:
{{
    "question": "...",
    "option_A": "...",
    "option_B": "...",
    "option_C": "...",
    "option_D": "...",
    "correct_option": "A",
    "logic_explanation": "...",
    "context": "optional context used in the question, or empty string"
}}
"""
    return payload


async def get_hybrid_mcq(skill, difficulty, score, use_cloud, seen_question_texts=None):
    seen_question_texts = set(seen_question_texts or [])
    verified_mcq = _retrieve_verified_mcq(skill, difficulty, seen_question_texts, score)
    if verified_mcq is not None:
        return verified_mcq

    grounding_rows = _select_grounding(skill, difficulty, seen_question_texts, score)
    prompt = _build_grounded_prompt(skill, difficulty, grounding_rows, seen_question_texts)

    if use_cloud and cloud_client is not None:
        try:
            res = cloud_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config={"response_mime_type": "application/json"},
            )
            mcq = _normalize_mcq(json.loads(res.text), skill, difficulty)
            return mcq if _row_is_usable(mcq) else _fallback_mcq(skill, difficulty)
        except Exception as e:
            print(f"Cloud generation failed. Falling back to local model: {e}")

    if local_client is not None:
        try:
            res = local_client.chat.completions.create(
                model="gemma3:1b",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            mcq = _normalize_mcq(json.loads(res.choices[0].message.content), skill, difficulty)
            return mcq if _row_is_usable(mcq) else _fallback_mcq(skill, difficulty)
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
            if is_correct and sub.difficulty in ["Easy", "Medium"]:
                expert = ""

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
