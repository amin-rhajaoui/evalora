# Scripts de maintenance

## cleanup_livekit_rooms.py

Script pour supprimer toutes les rooms LiveKit (nettoyage).

### Prérequis

- Python 3.8+
- Module `livekit-api` installé
- Variables d'environnement configurées dans `.env`:
  - `LIVEKIT_API_KEY`
  - `LIVEKIT_API_SECRET`
  - `LIVEKIT_URL`

### Usage

```bash
# Depuis le répertoire backend/
cd backend

# Mode dry-run (affiche sans supprimer)
python scripts/cleanup_livekit_rooms.py --dry-run

# Supprimer toutes les rooms
python scripts/cleanup_livekit_rooms.py

# Supprimer uniquement les rooms commençant par "evalora"
python scripts/cleanup_livekit_rooms.py --filter evalora

# Forcer la suppression même si des participants sont actifs
python scripts/cleanup_livekit_rooms.py --force
```

### Options

- `--dry-run`: Affiche les rooms qui seraient supprimées sans les supprimer réellement
- `--filter <nom>`: Filtre les rooms par nom (ex: `evalora` pour ne supprimer que les rooms commençant par "evalora")
- `--force`: Supprime même les rooms avec des participants actifs (attention!)

### Exemples

```bash
# Voir toutes les rooms sans les supprimer
python scripts/cleanup_livekit_rooms.py --dry-run

# Supprimer uniquement les rooms d'examen (commençant par "evalora-")
python scripts/cleanup_livekit_rooms.py --filter evalora

# Nettoyage complet (supprime toutes les rooms)
python scripts/cleanup_livekit_rooms.py
```

## list_tavus_replicas.py

Script pour lister les replicas Tavus disponibles.

### Usage

```bash
python scripts/list_tavus_replicas.py
```
