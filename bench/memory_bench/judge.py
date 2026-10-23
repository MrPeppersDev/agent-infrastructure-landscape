"""Shared answer and judge prompts.

Every system's retrieved memories go through the SAME answer prompt and
model, and every answer through the SAME judge prompt and model, so score
differences come from the memory layer alone.

The judge follows LongMemEval's evaluation design (an LLM decides whether
the response contains the correct answer, with type-specific leniency for
temporal off-by-one, knowledge updates where the latest value must win,
preference questions and abstention). The wording here is our own, not a
copy of LongMemEval's script, so absolute numbers are comparable within
this harness, not to scores reported elsewhere.
"""

from __future__ import annotations

ANSWER_SYSTEM = (
    "You answer questions about a user's past conversations using ONLY the memories provided. "
    "Memories may be out of date: when two memories conflict, prefer the more recent one. "
    "If the memories do not contain the answer, say exactly: \"The information is not mentioned.\" "
    "Answer in one or two short sentences."
)


def answer_prompt(question: str, question_date: str, memories: list[str]) -> str:
    mem = "\n".join(f"- {m}" for m in memories) if memories else "- (no memories retrieved)"
    date = f"Today's date: {question_date}\n" if question_date else ""
    return f"Memories:\n{mem}\n\n{date}Question: {question}\nAnswer:"


JUDGE_SYSTEM = (
    "JUDGE. You grade whether a model's response to a question is correct, given the correct answer. "
    "Reply with exactly one word: yes or no."
)

_RULES = {
    "temporal-reasoning": "Accept off-by-one errors in counts of days, weeks or months.",
    "temporal": "Accept off-by-one errors in counts of days, weeks or months.",
    "knowledge-update": "The correct answer is the LATEST value. A response that gives the latest value is correct even if it also mentions the old one; a response that gives only an outdated value is wrong.",
    "single-session-preference": "The correct answer is a rubric of the user's preferences. The response is correct if it uses and respects that personal information.",
}


def judge_prompt(question: str, gold: str, response: str, qtype: str, abstention: bool) -> str:
    if abstention:
        rule = ("The correct behaviour is to say the information is not available. "
                "The response is correct only if it says the information is not mentioned or unknown.")
    else:
        rule = _RULES.get(qtype, "The response is correct if it contains the correct answer or an equivalent, even with extra detail; it is wrong if it is missing, contradicts it, or only gives part of it.")
    return (f"Question: {question}\nCorrect answer: {gold}\nModel response: {response}\n\n"
            f"Rule: {rule}\nIs the model response correct? Answer yes or no.")


def parse_verdict(text: str) -> bool:
    return text.strip().lower().lstrip("*\"' ").startswith("yes")
