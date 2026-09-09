from typing import List

from fastapi import APIRouter, HTTPException

from lib import bot
from lib.db import db
from models.schemas import ChatMessage, ChatRequest, ChatResponse, OrderRecord, ToolTrace
from routers.stores import client_for, get_store

router = APIRouter(prefix="/chat", tags=["chat"])


def _session_key(store_id: str, session_id: str) -> str:
    return f"{store_id}:{session_id}"


@router.get("/{store_id}/{session_id}", response_model=List[ChatMessage])
async def history(store_id: str, session_id: str):
    docs = await db.chat_messages.find(
        {"store_id": store_id, "session_id": session_id}
    ).sort("created_at", 1).to_list(500)
    for d in docs:
        d.pop("_id", None)
    return [ChatMessage(**d) for d in docs]


@router.delete("/{store_id}/{session_id}", status_code=204)
async def reset(store_id: str, session_id: str):
    await db.chat_messages.delete_many({"store_id": store_id, "session_id": session_id})
    bot.reset_session(_session_key(store_id, session_id))
    return None


@router.post("/{store_id}", response_model=ChatResponse)
async def send(store_id: str, payload: ChatRequest):
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Mensagem vazia")
    store = await get_store(store_id)
    lad = client_for(store)

    system_message = bot.BASE_PROMPT.format(
        nome_loja=store.nome,
        extra=f"\nInstruções extras do lojista: {store.bot_prompt}" if store.bot_prompt.strip() else "",
    )
    key = _session_key(store_id, payload.session_id)

    user_msg = ChatMessage(session_id=payload.session_id, store_id=store_id,
                           role="user", text=payload.message.strip())
    await db.chat_messages.insert_one(user_msg.model_dump())

    try:
        text, traces, pedido = await bot.run_turn(key, system_message, lad, payload.message.strip())
    except Exception as exc:  # noqa: BLE001
        detalhe = str(exc)
        if "Budget has been exceeded" in detalhe or "RateLimitError" in detalhe:
            text = ("Estou temporariamente fora do ar: os créditos da chave de IA (Emergent LLM Key) "
                    "acabaram. Recarregue os créditos no painel da Emergent para o bot voltar a atender.")
        else:
            text = f"Não consegui responder agora ({detalhe[:160]}). Tente novamente em instantes."
        traces = [{"name": "erro_ia", "ok": False, "resumo": detalhe[:180]}]
        pedido = None

    bot_msg = ChatMessage(session_id=payload.session_id, store_id=store_id, role="bot",
                          text=text, tools=[ToolTrace(**t) for t in traces])
    await db.chat_messages.insert_one(bot_msg.model_dump())

    order_uuid = None
    if pedido and pedido.get("uuid"):
        order_uuid = pedido["uuid"]
        status = pedido.get("status") or {}
        cliente = pedido.get("cliente") or {}
        record = OrderRecord(
            id=order_uuid, store_id=store_id, session_id=payload.session_id,
            cliente_nome=cliente.get("nome", ""), cliente_telefone=cliente.get("telefone", ""),
            tipo=pedido.get("tipo", "DELIVERY"),
            status_codigo=status.get("codigo", "E"),
            status_descricao=status.get("descricao", "Pendente"),
            valor_total=float(pedido.get("valorTotal") or 0),
            data_pedido=str(pedido.get("dataPedido") or ""),
            demo=store.demo or not store.token,
            payload=pedido,
        )
        await db.orders.update_one({"id": order_uuid}, {"$set": record.model_dump()}, upsert=True)

    return ChatResponse(reply=text, tools=[ToolTrace(**t) for t in traces], order_uuid=order_uuid)
