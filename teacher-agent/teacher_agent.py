"""Teacher Agent: an AI "teacher" that assigns research lessons to "student" agents.

The teacher splits a topic into lessons, sends each lesson to a student agent that
researches it on the web (web_search + web_fetch), grades the returned report
against the lesson's criteria, sends it back with feedback if needed, and finally
writes one combined report with references.

Usage:
    python teacher_agent.py "your topic"
"""

from __future__ import annotations

import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import anthropic

# ---------------------------------------------------------------------------
# Settings (override with environment variables)
# ---------------------------------------------------------------------------
TEACHER_MODEL = os.environ.get("TEACHER_MODEL", "claude-opus-5-5")
STUDENT_MODEL = os.environ.get("STUDENT_MODEL", "claude-opus-5-5")
TEACHER_EFFORT = os.environ.get("TEACHER_EFFORT", "high")
STUDENT_EFFORT = os.environ.get("STUDENT_EFFORT", "medium")
MAX_ASSIGNMENTS = int(os.environ.get("MAX_ASSIGNMENTS", "12"))  # lessons + revisions in total
MAX_SEARCHES_PER_LESSON = int(os.environ.get("MAX_SEARCHES_PER_LESSON", "6"))
MAX_PARALLEL_STUDENTS = int(os.environ.get("MAX_PARALLEL_STUDENTS", "4"))
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "reports"))

# Server-side fallback: if a model declines a request, the API retries it on
# Anthropic's recommended fallback model instead of returning a refusal.
FALLBACK_BETA = "server-side-fallback-2026-07-01"

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------
STUDENT_SYSTEM = """You are a research student. Your teacher gives you one lesson at a time.

How to work:
- Search the web with web_search, then open the most relevant pages with web_fetch and read them; do not rely on search snippets alone.
- Prefer primary and authoritative sources (official docs, papers, standards bodies, reputable news). Note the publication date of each source.
- If sources disagree, say so and explain which you trust more and why.
- If you could not find something, say so plainly. Never invent facts or URLs.
- Address every point in the teacher's criteria and feedback.

Answer in the same language as the lesson, in this format:

## Findings
Key points, each followed by its source number, e.g. [1].

## Open questions
What remains uncertain or unverified.

## Sources
[1] Title - URL (date)
"""

TEACHER_SYSTEM = """You are a teacher who directs research done by student agents.
You cannot browse the web yourself; your students can, through the assign_lesson tool.

Process:
1. Break the user's topic into 2-5 focused lessons that together cover it.
2. Assign each lesson with assign_lesson. Give the student a clear goal and concrete, checkable criteria
   (e.g. "at least 3 independent sources, at least 1 primary source, include dates"). Assign independent
   lessons in the same turn so students can work in parallel.
3. Grade each report against its criteria. If sources are weak, claims are unsupported, sources conflict
   without explanation, or the criteria are not met, assign that lesson again with specific feedback.
   Give at most 2 revisions per lesson.
4. When every lesson passes (or revisions are used up), write the final report: a clear, well-structured
   synthesis of what the students found, citing sources inline, with a deduplicated reference list at the end
   and a short note on any limitations. Use only facts that students found and cited.

Write the final report in the same language the user used for the topic."""

WEB_TOOLS = [
    {"type": "web_search_20260209", "name": "web_search", "max_uses": MAX_SEARCHES_PER_LESSON},
    {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": MAX_SEARCHES_PER_LESSON},
]

TEACHER_TOOLS = [
    {
        "name": "assign_lesson",
        "description": (
            "Send one research lesson to a student agent, who searches the web and returns a report "
            "with findings and cited sources. Call it several times in one turn to run students in parallel. "
            "To request a revision, call it again with the same lesson and your feedback."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "lesson": {"type": "string", "description": "What the student must research and answer."},
                "criteria": {"type": "string", "description": "Checkable criteria the report must meet to pass."},
                "feedback": {
                    "type": "string",
                    "description": "Feedback on the previous attempt; empty string for a first assignment.",
                },
            },
            "required": ["lesson", "criteria", "feedback"],
            "additionalProperties": False,
        },
    }
]

_print_lock = threading.Lock()


def log(message: str) -> None:
    with _print_lock:
        print(message, flush=True)


