#!/bin/bash

# Script d'installation pour le backend BOTFLE
# Ce script détecte la version de Python et installe les dépendances

echo "🔍 Vérification de la version de Python..."

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
PYTHON_FULL_VERSION=$(python3 --version 2>&1 | awk '{print $2}')

echo "Version Python détectée: $PYTHON_FULL_VERSION"

# Vérifier si Python 3.14
if [[ "$PYTHON_VERSION" == "3.14" ]]; then
    echo "⚠️  ATTENTION: Python 3.14 détecté"
    echo "PyO3 (utilisé par pydantic-core) ne supporte officiellement que jusqu'à Python 3.13"
    echo ""
    echo "Options:"
    echo "1. Utiliser Python 3.13 ou 3.12 (recommandé)"
    echo "2. Forcer l'installation avec Python 3.14 (peut échouer)"
    echo ""
    read -p "Voulez-vous forcer l'installation avec Python 3.14? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🚀 Installation avec PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1..."
        export PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1
        pip install -r requirements.txt
    else
        echo "❌ Installation annulée. Veuillez utiliser Python 3.13 ou 3.12."
        echo "Pour installer Python 3.13: brew install python@3.13"
        exit 1
    fi
elif [[ "$PYTHON_VERSION" == "3.13" ]] || [[ "$PYTHON_VERSION" == "3.12" ]]; then
    echo "✅ Version Python compatible détectée"
    pip install -r requirements.txt
else
    echo "⚠️  Version Python: $PYTHON_FULL_VERSION"
    echo "Installation standard..."
    pip install -r requirements.txt
fi

echo ""
echo "✅ Installation terminée!"
