"""
Modèles pour l'évaluation et le feedback
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime


class CriterionScore(BaseModel):
    """Score pour un critère d'évaluation"""
    criterion: str
    score: float
    max_score: float
    comment: Optional[str] = None


class EvaluationCreate(BaseModel):
    """Données pour créer une évaluation"""
    session_id: str
    monologue_transcript: Optional[str] = None  # Transcription du monologue
    debat_transcript: Optional[str] = None  # Transcription du débat
    monologue_duration: int  # en secondes
    debat_duration: int


class Evaluation(BaseModel):
    """Évaluation complète"""
    id: str
    session_id: str

    # Scores par partie
    monologue_scores: Dict[str, CriterionScore] = {}
    debat_scores: Dict[str, CriterionScore] = {}
    general_scores: Dict[str, CriterionScore] = {}

    # Note finale
    total_score: float = 0.0
    max_score: float = 20.0

    # Feedback détaillé
    summary: str = ""  # Résumé global
    strengths: List[str] = []  # Points forts
    improvements: List[str] = []  # Axes d'amélioration
    advice: List[str] = []  # Conseils personnalisés

    # Méta
    avatar_id: Optional[str] = None
    feedback_tone: str = "neutral"  # Adapté au ton de l'avatar
    created_at: datetime = Field(default_factory=datetime.now)

    # Durées (secondes) pour format_duration dans le feedback
    monologue_duration: Optional[int] = None
    debat_duration: Optional[int] = None


class EvaluationResponse(BaseModel):
    """Réponse API pour une évaluation"""
    session_id: str
    total_score: float
    max_score: float
    grade_letter: str  # A, B, C, D, E
    passed: bool


class FeedbackResponse(BaseModel):
    """Feedback détaillé pour l'étudiant"""
    session_id: str
    student_name: str
    avatar_name: Optional[str]

    # Note
    total_score: float
    max_score: float = 20.0
    grade_letter: str
    passed: bool

    # Détails par partie
    monologue_score: float
    monologue_max: float = 8.5
    debat_score: float
    debat_max: float = 4.5
    general_score: float
    general_max: float = 7.0

    # Feedback textuel
    summary: str
    strengths: List[str]
    improvements: List[str]
    advice: List[str]

    # Détail des critères
    detailed_scores: Dict[str, List[CriterionScore]]

    # Durées
    monologue_duration: str  # Format "mm:ss"
    debat_duration: str
    total_duration: str


class QuickFeedback(BaseModel):
    """Feedback rapide pendant l'examen (pour relances)"""
    type: str  # clarification, developpement, reformulation, etc.
    message: str
    avatar_tone: str
