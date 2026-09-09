from typing import Any, List

from fastapi import APIRouter, HTTPException

from lib.db import db
from lib.lad import LadClient, LadError
from models.schemas import (
    ConnectionResult,
    OrderRecord,
    Store,
    StoreCreate,
    StoreUpdate,
)

router = APIRouter(prefix="/stores", tags=["stores"])


async def get_store(store_id: str) -> Store:
    doc = await db.stores.find_one({"id": store_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Loja não encontrada")
    doc.pop("_id", None)
    return Store(**doc)


def client_for(store: Store) -> LadClient:
    return LadClient(token=store.token, demo=store.demo or not store.token)


async def _probe(store: Store) -> ConnectionResult:
    try:
        loja = await client_for(store).loja()
    except LadError as exc:
        return ConnectionResult(ok=False, mensagem=f"[{exc.status}] {exc.descricao}")
    return ConnectionResult(
        ok=True,
        mensagem="Modo demonstração ativo" if (store.demo or not store.token) else "Token válido, loja conectada",
        nome_loja=loja.get("nome"),
        aberta_agora=loja.get("abertaAgora"),
    )


@router.get("", response_model=List[Store])
async def list_stores():
    docs = await db.stores.find().sort("created_at", 1).to_list(200)
    for d in docs:
        d.pop("_id", None)
    return [Store(**d) for d in docs]


@router.post("", response_model=Store, status_code=201)
async def create_store(payload: StoreCreate):
    if not payload.nome.strip():
        raise HTTPException(status_code=400, detail="Informe o nome da loja")
    store = Store(**payload.model_dump())
    probe = await _probe(store)
    store.conexao_ok = probe.ok
    store.conexao_msg = probe.mensagem
    await db.stores.insert_one(store.model_dump())
    return store


@router.get("/{store_id}", response_model=Store)
async def read_store(store_id: str):
    return await get_store(store_id)


@router.patch("/{store_id}", response_model=Store)
async def update_store(store_id: str, payload: StoreUpdate):
    store = await get_store(store_id)
    changes = {k: v for k, v in payload.model_dump().items() if v is not None}
    updated = store.model_copy(update=changes)
    probe = await _probe(updated)
    updated.conexao_ok = probe.ok
    updated.conexao_msg = probe.mensagem
    await db.stores.update_one({"id": store_id}, {"$set": updated.model_dump()})
    return updated


@router.delete("/{store_id}", status_code=204)
async def delete_store(store_id: str):
    await get_store(store_id)
    await db.stores.delete_one({"id": store_id})
    await db.chat_messages.delete_many({"store_id": store_id})
    return None


@router.post("/{store_id}/testar", response_model=ConnectionResult)
async def test_connection(store_id: str):
    store = await get_store(store_id)
    probe = await _probe(store)
    await db.stores.update_one(
        {"id": store_id}, {"$set": {"conexao_ok": probe.ok, "conexao_msg": probe.mensagem}}
    )
    return probe


@router.get("/{store_id}/loja")
async def store_info(store_id: str) -> Any:
    store = await get_store(store_id)
    try:
        return await client_for(store).loja()
    except LadError as exc:
        raise HTTPException(status_code=502, detail=exc.descricao) from exc


@router.get("/{store_id}/cardapio")
async def store_menu(store_id: str) -> Any:
    store = await get_store(store_id)
    try:
        return await client_for(store).cardapio()
    except LadError as exc:
        raise HTTPException(status_code=502, detail=exc.descricao) from exc


@router.get("/{store_id}/pedidos", response_model=List[OrderRecord])
async def store_orders(store_id: str):
    await get_store(store_id)
    docs = await db.orders.find({"store_id": store_id}).sort("created_at", -1).to_list(200)
    for d in docs:
        d.pop("_id", None)
    return [OrderRecord(**d) for d in docs]


@router.post("/{store_id}/pedidos/{uuid_}/atualizar", response_model=OrderRecord)
async def refresh_order(store_id: str, uuid_: str):
    store = await get_store(store_id)
    doc = await db.orders.find_one({"store_id": store_id, "id": uuid_})
    if not doc:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    doc.pop("_id", None)
    record = OrderRecord(**doc)
    try:
        pedido = await client_for(store).pedido(uuid_)
    except LadError as exc:
        if record.demo:
            return record
        raise HTTPException(status_code=502, detail=exc.descricao) from exc
    status = pedido.get("status") or {}
    record.status_codigo = status.get("codigo", record.status_codigo)
    record.status_descricao = status.get("descricao", record.status_descricao)
    record.valor_total = pedido.get("valorTotal", record.valor_total)
    record.payload = pedido
    await db.orders.update_one({"id": uuid_}, {"$set": record.model_dump()})
    return record
