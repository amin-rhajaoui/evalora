# Skill: Evaluation System (GPT-4o)

## Overview
The evaluation uses GPT-4o to score student performance on the official DU FLE grid (20 points), enhanced with Interactional Competence (IC) dimensions from Galaczi & Taylor (2018) research.

## Official Grading Grid (20 Points)

### Monologue (10.5 pts)
| Criterion | Max | Description |
|-----------|-----|-------------|
| Respect des consignes | 2.0 | Follows format, stays within time, addresses document |
| Contenu informatif | 4.5 | Document comprehension, personal stance, examples |
| Cohérence et cohésion | 2.0 | Logical structure, connectors, progression |
| Expression et aisance | 2.0 | Fluency, spontaneity, natural delivery |

### Débat (5 pts) — Enhanced with IC Dimensions
| Criterion | Max | Description |
|-----------|-----|-------------|
| Interaction | 2.5 | Topic management, turn-taking, active listening, breakdown repair |
| Argumentation | 2.5 | Develops own ideas, nuances arguments, provides examples |

### Langue (4.5 pts)
| Criterion | Max | Description |
|-----------|-----|-------------|
| Lexique | 1.5 | Vocabulary range and precision |
| Morphosyntaxe | 1.5 | Grammar accuracy and complexity |
| Phonétique | 1.5 | Pronunciation, intonation, rhythm |

## IC Dimensions (Galaczi & Taylor, 2018)
Integrated into the "Interaction" criterion scoring:

1. **Topic Management** — Does the student initiate topics, develop ideas, extend discussions?
   - High level: produces fewer but more developed turns with own thematic extensions
   - Low level: only responds yes/no, never initiates

2. **Turn-Taking** — Does the student take turns naturally?
   - High level: appropriate timing, signals completion clearly
   - Low level: awkward silences, speaks over examiner

3. **Interactive Listening** — Does the student show comprehension?
   - High level: backchannels ("d'accord", "je vois"), references examiner's points
   - Low level: ignores questions, responds off-topic

4. **Breakdown Repair** — Does the student manage misunderstandings?
   - High level: asks for clarification, reformulates when not understood, self-corrects
   - Low level: freezes on misunderstanding, never asks for repetition

5. **Nonverbal** — (Not scored in audio-only mode, noted for Tavus video future)

## Evaluation Prompt (GPT-4o)

**File**: `backend/app/services/evaluation_service.py`

```python
EVALUATION_PROMPT = """Tu es un évaluateur expert du DU FLE (Diplôme Universitaire de Français Langue Étrangère) 
à la Sorbonne Abu Dhabi. Tu évalues une production orale de niveau {level}.

## Grille officielle (20 points)

### MONOLOGUE (10.5 pts)
- Respect des consignes (0-2): L'étudiant respecte-t-il le format demandé ? 
  Reste-t-il dans le temps ? Aborde-t-il le document ?
- Contenu informatif (0-4.5): Compréhension du document, prise de position personnelle, 
  exemples pertinents, profondeur de l'analyse
- Cohérence et cohésion (0-2): Structure logique, utilisation de connecteurs, 
  progression claire des idées
- Expression et aisance (0-2): Fluidité de la parole, spontanéité, pauses naturelles 
  vs hésitations excessives, reformulations

### DÉBAT (5 pts)
- Interaction (0-2.5): Évalue les 4 dimensions de la compétence interactionnelle:
  * Gestion du sujet: initie des idées, développe les thèmes, élargit le débat
  * Gestion des tours: prend la parole au bon moment, signale la fin de ses tours
  * Écoute interactive: montre qu'il comprend (backchannels, rebondit sur les questions)
  * Gestion des ruptures: demande des reformulations, se corrige, clarifie
  Note: un étudiant de bon niveau produit MOINS de tours mais PLUS développés.
- Argumentation (0-2.5): Développe ses propres idées, nuance ses arguments, 
  ne répète pas, fournit des exemples variés

### LANGUE (4.5 pts)
- Lexique (0-1.5): Étendue et précision du vocabulaire
- Morphosyntaxe (0-1.5): Correction grammaticale, complexité des structures
- Phonétique (0-1.5): Prononciation, intonation, rythme
  ⚠️ Note: La prononciation est évaluée de façon INDICATIVE via transcription audio.
  La précision est limitée par le STT. Pondérer en conséquence.

## Calibration
- Niveau cible: {level} (A2+ ou B1)
- ⚠️ BIAIS CONNU: L'IA tend à surévaluer les niveaux faibles (A2+, B1). 
  Sois rigoureux et n'arrondis PAS systématiquement vers le haut.
- Un B1 solide obtient 12-14/20. Un B1 excellent: 15-17/20. Au-dessus de 17: exceptionnel.
- Un A2+ solide obtient 10-12/20.

## Données de l'examen
Document: "{document_title}" - {document_theme}
Avatar examinateur: {avatar_name} ({avatar_style})

### Transcription du monologue:
{monologue_transcript}

### Transcription du débat (Q&A):
{debat_transcript}

## Format de réponse OBLIGATOIRE (JSON)
Réponds UNIQUEMENT avec ce JSON, sans texte avant ou après:
{{
  "scores": {{
    "monologue": {{
      "respect_consignes": {{"score": 0.0, "max": 2.0, "justification": "..."}},
      "contenu_informatif": {{"score": 0.0, "max": 4.5, "justification": "..."}},
      "coherence_cohesion": {{"score": 0.0, "max": 2.0, "justification": "..."}},
      "expression_aisance": {{"score": 0.0, "max": 2.0, "justification": "..."}}
    }},
    "debat": {{
      "interaction": {{
        "score": 0.0, "max": 2.5, "justification": "...",
        "ic_details": {{
          "topic_management": "...",
          "turn_taking": "...",
          "interactive_listening": "...",
          "breakdown_repair": "..."
        }}
      }},
      "argumentation": {{"score": 0.0, "max": 2.5, "justification": "..."}}
    }},
    "langue": {{
      "lexique": {{"score": 0.0, "max": 1.5, "justification": "..."}},
      "morphosyntaxe": {{"score": 0.0, "max": 1.5, "justification": "..."}},
      "phonetique": {{"score": 0.0, "max": 1.5, "justification": "⚠️ Évaluation indicative. ..."}}
    }}
  }},
  "total_score": 0.0,
  "grade_letter": "A/B/C/D/E",
  "passed": true,
  "summary": "Résumé en 3-4 phrases du feedback global",
  "points_forts": ["...", "..."],
  "axes_amelioration": ["...", "..."],
  "confidence_note": "Note sur la fiabilité de l'évaluation IA"
}}"""
```

