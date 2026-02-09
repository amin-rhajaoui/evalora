"""
Router pour l'évaluation et le feedback
"""
from fastapi import APIRouter, Depends, HTTPException
import uuid
import json
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models.evaluation import (
    Evaluation, EvaluationCreate, EvaluationResponse,
    FeedbackResponse, CriterionScore
)
from ..services.evaluation_service import EvaluationService
from ..services.voice_agent_service import voice_agent_service
from ..db.database import get_db
from ..db.models import ExamSession, EvaluationResult
from ..config import AVATARS

router = APIRouter()
evaluation_service = EvaluationService()
logger = logging.getLogger("evalora.evaluation")

TRANSCRIPT_SEP = "\n"


def _build_transcripts_from_entries(transcript_entries):
    """Construit monologue_transcript et debat_transcript à partir des entrées."""
    monologue_parts = []
    debat_parts = []
    for e in transcript_entries:
        if e.role != "user":
            continue
        text = (e.text or "").strip()
        if not text:
            continue
        if e.phase == "monologue":
            monologue_parts.append(text)
        elif e.phase == "debat":
            debat_parts.append(text)
    return (
        TRANSCRIPT_SEP.join(monologue_parts) if monologue_parts else None,
        TRANSCRIPT_SEP.join(debat_parts) if debat_parts else None,
    )


def _build_full_transcript_from_entries(transcript_entries):
    """Construit la transcription complète monologue + débat (user + assistant)."""
    monologue_parts = []
    debat_parts = []
    for e in transcript_entries:
        text = (e.text or "").strip()
        if not text:
            continue
        prefix = "Étudiant" if e.role == "user" else "Examinateur"
        line = f"{prefix}: {text}"
        if e.phase == "monologue":
            monologue_parts.append(line)
        elif e.phase == "debat":
            debat_parts.append(line)
    return (
        TRANSCRIPT_SEP.join(monologue_parts) if monologue_parts else None,
        TRANSCRIPT_SEP.join(debat_parts) if debat_parts else None,
    )


def _serialize_scores(scores_dict):
    """Serialize CriterionScore dict to JSON-safe dict."""
    return {k: v.model_dump() for k, v in scores_dict.items()}


def _deserialize_scores(scores_json):
    """Deserialize JSON dict to CriterionScore dict."""
    if not scores_json:
        return {}
    return {k: CriterionScore(**v) for k, v in scores_json.items()}


@router.post("/submit", response_model=EvaluationResponse)
async def submit_evaluation(data: EvaluationCreate, db: AsyncSession = Depends(get_db)):
    """Soumet une session pour évaluation."""
    monologue_transcript = data.monologue_transcript
    debat_transcript = data.debat_transcript

    if not monologue_transcript or not debat_transcript:
        transcription = await voice_agent_service.get_transcription(db, data.session_id)
        if transcription and transcription.transcript:
            built_mono, built_debat = _build_full_transcript_from_entries(transcription.transcript)
            if not monologue_transcript:
                monologue_transcript = built_mono
            if not debat_transcript:
                debat_transcript = built_debat

    evaluation = await evaluation_service.evaluate(
        session_id=data.session_id,
        monologue_transcript=monologue_transcript,
        debat_transcript=debat_transcript,
        monologue_duration=data.monologue_duration,
        debat_duration=data.debat_duration,
    )

    # Persist to DB
    db_eval = EvaluationResult(
        session_id=data.session_id,
        total_score=evaluation.total_score,
        monologue_scores_json=_serialize_scores(evaluation.monologue_scores),
        debat_scores_json=_serialize_scores(evaluation.debat_scores),
        general_scores_json=_serialize_scores(evaluation.general_scores),
        summary=evaluation.summary,
        strengths_json=evaluation.strengths,
        improvements_json=evaluation.improvements,
        advice_json=evaluation.advice,
        monologue_duration=evaluation.monologue_duration,
        debat_duration=evaluation.debat_duration,
    )
    db.add(db_eval)
    await db.commit()

    grade_letter = get_grade_letter(evaluation.total_score)
    passed = evaluation.total_score >= 10

    return EvaluationResponse(
        session_id=data.session_id,
        total_score=evaluation.total_score,
        max_score=evaluation.max_score,
        grade_letter=grade_letter,
        passed=passed,
    )


