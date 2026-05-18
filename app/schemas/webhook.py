"""
Schémas Pydantic pour les payloads WhatsApp Business API (Meta)
Correspond au format exact de la Cloud API de Meta
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator


# ============================================================================
# ENUMS
# ============================================================================

class MessageType(str, Enum):
    """Types de messages supportés par WhatsApp"""
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    VOICE = "voice"
    DOCUMENT = "document"
    STICKER = "sticker"
    LOCATION = "location"
    CONTACTS = "contacts"
    INTERACTIVE = "interactive"
    ORDER = "order"
    REACTION = "reaction"


class MessageStatus(str, Enum):
    """Statuts des messages"""
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    PENDING = "pending"


class WebhookEventType(str, Enum):
    """Types d'événements webhook"""
    MESSAGE_RECEIVED = "messages"
    MESSAGE_STATUS = "message_status"
    CONTACTS = "contacts"
    ERRORS = "message_template_status_update"


# ============================================================================
# TEXT MESSAGE
# ============================================================================

class TextMessageBody(BaseModel):
    """Contenu d'un message texte"""
    body: str = Field(..., description="Contenu du texte du message")

    class Config:
        json_schema_extra = {
            "example": {
                "body": "Comment ajouter un produit?"
            }
        }


# ============================================================================
# IMAGE MESSAGE
# ============================================================================

class ImageObject(BaseModel):
    """Objet image reçu"""
    id: str = Field(..., description="Media ID de l'image")
    mime_type: Optional[str] = Field(None, description="Type MIME (image/jpeg, image/png)")
    sha256: Optional[str] = Field(None, description="Hash SHA256 du fichier")
    caption: Optional[str] = Field(None, description="Légende de l'image")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "120044660420540",
                "mime_type": "image/jpeg",
                "sha256": "1234567890abcdef",
                "caption": "Photo du produit"
            }
        }


# ============================================================================
# VIDEO MESSAGE
# ============================================================================

class VideoObject(BaseModel):
    """Objet vidéo reçu"""
    id: str = Field(..., description="Media ID de la vidéo")
    mime_type: Optional[str] = Field(None, description="Type MIME (video/mp4)")
    sha256: Optional[str] = Field(None, description="Hash SHA256 du fichier")
    caption: Optional[str] = Field(None, description="Légende de la vidéo")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "120044660420540",
                "mime_type": "video/mp4",
                "sha256": "1234567890abcdef",
                "caption": "Démo du produit"
            }
        }


# ============================================================================
# AUDIO MESSAGE
# ============================================================================

class AudioObject(BaseModel):
    """Objet audio reçu"""
    id: str = Field(..., description="Media ID de l'audio")
    mime_type: Optional[str] = Field(None, description="Type MIME (audio/aac, audio/ogg)")
    sha256: Optional[str] = Field(None, description="Hash SHA256 du fichier")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "120044660420540",
                "mime_type": "audio/aac",
                "sha256": "1234567890abcdef"
            }
        }


# ============================================================================
# VOICE MESSAGE (Note vocale)
# ============================================================================

class VoiceObject(BaseModel):
    """Objet note vocale reçu"""
    id: str = Field(..., description="Media ID de la note vocale")
    mime_type: Optional[str] = Field(None, description="Type MIME (audio/ogg)")
    sha256: Optional[str] = Field(None, description="Hash SHA256 du fichier")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "120044660420540",
                "mime_type": "audio/ogg",
                "sha256": "1234567890abcdef"
            }
        }


# ============================================================================
# DOCUMENT MESSAGE
# ============================================================================

class DocumentObject(BaseModel):
    """Objet document reçu"""
    id: str = Field(..., description="Media ID du document")
    mime_type: Optional[str] = Field(None, description="Type MIME (application/pdf, etc.)")
    sha256: Optional[str] = Field(None, description="Hash SHA256 du fichier")
    filename: Optional[str] = Field(None, description="Nom du fichier")
    caption: Optional[str] = Field(None, description="Légende du document")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "120044660420540",
                "mime_type": "application/pdf",
                "sha256": "1234567890abcdef",
                "filename": "catalogue.pdf",
                "caption": "Catalogue produits 2025"
            }
        }


# ============================================================================
# STICKER MESSAGE
# ============================================================================

