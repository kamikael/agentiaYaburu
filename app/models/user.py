from sqlalchemy import (
    Column, String, Integer, Boolean, Text, DateTime, ForeignKey,
    Numeric
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, synonym
from sqlalchemy.sql import func

import uuid

from app.db import Base

class User(Base):
    __tablename__ = "utilisateur"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Colonnes physiques (noms conformes à l'UML)
    telephone = Column(String(20), unique=True, nullable=False)
    email = Column(String(255), unique=True)
    prenom = Column(String(100))
    nom = Column(String(100))
    integration_etape = Column(String(50), default="boutique_en_attente")
    derniere_vue = Column(DateTime)
    langue = Column(String(10), default="fr")
    date_creation = Column(DateTime, server_default=func.now())
    date_mise_a_jour = Column(DateTime, server_default=func.now(), onupdate=func.now())
    date_suppression = Column(DateTime)
    traitement_en_cours = Column(Boolean, default=False, nullable=False)

    # Métadonnées additionnelles héritées de la version précédente
    timezone = Column(String(50), default="Africa/Porto-Novo")
    temp_email = Column(String(255))

    # Synonymes pour compatibilité totale avec le code existant en Python
    phone_number = synonym("telephone")
    first_name = synonym("prenom")
    last_name = synonym("nom")
    onboarding_step = synonym("integration_etape")
    last_seen_at = synonym("derniere_vue")
    language_preference = synonym("langue")
    created_at = synonym("date_creation")
    updated_at = synonym("date_mise_a_jour")
    deleted_at = synonym("date_suppression")

    # Relations
    stores = relationship("store", back_populates="user")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")


    @property
    def conversations(self):
        convs_list = []
        for s in self.stores:
            convs_list.extend(s.conversations)
        return convs_list

    @property
    def messages(self):
        msgs_list = []
        for c in self.conversations:
            msgs_list.extend(c.messages)
        return msgs_list
