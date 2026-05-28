"""
Schémas Pydantic pour les payloads WhatsApp Business API (Meta)
Correspond au format exact de la Cloud API de Meta
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator, field_validator


from typing import Optional
from pydantic import BaseModel


class DisappearingMode(BaseModel):
    initiator: Optional[str] = None
    trigger: Optional[str] = None
    initiatedByMe: Optional[bool] = None


class AudioContextInfo(BaseModel):
    ephemeralSettingTimestamp: Optional[str] = None
    disappearingMode: Optional[dict] = None


class ImageContextInfo(BaseModel):
    ephemeralSettingTimestamp: Optional[str] = None
    disappearingMode: Optional[dict] = None


class ContextInfo(BaseModel):
    ephemeralSettingTimestamp: Optional[str] = None
    disappearingMode: Optional[DisappearingMode] = None


class ImageMessage(BaseModel):
    url: Optional[str] = None
    mimetype: Optional[str] = None
    fileSha256: Optional[str] = None
    fileLength: Optional[str] = None
    height: Optional[int] = None
    width: Optional[int] = None
    mediaKey: Optional[str] = None
    fileEncSha256: Optional[str] = None
    directPath: Optional[str] = None
    mediaKeyTimestamp: Optional[str] = None
    jpegThumbnail: Optional[str] = None
    contextInfo: Optional[ImageContextInfo] = None
    viewOnce: Optional[bool] = None

    @field_validator('height', 'width', mode='before')
    @classmethod
    def parse_protobuf_int(cls, v: Any) -> Optional[int]:
        if isinstance(v, dict):
            low = v.get('low')
            high = v.get('high', 0)
            if high == 0:
                return low
            return low + (high * 4294967296)
        return v


class AudioMessage(BaseModel):
    url: Optional[str] = None
    mimetype: Optional[str] = None
    fileSha256: Optional[str] = None
    fileLength: Optional[str] = None
    seconds: Optional[int] = None
    ptt: Optional[bool] = None
    mediaKey: Optional[str] = None
    fileEncSha256: Optional[str] = None
    directPath: Optional[str] = None
    mediaKeyTimestamp: Optional[str] = None
    contextInfo: Optional[AudioContextInfo] = None
    waveform: Optional[str] = None
    viewOnce: Optional[bool] = None

    @field_validator('seconds', mode='before')
    @classmethod
    def parse_protobuf_int(cls, v: Any) -> Optional[int]:
        if isinstance(v, dict):
            low = v.get('low')
            high = v.get('high', 0)
            if high == 0:
                return low
            return low + (high * 4294967296)
        return v


class QuotedMessage(BaseModel):
    conversation: Optional[str] = None


class QuotedImageMessage(BaseModel):
    imageMessage: Optional[ImageMessage] = None


class ReplyContextInfo(BaseModel):
    stanzaId: Optional[str] = None
    participant: Optional[str] = None
    quotedMessage: Optional[QuotedMessage] = None
    ephemeralSettingTimestamp: Optional[str] = None
    disappearingMode: Optional[DisappearingMode] = None


class ReplyImageContextInfo(BaseModel):
    stanzaId: Optional[str] = None
    participant: Optional[str] = None
    quotedMessage: Optional[QuotedImageMessage] = None
    ephemeralSettingTimestamp: Optional[str] = None
    disappearingMode: Optional[DisappearingMode] = None


class ExtendedTextMessage(BaseModel):
    text: Optional[str] = None

    contextInfo: Optional[
        ReplyImageContextInfo
        | ReplyContextInfo
        | ContextInfo
    ] = None

    inviteLinkGroupTypeV2: Optional[str] = None


class DeviceListMetadata(BaseModel):
    senderKeyHash: Optional[str] = None
    senderTimestamp: Optional[str] = None
    senderAccountType: Optional[str] = None
    receiverAccountType: Optional[str] = None
    recipientKeyHash: Optional[str] = None
    recipientTimestamp: Optional[str] = None


class LimitSharingV2(BaseModel):
    sharingLimited: Optional[bool] = None
    trigger: Optional[str] = None
    limitSharingSettingTimestamp: Optional[str] = None
    initiatedByMe: Optional[bool] = None


class MessageContextInfo(BaseModel):
    deviceListMetadata: Optional[DeviceListMetadata] = None
    deviceListMetadataVersion: Optional[int] = None
    messageSecret: Optional[str] = None
    limitSharingV2: Optional[LimitSharingV2] = None
    imageMessage: Optional[ImageMessage] = None

    @field_validator('deviceListMetadataVersion', mode='before')
    @classmethod
    def parse_protobuf_int(cls, v: Any) -> Optional[int]:
        if isinstance(v, dict):
            low = v.get('low')
            high = v.get('high', 0)
            if high == 0:
                return low
            return low + (high * 4294967296)
        return v


class MessageContent(BaseModel):
    conversation: Optional[str] = None
    extendedTextMessage: Optional[ExtendedTextMessage] = None
    messageContextInfo: Optional[MessageContextInfo] = None
    audioMessage: Optional[AudioMessage] = None
    imageMessage: Optional[ImageMessage] = None


class MessageKey(BaseModel):
    id: Optional[str] = None
    fromMe: Optional[bool] = None
    remoteJid: Optional[str] = None
    senderPn: Optional[str] = None
    cleanedSenderPn: Optional[str] = None
    senderLid: Optional[str] = None
    addressingMode: Optional[str] = None


class MessageData(BaseModel):
    key: Optional[MessageKey] = None
    messageTimestamp: Optional[int] = None
    pushName: Optional[str] = None
    broadcast: Optional[bool] = None
    message: Optional[MessageContent] = None
    messageBody: Optional[str] = None
    remoteJid: Optional[str] = None
    id: Optional[str] = None

    @field_validator('messageTimestamp', mode='before')
    @classmethod
    def parse_protobuf_int(cls, v: Any) -> Optional[int]:
        if isinstance(v, dict):
            low = v.get('low')
            high = v.get('high', 0)
            if high == 0:
                return low
            return low + (high * 4294967296)
        return v


class Data(BaseModel):
    messages: Optional[MessageData] = None


class Payload(BaseModel):
    event: Optional[str] = None
    sessionId: Optional[str] = None
    data: Optional[Data] = None
    timestamp: Optional[int] = None

    @field_validator('timestamp', mode='before')
    @classmethod
    def parse_protobuf_int(cls, v: Any) -> Optional[int]:
        if isinstance(v, dict):
            low = v.get('low')
            high = v.get('high', 0)
            if high == 0:
                return low
            return low + (high * 4294967296)
        return v


# ============================================================================
# SCHÉMAS SORTANTS — WASenderAPI
# ============================================================================

class WASenderTextPayload(BaseModel):
    """Payload pour envoyer un message texte simple via WASenderAPI"""
    to: str = Field(..., description="Numéro destinataire au format international (ex: +22967044033)")
    text: str = Field(..., description="Contenu du message texte")


class WASenderImagePayload(BaseModel):
    """Payload pour envoyer une image (avec ou sans légende) via WASenderAPI"""
    to: str = Field(..., description="Numéro destinataire au format international")
    imageUrl: str = Field(..., description="URL publique de l'image à envoyer")
    text: Optional[str] = Field(None, description="Légende optionnelle de l'image")


class WASenderAudioPayload(BaseModel):
    """Payload pour envoyer un audio/note vocale via WASenderAPI"""
    to: str = Field(..., description="Numéro destinataire au format international")
    audioUrl: str = Field(..., description="URL publique du fichier audio à envoyer")


class WASenderDocumentPayload(BaseModel):
    """Payload pour envoyer un document via WASenderAPI"""
    to: str = Field(..., description="Numéro destinataire au format international")
    documentUrl: str = Field(..., description="URL publique du document à envoyer")
    fileName: Optional[str] = Field(None, description="Nom affiché du fichier")
    text: Optional[str] = Field(None, description="Légende optionnelle du document")
    