class StickerObject(BaseModel):
    """Objet sticker reçu"""
    id: str = Field(..., description="Media ID du sticker")
    mime_type: Optional[str] = Field(None, description="Type MIME (image/webp)")
    sha256: Optional[str] = Field(None, description="Hash SHA256 du fichier")
    animated: Optional[bool] = Field(None, description="Si le sticker est animé")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "120044660420540",
                "mime_type": "image/webp",
                "sha256": "1234567890abcdef",
                "animated": False
            }
        }


# ============================================================================
# LOCATION MESSAGE
# ============================================================================

class LocationObject(BaseModel):
    """Objet localisation reçue"""
    latitude: float = Field(..., description="Latitude")
    longitude: float = Field(..., description="Longitude")
    name: Optional[str] = Field(None, description="Nom du lieu")
    address: Optional[str] = Field(None, description="Adresse")

    class Config:
        json_schema_extra = {
            "example": {
                "latitude": 6.4969,
                "longitude": 2.6289,
                "name": "Boutique principale",
                "address": "Cotonou, Bénin"
            }
        }


# ============================================================================
# CONTACTS MESSAGE
# ============================================================================

class ContactPhone(BaseModel):
    """Numéro de téléphone d'un contact"""
    phone: str
    type: Optional[str] = None  # CELL, MAIN, IPHONE, HOME, WORK


class ContactEmail(BaseModel):
    """Email d'un contact"""
    email: str
    type: Optional[str] = None  # PERSONAL, WORK


class ContactName(BaseModel):
    """Nom d'un contact"""
    formatted_name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    suffix: Optional[str] = None
    prefix: Optional[str] = None


class ContactObject(BaseModel):
    """Objet contact reçu"""
    addresses: Optional[List[Dict[str, Any]]] = None
    birthday: Optional[str] = None
    emails: Optional[List[ContactEmail]] = None
    name: ContactName
    org: Optional[Dict[str, Any]] = None
    phones: Optional[List[ContactPhone]] = None
    urls: Optional[List[Dict[str, Any]]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": {
                    "formatted_name": "Jean Dupont",
                    "first_name": "Jean",
                    "last_name": "Dupont"
                },
                "phones": [
                    {
                        "phone": "+22967123456",
                        "type": "CELL"
                    }
                ]
            }
        }


# ============================================================================
# INTERACTIVE MESSAGE (Boutons, listes)
# ============================================================================

class InteractiveReply(BaseModel):
    """Réponse à un message interactif (bouton, liste)"""
    id: str = Field(..., description="ID de la réponse (bouton ou option)")
    title: str = Field(..., description="Titre de la réponse")


class InteractiveObject(BaseModel):
    """Objet pour les messages interactifs (boutons, listes)"""
    type: str = Field(..., description="Type interactif: button_reply, list_reply")
    button_reply: Optional[InteractiveReply] = None
    list_reply: Optional[InteractiveReply] = None

    class Config:
        json_schema_extra = {
            "example": {
                "type": "button_reply",
                "button_reply": {
                    "id": "btn_create_product",
                    "title": "Créer un produit"
                }
            }
        }


# ============================================================================
# MESSAGE (Conteneur principal)
# ============================================================================

class Message(BaseModel):
    """Message reçu sur WhatsApp"""
    id: str = Field(..., description="ID unique du message (WhatsApp message ID)")
    from_: str = Field(..., alias="from", description="Numéro de téléphone de l'expéditeur (avec code pays)")
    timestamp: str = Field(..., description="Timestamp UNIX du message")
    type: MessageType = Field(..., description="Type de message")
    
    # Contenu selon le type
    text: Optional[TextMessageBody] = None
    image: Optional[ImageObject] = None
    video: Optional[VideoObject] = None
    audio: Optional[AudioObject] = None
    voice: Optional[VoiceObject] = None
    document: Optional[DocumentObject] = None
    sticker: Optional[StickerObject] = None
    location: Optional[LocationObject] = None
    contacts: Optional[List[ContactObject]] = None
    interactive: Optional[InteractiveObject] = None

    # Métadonnées
    context: Optional[Dict[str, str]] = None  # {from: "...", id: "..."} pour réponses
    referral: Optional[Dict[str, Any]] = None  # Pour clics de catalogue/annonces

    class Config:
        json_schema_extra = {
            "example": {
                "id": "wamid.HBEUGVJBMkQwQkQyQUJCNUZCNzJGNzI4NzJGN0ZDQzAyNDMA",
                "from": "237612345678",
                "timestamp": "1663880309",
                "type": "text",
                "text": {
                    "body": "Comment créer un produit?"
                }
            }
        }

    @validator('from_', always=True)
    def set_from(cls, v, values):
        """Gère le mapping du champ 'from' avec alias"""
        return v or values.get('from_')


