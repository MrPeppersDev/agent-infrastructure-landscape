"""Dataset loaders. Both benchmarks are normalised to the same shape:

    Conversation(id, sessions=[Session(id, date, turns=[Turn(speaker, text)])])
    Question(id, conversation_id, text, answer, qtype, date, abstention)

LongMemEval (Wu et al., ICLR 2025): every question has its own haystack of
chat sessions, so each question is its own Conversation. Question types:
single-session-user / -assistant / -preference, temporal-reasoning,
knowledge-update, multi-session; ids ending in `_abs` are abstention
questions (the right answer is "not mentioned").
  https://github.com/xiaowu0162/LongMemEval
  https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned

LoCoMo (Maharana et al., ACL 2024): 10 long two-speaker conversations with
~200 QA each. `category` is kept as-is (1–5); category 5 (adversarial, no
gold answer in the data) is excluded by default, as most published
evaluations do.
  https://github.com/snap-research/locomo  (data/locomo10.json)
"""

from __future__ import annotations

import json
import random
import re
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

CACHE = Path(__file__).resolve().parent.parent / ".cache"

SOURCES = {
    "longmemeval_s": "https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/main/longmemeval_s_cleaned.json",
    "longmemeval_oracle": "https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/main/longmemeval_oracle.json",
    "locomo": "https://raw.githubusercontent.com/snap-research/locomo/main/data/locomo10.json",
}

LOCOMO_CATEGORY = {
    # Category numbers as stored in locomo10.json. The labels follow the
    # mapping most public evaluations use; they are descriptive only.
    1: "multi-hop",
    2: "temporal",
    3: "open-domain",
    4: "single-hop",
    5: "adversarial",
}


@dataclass
class Turn:
    speaker: str
    text: str


@dataclass
class Session:
    id: str
    date: str
    turns: list[Turn] = field(default_factory=list)


@dataclass
class Conversation:
    id: str
    sessions: list[Session]
    speakers: tuple[str, str] = ("user", "assistant")


@dataclass
class Question:
    id: str
    conversation_id: str
    text: str
    answer: str
    qtype: str
    date: str = ""
    abstention: bool = False
    evidence: list[str] = field(default_factory=list)


@dataclass
class Dataset:
    name: str
    conversations: dict[str, Conversation]
    questions: list[Question]


def fetch(name: str, path: str | None = None) -> Path:
    """Return a local path for a dataset, downloading it once into .cache/."""
    if path:
        return Path(path)
    CACHE.mkdir(parents=True, exist_ok=True)
    dest = CACHE / Path(SOURCES[name]).name
    if not dest.exists():
        req = urllib.request.Request(SOURCES[name], headers={"User-Agent": "memory-bench/0.1"})
        with urllib.request.urlopen(req, timeout=300) as r, open(dest, "wb") as f:
            f.write(r.read())
    return dest


def load_longmemeval(path: Path, name: str = "longmemeval_s") -> Dataset:
    items = json.loads(path.read_text())
    convs: dict[str, Conversation] = {}
    qs: list[Question] = []
    for it in items:
        qid = str(it["question_id"])
        sessions = []
        for sid, date, sess in zip(it["haystack_session_ids"], it["haystack_dates"], it["haystack_sessions"]):
            sessions.append(Session(id=str(sid), date=str(date),
                                    turns=[Turn(t["role"], t["content"]) for t in sess]))
        convs[qid] = Conversation(id=qid, sessions=sessions)
        qs.append(Question(id=qid, conversation_id=qid, text=it["question"], answer=str(it["answer"]),
                           qtype=it["question_type"], date=str(it.get("question_date", "")),
                           abstention=qid.endswith("_abs"),
                           evidence=[str(s) for s in it.get("answer_session_ids", [])]))
    return Dataset(name, convs, qs)


