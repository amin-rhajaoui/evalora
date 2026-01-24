"""
Service d'évaluation et de feedback.

Génère les notes et le feedback pédagogique basés sur la grille DU officielle.
"""
from typing import Optional, Dict, Any, List
import uuid
import random
from datetime import datetime

from ..models.evaluation import Evaluation, CriterionScore
from ..config import GRADING_CRITERIA, AVATARS


class EvaluationService:
    """
    Service pour générer l'évaluation et le feedback.

    La notation suit la grille DU officielle:
    - Monologue: 8.5 points
    - Débat: 4.5 points
    - Général: 7 points
    - Total: 20 points

    AMÉLIORATION FUTURE:
    Brancher sur un LLM (GPT, Claude) pour une évaluation sémantique
    basée sur la transcription audio.
    """

    async def evaluate(
        self,
        session_id: str,
        monologue_transcript: Optional[str],
        debat_transcript: Optional[str],
        monologue_duration: int,
        debat_duration: int
    ) -> Evaluation:
        """
        Évalue une session d'examen.

        PLACEHOLDER: Génère des scores simulés.
        À améliorer avec analyse NLP/LLM de la transcription.
        """
        evaluation_id = str(uuid.uuid4())

        # Générer les scores (simulés pour l'instant)
        monologue_scores = self._evaluate_monologue(
            monologue_transcript,
            monologue_duration
        )
        debat_scores = self._evaluate_debat(
            debat_transcript,
            debat_duration
        )
        general_scores = self._evaluate_general(
            monologue_transcript,
            debat_transcript
        )

        # Calculer le total
        total = (
            sum(s.score for s in monologue_scores.values()) +
            sum(s.score for s in debat_scores.values()) +
            sum(s.score for s in general_scores.values())
        )

        # Générer le feedback
        summary, strengths, improvements, advice = self._generate_feedback(
            monologue_scores,
            debat_scores,
            general_scores,
            total
        )

        return Evaluation(
            id=evaluation_id,
            session_id=session_id,
            monologue_scores=monologue_scores,
            debat_scores=debat_scores,
            general_scores=general_scores,
            total_score=round(total, 1),
            summary=summary,
            strengths=strengths,
            improvements=improvements,
            advice=advice,
            created_at=datetime.now()
        )

    def _evaluate_monologue(
        self,
        transcript: Optional[str],
        duration: int
    ) -> Dict[str, CriterionScore]:
        """Évalue la partie monologue"""
        criteria = GRADING_CRITERIA["monologue"]
        scores = {}

        for key, criterion in criteria.items():
            # Score simulé (à remplacer par analyse réelle)
            base_score = random.uniform(0.6, 0.95) * criterion["max"]

            # Ajustement selon la durée
            if duration < 300:  # Moins de 5 min
                base_score *= 0.8
            elif duration > 600:  # Plus de 10 min
                base_score *= 0.9

            scores[key] = CriterionScore(
                criterion=key,
                score=round(base_score, 1),
                max_score=criterion["max"],
                comment=self._get_criterion_comment(key, base_score, criterion["max"])
            )

        return scores

    def _evaluate_debat(
        self,
        transcript: Optional[str],
        duration: int
    ) -> Dict[str, CriterionScore]:
        """Évalue la partie débat"""
        criteria = GRADING_CRITERIA["debat"]
        scores = {}

        for key, criterion in criteria.items():
            base_score = random.uniform(0.6, 0.95) * criterion["max"]

            scores[key] = CriterionScore(
                criterion=key,
                score=round(base_score, 1),
                max_score=criterion["max"],
                comment=self._get_criterion_comment(key, base_score, criterion["max"])
            )

        return scores

    def _evaluate_general(
        self,
        monologue_transcript: Optional[str],
        debat_transcript: Optional[str]
    ) -> Dict[str, CriterionScore]:
        """Évalue les critères généraux"""
        criteria = GRADING_CRITERIA["general"]
        scores = {}

        for key, criterion in criteria.items():
            base_score = random.uniform(0.6, 0.95) * criterion["max"]

            scores[key] = CriterionScore(
                criterion=key,
                score=round(base_score, 1),
                max_score=criterion["max"],
                comment=self._get_criterion_comment(key, base_score, criterion["max"])
            )

        return scores

    def _get_criterion_comment(
        self,
        criterion: str,
        score: float,
        max_score: float
    ) -> str:
        """Génère un commentaire pour un critère"""
        ratio = score / max_score

        comments = {
            "presentation": {
                "high": "Présentation complète et précise du document.",
                "medium": "Présentation correcte mais manque quelques éléments.",
                "low": "Présentation incomplète du document."
            },
            "description": {
                "high": "Description détaillée avec un vocabulaire riche.",
                "medium": "Description acceptable, vocabulaire à enrichir.",
                "low": "Description insuffisante."
            },
            "analyse_opinion": {
                "high": "Excellente analyse avec des arguments personnels.",
                "medium": "Analyse correcte, arguments à développer.",
                "low": "Analyse superficielle, peu d'arguments."
            },
            "coherence": {
                "high": "Discours bien structuré avec des connecteurs variés.",
                "medium": "Structure acceptable, connecteurs basiques.",
                "low": "Structure confuse, manque de connecteurs."
            },
            "aisance": {
                "high": "Expression fluide et naturelle.",
                "medium": "Expression correcte avec quelques hésitations.",
                "low": "Expression hésitante."
            },
            "interaction": {
                "high": "Excellente réactivité et reformulation.",
                "medium": "Bonne interaction, reformulation à améliorer.",
                "low": "Difficulté à interagir."
            },
            "argumentation": {
                "high": "Arguments solides et nuancés.",
                "medium": "Arguments corrects mais peu développés.",
                "low": "Argumentation faible."
            },
            "elargissement": {
                "high": "Capacité à ouvrir le débat.",
                "medium": "Quelques ouvertures.",
                "low": "Reste centré sur le sujet initial."
            },
            "vocabulaire": {
                "high": "Vocabulaire riche et varié.",
                "medium": "Vocabulaire correct, à enrichir.",
                "low": "Vocabulaire limité."
            },
            "prononciation": {
                "high": "Prononciation claire et correcte.",
                "medium": "Prononciation acceptable.",
                "low": "Difficultés de prononciation."
            },
            "grammaire": {
                "high": "Grammaire maîtrisée.",
                "medium": "Quelques erreurs grammaticales.",
                "low": "Erreurs grammaticales fréquentes."
            },
            "comprehension": {
                "high": "Bonne compréhension des questions.",
                "medium": "Compréhension correcte.",
                "low": "Difficultés de compréhension."
            }
        }

        if criterion not in comments:
            return ""

        if ratio >= 0.8:
            return comments[criterion]["high"]
        elif ratio >= 0.5:
            return comments[criterion]["medium"]
        else:
            return comments[criterion]["low"]

    def _generate_feedback(
        self,
        monologue_scores: Dict[str, CriterionScore],
        debat_scores: Dict[str, CriterionScore],
        general_scores: Dict[str, CriterionScore],
        total: float
    ) -> tuple[str, List[str], List[str], List[str]]:
        """Génère le feedback textuel"""

        # Résumé
        if total >= 16:
            summary = "Excellente performance ! Vous maîtrisez bien les compétences de production orale."
        elif total >= 14:
            summary = "Très bonne performance avec quelques points à perfectionner."
        elif total >= 12:
            summary = "Bonne performance. Continuez à vous entraîner pour progresser."
        elif total >= 10:
            summary = "Performance satisfaisante. Des efforts supplémentaires sont nécessaires."
        else:
            summary = "Performance à améliorer. Concentrez-vous sur les points essentiels."

        # Points forts
        strengths = []
        all_scores = {**monologue_scores, **debat_scores, **general_scores}
        for key, score in all_scores.items():
            if score.score / score.max_score >= 0.8:
                strengths.append(score.comment)

        if not strengths:
            strengths = ["Effort de participation à l'examen."]

        # Axes d'amélioration
        improvements = []
        for key, score in all_scores.items():
            if score.score / score.max_score < 0.6:
                improvements.append(score.comment)

        if not improvements:
            improvements = ["Continuez à enrichir votre vocabulaire."]

        # Conseils
        advice = [
            "Entraînez-vous régulièrement à parler français.",
            "Lisez des articles de presse pour enrichir votre vocabulaire.",
            "Pratiquez l'argumentation sur des sujets variés.",
            "Écoutez des podcasts en français pour améliorer la compréhension."
        ]

        return summary, strengths[:3], improvements[:3], advice[:3]

    async def adapt_feedback_tone(
        self,
        evaluation: Evaluation,
        avatar_config: Dict[str, Any]
    ) -> Evaluation:
        """Adapte le ton du feedback selon l'avatar"""
        tone = avatar_config.get("feedback_tone", "neutral")
        name = avatar_config.get("name", "l'examinateur")

        # Adapter le résumé selon le ton
        if "chaleureux" in tone.lower() or "empathique" in tone.lower():
            evaluation.summary = f"Bravo ! {evaluation.summary}"
        elif "encourageant" in tone.lower():
            evaluation.summary = f"Super ! {evaluation.summary}"
        elif "exigeant" in tone.lower():
            if evaluation.total_score < 14:
                evaluation.summary = f"Il y a du travail, mais c'est un début. {evaluation.summary}"

        evaluation.feedback_tone = tone
        evaluation.avatar_id = avatar_config.get("id")

        return evaluation
