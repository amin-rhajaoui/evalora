"""
Router pour la gestion des avatars (Tavus)
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from ..config import AVATARS, settings
from ..services.tavus_service import TavusService

router = APIRouter()
tavus_service = TavusService()


class AvatarListResponse(BaseModel):
    avatars: List[dict]


class InitAvatarRequest(BaseModel):
    session_id: str
    avatar_id: str
    student_name: str


class SpeakRequest(BaseModel):
    conversation_id: str
    text: str
    message_type: str = "normal"  # normal, question, feedback


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


@router.post("/init")
async def init_avatar(request: InitAvatarRequest):
    """
    Initialise une conversation Tavus pour un avatar.

    PLACEHOLDER: Retourne des données mock si Tavus n'est pas configuré.
    Quand Tavus sera configuré, cette méthode créera une vraie conversation vidéo.
    """
    if request.avatar_id not in AVATARS:
        raise HTTPException(status_code=404, detail="Avatar non trouvé")

    avatar = AVATARS[request.avatar_id]

    # Appeler le service Tavus
    result = await tavus_service.create_conversation(
        replica_id=avatar["tavus_replica_id"],
        session_id=request.session_id,
        student_name=request.student_name,
        avatar_config=avatar
    )

    return {
        "avatar_id": request.avatar_id,
        "avatar_name": avatar["name"],
        "conversation_id": result["conversation_id"],
        "conversation_url": result.get("conversation_url"),
        "stream_url": result.get("stream_url"),
        "status": result["status"],
        "mode": "tavus" if result["status"] != "placeholder" else "text",
        "message": result.get("message", "")
    }


@router.post("/speak")
async def make_avatar_speak(request: SpeakRequest):
    """
    Fait parler l'avatar (envoie un message à Tavus).

    PLACEHOLDER: Retourne le texte si Tavus n'est pas configuré.
    """
    result = await tavus_service.send_message(
        conversation_id=request.conversation_id,
        text=request.text,
        avatar_personality={}
    )

    return {
        "conversation_id": request.conversation_id,
        "text": request.text,
        "message_type": request.message_type,
        "audio_url": result.get("audio_url"),
        "video_url": result.get("video_url"),
        "status": result["status"]
    }


@router.post("/end/{conversation_id}")
async def end_avatar_conversation(conversation_id: str):
    """Termine la conversation Tavus"""
    result = await tavus_service.end_conversation(conversation_id)
    return result


# Messages pré-définis par phase et par avatar
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
