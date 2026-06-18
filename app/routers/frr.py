from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import verify_api_key
from app.schemas import (
    ConfigContent,
    ConfigFile,
    FrrStatus,
    ReloadResult,
    RunningConfig,
)
from app.services import frr_reload

router = APIRouter(prefix="/api/v1", tags=["FRR 配置管理"])


@router.get(
    "/status",
    response_model=FrrStatus,
    summary="获取 FRR 运行状态",
    description="通过 vtysh 查询 FRR 版本，判断守护进程是否可用。",
)
async def get_status(_: str = Depends(verify_api_key)) -> FrrStatus:
    try:
        version = frr_reload.run_vtysh("show version")
        return FrrStatus(version=version.strip(), running=True)
    except frr_reload.FrrReloadError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"FRR 服务不可用: {exc}",
        ) from exc


@router.get(
    "/running-config",
    response_model=RunningConfig,
    summary="获取当前运行配置",
    description="执行 `vtysh -c 'show running-config'`，返回 FRR 当前内存中的运行配置。",
)
async def get_running_config(_: str = Depends(verify_api_key)) -> RunningConfig:
    try:
        raw = frr_reload.run_vtysh("show running-config")
        parsed = frr_reload.parse_running_config(raw)
        return RunningConfig(**parsed)
    except frr_reload.FrrReloadError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"获取运行配置失败: {exc.stderr or exc}",
        ) from exc


@router.get(
    "/config",
    response_model=ConfigFile,
    summary="读取 frr.conf 配置文件",
    description="读取磁盘上的 FRR 主配置文件（默认 /etc/frr/frr.conf）。",
)
async def get_config_file(_: str = Depends(verify_api_key)) -> ConfigFile:
    try:
        content = frr_reload.read_frr_conf()
        from app.config import settings

        parsed = frr_reload.parse_running_config(content)
        return ConfigFile(path=settings.frr_conf_path, content=content, **parsed)
    except frr_reload.FrrReloadError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/reload/test",
    response_model=ReloadResult,
    summary="预览配置变更（dry-run）",
    description=(
        "将提交的配置与当前运行配置对比，调用 `frr-reload.py --test` 输出将要执行的变更，"
        "**不会**实际修改运行配置。建议在应用前先调用此接口。"
    ),
)
async def test_reload(
    body: ConfigContent,
    _: str = Depends(verify_api_key),
) -> ReloadResult:
    backup_path = None
    if body.save_to_file:
        backup_path = frr_reload.write_frr_conf(body.content, backup=body.backup)

    result = frr_reload.run_frr_reload(body.content, apply=False)
    return ReloadResult(**result, backup_path=backup_path)


@router.post(
    "/reload/apply",
    response_model=ReloadResult,
    summary="应用配置变更",
    description=(
        "将提交的配置与当前运行配置对比，调用 `frr-reload.py --reload` 动态应用差异。"
        "此操作会**直接修改** FRR 运行配置，请谨慎使用。"
    ),
)
async def apply_reload(
    body: ConfigContent,
    _: str = Depends(verify_api_key),
) -> ReloadResult:
    backup_path = None
    if body.save_to_file:
        backup_path = frr_reload.write_frr_conf(body.content, backup=body.backup)

    result = frr_reload.run_frr_reload(body.content, apply=True)
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "配置重载失败",
                "stdout": result["stdout"],
                "stderr": result["stderr"],
                "returncode": result["returncode"],
            },
        )
    return ReloadResult(**result, backup_path=backup_path)
