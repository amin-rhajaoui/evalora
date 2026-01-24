#!/usr/bin/env python3
"""
Script pour supprimer toutes les rooms LiveKit.
Utile pour nettoyer les rooms inutilisées.

Usage:
    python scripts/cleanup_livekit_rooms.py
    python scripts/cleanup_livekit_rooms.py --dry-run  # Affiche sans supprimer
    python scripts/cleanup_livekit_rooms.py --filter evalora  # Supprime uniquement les rooms commençant par "evalora"
"""

import asyncio
import sys
import os
import argparse
from pathlib import Path

# Ajouter le répertoire parent au path pour importer les modules
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from livekit import api
except ImportError:
    print("❌ Erreur: Le module 'livekit-api' n'est pas installé.")
    print("   Installez-le avec: pip install livekit-api")
    sys.exit(1)

# Charger les variables d'environnement depuis .env si disponible
from dotenv import load_dotenv
load_dotenv()

# Configuration LiveKit depuis les variables d'environnement
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")
LIVEKIT_URL = os.getenv("LIVEKIT_URL", "wss://your-livekit-server.livekit.cloud")


def get_api_url(ws_url: str) -> str:
    """Convertit l'URL WebSocket en URL HTTP pour l'API REST"""
    return ws_url.replace("wss://", "https://", 1).replace("ws://", "http://", 1)


async def list_all_rooms(api_url: str, api_key: str, api_secret: str, debug: bool = False) -> list:
    """Liste toutes les rooms LiveKit"""
    try:
        async with api.LiveKitAPI(
            url=api_url,
            api_key=api_key,
            api_secret=api_secret,
        ) as lkapi:
            # Lister toutes les rooms (sans filtre)
            # Essayer sans paramètres d'abord
            rooms_resp = await lkapi.room.list_rooms(api.ListRoomsRequest())
            
            if debug:
                print(f"   Requête: ListRoomsRequest() sans paramètres")
            
            if debug:
                print(f"   Type de réponse: {type(rooms_resp)}")
                print(f"   Attributs disponibles: {[a for a in dir(rooms_resp) if not a.startswith('_')]}")
            
            # Accéder aux rooms depuis la réponse
            rooms = []
            
            # Vérifier si l'attribut rooms existe
            if hasattr(rooms_resp, "rooms"):
                rooms_attr = rooms_resp.rooms
                if debug:
                    print(f"   rooms_resp.rooms existe")
                    print(f"   Type: {type(rooms_attr)}")
                    print(f"   Valeur: {rooms_attr}")
                    print(f"   Est None: {rooms_attr is None}")
                    if rooms_attr is not None:
                        print(f"   Longueur/itérable: {len(rooms_attr) if hasattr(rooms_attr, '__len__') else 'N/A'}")
                
                # Convertir en liste si ce n'est pas None
                if rooms_attr is not None:
                    try:
                        # Si c'est déjà une liste ou un itérable
                        if hasattr(rooms_attr, "__iter__") and not isinstance(rooms_attr, str):
                            rooms = list(rooms_attr)
                            # Vérifier que ce n'est pas juste le conteneur vide lui-même
                            if len(rooms) == 1 and rooms[0] == rooms_attr:
                                # C'était le conteneur lui-même, pas son contenu
                                rooms = list(rooms_attr) if len(rooms_attr) > 0 else []
                        else:
                            # Sinon, essayer de le traiter comme une seule room
                            rooms = [rooms_attr]
                        
                        if debug:
                            print(f"   ✅ {len(rooms)} room(s) trouvée(s) via rooms_resp.rooms")
                    except Exception as e:
                        if debug:
                            print(f"   ❌ Erreur lors de la conversion: {e}")
            else:
                if debug:
                    print(f"   ⚠️  rooms_resp.rooms n'existe pas")
                # Essayer getattr comme fallback
                rooms_attr = getattr(rooms_resp, "rooms", None)
                if rooms_attr:
                    rooms = list(rooms_attr) if hasattr(rooms_attr, "__iter__") else [rooms_attr]
                    if debug:
                        print(f"   ✅ {len(rooms)} room(s) trouvée(s) via getattr")
            
            # Si rooms est vide mais que rooms_resp.rooms existe, essayer de l'itérer directement
            if len(rooms) == 0 and hasattr(rooms_resp, "rooms") and rooms_resp.rooms is not None:
                if debug:
                    print(f"   Tentative d'itération directe sur rooms_resp.rooms...")
                try:
                    # Essayer d'itérer directement
                    for room in rooms_resp.rooms:
                        rooms.append(room)
                    if debug and len(rooms) > 0:
                        print(f"   ✅ {len(rooms)} room(s) trouvée(s) via itération directe")
                except Exception as e:
                    if debug:
                        print(f"   ❌ Erreur lors de l'itération: {e}")
            
            if debug and rooms:
                print(f"   Exemple de première room:")
                first_room = rooms[0]
                print(f"      Type: {type(first_room)}")
                print(f"      Attributs: {[a for a in dir(first_room) if not a.startswith('_')]}")
                if hasattr(first_room, "name"):
                    print(f"      Nom: {first_room.name}")
                if hasattr(first_room, "num_participants"):
                    print(f"      Participants: {first_room.num_participants}")
            
            if not rooms:
                if debug:
                    print(f"   ⚠️  Aucune room trouvée dans la réponse")
                    # Essayer d'afficher tous les champs de la réponse
                    print(f"   Tous les champs de la réponse:")
                    try:
                        # Utiliser ListFields pour voir tous les champs remplis
                        for field, value in rooms_resp.ListFields():
                            print(f"      {field.name}: {value} (type: {type(value)})")
                    except:
                        pass
                    
                    # Essayer d'afficher rooms_resp.rooms de différentes façons
                    if hasattr(rooms_resp, "rooms"):
                        rooms_attr = rooms_resp.rooms
                        print(f"   rooms_resp.rooms = {rooms_attr}")
                        print(f"   type(rooms_resp.rooms) = {type(rooms_attr)}")
                        if rooms_attr is not None:
                            try:
                                print(f"   len(rooms_resp.rooms) = {len(rooms_attr)}")
                                if len(rooms_attr) > 0:
                                    print(f"   Première room: {rooms_attr[0]}")
                                    print(f"   Type première room: {type(rooms_attr[0])}")
                            except:
                                print(f"   rooms_resp.rooms n'a pas de len() ou est vide")
                            try:
                                rooms_list = list(rooms_attr)
                                print(f"   list(rooms_resp.rooms) = {rooms_list}")
                                print(f"   len(list(...)) = {len(rooms_list)}")
                            except Exception as e:
                                print(f"   Impossible de convertir en liste: {e}")
                    
                    # Vérifier s'il y a d'autres attributs qui pourraient contenir les rooms
                    print(f"   Autres attributs potentiels:")
                    for attr in dir(rooms_resp):
                        if not attr.startswith("_") and attr != "rooms":
                            try:
                                value = getattr(rooms_resp, attr)
                                if not callable(value) and value:
                                    print(f"      {attr}: {value}")
                            except:
                                pass
            
            return rooms
    except Exception as e:
        print(f"❌ Erreur lors de la récupération des rooms: {e}")
        import traceback
        if debug:
            traceback.print_exc()
        return []