def text_of(response) -> str:
    return "\n".join(block.text for block in response.content if block.type == "text").strip()


def call_claude(**kwargs):
    """messages.create with server-side refusal fallback enabled."""
    return client.beta.messages.create(betas=[FALLBACK_BETA], fallbacks="default", **kwargs)


# ---------------------------------------------------------------------------
# Student
# ---------------------------------------------------------------------------
def run_student(number: int, lesson: str, criteria: str, feedback: str) -> str:
    tag = f"[student {number}]"
    log(f"{tag} {'revising' if feedback else 'starting'}: {lesson[:90]}")

    prompt = f"Lesson:\n{lesson}\n\nCriteria to pass:\n{criteria}"
    if feedback:
        prompt += f"\n\nTeacher's feedback on your previous attempt (address all of it):\n{feedback}"
    messages = [{"role": "user", "content": prompt}]

    for _ in range(10):  # a paused server-tool turn is continued by sending it back
        response = call_claude(
            model=STUDENT_MODEL,
            max_tokens=16000,
            system=STUDENT_SYSTEM,
            tools=WEB_TOOLS,
            output_config={"effort": STUDENT_EFFORT},
            messages=messages,
        )
        if response.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": response.content})
            continue
        break

    if response.stop_reason == "refusal":
        log(f"{tag} declined the lesson")
        return "The student could not complete this lesson (the request was declined)."

    log(f"{tag} done")
    report = text_of(response)
    return report or "The student returned no report."


# ---------------------------------------------------------------------------
# Teacher
# ---------------------------------------------------------------------------
def run_teacher(topic: str) -> str:
    log(f"[teacher] topic: {topic}")
    messages = [{"role": "user", "content": f"Topic to research and teach:\n{topic}"}]
    assignments = 0

    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_STUDENTS) as pool:
        while True:
            with client.beta.messages.stream(
                model=TEACHER_MODEL,
                max_tokens=64000,
                system=TEACHER_SYSTEM,
                tools=TEACHER_TOOLS,
                output_config={"effort": TEACHER_EFFORT},
                betas=[FALLBACK_BETA],
                fallbacks="default",
                messages=messages,
            ) as stream:
                response = stream.get_final_message()

            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "refusal":
                raise RuntimeError("The teacher declined this topic.")
            if response.stop_reason != "tool_use":
                return text_of(response)

            calls = [b for b in response.content if b.type == "tool_use"]
            futures = {}
            results = []
            for call in calls:
                if call.name != "assign_lesson":
                    results.append({"type": "tool_result", "tool_use_id": call.id,
                                    "content": f"Unknown tool {call.name}.", "is_error": True})
                elif assignments >= MAX_ASSIGNMENTS:
                    results.append({"type": "tool_result", "tool_use_id": call.id, "is_error": True,
                                    "content": "Assignment limit reached. Write the final report now "
                                               "from the reports you already have."})
                else:
                    assignments += 1
                    args = call.input
                    futures[call.id] = pool.submit(
                        run_student, assignments, args["lesson"], args["criteria"], args.get("feedback", "")
                    )

            for call_id, future in futures.items():
                try:
                    results.append({"type": "tool_result", "tool_use_id": call_id, "content": future.result()})
                except anthropic.APIError as exc:
                    results.append({"type": "tool_result", "tool_use_id": call_id, "is_error": True,
                                    "content": f"The student failed with an API error: {exc}"})

            log(f"[teacher] grading {len(results)} report(s)...")
            messages.append({"role": "user", "content": results})  # all results in one message


def save_report(topic: str, report: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^\w\u0E00-\u0E7F]+", "-", topic.lower()).strip("-")[:50] or "report"
    path = OUTPUT_DIR / f"{datetime.now():%Y%m%d-%H%M%S}-{slug}.md"
    path.write_text(f"# {topic}\n\n{report}\n", encoding="utf-8")
    return path


def main() -> None:
    topic = " ".join(sys.argv[1:]).strip() or input("Topic: ").strip()
    if not topic:
        sys.exit("Please give a topic, e.g. python teacher_agent.py \"history of RAG\"")

    report = run_teacher(topic)
    path = save_report(topic, report)
    print("\n" + "=" * 70 + "\n" + report + "\n" + "=" * 70)
    print(f"\nSaved to {path}")


if __name__ == "__main__":
    main()
