# Installation avec Python 3.14

## Problème
Python 3.14 est très récent et PyO3 (utilisé par pydantic-core) ne le supporte officiellement que jusqu'à Python 3.13.

## Solution 1 : Utiliser Python 3.13 ou 3.12 (RECOMMANDÉ)

C'est la solution la plus stable. Installez Python 3.13 ou 3.12 et créez un environnement virtuel :

```bash
# Installer Python 3.13 (via Homebrew)
brew install python@3.13

# Créer un environnement virtuel
python3.13 -m venv venv

# Activer l'environnement
source venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt
```

## Solution 2 : Forcer la compilation avec Python 3.14

Si vous devez absolument utiliser Python 3.14, utilisez la variable d'environnement :

```bash
# Dans le répertoire backend
export PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1
pip install -r requirements.txt
```

Ou en une seule commande :
```bash
PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1 pip install -r requirements.txt
```

**Note** : Cette solution utilise l'ABI stable de Python, ce qui peut fonctionner mais n'est pas garanti.
