from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth import verify_api_key
from app.schemas import (
    BgpActionResult,
    BgpInstance,
    BgpNeighborCreate,
    BgpNeighborList,
    BgpNeighborUpdate,
    BgpNetworkCreate,
    BgpRouteList,
)
from app.services import bgp
from app.services.vtysh import VtyshError

router = APIRouter(prefix="/api/v1/bgp", tags=["BGP"])


@router.get(
    "/instance",
    response_model=BgpInstance,
    summary="获取 BGP 实例配置",
    description="返回本地 AS、已配置邻居、宣告网络及 BGP 配置命令。",
)
async def get_instance(_: str = Depends(verify_api_key)) -> BgpInstance:
    try:
        return BgpInstance(**bgp.get_bgp_instance())
    except VtyshError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.get(
    "/summary",
    summary="获取 BGP 摘要",
    description="等同于 `show bgp summary`，返回 Router ID、本地 AS 及邻居状态表。",
)
async def get_summary(_: str = Depends(verify_api_key)) -> dict:
    try:
        return bgp.get_bgp_summary()
    except VtyshError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.get(
    "/neighbors",
    response_model=BgpNeighborList,
    summary="列出 BGP 邻居",
    description="合并运行配置与 `show bgp summary` 状态，返回完整邻居信息。",
)
async def list_neighbors(_: str = Depends(verify_api_key)) -> BgpNeighborList:
    try:
        neighbors = bgp.list_bgp_neighbors()
        return BgpNeighborList(neighbors=neighbors, total=len(neighbors))
    except VtyshError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.get(
    "/neighbors/{address}",
    summary="获取 BGP 邻居详情",
    description="返回指定邻居的配置信息与 `show bgp neighbors` 运行详情。",
)
async def get_neighbor(address: str, _: str = Depends(verify_api_key)) -> dict:
    try:
        return bgp.get_bgp_neighbor(address)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except VtyshError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post(
    "/neighbors",
    response_model=BgpActionResult,
    summary="添加 BGP 邻居",
    description="在现有 BGP 实例下添加邻居，配置 remote-as 及可选描述。",
)
async def create_neighbor(
    body: BgpNeighborCreate,
    _: str = Depends(verify_api_key),
) -> BgpActionResult:
    try:
        result = bgp.add_bgp_neighbor(
            address=body.address,
            remote_as=body.remote_as,
            description=body.description,
            update_source=body.update_source,
            write_memory=body.write_memory,
        )
        return BgpActionResult(message=result["message"])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except VtyshError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.patch(
    "/neighbors/{address}",
    response_model=BgpActionResult,
    summary="更新 BGP 邻居",
    description="更新邻居描述、update-source 等属性。",
)
async def update_neighbor(
    address: str,
    body: BgpNeighborUpdate,
    _: str = Depends(verify_api_key),
) -> BgpActionResult:
    try:
        result = bgp.update_bgp_neighbor(
            address,
            description=body.description,
            update_source=body.update_source,
            write_memory=body.write_memory,
        )
        return BgpActionResult(message=result["message"])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except VtyshError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.delete(
    "/neighbors/{address}",
    response_model=BgpActionResult,
    summary="删除 BGP 邻居",
    description="从 BGP 实例中移除指定邻居。",
)
async def delete_neighbor(
    address: str,
    write_memory: bool = Query(default=False, description="是否持久化到 frr.conf"),
    _: str = Depends(verify_api_key),
) -> BgpActionResult:
    try:
        result = bgp.delete_bgp_neighbor(address, write_memory=write_memory)
        return BgpActionResult(message=result["message"])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except VtyshError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get(
    "/routes",
    response_model=BgpRouteList,
    summary="获取 BGP 路由表",
    description="查询 BGP IPv4 或 IPv6 单播路由表。",
)
async def list_routes(
    afi: Literal["ipv4", "ipv6"] = Query(default="ipv4", description="地址族"),
    _: str = Depends(verify_api_key),
) -> BgpRouteList:
    try:
        routes = bgp.get_bgp_routes(afi=afi)
        return BgpRouteList(afi=afi, routes=routes, total=len(routes))
    except VtyshError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post(
    "/networks",
    response_model=BgpActionResult,
    summary="宣告 BGP 网络",
    description="在 BGP 实例中添加 network 宣告。",
)
async def advertise_network(
    body: BgpNetworkCreate,
    _: str = Depends(verify_api_key),
) -> BgpActionResult:
    try:
        result = bgp.add_bgp_network(body.network, write_memory=body.write_memory)
        return BgpActionResult(message=result["message"])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except VtyshError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.delete(
    "/networks",
    response_model=BgpActionResult,
    summary="撤销 BGP 网络宣告",
    description="从 BGP 实例中移除 network 宣告。",
)
async def withdraw_network(
    body: BgpNetworkCreate,
    _: str = Depends(verify_api_key),
) -> BgpActionResult:
    try:
        result = bgp.delete_bgp_network(body.network, write_memory=body.write_memory)
        return BgpActionResult(message=result["message"])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except VtyshError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
