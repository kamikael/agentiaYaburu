from contextvars import ContextVar
from typing import Optional

# Variable de contexte pour stocker l'ID de la boutique de manière isolée par requête
store_id_ctx: ContextVar[Optional[str]] = ContextVar("store_id", default=None)
yaburu_store_id_ctx: ContextVar[Optional[str]] = ContextVar("yaburu_store_id", default=None)
phone_number_ctx: ContextVar[Optional[str]] = ContextVar("phone_number", default=None)
