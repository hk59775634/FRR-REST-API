from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth import verify_api_key
from app.schemas import (
    ProtocolActionResult,
    RipngInterfaceBody,
    RipngRedistributeBody,
    WriteMemoryOption,
)
from app.services import ripng
from app.services.vtysh import VtyshError

router = APIRouter(prefix="/api/v1/ripng", tags=["RIPng"])


def _handle(exc: Exception) -> None:
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if isinstance(exc, VtyshError):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    raise exc


@router.get("/instance", summary="获取 RIPng 实例配置")
async def get_instance(_: str = Depends(verify_api_key)) -> dict:
    try:
        return ripng.get_instance()
    except VtyshError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post("/instance", response_model=ProtocolActionResult, summary="创建 RIPng 实例")
async def create_instance(
    body: WriteMemoryOption,
    _: str = Depends(verify_api_key),
) -> ProtocolActionResult:
    try:
        return ProtocolActionResult(**ripng.create_instance(write_memory=body.write_memory))
    except (ValueError, VtyshError) as exc:
        _handle(exc)


@router.delete("/instance", response_model=ProtocolActionResult, summary="删除 RIPng 实例")
async def delete_instance(
    write_memory: bool = Query(default=False),
    _: str = Depends(verify_api_key),
) -> ProtocolActionResult:
    try:
        return ProtocolActionResult(**ripng.delete_instance(write_memory=write_memory))
    except (ValueError, VtyshError) as exc:
        _handle(exc)


@router.get("/status", summary="获取 RIPng 运行状态")
async def get_status(_: str = Depends(verify_api_key)) -> dict:
    try:
        return ripng.get_status()
    except VtyshError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post("/interfaces", response_model=ProtocolActionResult, summary="添加 RIPng 接口")
async def add_interface(body: RipngInterfaceBody, _: str = Depends(verify_api_key)) -> ProtocolActionResult:
    try:
        return ProtocolActionResult(**ripng.add_interface(
            body.interface, write_memory=body.write_memory
        ))
    except (ValueError, VtyshError) as exc:
        _handle(exc)


@router.delete("/interfaces", response_model=ProtocolActionResult, summary="删除 RIPng 接口")
async def delete_interface(body: RipngInterfaceBody, _: str = Depends(verify_api_key)) -> ProtocolActionResult:
    try:
        return ProtocolActionResult(**ripng.delete_interface(
            body.interface, write_memory=body.write_memory
        ))
    except (ValueError, VtyshError) as exc:
        _handle(exc)


@router.put("/redistribute", response_model=ProtocolActionResult, summary="配置 RIPng 重分发")
async def set_redistribute(
    body: RipngRedistributeBody,
    _: str = Depends(verify_api_key),
) -> ProtocolActionResult:
    try:
        return ProtocolActionResult(**ripng.set_redistribute(
            body.protocol, enabled=body.enabled, write_memory=body.write_memory
        ))
    except (ValueError, VtyshError) as exc:
        _handle(exc)
