"""
Router pour l'évaluation et le feedback
"""
from fastapi import APIRouter, HTTPException
from typing import Dict
import uuid

from ..models.evaluation import (
    Evaluation, EvaluationCreate, EvaluationResponse,
    FeedbackResponse, CriterionScore
)
from ..services.evaluation_service import EvaluationService
from ..config import AVATARS

router = APIRouter()
evaluation_service = EvaluationService()

# Stockage en mémoire
evaluations: Dict[str, Evaluation] = {}


@router.post("/submit", response_model=EvaluationResponse)
async def submit_evaluation(data: EvaluationCreate):
    """
    Soumet une session pour évaluation.

    Génère une note /20 basée sur la grille DU officielle
    et un feedback pédagogique personnalisé.
    """
    # Générer l'évaluation
    evaluation = await evaluation_service.evaluate(
        session_id=data.session_id,
        monologue_transcript=data.monologue_transcript,
        debat_transcript=data.debat_transcript,
        monologue_duration=data.monologue_duration,
        debat_duration=data.debat_duration
    )

    evaluations[data.session_id] = evaluation

    # Déterminer la lettre de note
    grade_letter = get_grade_letter(evaluation.total_score)
    passed = evaluation.total_score >= 10

    return EvaluationResponse(
        session_id=data.session_id,
        total_score=evaluation.total_score,
        max_score=evaluation.max_score,
        grade_letter=grade_letter,
        passed=passed
    )


@router.get("/{session_id}", response_model=FeedbackResponse)
async def get_feedback(session_id: str, avatar_id: str = None):
    """
    Récupère le feedback détaillé pour une session.

    Le feedback est adapté au ton de l'avatar si spécifié.
    """
    if session_id not in evaluations:
        raise HTTPException(status_code=404, detail="Évaluation non trouvée")

    evaluation = evaluations[session_id]

    # Adapter le feedback au ton de l'avatar
    avatar_name = None
    if avatar_id and avatar_id in AVATARS:
        avatar_name = AVATARS[avatar_id]["name"]
        evaluation = await evaluation_service.adapt_feedback_tone(
            evaluation,
            AVATARS[avatar_id]
        )

    # Calculer les scores par partie
    monologue_score = sum(s.score for s in evaluation.monologue_scores.values())
    debat_score = sum(s.score for s in evaluation.debat_scores.values())
    general_score = sum(s.score for s in evaluation.general_scores.values())

    # Formater les durées
    monologue_duration = format_duration(evaluation.id)  # Placeholder
    debat_duration = format_duration(evaluation.id)
    total_duration = format_duration(evaluation.id)

    grade_letter = get_grade_letter(evaluation.total_score)

    return FeedbackResponse(
        session_id=session_id,
        student_name="Étudiant",  # À récupérer de la session
        avatar_name=avatar_name,
        total_score=evaluation.total_score,
        grade_letter=grade_letter,
        passed=evaluation.total_score >= 10,
        monologue_score=monologue_score,
        debat_score=debat_score,
        general_score=general_score,
        summary=evaluation.summary,
        strengths=evaluation.strengths,
        improvements=evaluation.improvements,
        advice=evaluation.advice,
        detailed_scores={
            "monologue": list(evaluation.monologue_scores.values()),
            "debat": list(evaluation.debat_scores.values()),
            "general": list(evaluation.general_scores.values())
        },
        monologue_duration=monologue_duration,
        debat_duration=debat_duration,
        total_duration=total_duration
    )


@router.get("/{session_id}/summary")
async def get_evaluation_summary(session_id: str):
    """Récupère un résumé rapide de l'évaluation"""
    if session_id not in evaluations:
        raise HTTPException(status_code=404, detail="Évaluation non trouvée")

    evaluation = evaluations[session_id]
    grade_letter = get_grade_letter(evaluation.total_score)

    return {
        "session_id": session_id,
        "total_score": evaluation.total_score,
        "max_score": evaluation.max_score,
        "grade_letter": grade_letter,
        "passed": evaluation.total_score >= 10,
        "summary": evaluation.summary
    }


def get_grade_letter(score: float) -> str:
    """Convertit un score en lettre"""
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


def format_duration(seconds_or_id) -> str:
    """Formate une durée en mm:ss"""
    # Placeholder - à implémenter avec les vraies durées
    return "07:30"
