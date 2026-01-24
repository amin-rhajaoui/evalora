"""
Modèles pour les documents d'examen
"""
from pydantic import BaseModel, Field
from typing import List, Optional


class Document(BaseModel):
    """Document d'examen (texte + image)"""
    id: str
    title: str
    theme: str  # société, culture, environnement, etc.
    author: Optional[str] = None
    source: Optional[str] = None
    date: Optional[str] = None
    text: str  # Texte du document (100-200 mots)
    image_url: str  # URL de l'image illustratrice
    keywords: List[str] = []  # Champ lexical principal
    difficulty: str = "B1"

    # Questions suggérées pour le débat
    debate_questions: List[str] = []


class DocumentResponse(BaseModel):
    """Réponse API pour un document"""
    id: str
    title: str
    theme: str
    author: Optional[str]
    source: Optional[str]
    date: Optional[str]
    text: str
    image_url: str
    keywords: List[str]


class DocumentListResponse(BaseModel):
    """Liste des documents disponibles"""
    documents: List[DocumentResponse]
    total: int
