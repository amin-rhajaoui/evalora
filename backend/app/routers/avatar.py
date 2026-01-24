"""
Router pour la gestion des avatars.

Les avatars sont utilisés par l'Agent LiveKit (config, messages par phase).
Aucune logique Tavus conversation : Tavus = rendu seul, piloté par l'Agent.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

from ..config import AVATARS, settings

router = APIRouter()


class AvatarListResponse(BaseModel):
    avatars: List[dict]


@router.get("", response_model=AvatarListResponse)
async def list_avatars():
    """
    Récupère la liste des 4 avatars disponibles.

    Avatars:
    - Cléa: Bienveillante, tutoiement
    - Alex: Détendu, tutoiement
    - Karim: Académique, vouvoiement
    - Claire: Exigeante, vouvoiement
    """
    return AvatarListResponse(
        avatars=[
            {
                "id": avatar["id"],
                "name": avatar["name"],
                "gender": avatar["gender"],
                "age": avatar["age"],
                "register": avatar["register"],
                "personality": avatar["personality"],
                "placeholder_image": avatar["placeholder_image"]
            }
            for avatar in AVATARS.values()
        ]
    )


@router.get("/{avatar_id}")
async def get_avatar(avatar_id: str):
    """Récupère les détails d'un avatar"""
    if avatar_id not in AVATARS:
        raise HTTPException(status_code=404, detail="Avatar non trouvé")

    avatar = AVATARS[avatar_id]
    return {
        "id": avatar["id"],
        "name": avatar["name"],
        "gender": avatar["gender"],
        "age": avatar["age"],
        "register": avatar["register"],
        "personality": avatar["personality"],
        "role": avatar["role"],
        "behavior": avatar["behavior"],
        "feedback_tone": avatar["feedback_tone"],
        "placeholder_image": avatar["placeholder_image"],
        "tavus_configured": settings.TAVUS_API_KEY is not None
    }


# Messages pré-définis par phase et par avatar (utilisés par l'Agent)
@router.get("/{avatar_id}/messages/{phase}")
async def get_avatar_messages(avatar_id: str, phase: str):
    """
    Récupère les messages pré-définis pour un avatar et une phase.

    Phases: consignes, monologue_start, monologue_end, debat_start, debat_questions, feedback
    """
    if avatar_id not in AVATARS:
        raise HTTPException(status_code=404, detail="Avatar non trouvé")

    avatar = AVATARS[avatar_id]
    is_tu = avatar["register"] == "tutoiement"

    # Messages selon la phase et le registre
    messages = get_phase_messages(avatar_id, phase, is_tu)

    return {
        "avatar_id": avatar_id,
        "phase": phase,
        "register": avatar["register"],
        "messages": messages
    }


def get_phase_messages(avatar_id: str, phase: str, is_tu: bool) -> List[str]:
    """Génère les messages selon la phase"""

    tu_vous = "tu" if is_tu else "vous"
    te_vous = "te" if is_tu else "vous"
    ton_votre = "ton" if is_tu else "votre"
    ta_votre = "ta" if is_tu else "votre"
    tes_vos = "tes" if is_tu else "vos"
    es_etes = "es" if is_tu else "êtes"
    as_avez = "as" if is_tu else "avez"
    peux_pouvez = "peux" if is_tu else "pouvez"
    veux_voulez = "veux" if is_tu else "voulez"

    messages = {
        "greeting": [
            f"Bonjour ! Je m'appelle {AVATARS[avatar_id]['name']}. Je serai {ton_votre} examinateur pour cette simulation.",
            f"Comment {tu_vous} {es_etes[-1] == 's' and 'vas' or 'allez'}-{tu_vous} aujourd'hui ?"
        ],
        "consignes": [
            f"Cet examen comporte deux parties principales :",
            f"- une première partie, un monologue, où {tu_vous} présent{es_etes[-1] == 's' and 'es' or 'ez'} un document,",
            f"- une deuxième partie, un débat, où nous discuterons ensemble du même sujet.",
            f"Dans la première partie, {tu_vous} {as_avez} entre 5 et 10 minutes pour présenter le document.",
            f"{tu_vous.capitalize()} {peux_pouvez} utiliser {tes_vos} notes, mais ne les lis pas : elles doivent simplement {te_vous} aider.",
            f"Quand {tu_vous} {es_etes} prêt{is_tu and '' or 'e'}, dis simplement : « Je suis prêt ».",
        ],
        "monologue_start": [
            f"Parfait ! Le timer démarre. {tu_vous.capitalize()} {peux_pouvez} commencer."
        ],
        "monologue_end": [
            f"Merci ! {tu_vous.capitalize()} {as_avez} bien présenté {ton_votre} document.",
            f"Maintenant, nous allons passer à la deuxième partie : le débat."
        ],
        "debat_start": [
            f"Je vais {te_vous} poser cinq questions sur le même thème que {ton_votre} document.",
            f"Le but, c'est de discuter, de donner {ton_votre} opinion et d'argumenter.",
            f"{tu_vous.capitalize()} {peux_pouvez} me donner des exemples personnels si {tu_vous} {veux_voulez}."
        ],
        "feedback_intro": [
            f"L'examen est terminé. Voici {ton_votre} feedback détaillé."
        ]
    }

    return messages.get(phase, [])
