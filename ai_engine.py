import json

from config import cloud_client, local_client

OPTION_KEYS = ("A", "B", "C", "D")


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

    fallback = _fallback_mcq(skill, difficulty)
    for key, value in fallback.items():
        raw_data.setdefault(key, value)

    correct_option = str(raw_data.get("correct_option", "A")).strip().upper()
    if correct_option.startswith("OPTION_"):
        correct_option = correct_option[-1]
    raw_data["correct_option"] = correct_option if correct_option in OPTION_KEYS else "A"

    return raw_data


async def get_hybrid_mcq(skill, difficulty, score, use_cloud):
    aptitude_ctx = ""
    if skill == "Aptitude":
        aptitude_ctx = "Focus on Quant/Logic. NO programming terms."

    verbal_context = ""
    if skill == "Verbal Ability":
        verbal_context = (
            "Focus only on Synonyms, Antonyms, Grammar (Spotting Errors), "
            "Sentence Completion, Analogies, and Idioms. Questions should be at "
            "GRE/GMAT or corporate placement paper level, such as TCS, Infosys, "
            "or Accenture. Strictly forbid General Knowledge, Science, Biology, "
            "or History questions."
        )

    prompt = f"""
    Generate a {difficulty} MCQ for {skill}. {aptitude_ctx} {verbal_context}
    STRICT JSON structure:
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

    if use_cloud:
        try:
            res = cloud_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config={"response_mime_type": "application/json"},
            )
            return _normalize_mcq(json.loads(res.text), skill, difficulty)
        except Exception as e:
            print(f"Cloud generation failed. Falling back to local model: {e}")

    try:
        res = local_client.chat.completions.create(
            model="gemma3:1b",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        return _normalize_mcq(json.loads(res.choices[0].message.content), skill, difficulty)
    except Exception as e:
        print(f"Local generation failed. Using fallback MCQ: {e}")
        return _fallback_mcq(skill, difficulty)


async def get_dual_feedback(sub):
    prompt = f"""
    Question: {sub.question_text}
    Student: {sub.selected_option_text} | Correct: {sub.correct_option_text}
    Return JSON: {{"mentor": "1-sentence Socratic tip", "expert": "1-sentence Industry insight"}}
    """

    try:
        res = local_client.chat.completions.create(
            model="gemma3:1b",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        feedback = json.loads(res.choices[0].message.content)
        if isinstance(feedback, dict):
            return {
                "mentor": feedback.get(
                    "mentor",
                    "Review the concept and try explaining your reasoning in one line.",
                ),
                "expert": feedback.get(
                    "expert",
                    "This concept matters because it helps you make reliable decisions under constraints.",
                ),
            }
    except Exception as e:
        print(f"Feedback generation failed. Using fallback feedback: {e}")

    return {
        "mentor": "Review the concept and try explaining your reasoning in one line.",
        "expert": "This concept matters because it helps you make reliable decisions under constraints.",
    }
