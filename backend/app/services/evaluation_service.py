"""
Service d'évaluation LLM pour Evalora.

Envoie la transcription à GPT-4o avec la grille DU officielle,
parse le retour JSON avec scores + commentaires par critère.
Fallback heuristique si l'API échoue.
"""
import json
import os
import logging
import uuid
import re
from typing import Optional, Dict, List
from datetime import datetime

import httpx

from ..models.evaluation import Evaluation, CriterionScore
from ..config import GRADING_CRITERIA, AVATARS

logger = logging.getLogger("evalora.evaluation")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


EVALUATION_PROMPT = """Tu es un correcteur expert pour l'examen de production orale du Diplôme Universitaire FLE (Français Langue Étrangère) de la Sorbonne Abu Dhabi.

Tu dois évaluer la performance d'un étudiant de niveau A2+/B1 en utilisant la grille de notation officielle ci-dessous.

## Grille de notation (total: 20 points)

### Monologue (8.5 points)
- **presentation** (max 1.5): Type de document, source, auteur, date
- **description** (max 2.0): Précision de la description, vocabulaire adapté
- **analyse_opinion** (max 3.0): Argumentation, exemples personnels, opinion développée
- **coherence** (max 1.0): Structure claire, connecteurs logiques
- **aisance** (max 1.0): Fluidité, autonomie, naturel

### Débat (4.5 points)
- **interaction** (max 2.5): Réactivité, reformulation, prise en compte de l'interlocuteur
- **argumentation** (max 1.5): Défense d'idées, nuance, contre-arguments
- **elargissement** (max 0.5): Capacité à ouvrir le débat, nouvelles perspectives

### Compétences générales (7 points)
- **vocabulaire** (max 2.0): Richesse lexicale, précision du vocabulaire
- **prononciation** (max 2.0): Clarté de prononciation (évaluation limitée via transcription)
- **grammaire** (max 2.0): Correction grammaticale, structures variées
- **comprehension** (max 1.0): Compréhension des questions posées

## Transcription du monologue:
{monologue_transcript}

## Transcription du débat:
{debat_transcript}

## Durées:
- Monologue: {monologue_duration} secondes
- Débat: {debat_duration} secondes

## Instructions:
1. Évalue chaque critère avec un score entre 0 et le maximum indiqué
2. Pour chaque critère, donne un commentaire constructif de 1-2 phrases
3. Génère un résumé global de la performance (2-3 phrases)
4. Liste 2-3 points forts
5. Liste 2-3 axes d'amélioration
6. Liste 2-3 conseils personnalisés

IMPORTANT: Sois juste et bienveillant. C'est un étudiant en apprentissage.
Pour la prononciation, comme tu n'as qu'une transcription textuelle, évalue plutôt la clarté du discours telle qu'elle apparaît dans la transcription.

Réponds UNIQUEMENT en JSON valide avec cette structure exacte:
{{
  "monologue_scores": {{
    "presentation": {{"score": 0.0, "comment": "..."}},
    "description": {{"score": 0.0, "comment": "..."}},
    "analyse_opinion": {{"score": 0.0, "comment": "..."}},
    "coherence": {{"score": 0.0, "comment": "..."}},
    "aisance": {{"score": 0.0, "comment": "..."}}
  }},
  "debat_scores": {{
    "interaction": {{"score": 0.0, "comment": "..."}},
    "argumentation": {{"score": 0.0, "comment": "..."}},
    "elargissement": {{"score": 0.0, "comment": "..."}}
  }},
  "general_scores": {{
    "vocabulaire": {{"score": 0.0, "comment": "..."}},
    "prononciation": {{"score": 0.0, "comment": "..."}},
    "grammaire": {{"score": 0.0, "comment": "..."}},
    "comprehension": {{"score": 0.0, "comment": "..."}}
  }},
  "summary": "...",
  "strengths": ["...", "..."],
  "improvements": ["...", "..."],
  "advice": ["...", "..."]
}}"""


