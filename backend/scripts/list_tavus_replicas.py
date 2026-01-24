#!/usr/bin/env python3
"""
Script pour lister les replicas Tavus disponibles
"""
import requests
import json
import sys
from pathlib import Path

# Ajouter le répertoire parent au path pour importer les modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings

def list_replicas():
    """Liste les replicas Tavus disponibles"""
    
    if not settings.TAVUS_API_KEY:
        print("❌ Erreur: TAVUS_API_KEY n'est pas configuré dans le .env")
        print("   Assurez-vous d'avoir défini TAVUS_API_KEY dans votre fichier .env")
        return
    
    base_url = settings.TAVUS_BASE_URL.rstrip('/')
    if not base_url.endswith('/v2'):
        if base_url.endswith('/v1'):
            base_url = base_url.replace('/v1', '/v2')
        else:
            base_url = f"{base_url}/v2"
    
    url = f"{base_url}/replicas"
    
    print("=" * 60)
    print("Liste des Replicas Tavus")
    print("=" * 60)
    print(f"Base URL: {base_url}")
    print(f"API Key: {settings.TAVUS_API_KEY[:8]}...")
    print("-" * 60)
    print(f"Requête: GET {url}")
    print()
    
    headers = {
        "Content-Type": "application/json",
        "x-api-key": settings.TAVUS_API_KEY
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        # L'API Tavus retourne les replicas dans "data" ou "replicas"
        replicas = data.get("data", data.get("replicas", []))
        
        if not replicas:
            print("⚠️  Aucun replica trouvé dans votre compte Tavus")
            print()
            print("Réponse complète:")
            print(json.dumps(data, indent=2))
            return
        
        print(f"✅ {len(replicas)} replica(s) trouvé(s):\n")
        
        for i, replica in enumerate(replicas, 1):
            replica_id = replica.get("replica_id") or replica.get("id") or "N/A"
            replica_name = replica.get("replica_name") or replica.get("name") or "Sans nom"
            status = replica.get("status", "N/A")
            
            print(f"{i}. {replica_name}")
            print(f"   ID: {replica_id}")
            print(f"   Status: {status}")
            
            # Afficher d'autres infos si disponibles
            if "created_at" in replica:
                print(f"   Créé le: {replica['created_at']}")
            if "video_url" in replica:
                print(f"   Vidéo: {replica['video_url']}")
            
            print()
        
        print("=" * 60)
        print("💡 Pour utiliser un replica, mettez à jour 'tavus_replica_id' dans")
        print("   backend/app/config.py avec l'un des IDs ci-dessus")
        print("=" * 60)
        
    except requests.exceptions.HTTPError as e:
        print(f"❌ Erreur HTTP: {e.response.status_code}")
        try:
            error_data = e.response.json()
            print(f"Message: {error_data.get('message', 'N/A')}")
            print()
            print("Réponse complète:")
            print(json.dumps(error_data, indent=2))
        except:
            print(f"Réponse: {e.response.text}")
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur de connexion: {e}")
        print(f"   Vérifiez votre connexion réseau et l'URL: {url}")
    
    except Exception as e:
        print(f"❌ Erreur inattendue: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    list_replicas()