# ============================================================================
# CONTACT (Changement de contact)
# ============================================================================

class ContactChange(BaseModel):
    """Changement dans les contacts (ajout, modification)"""
    profile: Dict[str, str] = Field(..., description="Profil du contact: {name, ...}")
    wa_id: str = Field(..., description="ID WhatsApp du contact")

    class Config:
        json_schema_extra = {
            "example": {
                "profile": {
                    "name": "Jean Dupont"
                },
                "wa_id": "237612345678"
            }
        }


# ============================================================================
# MESSAGE STATUS (Statut de délivraison)
# ============================================================================

class MessageStatusNotification(BaseModel):
    """Notification de statut de message"""
    id: str = Field(..., description="ID du message")
    status: MessageStatus = Field(..., description="Statut: sent, delivered, read, failed")
    timestamp: str = Field(..., description="Timestamp UNIX du changement")
    recipient_id: str = Field(..., description="ID du destinataire")
    errors: Optional[List[Dict[str, Any]]] = None  # Erreurs si status=failed

    class Config:
        json_schema_extra = {
            "example": {
                "id": "wamid.HBEUGVJBMkQwQkQyQUJCNUZCNzJGNzI4NzJGN0ZDQzAyNDMA",
                "status": "delivered",
                "timestamp": "1663880309",
                "recipient_id": "237612345678"
            }
        }


# ============================================================================
# VALUE (Conteneur pour changes)
# ============================================================================

class WebhookValue(BaseModel):
    """Conteneur pour les changements du webhook"""
    messaging_product: str = Field(default="whatsapp", description="Toujours 'whatsapp'")
    metadata: Dict[str, str] = Field(..., description="Métadonnées: {display_phone_number, phone_number_id, ...}")
    
    messages: Optional[List[Message]] = None
    statuses: Optional[List[MessageStatusNotification]] = None
    contacts: Optional[List[ContactChange]] = None
    errors: Optional[List[Dict[str, Any]]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "messaging_product": "whatsapp",
                "metadata": {
                    "display_phone_number": "16505551234",
                    "phone_number_id": "106540352242922",
                    "business_account_id": "277846842471897"
                },
                "messages": [
                    {
                        "id": "wamid.HBEUGVJBMkQwQkQyQUJCNUZCNzJGNzI4NzJGN0ZDQzAyNDMA",
                        "from": "237612345678",
                        "timestamp": "1663880309",
                        "type": "text",
                        "text": {
                            "body": "Hello!"
                        }
                    }
                ]
            }
        }


# ============================================================================
# CHANGE (Changement dans le webhook)
# ============================================================================

class WebhookChange(BaseModel):
    """Changement dans le webhook"""
    field: str = Field(..., description="Champ affecté: messages, message_status, contacts")
    value: WebhookValue = Field(..., description="Valeur du changement")

    class Config:
        json_schema_extra = {
            "example": {
                "field": "messages",
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {
                        "display_phone_number": "16505551234",
                        "phone_number_id": "106540352242922"
                    },
                    "messages": []
                }
            }
        }


# ============================================================================
# ENTRY (Conteneur pour les changements)
# ============================================================================

class WebhookEntry(BaseModel):
    """Entrée dans le webhook"""
    id: str = Field(..., description="ID de l'entrée")
    changes: List[WebhookChange] = Field(..., description="Liste des changements")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "106540352242922",
                "changes": [
                    {
                        "field": "messages",
                        "value": {}
                    }
                ]
            }
        }


# ============================================================================
# WEBHOOK PAYLOAD (Racine)
# ============================================================================

