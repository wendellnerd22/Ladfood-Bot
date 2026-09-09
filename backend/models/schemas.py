import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


class StoreCreate(BaseModel):
    nome: str
    token: str = ""
    demo: bool = False
    bot_prompt: str = ""
    lojista_email: str = ""
    lojista_senha: str = ""


class StoreUpdate(BaseModel):
    nome: Optional[str] = None
    token: Optional[str] = None
    demo: Optional[bool] = None
    bot_prompt: Optional[str] = None
    lojista_email: Optional[str] = None
    lojista_senha: Optional[str] = None


class Store(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    nome: str
    token: str = ""
    demo: bool = False
    bot_prompt: str = ""
    conexao_ok: bool = False
    conexao_msg: str = "Nunca testada"
    api_key: str = Field(default_factory=lambda: uuid.uuid4().hex)
    lojista_email: str = ""
    created_at: datetime = Field(default_factory=_now)


class ConnectionResult(BaseModel):
    ok: bool
    mensagem: str
    nome_loja: Optional[str] = None
    aberta_agora: Optional[bool] = None


class OrderRecord(BaseModel):
    id: str
    store_id: str
    session_id: str = ""
    cliente_nome: str = ""
    cliente_telefone: str = ""
    tipo: str = "DELIVERY"
    status_codigo: str = "E"
    status_descricao: str = "Pendente"
    valor_total: float = 0.0
    data_pedido: str = ""
    demo: bool = False
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_now)


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ToolTrace(BaseModel):
    name: str
    ok: bool
    resumo: str


class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    store_id: str
    role: str  # "user" | "bot"
    text: str
    tools: List[ToolTrace] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_now)


class ChatResponse(BaseModel):
    reply: str
    tools: List[ToolTrace] = Field(default_factory=list)
    order_uuid: Optional[str] = None