## API Call Pattern
```python
import openai
import json

async def evaluate_exam(
    monologue_transcript: str,
    debat_transcript: str,
    document: dict,
    avatar: dict,
    level: str = "B1"
) -> dict:
    prompt = EVALUATION_PROMPT.format(
        level=level,
        document_title=document["title"],
        document_theme=document["theme"],
        avatar_name=avatar["name"],
        avatar_style=avatar["style"],
        monologue_transcript=monologue_transcript or "(Pas de transcription disponible)",
        debat_transcript=debat_transcript or "(Pas de transcription disponible)",
    )
    
    client = openai.AsyncOpenAI()
    response = await client.chat.completions.create(
        model="gpt-4o",              # ⚠️ NEVER use gpt-4o-mini for evaluation
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.3,              # Low temperature for consistent scoring
        max_tokens=2000,
    )
    
    result = json.loads(response.choices[0].message.content)
    
    # Validate: recompute total from individual scores
    total = 0.0
    for category in result["scores"].values():
        for criterion in category.values():
            if isinstance(criterion, dict) and "score" in criterion:
                total += criterion["score"]
    
    result["total_score"] = round(total, 1)
    result["passed"] = result["total_score"] >= 10.0
    
    # Grade letter mapping
    score = result["total_score"]
    if score >= 16: result["grade_letter"] = "A"
    elif score >= 14: result["grade_letter"] = "B"
    elif score >= 12: result["grade_letter"] = "C"
    elif score >= 10: result["grade_letter"] = "D"
    else: result["grade_letter"] = "E"
    
    return result
```

## Feedback Tone by Avatar
The `adapt_feedback_tone` function wraps the raw evaluation with avatar personality:

```python
FEEDBACK_TONES = {
    "karim": {
        "intro": "Voici mon analyse détaillée de votre prestation.",
        "style": "Formel et analytique. Donne les scores d'abord, puis les détails. Utilise le vouvoiement.",
    },
    "clea": {
        "intro": "Alors, je vais te donner mon retour ! Commençons par ce qui était bien.",
        "style": "Chaleureux et encourageant. Commence par les points forts. Utilise le tutoiement.",
    },
    "claire": {
        "intro": "Voici mon évaluation. Je serai directe.",
        "style": "Direct et exigeant. Pointe les faiblesses clairement. Utilise le vouvoiement.",
    },
    "alex": {
        "intro": "OK, alors voici ce que j'ai pensé de ta prestation !",
        "style": "Décontracté et positif. Mélange encouragement et conseils concrets. Utilise le tutoiement.",
    },
}

def adapt_feedback_tone(evaluation: dict, avatar_id: str) -> str:
    """Generate spoken feedback text adapted to avatar personality."""
    tone = FEEDBACK_TONES.get(avatar_id, FEEDBACK_TONES["clea"])
    
    # Build the spoken feedback (this will be sent to TTS)
    feedback_text = f"""{tone['intro']}

Points forts: {', '.join(evaluation.get('points_forts', []))}

Axes d'amélioration: {', '.join(evaluation.get('axes_amelioration', []))}

Ta note finale est de {evaluation['total_score']} sur 20. 
{evaluation.get('summary', '')}
"""
    return feedback_text
```

## Known Limitations (from Academic Research)
Source: Yanholenko et al. (RECITAL 2025), Karatay & Xu (TESOL Quarterly 2025)

| Criterion | AI Reliability | Action |
|-----------|---------------|--------|
| Interaction | 75% agreement | ✅ Score fiable |
| Vocabulary | 81% agreement | ✅ Score fiable |
| Grammar & Fluency | 69% agreement | ✅ Fiable avec nuance |
| Pronunciation | 50% agreement | ⚠️ Mention "indicatif" obligatoire |
| Overall Level | 56% agreement | ⚠️ Encourager validation prof |

**Key findings:**
- AI tends to **overestimate** A2+ and B1 levels → calibrate prompts to be stricter
- High-level students produce **fewer but more developed turns** → use as IC indicator
- Pronunciation assessment via STT transcription is unreliable → always add disclaimer
- The `confidence_note` field in the JSON response should reflect these limitations
