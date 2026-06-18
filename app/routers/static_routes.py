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
    StaticRoute,
    StaticRouteActionResult,
    StaticRouteCreate,
    StaticRouteList,
)
from app.services import bgp, static_routes
from app.services.vtysh import VtyshError

router = APIRouter(prefix="/api/v1/routes", tags=["静态路由"])


@router.get(
    "/static",
    response_model=StaticRouteList,
    summary="列出静态路由",
    description="返回运行配置中的静态路由及路由表中已安装的静态路由。",
)
async def list_static_routes(_: str = Depends(verify_api_key)) -> StaticRouteList:
    try:
        configured = static_routes.list_static_routes()
        installed = static_routes.list_static_routes_in_table()
        return StaticRouteList(configured=configured, installed=installed)
    except VtyshError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.get(
    "/static/{prefix:path}",
    response_model=StaticRoute,
    summary="查询指定静态路由",
    description="按目标网段前缀查询已配置的静态路由。",
)
async def get_static_route(
    prefix: str,
    family: Literal["ipv4", "ipv6"] | None = Query(default=None, description="地址族过滤"),
    _: str = Depends(verify_api_key),
) -> StaticRoute:
    route = static_routes.find_static_route(prefix, family)
    if not route:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"未找到静态路由: {prefix}")
    return StaticRoute(**{k: v for k, v in route.items() if k != "raw"})


@router.post(
    "/static",
    response_model=StaticRouteActionResult,
    summary="添加静态路由",
    description=(
        "通过 vtysh 添加 IPv4/IPv6 静态路由。"
        "持久化可设置 JSON 字段 `write_memory: true`，或使用查询参数 `?write_memory=true`。"
    ),
)
async def create_static_route(
    body: StaticRouteCreate,
    write_memory: bool = Query(default=False, description="是否持久化到 frr.conf（与 body 二选一，任一为 true 即生效）"),
    _: str = Depends(verify_api_key),
) -> StaticRouteActionResult:
    persist = body.write_memory or write_memory
    try:
        result = static_routes.add_static_route(
            family=body.family,
            prefix=body.prefix,
            type=body.type,
            nexthop=body.nexthop,
            interface=body.interface,
            distance=body.distance,
            write_memory=persist,
        )
        return StaticRouteActionResult(**result, write_memory=persist)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except VtyshError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.delete(
    "/static",
    response_model=StaticRouteActionResult,
    summary="删除静态路由",
    description="删除指定的静态路由，参数须与添加时一致。",
)
async def remove_static_route(
    body: StaticRouteCreate,
    write_memory: bool = Query(default=False, description="是否持久化到 frr.conf（与 body 二选一，任一为 true 即生效）"),
    _: str = Depends(verify_api_key),
) -> StaticRouteActionResult:
    persist = body.write_memory or write_memory
    try:
        result = static_routes.delete_static_route(
            family=body.family,
            prefix=body.prefix,
            type=body.type,
            nexthop=body.nexthop,
            interface=body.interface,
            distance=body.distance,
            write_memory=persist,
        )
        return StaticRouteActionResult(**result, write_memory=persist)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except VtyshError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
