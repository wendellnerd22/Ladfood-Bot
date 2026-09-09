"""Agente de atendimento (Gemini 3 Flash) que monta pedidos usando a API LAD v1."""
from __future__ import annotations

import json
import os
import uuid
from typing import Any, Dict, List, Tuple

from emergentintegrations.llm.chat import LlmChat, UserMessage

from lib.lad import LadClient, LadError

MODEL_PROVIDER = "gemini"
MODEL_NAME = "gemini-3-flash-preview"

TOOLS: List[Dict[str, Any]] = [
    {"type": "function", "function": {
        "name": "consultar_loja",
        "description": "Consulta dados da loja: se está aberta, horários, formas de pagamento aceitas, pedido mínimo, entrega/retirada.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},
    {"type": "function", "function": {
        "name": "consultar_cardapio",
        "description": "Retorna o cardápio: categorias, produtos, preços, tamanhos e grupos de opcionais com os IDs usados em criar_pedido.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},
    {"type": "function", "function": {
        "name": "cotar_frete",
        "description": "Calcula o valor da entrega para um endereço. Use antes de fechar pedidos DELIVERY.",
        "parameters": {"type": "object", "properties": {
            "endereco": {"type": "string"}, "numero": {"type": "string"},
            "bairro": {"type": "string"}, "cidade": {"type": "string"},
            "estado": {"type": "string"}, "cep": {"type": "string"},
        }, "required": ["bairro", "cidade"]},
    }},
    {"type": "function", "function": {
        "name": "criar_pedido",
        "description": "Cria o pedido na loja. NÃO envie preços — o servidor calcula tudo. Confirme o total com o cliente usando a resposta.",
        "parameters": {"type": "object", "properties": {
            "tipo": {"type": "string", "enum": ["DELIVERY", "RETIRADA"]},
            "cliente": {"type": "object", "properties": {
                "nome": {"type": "string"}, "telefone": {"type": "string"}},
                "required": ["nome", "telefone"]},
            "itens": {"type": "array", "items": {"type": "object", "properties": {
                "idProduto": {"type": "integer"},
                "idTamanho": {"type": "integer"},
                "quantidade": {"type": "number"},
                "observacao": {"type": "string"},
                "opcionais": {"type": "array", "items": {"type": "object", "properties": {
                    "idGrupo": {"type": "integer"},
                    "idsOpcoes": {"type": "array", "items": {"type": "integer"}},
                }, "required": ["idGrupo", "idsOpcoes"]}},
            }, "required": ["idProduto", "quantidade"]}},
            "enderecoEntrega": {"type": "object", "properties": {
                "endereco": {"type": "string"}, "numero": {"type": "string"},
                "bairro": {"type": "string"}, "complemento": {"type": "string"},
                "cidade": {"type": "string"}, "estado": {"type": "string"},
                "cep": {"type": "string"}, "pontoReferencia": {"type": "string"},
            }},
            "pagamento": {"type": "object", "properties": {
                "forma": {"type": "string"}, "trocoPara": {"type": "number"},
                "observacao": {"type": "string"}}, "required": ["forma"]},
            "cupom": {"type": "string"},
            "observacao": {"type": "string"},
        }, "required": ["tipo", "cliente", "itens", "pagamento"]},
    }},
    {"type": "function", "function": {
        "name": "consultar_pedido",
        "description": "Consulta o status atual de um pedido pelo uuid.",
        "parameters": {"type": "object", "properties": {"uuid": {"type": "string"}}, "required": ["uuid"]},
    }},
]

BASE_PROMPT = """Você é o atendente virtual de WhatsApp da loja "{nome_loja}".
Fale em português do Brasil, com mensagens curtas, cordiais e objetivas — estilo WhatsApp.

REGRAS ABSOLUTAS:
- Nunca calcule nem prometa preços por conta própria: use SEMPRE os valores retornados pelas ferramentas.
- Consulte o cardápio antes de sugerir produtos; só ofereça o que existe nele.
- Se o produto tiver tamanhos, pergunte o tamanho antes de adicionar.
- Antes de criar o pedido você precisa de: tipo (entrega ou retirada), nome e telefone do cliente,
  itens, endereço completo (se entrega) e forma de pagamento (use apenas as formas de consultar_loja).
- Antes de chamar criar_pedido, confirme com o cliente o resumo do pedido e espere um "sim".
- Depois de criar_pedido, repita ao cliente os itens e o valorTotal retornado pela ferramenta.
- Se uma ferramenta devolver erro, leia a descrição e corrija exatamente o que ela pede, sem culpar o cliente.
- Nunca invente formas de pagamento genéricas como "cartão": use os rótulos exatos da loja.
{extra}"""

_SESSIONS: Dict[str, LlmChat] = {}


def _new_chat(session_key: str, system_message: str) -> LlmChat:
    key = os.environ.get("EMERGENT_LLM_KEY", "")
    chat = LlmChat(api_key=key, session_id=session_key, system_message=system_message)
    chat = chat.with_model(MODEL_PROVIDER, MODEL_NAME).with_tools(TOOLS, tool_choice="auto")
    return chat


def reset_session(session_key: str) -> None:
    _SESSIONS.pop(session_key, None)


async def _dispatch(lad: LadClient, name: str, args: Dict[str, Any]) -> Tuple[Any, bool]:
    try:
        if name == "consultar_loja":
            return await lad.loja(), True
        if name == "consultar_cardapio":
            return await lad.cardapio(), True
        if name == "cotar_frete":
            return await lad.frete(args), True
        if name == "criar_pedido":
            payload = dict(args)
            payload.setdefault("idempotencyKey", str(uuid.uuid4()))
            return await lad.criar_pedido(payload), True
        if name == "consultar_pedido":
            return await lad.pedido(args.get("uuid", "")), True
    except LadError as exc:
        return {"codigo": exc.status, "titulo": "Erro", "descricao": exc.descricao}, False
    except Exception as exc:  # noqa: BLE001
        return {"codigo": 500, "titulo": "Erro", "descricao": str(exc)}, False
    return {"codigo": 400, "descricao": f"Ferramenta desconhecida: {name}"}, False


RESUMOS = {
    "consultar_loja": "Consultou os dados da loja",
    "consultar_cardapio": "Consultou o cardápio",
    "cotar_frete": "Cotou o frete",
    "criar_pedido": "Criou o pedido",
    "consultar_pedido": "Consultou o pedido",
}


async def run_turn(session_key: str, system_message: str, lad: LadClient, message: str):
    """Executa um turno da conversa. Devolve (texto, traces, pedido_criado|None)."""
    chat = _SESSIONS.get(session_key)
    if chat is None:
        chat = _new_chat(session_key, system_message)
        _SESSIONS[session_key] = chat

    response = await chat.send_message_with_tools(UserMessage(text=message))
    traces: List[Dict[str, Any]] = []
    pedido: Any = None
    guard = 0

    while getattr(response, "tool_calls", None) and guard < 8:
        guard += 1
        for tc in response.tool_calls:
            args = tc.arguments if isinstance(tc.arguments, dict) else json.loads(tc.arguments or "{}")
            result, ok = await _dispatch(lad, tc.name, args)
            if tc.name == "criar_pedido" and ok:
                pedido = result
            traces.append({
                "name": tc.name,
                "ok": ok,
                "resumo": RESUMOS.get(tc.name, tc.name) if ok else str(result.get("descricao", "erro"))[:180],
            })
            chat.add_tool_result(tc.id, json.dumps(result, ensure_ascii=False, default=str))
        response = await chat.send_message_with_tools()

    text = (getattr(response, "content", None) or "").strip()
    if not text:
        text = "Desculpe, não consegui responder agora. Pode repetir?"
    return text, traces, pedido
