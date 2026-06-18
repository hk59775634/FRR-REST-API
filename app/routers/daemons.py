from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import verify_api_key
from app.schemas import DaemonActionResult, DaemonList, DaemonStatus, DaemonToggle
from app.services import daemons
from app.services.daemons import DaemonsError

router = APIRouter(prefix="/api/v1/daemons", tags=["动态路由开关"])


@router.get(
    "",
    response_model=DaemonList,
    summary="列出所有动态路由守护进程",
    description="读取 /etc/frr/daemons，返回各协议启用状态与进程运行情况。",
)
async def list_daemons(_: str = Depends(verify_api_key)) -> DaemonList:
    try:
        items = daemons.list_daemons()
        service = daemons.get_frr_service_status()
        return DaemonList(
            daemons=[DaemonStatus(**d) for d in items],
            frr_service=service,
        )
    except DaemonsError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.get(
    "/{name}",
    response_model=DaemonStatus,
    summary="查询单个守护进程状态",
    description="查询指定守护进程（如 bgpd、ospfd）的启用与运行状态。",
)
async def get_daemon(name: str, _: str = Depends(verify_api_key)) -> DaemonStatus:
    try:
        item = daemons.get_daemon(name)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"未找到: {name}")
        return DaemonStatus(**item)
    except DaemonsError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.put(
    "/{name}",
    response_model=DaemonActionResult,
    summary="启用或禁用动态路由守护进程",
    description=(
        "修改 /etc/frr/daemons 中对应项（yes/no），可选重启 FRR。"
        "等效于手动编辑 daemons 文件后执行 systemctl restart frr。"
    ),
)
async def set_daemon(
    name: str,
    body: DaemonToggle,
    _: str = Depends(verify_api_key),
) -> DaemonActionResult:
    try:
        result = daemons.set_daemon_enabled(
            name,
            enabled=body.enabled,
            restart=body.restart,
        )
        return DaemonActionResult(**result)
    except DaemonsError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/frr/restart",
    summary="重启 FRR 服务",
    description="执行 frrinit.sh restart，使 daemons 变更或配置生效。",
)
async def restart_frr(_: str = Depends(verify_api_key)) -> dict:
    try:
        return daemons.restart_frr()
    except DaemonsError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