def load_locomo(path: Path, include_adversarial: bool = False) -> Dataset:
    samples = json.loads(path.read_text())
    convs: dict[str, Conversation] = {}
    qs: list[Question] = []
    for s in samples:
        cid = str(s["sample_id"])
        c = s["conversation"]
        nums = sorted(int(m.group(1)) for k in c if (m := re.fullmatch(r"session_(\d+)", k)))
        sessions = []
        for n in nums:
            turns = []
            for t in c[f"session_{n}"]:
                text = t.get("text", "")
                if t.get("blip_caption"):
                    text = f"{text} [shares an image: {t['blip_caption']}]".strip()
                turns.append(Turn(t["speaker"], text))
            sessions.append(Session(id=f"{cid}-s{n}", date=str(c.get(f"session_{n}_date_time", "")), turns=turns))
        convs[cid] = Conversation(id=cid, sessions=sessions, speakers=(c.get("speaker_a", "A"), c.get("speaker_b", "B")))
        for i, q in enumerate(s.get("qa", [])):
            cat = int(q.get("category", 0))
            if cat == 5 and not include_adversarial:
                continue
            ans = q.get("answer", q.get("adversarial_answer", ""))
            qs.append(Question(id=f"{cid}-q{i}", conversation_id=cid, text=q["question"], answer=str(ans),
                               qtype=LOCOMO_CATEGORY.get(cat, f"category-{cat}"),
                               abstention=(cat == 5), evidence=[str(e) for e in q.get("evidence", [])]))
    return Dataset("locomo", convs, qs)


def load(name: str, path: str | None = None, **kw) -> Dataset:
    if name.startswith("longmemeval"):
        return load_longmemeval(fetch(name, path), name)
    if name == "locomo":
        return load_locomo(fetch(name, path), **kw)
    if name == "smoke":
        return smoke()
    raise SystemExit(f"unknown dataset {name!r}; choose longmemeval_s, longmemeval_oracle, locomo or smoke")


def sample(ds: Dataset, limit: int | None, types: list[str] | None, seed: int = 7,
           per_type: int | None = None) -> Dataset:
    """Deterministic subset: filter by type, then either `per_type` per
    type (stratified) or `limit` overall, keeping only the conversations
    the chosen questions need."""
    qs = [q for q in ds.questions if not types or q.qtype in types]
    rng = random.Random(seed)
    if per_type:
        by: dict[str, list[Question]] = {}
        for q in qs:
            by.setdefault(q.qtype, []).append(q)
        qs = []
        for t in sorted(by):
            pool = by[t][:]
            rng.shuffle(pool)
            qs.extend(pool[:per_type])
    elif limit and len(qs) > limit:
        qs = rng.sample(qs, limit)
    qs.sort(key=lambda q: q.id)
    need = {q.conversation_id for q in qs}
    return Dataset(ds.name, {k: v for k, v in ds.conversations.items() if k in need}, qs)


def smoke() -> Dataset:
    """A tiny offline dataset with an update, a temporal and an abstention
    question — used by tests and `--dataset smoke`."""
    conv = Conversation(id="smoke-1", sessions=[
        Session("s1", "2026/01/05 (Mon) 10:00", [
            Turn("user", "Hi! I just moved to Lisbon for work."),
            Turn("assistant", "Congratulations on the move to Lisbon!"),
            Turn("user", "My dog is called Pixel, she's a border collie."),
        ]),
        Session("s2", "2026/03/12 (Thu) 09:30", [
            Turn("user", "Update: I relocated again, I live in Hong Kong now."),
            Turn("assistant", "Got it, Hong Kong it is."),
            Turn("user", "I started training for a half marathon in February."),
        ]),
    ])
    qs = [
        Question("smoke-1-q1", "smoke-1", "Which city does the user live in now?", "Hong Kong", "knowledge-update", "2026/04/01"),
        Question("smoke-1-q2", "smoke-1", "What is the name of the user's dog?", "Pixel", "single-session-user", "2026/04/01"),
        Question("smoke-1-q3", "smoke-1", "When did the user start half-marathon training?", "February 2026", "temporal-reasoning", "2026/04/01"),
        Question("smoke-1-q4_abs", "smoke-1", "What is the user's favourite film?", "The information is not mentioned.", "single-session-user", "2026/04/01", abstention=True),
    ]
    return Dataset("smoke", {conv.id: conv}, qs)
