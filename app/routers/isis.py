from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth import verify_api_key
from app.schemas import (
    IsisInstanceCreate,
    IsisInstanceUpdate,
    IsisRedistributeBody,
    ProtocolActionResult,
    WriteMemoryOption,
)
from app.services import isis
from app.services.vtysh import VtyshError

router = APIRouter(prefix="/api/v1/isis", tags=["IS-IS"])


def _handle(exc: Exception) -> None:
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if isinstance(exc, VtyshError):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    raise exc


@router.get("/instance", summary="获取 IS-IS 实例配置")
async def get_instance(_: str = Depends(verify_api_key)) -> dict:
    try:
        return isis.get_instance()
    except VtyshError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post("/instance", response_model=ProtocolActionResult, summary="创建 IS-IS 实例")
async def create_instance(
    body: IsisInstanceCreate,
    _: str = Depends(verify_api_key),
) -> ProtocolActionResult:
    try:
        return ProtocolActionResult(**isis.create_instance(
            body.tag,
            net=body.net,
            is_type=body.is_type,
            write_memory=body.write_memory,
        ))
    except (ValueError, VtyshError) as exc:
        _handle(exc)


@router.patch("/instance", response_model=ProtocolActionResult, summary="更新 IS-IS 实例")
async def update_instance(
    body: IsisInstanceUpdate,
    _: str = Depends(verify_api_key),
) -> ProtocolActionResult:
    try:
        return ProtocolActionResult(**isis.update_instance(
            net=body.net,
            is_type=body.is_type,
            write_memory=body.write_memory,
        ))
    except (ValueError, VtyshError) as exc:
        _handle(exc)


@router.delete("/instance", response_model=ProtocolActionResult, summary="删除 IS-IS 实例")
async def delete_instance(
    write_memory: bool = Query(default=False),
    _: str = Depends(verify_api_key),
) -> ProtocolActionResult:
    try:
        return ProtocolActionResult(**isis.delete_instance(write_memory=write_memory))
    except (ValueError, VtyshError) as exc:
        _handle(exc)


@router.get("/summary", summary="获取 IS-IS 运行摘要")
async def get_summary(_: str = Depends(verify_api_key)) -> dict:
    try:
        return isis.get_summary()
    except VtyshError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.get("/neighbors", summary="获取 IS-IS 邻居")
async def get_neighbors(_: str = Depends(verify_api_key)) -> dict:
    try:
        return isis.get_neighbors()
    except VtyshError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.put(
    "/interfaces/{interface}",
    response_model=ProtocolActionResult,
    summary="配置接口加入 IS-IS",
)
async def set_interface(
    interface: str,
    body: WriteMemoryOption,
    _: str = Depends(verify_api_key),
) -> ProtocolActionResult:
    try:
        return ProtocolActionResult(**isis.set_interface(
            interface, write_memory=body.write_memory
        ))
    except (ValueError, VtyshError) as exc:
        _handle(exc)


@router.delete(
    "/interfaces/{interface}",
    response_model=ProtocolActionResult,
    summary="从 IS-IS 移除接口",
)
async def delete_interface(
    interface: str,
    write_memory: bool = Query(default=False),
    _: str = Depends(verify_api_key),
) -> ProtocolActionResult:
    try:
        return ProtocolActionResult(**isis.delete_interface(
            interface, write_memory=write_memory
        ))
    except (ValueError, VtyshError) as exc:
        _handle(exc)


@router.put("/redistribute", response_model=ProtocolActionResult, summary="配置 IS-IS 重分发")
async def set_redistribute(
    body: IsisRedistributeBody,
    _: str = Depends(verify_api_key),
) -> ProtocolActionResult:
    try:
        return ProtocolActionResult(**isis.set_redistribute(
            body.protocol, enabled=body.enabled, write_memory=body.write_memory
        ))
    except (ValueError, VtyshError) as exc:
        _handle(exc)