class EvaluationService:

    async def evaluate(
        self,
        session_id: str,
        monologue_transcript: Optional[str],
        debat_transcript: Optional[str],
        monologue_duration: int,
        debat_duration: int,
    ) -> Evaluation:
        evaluation_id = str(uuid.uuid4())

        # Try LLM evaluation first
        llm_result = None
        if OPENAI_API_KEY and (monologue_transcript or debat_transcript):
            llm_result = await self._evaluate_with_llm(
                monologue_transcript or "(Pas de transcription disponible)",
                debat_transcript or "(Pas de transcription disponible)",
                monologue_duration,
                debat_duration,
            )

        if llm_result:
            monologue_scores = self._parse_scores(llm_result.get("monologue_scores", {}), "monologue")
            debat_scores = self._parse_scores(llm_result.get("debat_scores", {}), "debat")
            general_scores = self._parse_scores(llm_result.get("general_scores", {}), "general")
            summary = llm_result.get("summary", "")
            strengths = llm_result.get("strengths", [])
            improvements = llm_result.get("improvements", [])
            advice = llm_result.get("advice", [])
        else:
            # Heuristic fallback
            logger.warning("LLM evaluation failed, using heuristic fallback")
            monologue_scores = self._heuristic_scores(monologue_transcript, monologue_duration, "monologue")
            debat_scores = self._heuristic_scores(debat_transcript, debat_duration, "debat")
            general_scores = self._heuristic_scores(
                (monologue_transcript or "") + " " + (debat_transcript or ""), 0, "general"
            )
            summary, strengths, improvements, advice = self._generate_heuristic_feedback(
                monologue_scores, debat_scores, general_scores
            )

        total = (
            sum(s.score for s in monologue_scores.values())
            + sum(s.score for s in debat_scores.values())
            + sum(s.score for s in general_scores.values())
        )

        return Evaluation(
            id=evaluation_id,
            session_id=session_id,
            monologue_scores=monologue_scores,
            debat_scores=debat_scores,
            general_scores=general_scores,
            total_score=round(total, 1),
            summary=summary,
            strengths=strengths[:3],
            improvements=improvements[:3],
            advice=advice[:3],
            created_at=datetime.now(),
            monologue_duration=monologue_duration,
            debat_duration=debat_duration,
        )

    async def _evaluate_with_llm(
        self,
        monologue_transcript: str,
        debat_transcript: str,
        monologue_duration: int,
        debat_duration: int,
    ) -> Optional[dict]:
        prompt = EVALUATION_PROMPT.format(
            monologue_transcript=monologue_transcript,
            debat_transcript=debat_transcript,
            monologue_duration=monologue_duration,
            debat_duration=debat_duration,
        )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENAI_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3,
                        "max_tokens": 2000,
                    },
                    timeout=60.0,
                )

                if response.status_code != 200:
                    logger.error(f"OpenAI API error: {response.status_code} {response.text}")
                    return None

                data = response.json()
                content = data["choices"][0]["message"]["content"]

                # Extract JSON from response (may be wrapped in ```json ... ```)
                json_match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
                if json_match:
                    content = json_match.group(1)

                result = json.loads(content)
                logger.info("LLM evaluation successful")
                return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"LLM evaluation error: {e}")
            return None

    def _parse_scores(self, scores_data: dict, section: str) -> Dict[str, CriterionScore]:
        criteria = GRADING_CRITERIA.get(section, {})
        result = {}
        for key, criterion in criteria.items():
            score_data = scores_data.get(key, {})
            score = min(float(score_data.get("score", 0)), criterion["max"])
            score = max(score, 0)
            comment = score_data.get("comment", criterion.get("description", ""))
            result[key] = CriterionScore(
                criterion=key,
                score=round(score, 1),
                max_score=criterion["max"],
                comment=comment,
            )
        return result

    def _heuristic_scores(
        self, transcript: Optional[str], duration: int, section: str
    ) -> Dict[str, CriterionScore]:
        criteria = GRADING_CRITERIA.get(section, {})
        text = transcript or ""
        word_count = len(text.split())
        scores = {}

        for key, criterion in criteria.items():
            max_score = criterion["max"]
            # Base ratio from word count (more words = better up to a point)
            if word_count < 20:
                ratio = 0.3
            elif word_count < 100:
                ratio = 0.5
            elif word_count < 300:
                ratio = 0.65
            else:
                ratio = 0.75

            # Duration bonus for monologue
            if section == "monologue" and duration:
                if 300 <= duration <= 600:
                    ratio = min(ratio + 0.1, 0.85)
                elif duration < 120:
                    ratio *= 0.7

            score = round(ratio * max_score, 1)
            scores[key] = CriterionScore(
                criterion=key,
                score=score,
                max_score=max_score,
                comment=criterion.get("description", ""),
            )
        return scores

    def _generate_heuristic_feedback(
        self,
        monologue_scores: Dict[str, CriterionScore],
        debat_scores: Dict[str, CriterionScore],
        general_scores: Dict[str, CriterionScore],
    ) -> tuple:
        total = (
            sum(s.score for s in monologue_scores.values())
            + sum(s.score for s in debat_scores.values())
            + sum(s.score for s in general_scores.values())
        )

        if total >= 16:
            summary = "Excellente performance ! Vous maîtrisez bien les compétences de production orale."
        elif total >= 12:
            summary = "Bonne performance. Continuez à vous entraîner pour progresser."
        elif total >= 10:
            summary = "Performance satisfaisante. Des efforts supplémentaires sont nécessaires."
        else:
            summary = "Performance à améliorer. Concentrez-vous sur les points essentiels."

        strengths = ["Participation active à l'examen."]
        improvements = ["Enrichir le vocabulaire utilisé.", "Développer davantage l'argumentation."]
        advice = [
            "Entraînez-vous régulièrement à parler français.",
            "Lisez des articles de presse pour enrichir votre vocabulaire.",
            "Pratiquez l'argumentation sur des sujets variés.",
        ]

        return summary, strengths, improvements, advice

    async def adapt_feedback_tone(self, evaluation: Evaluation, avatar_config: dict) -> Evaluation:
        tone = avatar_config.get("feedback_tone", "neutral")
        if "chaleureux" in tone.lower() or "empathique" in tone.lower():
            evaluation.summary = f"Bravo ! {evaluation.summary}"
        elif "encourageant" in tone.lower():
            evaluation.summary = f"Super ! {evaluation.summary}"
        elif "exigeant" in tone.lower() and evaluation.total_score < 14:
            evaluation.summary = f"Il y a du travail, mais c'est un début. {evaluation.summary}"
        evaluation.feedback_tone = tone
        evaluation.avatar_id = avatar_config.get("id")
        return evaluation
