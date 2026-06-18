from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth import verify_api_key
from app.schemas import (
    ProtocolActionResult,
    RipInstanceCreate,
    RipNetworkBody,
    RipRedistributeBody,
)
from app.services import rip
from app.services.vtysh import VtyshError

router = APIRouter(prefix="/api/v1/rip", tags=["RIP"])


def _handle(exc: Exception) -> None:
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if isinstance(exc, VtyshError):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    raise exc


@router.get("/instance", summary="获取 RIPv2 实例配置")
async def get_instance(_: str = Depends(verify_api_key)) -> dict:
    try:
        return rip.get_instance()
    except VtyshError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post("/instance", response_model=ProtocolActionResult, summary="创建 RIPv2 实例")
async def create_instance(
    body: RipInstanceCreate,
    _: str = Depends(verify_api_key),
) -> ProtocolActionResult:
    try:
        return ProtocolActionResult(**rip.create_instance(
            version=body.version, write_memory=body.write_memory
        ))
    except (ValueError, VtyshError) as exc:
        _handle(exc)


@router.delete("/instance", response_model=ProtocolActionResult, summary="删除 RIPv2 实例")
async def delete_instance(
    write_memory: bool = Query(default=False),
    _: str = Depends(verify_api_key),
) -> ProtocolActionResult:
    try:
        return ProtocolActionResult(**rip.delete_instance(write_memory=write_memory))
    except (ValueError, VtyshError) as exc:
        _handle(exc)


@router.get("/status", summary="获取 RIPv2 运行状态")
async def get_status(_: str = Depends(verify_api_key)) -> dict:
    try:
        return rip.get_status()
    except VtyshError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post("/networks", response_model=ProtocolActionResult, summary="添加 RIP 网络")
async def add_network(body: RipNetworkBody, _: str = Depends(verify_api_key)) -> ProtocolActionResult:
    try:
        return ProtocolActionResult(**rip.add_network(body.prefix, write_memory=body.write_memory))
    except (ValueError, VtyshError) as exc:
        _handle(exc)


@router.delete("/networks", response_model=ProtocolActionResult, summary="删除 RIP 网络")
async def delete_network(body: RipNetworkBody, _: str = Depends(verify_api_key)) -> ProtocolActionResult:
    try:
        return ProtocolActionResult(**rip.delete_network(body.prefix, write_memory=body.write_memory))
    except (ValueError, VtyshError) as exc:
        _handle(exc)


@router.put("/redistribute", response_model=ProtocolActionResult, summary="配置 RIP 重分发")
async def set_redistribute(
    body: RipRedistributeBody,
    _: str = Depends(verify_api_key),
) -> ProtocolActionResult:
    try:
        return ProtocolActionResult(**rip.set_redistribute(
            body.protocol, enabled=body.enabled, write_memory=body.write_memory
        ))
    except (ValueError, VtyshError) as exc:
        _handle(exc)
