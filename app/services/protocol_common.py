import re
from typing import Any

from app.services.daemons import is_daemon_running
from app.services.vtysh import VtyshError, run_vtysh, run_vtysh_commands


def require_daemon(daemon: str) -> None:
    if not is_daemon_running(daemon):
        raise ValueError(
            f"{daemon} 未运行，请先通过 PUT /api/v1/daemons/{daemon} 启用并重启 FRR"
        )


def safe_show(command: str, daemon: str) -> dict[str, Any]:
    try:
        raw = run_vtysh(command)
        return {"running": True, "raw": raw.strip()}
    except VtyshError as exc:
        combined = f"{exc} {exc.stdout} {exc.stderr}".lower()
        if "not running" in combined:
            return {
                "running": False,
                "message": f"{daemon} 守护进程未运行，请先通过 /api/v1/daemons 启用",
            }
        raise


def get_router_block(header_prefix: str) -> tuple[str | None, list[str]]:
    """返回 (完整 router 行, 块内命令列表)。"""
    raw = run_vtysh("show running-config")
    header: str | None = None
    commands: list[str] = []
    in_block = False

    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.startswith(header_prefix):
            header = stripped
            in_block = True
            continue
        if in_block:
            if stripped in ("exit", "!", "end"):
                break
            if stripped:
                commands.append(stripped)
    return header, commands


def apply_commands(commands: list[str], *, write_memory: bool = False) -> None:
    run_vtysh_commands(commands, write_memory=write_memory)


def action_result(message: str, *, write_memory: bool = False) -> dict[str, Any]:
    return {
        "success": True,
        "message": message + ("，已写入 frr.conf" if write_memory else ""),
        "write_memory": write_memory,
    }


def parse_network_area(cmd: str) -> dict[str, str] | None:
    match = re.match(r"network (\S+) area (\S+)", cmd)
    if match:
        return {"prefix": match.group(1), "area": match.group(2)}
    return None