async def delete_room(api_url: str, api_key: str, api_secret: str, room_name: str) -> bool:
    """Supprime une room LiveKit"""
    try:
        async with api.LiveKitAPI(
            url=api_url,
            api_key=api_key,
            api_secret=api_secret,
        ) as lkapi:
            await lkapi.room.delete_room(api.DeleteRoomRequest(room=room_name))
            return True
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        return False


async def main():
    parser = argparse.ArgumentParser(
        description="Supprime toutes les rooms LiveKit (ou celles correspondant à un filtre)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Affiche les rooms qui seraient supprimées sans les supprimer réellement"
    )
    parser.add_argument(
        "--filter",
        type=str,
        help="Filtre les rooms par nom (ex: 'evalora' pour ne supprimer que les rooms commençant par 'evalora')"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Supprime même les rooms avec des participants actifs"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Affiche des informations de débogage détaillées"
    )
    parser.add_argument(
        "--room-name",
        type=str,
        help="Supprime une room spécifique par son nom exact (ex: 'evalora-12345')"
    )
    args = parser.parse_args()

    # Vérifier la configuration
    if not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET:
        print("❌ Erreur: LIVEKIT_API_KEY et LIVEKIT_API_SECRET doivent être configurés")
        print("   Définissez-les dans votre fichier .env ou comme variables d'environnement")
        sys.exit(1)

    if LIVEKIT_URL == "wss://your-livekit-server.livekit.cloud":
        print("❌ Erreur: LIVEKIT_URL doit être configuré avec votre URL LiveKit")
        sys.exit(1)

    api_url = get_api_url(LIVEKIT_URL)
    
    print("🔍 Connexion à LiveKit...")
    print(f"   URL: {api_url}")
    print(f"   API Key: {LIVEKIT_API_KEY[:8]}...")
    print()

    # Si un nom de room spécifique est fourni, supprimer directement cette room
    if args.room_name:
        print(f"🗑️  Suppression de la room '{args.room_name}'...")
        if not args.dry_run:
            response = input("   Confirmer la suppression? (oui/non): ")
            if response.lower() not in ["oui", "o", "yes", "y"]:
                print("❌ Opération annulée")
                return
            
            success = await delete_room(api_url, LIVEKIT_API_KEY, LIVEKIT_API_SECRET, args.room_name)
            if success:
                print(f"✅ Room '{args.room_name}' supprimée avec succès")
            else:
                print(f"❌ Échec de la suppression de la room '{args.room_name}'")
        else:
            print(f"🔍 Mode DRY-RUN: La room '{args.room_name}' serait supprimée")
        return

    # Lister toutes les rooms
    print("📋 Récupération de la liste des rooms...")
    if args.debug:
        print("   Mode debug activé")
    rooms = await list_all_rooms(api_url, LIVEKIT_API_KEY, LIVEKIT_API_SECRET, debug=args.debug)

    if not rooms:
        print("✅ Aucune room trouvée. Rien à nettoyer!")
        print()
        print("💡 Note: Cela peut signifier que:")
        print("   - Toutes les rooms ont été supprimées automatiquement (timeout de 60s)")
        print("   - Aucune room n'existe actuellement dans votre compte LiveKit")
        print("   - Les rooms sont vides et ont été nettoyées")
        print()
        print("   Si vous pensez qu'il devrait y avoir des rooms, vérifiez:")
        print("   - Votre dashboard LiveKit")
        print("   - Que les credentials sont corrects")
        print("   - Que l'URL LiveKit est correcte")
        return

    print(f"   {len(rooms)} room(s) trouvée(s)\n")

    # Filtrer les rooms si nécessaire
    if args.filter:
        rooms = [r for r in rooms if getattr(r, "name", "").startswith(args.filter)]
        if not rooms:
            print(f"✅ Aucune room ne correspond au filtre '{args.filter}'")
            return
        print(f"🔍 Filtre appliqué: {len(rooms)} room(s) correspondant à '{args.filter}'\n")

    # Afficher les rooms
    print("📋 Rooms trouvées:")
    rooms_to_delete = []
    for room in rooms:
        # Obtenir le nom de la room (méthode directe comme dans l'exemple)
        room_name = getattr(room, "name", None)
        if not room_name:
            room_name = "Unknown"
        
        # Obtenir le SID
        room_sid = getattr(room, "sid", None)
        if not room_sid:
            room_sid = "Unknown"
        
        # Obtenir le nombre de participants (méthode directe comme dans l'exemple)
        num_participants = getattr(room, "num_participants", 0) or 0
        
        # Vérifier si la room a des participants
        if num_participants > 0 and not args.force:
            print(f"   ⚠️  {room_name} (SID: {room_sid}) - {num_participants} participant(s) - IGNORÉE")
        else:
            status = f" - {num_participants} participant(s)" if num_participants > 0 else ""
            print(f"   🗑️  {room_name} (SID: {room_sid}){status}")
            rooms_to_delete.append(room_name)

    if not rooms_to_delete:
        print("\n✅ Aucune room à supprimer (toutes ont des participants actifs)")
        if not args.force:
            print("   Utilisez --force pour forcer la suppression")
        return

    print(f"\n📊 Résumé: {len(rooms_to_delete)} room(s) à supprimer")

    if args.dry_run:
        print("\n🔍 Mode DRY-RUN: Aucune room ne sera supprimée")
        print("   Supprimez l'option --dry-run pour supprimer réellement les rooms")
        return

    # Demander confirmation
    print("\n⚠️  ATTENTION: Cette action est irréversible!")
    response = input("   Voulez-vous vraiment supprimer ces rooms? (oui/non): ")
    if response.lower() not in ["oui", "o", "yes", "y"]:
        print("❌ Opération annulée")
        return

    # Supprimer les rooms
    print("\n🗑️  Suppression des rooms...")
    deleted = 0
    failed = 0

    for room_name in rooms_to_delete:
        print(f"   Suppression de '{room_name}'...", end=" ")
        success = await delete_room(api_url, LIVEKIT_API_KEY, LIVEKIT_API_SECRET, room_name)
        if success:
            print("✅")
            deleted += 1
        else:
            print("❌")
            failed += 1

    # Résumé final
    print("\n" + "=" * 60)
    print("📊 Résumé final:")
    print(f"   ✅ Supprimées: {deleted}")
    if failed > 0:
        print(f"   ❌ Échecs: {failed}")
    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n❌ Opération interrompue par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erreur fatale: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
