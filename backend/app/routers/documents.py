"""
Router pour la bibliothèque de documents
"""
from fastapi import APIRouter, HTTPException
from typing import List
import json
import os

from ..models.document import Document, DocumentResponse, DocumentListResponse

router = APIRouter()

# Charger les documents depuis le fichier JSON
def load_documents() -> List[Document]:
    """Charge les documents depuis le fichier data"""
    data_path = os.path.join(os.path.dirname(__file__), "..", "data", "documents.json")
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return [Document(**doc) for doc in data["documents"]]
    except FileNotFoundError:
        return []

# Cache des documents
_documents_cache: List[Document] = []


def get_documents() -> List[Document]:
    """Récupère les documents (avec cache)"""
    global _documents_cache
    if not _documents_cache:
        _documents_cache = load_documents()
    return _documents_cache


@router.get("", response_model=DocumentListResponse)
async def list_documents():
    """
    Récupère la liste des 8 documents disponibles.

    Chaque document contient un texte (100-200 mots) et une image.
    Thèmes: société, culture, environnement, numérique, travail, éducation, diversité, relations humaines.
    """
    docs = get_documents()
    return DocumentListResponse(
        documents=[
            DocumentResponse(
                id=doc.id,
                title=doc.title,
                theme=doc.theme,
                author=doc.author,
                source=doc.source,
                date=doc.date,
                text=doc.text,
                image_url=doc.image_url,
                keywords=doc.keywords
            )
            for doc in docs
        ],
        total=len(docs)
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str):
    """Récupère un document par son ID"""
    docs = get_documents()

    for doc in docs:
        if doc.id == document_id:
            return DocumentResponse(
                id=doc.id,
                title=doc.title,
                theme=doc.theme,
                author=doc.author,
                source=doc.source,
                date=doc.date,
                text=doc.text,
                image_url=doc.image_url,
                keywords=doc.keywords
            )

    raise HTTPException(status_code=404, detail="Document non trouvé")


@router.get("/{document_id}/questions")
async def get_debate_questions(document_id: str):
    """
    Récupère les questions de débat suggérées pour un document.

    Ces questions sont utilisées par l'avatar pendant la partie 2 (Débat).
    """
    docs = get_documents()

    for doc in docs:
        if doc.id == document_id:
            return {
                "document_id": document_id,
                "theme": doc.theme,
                "questions": doc.debate_questions
            }

    raise HTTPException(status_code=404, detail="Document non trouvé")