@router.post("/auto-evaluate", response_model=EvaluationResponse)
async def auto_evaluate(session_id: str, db: AsyncSession = Depends(get_db)):
    """
    Auto-évaluation déclenchée par l'agent à la fin du débat.
    Récupère la transcription depuis la BDD, évalue, persiste.
    """
    # Check if already evaluated
    existing = await db.execute(
        select(EvaluationResult).where(EvaluationResult.session_id == session_id)
    )
    ev = existing.scalar_one_or_none()
    if ev:
        grade_letter = get_grade_letter(ev.total_score)
        return EvaluationResponse(
            session_id=session_id,
            total_score=ev.total_score,
            max_score=20.0,
            grade_letter=grade_letter,
            passed=ev.total_score >= 10,
        )

    # Get session for durations
    session_result = await db.execute(
        select(ExamSession).where(ExamSession.id == session_id)
    )
    session = session_result.scalar_one_or_none()

    monologue_duration = session.monologue_duration or 0 if session else 0
    debat_duration = session.debat_duration or 0 if session else 0

    # Get transcription
    transcription = await voice_agent_service.get_transcription(db, session_id)
    monologue_transcript = None
    debat_transcript = None
    if transcription and transcription.transcript:
        monologue_transcript, debat_transcript = _build_full_transcript_from_entries(
            transcription.transcript
        )

    evaluation = await evaluation_service.evaluate(
        session_id=session_id,
        monologue_transcript=monologue_transcript,
        debat_transcript=debat_transcript,
        monologue_duration=monologue_duration,
        debat_duration=debat_duration,
    )

    # Persist
    db_eval = EvaluationResult(
        session_id=session_id,
        total_score=evaluation.total_score,
        monologue_scores_json=_serialize_scores(evaluation.monologue_scores),
        debat_scores_json=_serialize_scores(evaluation.debat_scores),
        general_scores_json=_serialize_scores(evaluation.general_scores),
        summary=evaluation.summary,
        strengths_json=evaluation.strengths,
        improvements_json=evaluation.improvements,
        advice_json=evaluation.advice,
        avatar_id=session.avatar_id if session else None,
        monologue_duration=monologue_duration,
        debat_duration=debat_duration,
    )
    db.add(db_eval)
    await db.commit()

    grade_letter = get_grade_letter(evaluation.total_score)
    return EvaluationResponse(
        session_id=session_id,
        total_score=evaluation.total_score,
        max_score=evaluation.max_score,
        grade_letter=grade_letter,
        passed=evaluation.total_score >= 10,
    )


@router.get("/{session_id}", response_model=FeedbackResponse)
async def get_feedback(session_id: str, avatar_id: str = None, db: AsyncSession = Depends(get_db)):
    """Récupère le feedback détaillé pour une session."""
    result = await db.execute(
        select(EvaluationResult).where(EvaluationResult.session_id == session_id)
    )
    db_eval = result.scalar_one_or_none()

    if not db_eval:
        raise HTTPException(status_code=404, detail="Évaluation non trouvée")

    monologue_scores = _deserialize_scores(db_eval.monologue_scores_json)
    debat_scores = _deserialize_scores(db_eval.debat_scores_json)
    general_scores = _deserialize_scores(db_eval.general_scores_json)

    monologue_score = sum(s.score for s in monologue_scores.values())
    debat_score = sum(s.score for s in debat_scores.values())
    general_score = sum(s.score for s in general_scores.values())

    avatar_name = None
    summary = db_eval.summary or ""
    if avatar_id and avatar_id in AVATARS:
        avatar_name = AVATARS[avatar_id]["name"]
        tone = AVATARS[avatar_id].get("feedback_tone", "neutral")
        if "chaleureux" in tone.lower() or "empathique" in tone.lower():
            summary = f"Bravo ! {summary}"
        elif "encourageant" in tone.lower():
            summary = f"Super ! {summary}"
        elif "exigeant" in tone.lower() and db_eval.total_score < 14:
            summary = f"Il y a du travail, mais c'est un début. {summary}"

    monologue_sec = db_eval.monologue_duration or 0
    debat_sec = db_eval.debat_duration or 0
    grade_letter = get_grade_letter(db_eval.total_score)

    # Get student name from session
    session_result = await db.execute(
        select(ExamSession).where(ExamSession.id == session_id)
    )
    session = session_result.scalar_one_or_none()
    student_name = session.student_name if session else "Étudiant"

    return FeedbackResponse(
        session_id=session_id,
        student_name=student_name,
        avatar_name=avatar_name,
        total_score=db_eval.total_score,
        grade_letter=grade_letter,
        passed=db_eval.total_score >= 10,
        monologue_score=monologue_score,
        debat_score=debat_score,
        general_score=general_score,
        summary=summary,
        strengths=db_eval.strengths_json or [],
        improvements=db_eval.improvements_json or [],
        advice=db_eval.advice_json or [],
        detailed_scores={
            "monologue": list(monologue_scores.values()),
            "debat": list(debat_scores.values()),
            "general": list(general_scores.values()),
        },
        monologue_duration=format_duration(monologue_sec),
        debat_duration=format_duration(debat_sec),
        total_duration=format_duration(monologue_sec + debat_sec),
    )


@router.get("/{session_id}/summary")
async def get_evaluation_summary(session_id: str, db: AsyncSession = Depends(get_db)):
    """Récupère un résumé rapide de l'évaluation"""
    result = await db.execute(
        select(EvaluationResult).where(EvaluationResult.session_id == session_id)
    )
    db_eval = result.scalar_one_or_none()

    if not db_eval:
        raise HTTPException(status_code=404, detail="Évaluation non trouvée")

    grade_letter = get_grade_letter(db_eval.total_score)
    return {
        "session_id": session_id,
        "total_score": db_eval.total_score,
        "max_score": 20.0,
        "grade_letter": grade_letter,
        "passed": db_eval.total_score >= 10,
        "summary": db_eval.summary,
    }


def get_grade_letter(score: float) -> str:
    if score >= 16:
        return "A"
    elif score >= 14:
        return "B"
    elif score >= 12:
        return "C"
    elif score >= 10:
        return "D"
    else:
        return "E"


def format_duration(seconds: int) -> str:
    if seconds < 0:
        seconds = 0
    m, s = divmod(seconds, 60)
    return f"{int(m):02d}:{int(s):02d}"
