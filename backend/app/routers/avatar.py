"""
Router pour la gestion des avatars.

Les avatars sont utilisés par l'Agent LiveKit (config, messages par phase).
Aucune logique Tavus conversation : Tavus = rendu seul, piloté par l'Agent.
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional

from ..config import AVATARS, settings

router = APIRouter()


# Séquences Phase 1 (Accueil et Consignes) par avatar - cahier des charges
# Clé = avatar_id, valeur = liste de 7 textes (séquence 1 à 7). {prenom} sera remplacé par student_name.
PHASE1_SEQUENCES: dict[str, List[str]] = {
    "clea": [
        "Bonjour {prenom} ! Je m'appelle Cléa. Je suis ravie de t'accompagner aujourd'hui pour cette simulation d'examen. Comment tu te sens aujourd'hui ?",
        "Alors, cet examen se déroule en deux parties principales. D'abord, tu vas faire un monologue. C'est-à-dire que tu vas présenter un document seul, sans que je t'interrompe. Ensuite, on aura un petit débat ensemble. Je te poserai des questions et on discutera du même sujet. Ça te va ?",
        "Cette première partie dure entre 5 et 10 minutes. Le document que tu vas présenter contient une image et un texte de presse. Voici ce que tu dois faire : présenter le document, son type, sa source, l'auteur si tu le connais, et la date ; décrire l'image en détail ; expliquer le message du texte ; donner ton opinion personnelle ; faire des liens avec ton expérience ; donner des exemples concrets. Ton discours doit être bien structuré. Utilise des connecteurs logiques comme d'abord, ensuite, enfin, par exemple. Tu peux utiliser tes notes comme support, mais attention : ne les lis pas. Pendant que tu parles, je ne t'interromprai pas. Ne t'inquiète pas si tu hésites un peu, c'est tout à fait normal. Quand tu seras prêt, dis simplement : Je suis prêt. Le timer démarrera automatiquement.",
        "La deuxième partie dure environ 10 minutes. Je te poserai cinq questions sur le thème de ton document. L'objectif, c'est de discuter ensemble, d'exprimer ton opinion, d'argumenter et de réagir à mes remarques. Donne des exemples personnels, compare avec ton expérience, nuance tes propos. C'est un échange naturel. N'hésite pas à développer tes réponses.",
        "Tu seras évalué sur : la richesse et la variété de ton vocabulaire ; la clarté de ton élocution ; comment tu organises tes idées avec des connecteurs ; ta capacité à argumenter avec des exemples ; ta réactivité pendant le débat. À la fin, je te donnerai une note sur 20 et un feedback détaillé. Ne t'inquiète pas trop pour la note, l'idée c'est surtout de t'aider à progresser.",
        "Voilà, c'est clair pour toi ? Est-ce que tu as des questions avant de commencer ?",
        "Parfait ! Maintenant, quand tu te sens prêt, dis simplement : Je suis prêt. Le timer démarrera tout seul et tu pourras commencer à parler. Prends ton temps, respire bien. Vas-y quand tu veux !",
    ],
    "alex": [
        "Salut {prenom} ! Moi c'est Alex. Cool, on va faire cette simulation ensemble ! Ça va ? T'es prêt ?",
        "Bon alors, c'est simple. Il y a deux parties. La première, tu parles tout seul, tu présentes un document. Moi je dis rien, je t'écoute juste. Et après, on discute ensemble, je te pose des questions. Cool non ?",
        "Cette première partie dure entre 5 et 10 minutes. Le document que tu vas présenter contient une image et un texte de presse. Tu dois : présenter le document, décrire l'image, expliquer le message, donner ton avis, faire des liens avec ton expérience. Utilise des connecteurs : d'abord, ensuite, par exemple. Tu peux t'aider de tes notes mais ne les lis pas. Pendant que tu parles je ne t'interromps pas. Tranquille, prends ton temps. Quand tu es prêt, dis : Je suis prêt et le timer part.",
        "La deuxième partie, environ 10 minutes. Je te pose cinq questions sur le thème. On discute, tu donnes ton opinion, tu argumentes. Donne des exemples perso si tu veux. On va discuter cool. Dis juste ce que tu penses vraiment.",
        "Je te note sur : ton vocabulaire, ta prononciation, comment tu structures, ta capacité à argumenter, ta réactivité au débat. À la fin tu auras une note sur 20 et un feedback. La note c'est juste pour te situer, le plus important c'est le feedback pour progresser.",
        "C'est clair ? T'as des questions avant de commencer ?",
        "Parfait ! Quand t'es prêt, dis : Je suis prêt. Le timer démarre tout seul. Prends ton temps, respire. Vas-y quand tu veux !",
    ],
    "karim": [
        "Bonjour {prenom}, je m'appelle Karim. Je serai votre examinateur pour cette simulation de l'examen de production orale du D.U. F.L.E. Comment allez-vous aujourd'hui ?",
        "Cet examen comporte deux parties principales. Premièrement, un monologue où vous présenterez un document sans interruption de ma part. Deuxièmement, un débat où nous échangerons sur le thème abordé. C'est clair ?",
        "Cette première partie dure entre 5 et 10 minutes. Le document que vous allez présenter contient une image et un texte de presse. Vous devez : présenter le document, décrire l'image, expliquer le message du texte, donner votre opinion, faire des liens avec votre expérience. Votre discours doit être bien structuré avec des connecteurs. Vous pouvez utiliser vos notes comme support mais ne les lisez pas. Pendant que vous parlez, je ne vous interromprai pas. Prenez le temps de bien organiser votre discours. Lorsque vous serez prêt, dites : Je suis prêt.",
        "La deuxième partie dure environ 10 minutes. Je vous poserai cinq questions sur le thème de votre document. L'objectif est de discuter ensemble, d'exprimer votre opinion, d'argumenter. Vous pouvez donner des exemples personnels, nuancer vos propos. Je vous invite à développer vos arguments de manière structurée.",
        "Vous serez évalué sur : la richesse et la variété du vocabulaire ; la clarté de l'élocution ; la structure du discours ; la capacité à argumenter ; la réactivité pendant le débat. À la fin, je vous donnerai une note sur 20 et un feedback détaillé. L'évaluation sera objective et basée sur la grille officielle du D.U.",
        "Tout est clair ? Avez-vous des questions avant de débuter ?",
        "Très bien. Lorsque vous serez prêt, dites : Je suis prêt ou Je suis prête. Le chronomètre se déclenchera automatiquement. Vous pouvez prendre quelques instants pour vous concentrer.",
    ],
    "claire": [
        "Bonjour {prenom}. Je suis Claire, votre examinatrice. Nous allons procéder à la simulation de l'épreuve de production orale. Êtes-vous prêt à commencer ?",
        "L'épreuve se compose de deux parties distinctes. Première partie : un monologue suivi sans interruption. Deuxième partie : un échange argumenté. Avez-vous compris la structure ?",
        "Cette première partie dure entre 5 et 10 minutes. Le document que vous allez présenter contient une image et un texte de presse. Vous devez présenter le document, décrire l'image, expliquer le message, donner votre opinion, illustrer par des exemples. Votre discours doit être structuré avec des connecteurs. Vous pouvez utiliser vos notes mais ne les lisez pas. Pendant votre prise de parole, je resterai silencieuse. Je vous rappelle que la structure et la précision du vocabulaire sont des critères importants. Quand vous serez prêt, dites : Je suis prêt.",
        "La deuxième partie dure environ 10 minutes. Je vous poserai cinq questions sur le thème. L'objectif est d'échanger, d'argumenter, de réagir à mes remarques. Défendez votre point de vue de manière structurée. Je serai attentive à la précision de votre argumentation.",
        "Vous serez évalué sur : le vocabulaire ; la clarté de l'élocution ; la structure du discours ; la capacité à argumenter ; la réactivité. À la fin, une note sur 20 et un feedback. L'évaluation sera rigoureuse et conforme aux critères académiques.",
        "Tout est clair ? Avez-vous des questions avant de débuter ?",
        "Très bien. Lorsque vous serez prêt, dites : Je suis prêt ou Je suis prête. Le chronomètre se déclenchera automatiquement. Donnez le meilleur de vous-même.",
    ],
}


def get_phase1_sequences(avatar_id: str, student_name: Optional[str] = None) -> List[dict]:
    """Retourne les 7 séquences Phase 1 pour un avatar. Remplace {prenom} par student_name."""
    if avatar_id not in PHASE1_SEQUENCES:
        return []
    prenom = (student_name or "étudiant").strip() or "étudiant"
    sequences = []
    for i, text in enumerate(PHASE1_SEQUENCES[avatar_id], start=1):
        sequences.append({"id": i, "text": text.format(prenom=prenom)})
    return sequences


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
    """Récupère les détails d'un avatar (dont config ElevenLabs pour l'agent)"""
    if avatar_id not in AVATARS:
        raise HTTPException(status_code=404, detail="Avatar non trouvé")

    avatar = AVATARS[avatar_id]
    out = {
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
    # Config ElevenLabs (optionnelle) pour l'agent TTS
    if avatar.get("elevenlabs_voice_id") is not None:
        out["elevenlabs_voice_id"] = avatar["elevenlabs_voice_id"]
        out["elevenlabs_stability"] = avatar.get("elevenlabs_stability")
        out["elevenlabs_similarity_boost"] = avatar.get("elevenlabs_similarity_boost")
        out["elevenlabs_style_exaggeration"] = avatar.get("elevenlabs_style_exaggeration")
        out["elevenlabs_speaker_boost"] = avatar.get("elevenlabs_speaker_boost")
    return out


@router.get("/{avatar_id}/phase-1-sequences")
async def get_phase1_sequences_endpoint(
    avatar_id: str,
    student_name: Optional[str] = Query(None, description="Prénom de l'étudiant pour personnaliser les séquences 1 et 7"),
):
    """
    Retourne les 7 séquences Phase 1 (Accueil et Consignes) pour l'agent.
    Utilisé par l'agent LiveKit pour enchaîner les consignes avec la voix ElevenLabs.
    """
    if avatar_id not in AVATARS:
        raise HTTPException(status_code=404, detail="Avatar non trouvé")
    sequences = get_phase1_sequences(avatar_id, student_name)
    return {"avatar_id": avatar_id, "sequences": sequences}


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
