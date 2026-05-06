# Batch 1 — Education AI memory (9 entries, all NEW)

Returned by background research agent on 2026-05-06. All 9 verified absent from landscape.html. Target: new sub-group "— Education AI memory" under "Vertical / domain-specific AI memory".

## 1. Khanmigo (T2)
- URL: https://www.khanmigo.ai/
- Memory model: Persistent conversation history + Khan Academy mastery state
- What it does: Stores full chat transcripts per student (student + teacher dashboard); layers over Khan Academy mastery graph for cross-session topic awareness; cross-session memory derived from structured mastery state, not free-text recall.
- Claims: 2M students/educators/parents in 2024–25 school year; K–12 student usage 40k → 700k YoY (Khan Academy SY24-25 Annual Report).
- Pros: Uniquely integrates AI tutoring with a structured curriculum graph — memory is mapped to a known knowledge domain, making context-aware scaffolding architecturally meaningful.
- Cons: Adoption is shallow — only ~15% of students with access actually use it; cross-session memory bounded by mastery taxonomy rather than open-ended goals.
- Links: khanmigo.ai · Annual Report (annualreport.khanacademy.org) · CBS 60 Minutes coverage

## 2. Synthesis Tutor (T3)
- URL: https://www.synthesis.com/tutor
- Memory model: Real-time adaptive state via micro-assessments; no disclosed cross-session profile store
- What it does: Embeds micro-assessments per lesson to track understanding in real time; combines AI personalization with human-curated content. No publicly disclosed durable cross-session learner profile beyond progress within math curriculum (ages 5–11).
- Claims: On pace for $10M+ revenue 2025; subscribed students 4.5x YoY.
- Pros: Combines AI-driven real-time adaptation with neuroscientist/educator-designed content rather than relying solely on LLM output.
- Cons: Limited to math for ages 5–11; memory effectively session-scoped adaptive state, not a long-term learner model.
- Links: synthesis.com/tutor · Unite.AI review

## 3. SchoolAI (T2)
- URL: https://schoolai.com/
- Memory model: Teacher-configured Spaces with observable student interaction logs
- What it does: Teacher-created "Spaces" route students through agendas; Dot, the student-facing assistant, runs the conversation. Student interaction data surfaces to teachers via dashboards. Memory is within-space session context; teacher holds the persistent profile, not the AI itself.
- Claims: 1M+ classrooms in 80+ countries; 400+ district partnerships; $25M raised April 2025.
- Pros: Strongest teacher-visibility layer of any product in this set — all student AI interactions are logged and observable.
- Cons: Persistent "memory" is a teacher-readable log, not a student-facing adaptive model; no mechanism for the AI to carry context across different Spaces or subjects.
- Links: schoolai.com · OpenAI case study · Stanford SCALE research

## 4. Duolingo Max (T2)
- URL: https://blog.duolingo.com/duolingo-max/
- Memory model: Lesson-completion history + spaced-repetition state; character roleplay has per-call continuity
- What it does: Adds GPT-4-powered Roleplay (character conversations, with cross-call memory for "Lily") and Explain My Answer on top of Duolingo's existing SRS engine, which tracks per-word and per-skill mastery across sessions.
- Claims: ~9% of 12.2M paid subscribers on Max by end-2025 (~1.1M); 78% of Roleplay users reported better real-world conversation readiness.
- Pros: Memory is architecturally grounded in a proven SRS with decades of research; Explain My Answer delivers context-specific error explanation rather than generic feedback.
- Cons: GPT-4 features sit on top of a lesson-completion model — no holistic learner profile; Roleplay memory is character-scoped rather than learning-goal-scoped; Max pricing $168/yr vs standard Super.
- Links: Max blog · TechCrunch launch

## 5. ELSA Speak (T1)
- URL: https://elsaspeak.com/en/
- Memory model: Evolving phoneme-level pronunciation profile, proprietary non-native speech model
- What it does: Builds a persistent pronunciation profile per user, tracking which sounds, words, and patterns the learner consistently mispronounces. Self-evolving AI re-evaluates and updates the profile as the learner improves. Competitive moat is proprietary non-native accent training data, not a general LLM.
- Claims: 50M+ users in 200+ countries; $32.5M revenue 2023; $60M raised total.
- Pros: Only product in this set with a genuinely domain-specific persistent model — pronunciation-error memory is precise and directly actionable, not fuzzy conversational history.
- Cons: Scope is narrow (English pronunciation only); persistent profile does not extend to grammar, vocabulary, or other language dimensions.
- Links: elsaspeak.com · ELSA AI page

