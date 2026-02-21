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

## Calibration anti-surévaluation
IMPORTANT : Un B1 solide correspond à 12-14/20, pas plus. Réserve les scores au-dessus de 15 aux performances véritablement excellentes (C1+). Ne sois pas artificiellement généreux : un score de 10-12 est honorable pour un apprenant B1.

## Grille de notation (total: 20 points)

### Monologue (8.5 points)
- **presentation** (max 1.5): Type de document, source, auteur, date — L'étudiant identifie-t-il correctement la nature du document, sa source et son contexte ?
- **description** (max 2.0): Précision de la description, vocabulaire adapté — Le contenu du document est-il décrit avec exactitude et un lexique approprié ?
- **analyse_opinion** (max 3.0): Argumentation, exemples personnels, opinion développée — L'étudiant dépasse-t-il la simple description pour donner un avis argumenté avec des exemples personnels ?
- **coherence** (max 1.0): Structure claire, connecteurs logiques — Le discours est-il organisé avec des transitions et des connecteurs (d'abord, ensuite, en revanche…) ?
- **aisance** (max 1.0): Fluidité, autonomie, naturel — L'étudiant parle-t-il de manière fluide, sans pauses excessives ni dépendance à des notes ?

### Débat (5.5 points)
- **interaction** (max 2.5): Compétences interactionnelles complètes :
  • Gestion des tours de parole : l'étudiant prend la parole au bon moment, sans couper l'interlocuteur ni laisser de blancs gênants
  • Écoute interactive : reformulation des propos de l'examinateur, accusés de réception ("oui, je comprends votre point…")
  • Gestion des ruptures : capacité à reprendre la conversation après un malentendu ou un silence
  • Rebonds : capacité à rebondir sur les propos de l'examinateur pour approfondir
- **argumentation** (max 1.5): Défense d'idées, nuance, contre-arguments — L'étudiant défend-il ses idées avec des arguments structurés ? Nuance-t-il son propos ?
- **elargissement** (max 0.5): Capacité à ouvrir le débat, nouvelles perspectives — L'étudiant propose-t-il des angles nouveaux ou des exemples inattendus ?
- **comprehension** (max 1.0): Compréhension des questions posées — L'étudiant comprend-il les questions de l'examinateur et y répond-il de manière pertinente ?

### Compétences générales (6 points)
- **vocabulaire** (max 2.0): Richesse lexicale, précision du vocabulaire — L'étudiant utilise-t-il un vocabulaire varié et précis, adapté au sujet ?
- **prononciation** (max 2.0): Clarté de prononciation — ⚠️ Score indicatif — à confirmer avec un professeur. L'évaluation de la prononciation à partir d'une transcription textuelle est limitée. Évalue principalement la clarté du discours telle qu'elle transparaît dans la transcription (mots tronqués, phrases incompréhensibles, etc.)
- **grammaire** (max 2.0): Correction grammaticale, structures variées — L'étudiant maîtrise-t-il les structures grammaticales de base ? Utilise-t-il des constructions variées (subjonctif, conditionnel, relatives) ?

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

IMPORTANT: Sois juste mais exigeant. C'est un étudiant en apprentissage, mais la bienveillance ne doit pas mener à la surévaluation.
Rappel : monologue = 8.5 pts, débat = 5.5 pts, général = 6 pts → total = 20 pts.

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
    "elargissement": {{"score": 0.0, "comment": "..."}},
    "comprehension": {{"score": 0.0, "comment": "..."}}
  }},
  "general_scores": {{
    "vocabulaire": {{"score": 0.0, "comment": "..."}},
    "prononciation": {{"score": 0.0, "comment": "..."}},
    "grammaire": {{"score": 0.0, "comment": "..."}}
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
                        "model": "gpt-4o",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3,
                        "max_tokens": 2000,
                        "response_format": {"type": "json_object"},
                    },
                    timeout=90.0,
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
        avatar_id = avatar_config.get("id", "")
        tone = avatar_config.get("feedback_tone", "neutral")
        evaluation.feedback_tone = tone
        evaluation.avatar_id = avatar_id

        if not OPENAI_API_KEY:
            return evaluation

        # Build persona instruction based on avatar
        persona_instructions = {
            "clea": (
                "Tu es Cléa, bienveillante et chaleureuse. Tu tutoies l'étudiant. "
                "Commence toujours par les points forts avec « Bravo pour... ». "
                "Ton ton est encourageant, empathique et motivant. Tu mets en valeur les efforts."
            ),
            "alex": (
                "Tu es Alex, décontracté et amical. Tu tutoies l'étudiant. "
                "Commence par « OK alors voici... ». Ton ton est cool mais structuré. "
                "Tu mélanges encouragement et conseils concrets de manière naturelle."
            ),
            "karim": (
                "Tu es Karim, formel et analytique. Tu vouvoies l'étudiant. "
                "Commence par « Voici mon analyse... ». Ton ton est professionnel et mesuré. "
                "Tu présentes d'abord les scores et l'analyse factuelle, puis les recommandations."
            ),
            "claire": (
                "Tu es Claire, exigeante et directe. Tu vouvoies l'étudiant. "
                "Commence par « Je serai directe... ». Ton ton est rigoureux et constructif. "
                "Tu pointes d'abord les faiblesses et les erreurs, puis ce qui fonctionne."
            ),
        }

        persona = persona_instructions.get(avatar_id, "Tu es un examinateur neutre et professionnel.")

        adapt_prompt = f"""{persona}

Voici le feedback brut d'un examen oral FLE. Reformule-le selon ta personnalité.
Garde TOUS les éléments factuels (scores, points forts, axes d'amélioration, conseils) mais adapte le ton et la formulation.

Score total : {evaluation.total_score}/20
Résumé : {evaluation.summary}
Points forts : {', '.join(evaluation.strengths[:3])}
Axes d'amélioration : {', '.join(evaluation.improvements[:3])}
Conseils : {', '.join(evaluation.advice[:3])}

Réponds en JSON avec cette structure exacte :
{{
  "summary": "...",
  "strengths": ["...", "..."],
  "improvements": ["...", "..."],
  "advice": ["...", "..."]
}}"""

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENAI_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "gpt-4o",
                        "messages": [{"role": "user", "content": adapt_prompt}],
                        "temperature": 0.7,
                        "max_tokens": 800,
                        "response_format": {"type": "json_object"},
                    },
                    timeout=30.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    result = json.loads(content)
                    evaluation.summary = result.get("summary", evaluation.summary)
                    evaluation.strengths = result.get("strengths", evaluation.strengths)[:3]
                    evaluation.improvements = result.get("improvements", evaluation.improvements)[:3]
                    evaluation.advice = result.get("advice", evaluation.advice)[:3]
                    logger.info(f"Feedback tone adapted for avatar {avatar_id}")
                else:
                    logger.warning(f"Tone adaptation API error: {response.status_code}")

        except Exception as e:
            logger.warning(f"Tone adaptation failed, keeping original: {e}")

        return evaluation
