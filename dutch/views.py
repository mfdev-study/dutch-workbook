"""Views for the Dutch de/het article quiz."""

import random
from typing import Any

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render

from .models import DutchArticleQuestion

SESSION_KEY = "de_het_quiz"
QUIZ_SIZE = 5

# Category preference order: try to cover as many distinct rules as possible.
CATEGORY_ORDER = ["plural", "person", "diminutive", "ing", "heid", "memorize"]


def _new_quiz_state() -> dict[str, Any]:
    """Select 5 active questions, preferring distinct categories, randomized."""
    active = DutchArticleQuestion.objects.filter(is_active=True)
    questions = list(active)

    if not questions:
        return {"question_ids": [], "current": 0, "answers": []}

    by_category: dict[str, list[DutchArticleQuestion]] = {}
    for q in questions:
        by_category.setdefault(q.category, []).append(q)

    selected: list[DutchArticleQuestion] = []
    used: set[int] = set()

    for category in CATEGORY_ORDER:
        if len(selected) >= QUIZ_SIZE:
            break
        pool = [q for q in by_category.get(category, []) if q.id not in used]
        if pool:
            chosen = random.choice(pool)
            selected.append(chosen)
            used.add(chosen.id)

    remaining = [q for q in questions if q.id not in used]
    random.shuffle(remaining)
    for q in remaining:
        if len(selected) >= QUIZ_SIZE:
            break
        selected.append(q)
        used.add(q.id)

    random.shuffle(selected)
    return {
        "question_ids": [q.id for q in selected],
        "current": 0,
        "answers": [],
        "score": 0,
    }


def _session_state(request: HttpRequest) -> dict[str, Any] | None:
    return request.session.get(SESSION_KEY)


def _is_htmx(request: HttpRequest) -> bool:
    return bool(request.headers.get("HX-Request"))


@login_required
def quiz(request: HttpRequest) -> HttpResponse:
    """Start or continue the de/het quiz, or show the result when finished."""
    state = _session_state(request)
    if not state:
        state = _new_quiz_state()
        request.session[SESSION_KEY] = state
        request.session.modified = True

    question_ids: list[int] = state["question_ids"]
    current: int = state["current"]

    if not question_ids:
        template = "dutch/de_het_empty.html"
        if _is_htmx(request):
            template = "dutch/de_het_empty_partial.html"
        return render(request, template, {})

    if current >= len(question_ids):
        return _render_result(request, state)

    question = get_object_or_404(DutchArticleQuestion, id=question_ids[current])

    context: dict[str, Any] = {
        "question": question,
        "question_num": current + 1,
        "total": len(question_ids),
        "score": state["score"],
    }
    template = "dutch/de_het_question.html" if _is_htmx(request) else "dutch/de_het_quiz.html"
    return render(request, template, context)


@login_required
def answer(request: HttpRequest) -> HttpResponse:
    """Check a submitted answer against the database (authoritative)."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    state = _session_state(request)
    if not state:
        return JsonResponse({"error": "No quiz session"}, status=400)

    question_ids: list[int] = state["question_ids"]
    current: int = state["current"]

    if not question_ids or current >= len(question_ids):
        return JsonResponse({"error": "Quiz already finished"}, status=400)

    try:
        question_id = int(request.POST.get("question_id", ""))
    except (TypeError, ValueError):
        return JsonResponse({"error": "Invalid question_id"}, status=400)

    # The browser-sent question_id must match the server-side session pointer.
    if question_id != question_ids[current]:
        return JsonResponse({"error": "Question mismatch"}, status=400)

    answer_value = request.POST.get("answer", "").strip().lower()
    if answer_value not in ("de", "het"):
        return JsonResponse({"error": "Invalid answer"}, status=400)

    question = get_object_or_404(DutchArticleQuestion, id=question_id)
    # Correctness is derived from the database, never from the client.
    is_correct = answer_value == question.correct_article

    state["answers"].append(
        {
            "question_id": question_id,
            "chosen": answer_value,
            "correct_article": question.correct_article,
            "is_correct": is_correct,
        }
    )
    if is_correct:
        state["score"] = state.get("score", 0) + 1
    state["current"] = current + 1
    request.session[SESSION_KEY] = state
    request.session.modified = True

    context: dict[str, Any] = {
        "question": question,
        "chosen": answer_value,
        "is_correct": is_correct,
        "question_num": current + 1,
        "total": len(question_ids),
        "score": state["score"],
    }
    return render(request, "dutch/de_het_answer.html", context)


@login_required
def result(request: HttpRequest) -> HttpResponse:
    """Show the quiz result (always accessible; mirrors quiz() when finished)."""
    state = _session_state(request)
    if not state:
        template = "dutch/de_het_empty.html"
        if _is_htmx(request):
            template = "dutch/de_het_empty_partial.html"
        return render(request, template, {})
    return _render_result(request, state)


@login_required
def reset(request: HttpRequest) -> HttpResponse:
    """Clear the quiz session and start a brand-new randomized quiz."""
    request.session.pop(SESSION_KEY, None)
    request.session.modified = True
    return quiz(request)


def _render_result(request: HttpRequest, state: dict[str, Any]) -> HttpResponse:
    total = len(state["question_ids"])
    score = sum(1 for a in state["answers"] if a["is_correct"])
    percentage = round(score * 100 / total) if total else 0

    wrong_answers = [a for a in state["answers"] if not a["is_correct"]]
    wrong_question_ids = [a["question_id"] for a in wrong_answers]
    wrong_questions = {
        q.id: q for q in DutchArticleQuestion.objects.filter(id__in=wrong_question_ids)
    }
    mistakes = [
        {"question": wrong_questions[a["question_id"]], "chosen": a["chosen"]}
        for a in wrong_answers
        if a["question_id"] in wrong_questions
    ]

    context: dict[str, Any] = {
        "score": score,
        "total": total,
        "percentage": percentage,
        "mistakes": mistakes,
        "is_htmx": _is_htmx(request),
    }
    template = "dutch/de_het_result.html"
    if _is_htmx(request):
        template = "dutch/de_het_result_partial.html"
    return render(request, template, context)
