from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth import verify_api_key
from app.schemas import (
    Ospf6InstanceCreate,
    Ospf6InterfaceBody,
    Ospf6RedistributeBody,
    ProtocolActionResult,
)
from app.services import ospf6, ripng
from app.services.vtysh import VtyshError

router = APIRouter(prefix="/api/v1/ospf6", tags=["OSPFv6"])


def _handle(exc: Exception) -> None:
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if isinstance(exc, VtyshError):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    raise exc


@router.get("/instance", summary="获取 OSPFv3 实例配置")
async def get_instance(_: str = Depends(verify_api_key)) -> dict:
    try:
        return ospf6.get_instance()
    except VtyshError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post("/instance", response_model=ProtocolActionResult, summary="创建 OSPFv3 实例")
async def create_instance(
    body: Ospf6InstanceCreate,
    _: str = Depends(verify_api_key),
) -> ProtocolActionResult:
    try:
        return ProtocolActionResult(**ospf6.create_instance(
            router_id=body.router_id, write_memory=body.write_memory
        ))
    except (ValueError, VtyshError) as exc:
        _handle(exc)


@router.delete("/instance", response_model=ProtocolActionResult, summary="删除 OSPFv3 实例")
async def delete_instance(
    write_memory: bool = Query(default=False),
    _: str = Depends(verify_api_key),
) -> ProtocolActionResult:
    try:
        return ProtocolActionResult(**ospf6.delete_instance(write_memory=write_memory))
    except (ValueError, VtyshError) as exc:
        _handle(exc)


@router.get("/summary", summary="获取 OSPFv3 运行摘要")
async def get_summary(_: str = Depends(verify_api_key)) -> dict:
    try:
        return ospf6.get_summary()
    except VtyshError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.put(
    "/interfaces/{interface}",
    response_model=ProtocolActionResult,
    summary="配置接口加入 OSPFv3",
)
async def set_interface(
    interface: str,
    body: Ospf6InterfaceBody,
    _: str = Depends(verify_api_key),
) -> ProtocolActionResult:
    try:
        return ProtocolActionResult(**ospf6.set_interface(
            interface, body.area, write_memory=body.write_memory
        ))
    except (ValueError, VtyshError) as exc:
        _handle(exc)


@router.delete(
    "/interfaces/{interface}",
    response_model=ProtocolActionResult,
    summary="从 OSPFv3 移除接口",
)
async def delete_interface(
    interface: str,
    area: str = Query(..., description="OSPFv3 区域"),
    write_memory: bool = Query(default=False),
    _: str = Depends(verify_api_key),
) -> ProtocolActionResult:
    try:
        return ProtocolActionResult(**ospf6.delete_interface(
            interface, area, write_memory=write_memory
        ))
    except (ValueError, VtyshError) as exc:
        _handle(exc)


@router.put("/redistribute", response_model=ProtocolActionResult, summary="配置 OSPFv3 重分发")
async def set_redistribute(
    body: Ospf6RedistributeBody,
    _: str = Depends(verify_api_key),
) -> ProtocolActionResult:
    try:
        return ProtocolActionResult(**ospf6.set_redistribute(
            body.protocol, enabled=body.enabled, write_memory=body.write_memory
        ))
    except (ValueError, VtyshError) as exc:
        _handle(exc)
