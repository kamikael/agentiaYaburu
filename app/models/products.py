from sqlalchemy import (
    Column, String, Integer, Boolean, Text, DateTime, ForeignKey,
    Numeric
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, synonym
from sqlalchemy.sql import func

import uuid

from app.db import Base

class Product(Base):
    __tablename__ = "produits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    boutique_id = Column(UUID(as_uuid=True), ForeignKey("boutique.id", ondelete="CASCADE"), nullable=False)

    type_produit = Column(String(20), nullable=True)  # service, physique, numerique
    chemin_fichier = Column(String(200)) # UML says String(30), but 200 is safer for file paths
    nom = Column(String(100), nullable=True) # UML says String(20), but 100 is safer for real product names
    description = Column(Text) # UML says String(20), but Text is safer for real descriptions
    prix = Column(Numeric(10, 2), nullable=True)
    quantite = Column(Integer, default=0)
    
    # Nouvelles colonnes
    status = Column(String(20), default="en_attente") # en_attente, publié
    instruction_achat = Column(Text)
    yaburu_produit_id = Column(String(255))
    publie_le = Column(DateTime)

    # Synonymes pour compatibilité
    type_product = synonym("type_produit")

    date_creation = Column(DateTime, server_default=func.now())
    date_mise_a_jour = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relations
    store = relationship("store", back_populates="products")
    attachments = relationship("AttachmentFile", back_populates="product", cascade="all, delete-orphan")
