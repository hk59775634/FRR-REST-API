from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth import verify_api_key
from app.schemas import (
    OspfInstanceCreate,
    OspfInstanceUpdate,
    OspfInterfaceBody,
    OspfNetworkBody,
    OspfRedistributeBody,
    ProtocolActionResult,
)
from app.services import ospf
from app.services.vtysh import VtyshError

router = APIRouter(prefix="/api/v1/ospf", tags=["OSPF"])


def _handle(exc: Exception) -> None:
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if isinstance(exc, VtyshError):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    raise exc


@router.get("/instance", summary="获取 OSPFv2 实例配置")
async def get_instance(
    vrf: str | None = Query(default=None, description="VRF 名称"),
    _: str = Depends(verify_api_key),
) -> dict:
    try:
        return ospf.get_instance(vrf)
    except VtyshError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post("/instance", response_model=ProtocolActionResult, summary="创建 OSPFv2 实例")
async def create_instance(
    body: OspfInstanceCreate,
    _: str = Depends(verify_api_key),
) -> ProtocolActionResult:
    try:
        return ProtocolActionResult(**ospf.create_instance(
            router_id=body.router_id, vrf=body.vrf, write_memory=body.write_memory
        ))
    except (ValueError, VtyshError) as exc:
        _handle(exc)


@router.patch("/instance", response_model=ProtocolActionResult, summary="更新 OSPFv2 实例")
async def update_instance(
    body: OspfInstanceUpdate,
    _: str = Depends(verify_api_key),
) -> ProtocolActionResult:
    try:
        return ProtocolActionResult(**ospf.update_instance(
            router_id=body.router_id, vrf=body.vrf, write_memory=body.write_memory
        ))
    except (ValueError, VtyshError) as exc:
        _handle(exc)


@router.delete("/instance", response_model=ProtocolActionResult, summary="删除 OSPFv2 实例")
async def delete_instance(
    vrf: str | None = Query(default=None),
    write_memory: bool = Query(default=False),
    _: str = Depends(verify_api_key),
) -> ProtocolActionResult:
    try:
        return ProtocolActionResult(**ospf.delete_instance(vrf=vrf, write_memory=write_memory))
    except (ValueError, VtyshError) as exc:
        _handle(exc)


@router.get("/summary", summary="获取 OSPFv2 运行摘要")
async def get_summary(_: str = Depends(verify_api_key)) -> dict:
    try:
        return ospf.get_summary()
    except VtyshError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.get("/neighbors", summary="获取 OSPFv2 邻居")
async def get_neighbors(_: str = Depends(verify_api_key)) -> dict:
    try:
        return ospf.get_neighbors()
    except VtyshError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.get("/routes", summary="获取 OSPFv2 路由表")
async def get_routes(_: str = Depends(verify_api_key)) -> dict:
    try:
        return ospf.get_routes()
    except VtyshError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post("/networks", response_model=ProtocolActionResult, summary="添加 OSPF 网络")
async def add_network(body: OspfNetworkBody, _: str = Depends(verify_api_key)) -> ProtocolActionResult:
    try:
        return ProtocolActionResult(**ospf.add_network(
            body.prefix, body.area, vrf=body.vrf, write_memory=body.write_memory
        ))
    except (ValueError, VtyshError) as exc:
        _handle(exc)


@router.delete("/networks", response_model=ProtocolActionResult, summary="删除 OSPF 网络")
async def delete_network(body: OspfNetworkBody, _: str = Depends(verify_api_key)) -> ProtocolActionResult:
    try:
        return ProtocolActionResult(**ospf.delete_network(
            body.prefix, body.area, vrf=body.vrf, write_memory=body.write_memory
        ))
    except (ValueError, VtyshError) as exc:
        _handle(exc)


@router.put("/redistribute", response_model=ProtocolActionResult, summary="配置 OSPF 重分发")
async def set_redistribute(
    body: OspfRedistributeBody,
    _: str = Depends(verify_api_key),
) -> ProtocolActionResult:
    try:
        return ProtocolActionResult(**ospf.set_redistribute(
            body.protocol,
            enabled=body.enabled,
            metric_type=body.metric_type,
            vrf=body.vrf,
            write_memory=body.write_memory,
        ))
    except (ValueError, VtyshError) as exc:
        _handle(exc)


@router.put(
    "/interfaces/{interface}",
    response_model=ProtocolActionResult,
    summary="配置接口加入 OSPF",
)
async def set_interface(
    interface: str,
    body: OspfInterfaceBody,
    _: str = Depends(verify_api_key),
) -> ProtocolActionResult:
    try:
        return ProtocolActionResult(**ospf.set_interface_area(
            interface,
            body.area,
            network_type=body.network_type,
            write_memory=body.write_memory,
        ))
    except (ValueError, VtyshError) as exc:
        _handle(exc)


@router.delete(
    "/interfaces/{interface}",
    response_model=ProtocolActionResult,
    summary="从 OSPF 移除接口",
)
async def delete_interface(
    interface: str,
    area: str = Query(..., description="OSPF 区域"),
    write_memory: bool = Query(default=False),
    _: str = Depends(verify_api_key),
) -> ProtocolActionResult:
    try:
        return ProtocolActionResult(**ospf.delete_interface_area(
            interface, area, write_memory=write_memory
        ))
    except (ValueError, VtyshError) as exc:
        _handle(exc)