class WebhookPayload(BaseModel):
    """
    Payload complet du webhook WhatsApp Business API (Meta)
    
    C'est le format exact que Meta envoie à votre endpoint.
    """
    object: str = Field(..., description="Type d'objet: whatsapp_business_account")
    entry: List[WebhookEntry] = Field(..., description="Liste des entrées avec changements")

    class Config:
        json_schema_extra = {
            "example": {
                "object": "whatsapp_business_account",
                "entry": [
                    {
                        "id": "106540352242922",
                        "changes": [
                            {
                                "field": "messages",
                                "value": {
                                    "messaging_product": "whatsapp",
                                    "metadata": {
                                        "display_phone_number": "16505551234",
                                        "phone_number_id": "106540352242922"
                                    },
                                    "messages": [
                                        {
                                            "id": "wamid.HBEUGVJBMkQwQkQyQUJCNUZCNzJGNzI4NzJGN0ZDQzAyNDMA",
                                            "from": "237612345678",
                                            "timestamp": "1663880309",
                                            "type": "text",
                                            "text": {
                                                "body": "Hello! How do I create a product?"
                                            }
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                ]
            }
        }


# ============================================================================
# WEBHOOK VERIFICATION (GET request)
# ============================================================================

class WebhookVerificationRequest(BaseModel):
    """Requête de vérification du webhook (GET)"""
    hub_mode: str = Field(..., alias="hub.mode", description="Mode: subscribe")
    hub_challenge: str = Field(..., alias="hub.challenge", description="Challenge à retourner")
    hub_verify_token: str = Field(..., alias="hub.verify_token", description="Token de vérification")

    class Config:
        populate_by_name = True


# ============================================================================
# OUTBOUND MESSAGE (Pour envoyer des messages)
# ============================================================================

class OutboundTextMessage(BaseModel):
    """Message texte à envoyer"""
    body: str = Field(..., description="Contenu du message", max_length=4096)

    class Config:
        json_schema_extra = {
            "example": {
                "body": "Bonjour! Voici les étapes pour créer un produit..."
            }
        }


class OutboundImageMessage(BaseModel):
    """Image à envoyer"""
    link: Optional[str] = None  # URL de l'image
    id: Optional[str] = None  # Media ID (si déjà uploadée)
    caption: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "link": "https://example.com/image.jpg",
                "caption": "Voici votre produit créé"
            }
        }


class OutboundButton(BaseModel):
    """Bouton interactif"""
    type: str = "reply"
    reply: Dict[str, str] = Field(..., description="{id, title}")


class OutboundListOption(BaseModel):
    """Option de liste"""
    id: str
    title: str
    description: Optional[str] = None


class OutboundListSection(BaseModel):
    """Section de liste"""
    title: str
    rows: List[OutboundListOption]


class OutboundInteractiveMessage(BaseModel):
    """Message interactif (boutons, liste)"""
    type: str = Field(..., description="button, list")
    header: Optional[Dict[str, Any]] = None
    body: Dict[str, str] = Field(..., description="{text}")
    footer: Optional[Dict[str, str]] = None
    action: Dict[str, Any] = Field(..., description="Pour buttons: {buttons: [...]}, pour lists: {button: '...', sections: [...]}")

    class Config:
        json_schema_extra = {
            "example": {
                "type": "button",
                "body": {
                    "text": "Que voulez-vous faire?"
                },
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {
                                "id": "btn_create",
                                "title": "Créer produit"
                            }
                        },
                        {
                            "type": "reply",
                            "reply": {
                                "id": "btn_check_stock",
                                "title": "Vérifier stock"
                            }
                        }
                    ]
                }
            }
        }


class SendMessageRequest(BaseModel):
    """Requête pour envoyer un message via l'API WhatsApp"""
    messaging_product: str = "whatsapp"
    recipient_type: str = "individual"
    to: str = Field(..., description="Numéro de téléphone destinataire (avec code pays)")
    type: MessageType = Field(..., description="Type de message: text, image, etc.")
    
    text: Optional[OutboundTextMessage] = None
    image: Optional[OutboundImageMessage] = None
    interactive: Optional[OutboundInteractiveMessage] = None

    class Config:
        json_schema_extra = {
            "example": {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": "237612345678",
                "type": "text",
                "text": {
                    "body": "Bonjour! Comment puis-je vous aider?"
                }
            }
        }