## 6. Speak (T2)
- URL: https://www.speak.com/
- Memory model: Personalized curriculum from onboarding assessment; limited cross-session vocabulary retention
- What it does: Onboarding assessment builds initial learner profile; AI supports open-ended conversational practice with real-time speech recognition. No SRS or long-term vocabulary tracking — saved phrases go to a Phrasebook but are not systematically reintegrated. Per-session context strong; cross-session memory structurally weak.
- Claims: 10M+ users; doubling annually for five years; $78M Series C at $1B (Dec 2024); $100M revenue 2025.
- Pros: Strongest real-time conversational AI of any language app — speech recognition, scenario roleplay, instant feedback are tightly integrated; OpenAI-backed.
- Cons: Cross-session memory acknowledged as a gap by reviewers — no SRS, no systematic error tracking across conversations, Phrasebook is passive rather than adaptive.
- Links: speak.com · OpenAI case study · TechCrunch Series C

## 7. Quizlet — AI Study Tools / Magic Notes (T1 SRS core / T3 AI personalization)
- URL: https://quizlet.com/features/ai-study-tools
- Memory model: Spaced-repetition Memory Score per study set; no cross-set or long-term learner profile
- What it does: Tracks per-card answer history within a study set; computes Memory Score for SRS scheduling. Magic Notes converts uploaded content into flashcard sets. Q-Chat (conversational AI) discontinued June 2025. Personalization scoped to individual study sets, not a unified learner model.
- Claims: 600M+ study sets created; used by 60% of US high school students.
- Pros: SRS scheduling is algorithmically mature and well-evidenced; Magic Notes dramatically reduces friction creating structured study material from unstructured content.
- Cons: Memory is siloed per study set with no cross-set or cross-subject learner model; Q-Chat shutdown left a gap in adaptive tutoring; memory does not carry forward to new content.
- Links: quizlet.com · AI Study Tools page · spaced-repetition page

## 8. ChatGPT Study Mode (T3)
- URL: https://openai.com/index/chatgpt-study-mode/
- Memory model: Optional cross-session memory (general ChatGPT Memory) + Socratic session scaffolding
- What it does: Activates a Socratic interaction style — asks guiding questions, scaffolds concepts, runs knowledge checks rather than providing direct answers. With ChatGPT Memory enabled, persists learning goals and facts across sessions. Memory is general ChatGPT Memory, not study-mode-specific — depth depends on user-enabled state.
- Claims: Launched July 30, 2025; available to all logged-in ChatGPT users (Free, Plus, Pro, Team); progress tracking across conversations marked as future work.
- Pros: Only product in this set built on a general-purpose model with cross-domain breadth — student can study any subject without vendor having pre-scoped curriculum; lowest friction (free tier).
- Cons: Implemented as custom system instructions rather than trained behavior — OpenAI describes it as a temporary iterative approach; educational memory is a thin layer over general ChatGPT Memory.
- Links: OpenAI Study Mode · OpenAI FAQ · Axios coverage

## 9. MagicSchool (T1 teacher tool, no student memory)
- URL: https://www.magicschool.ai/
- Memory model: No student-facing persistent memory; teacher context is user-input at tool-invocation time
- What it does: Teacher productivity platform (80+ teacher tools, 50+ student tools) for planning, differentiation, IEP generation, feedback. Does not maintain a cross-session learner model; teachers input student context manually each session; district deployments can pre-populate fields via RAG over uploaded curriculum documents.
- Claims: ~6M educators; 40% of US public schools; 13,000+ schools/districts in 160+ countries; 77% of teachers report significantly improved quality of life.
- Pros: Largest educator user base of any product in this set; district-level RAG customization (curriculum + policy docs) is a practical and architecturally honest form of context persistence.
- Cons: No student-facing memory or adaptive personalization — context is ephemeral and teacher-supplied each session (deliberate product choice, but disqualifies meaningful student-memory classification).
- Links: magicschool.ai · Impact Report
