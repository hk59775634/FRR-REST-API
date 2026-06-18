import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import settings
from app.services.daemon_registry import ALWAYS_ON_DAEMONS, DAEMON_REGISTRY


class DaemonsError(Exception):
    pass


def _daemons_path() -> Path:
    return Path(settings.frr_daemons_path)


def _backup_daemons() -> str:
    path = _daemons_path()
    backup = path.with_suffix(f".bak.{datetime.now().strftime('%Y%m%d%H%M%S')}")
    shutil.copy2(path, backup)
    return str(backup)


def read_daemons_file() -> str:
    path = _daemons_path()
    if not path.exists():
        raise DaemonsError(f"daemons 文件不存在: {path}")
    return path.read_text(encoding="utf-8")


def parse_daemon_flags(content: str) -> dict[str, bool]:
    flags: dict[str, bool] = {}
    for line in content.splitlines():
        match = re.match(r"^([a-z0-9]+d)=(yes|no)\s*$", line.strip())
        if match:
            flags[match.group(1)] = match.group(2) == "yes"
    return flags


def is_daemon_running(daemon: str) -> bool:
    result = subprocess.run(
        ["pgrep", "-x", daemon],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def list_daemons() -> list[dict[str, Any]]:
    content = read_daemons_file()
    flags = parse_daemon_flags(content)
    items: list[dict[str, Any]] = []

    for name, meta in DAEMON_REGISTRY.items():
        enabled = flags.get(name, False)
        items.append(
            {
                "daemon": name,
                "protocol": meta["protocol"],
                "name_zh": meta["name_zh"],
                "description": meta["description"],
                "enabled": enabled,
                "running": is_daemon_running(name) if enabled else False,
                "manageable": True,
                "api_prefix": meta.get("api_prefix"),
            }
        )

    for name in sorted(ALWAYS_ON_DAEMONS):
        items.append(
            {
                "daemon": name,
                "protocol": name,
                "name_zh": name,
                "description": "FRR 核心守护进程（始终运行）",
                "enabled": True,
                "running": is_daemon_running(name),
                "manageable": False,
                "api_prefix": None,
            }
        )

    return items


def get_daemon(name: str) -> dict[str, Any]:
    if name in ALWAYS_ON_DAEMONS:
        return next((d for d in list_daemons() if d["daemon"] == name), {})
    if name not in DAEMON_REGISTRY:
        raise DaemonsError(f"不支持的守护进程: {name}")
    return next((d for d in list_daemons() if d["daemon"] == name), {})


def set_daemon_enabled(
    name: str,
    *,
    enabled: bool,
    restart: bool = True,
) -> dict[str, Any]:
    if name in ALWAYS_ON_DAEMONS:
        raise DaemonsError(f"{name} 是核心守护进程，不能通过 API 开关")
    if name not in DAEMON_REGISTRY:
        raise DaemonsError(f"不支持的守护进程: {name}")

    path = _daemons_path()
    content = read_daemons_file()
    pattern = re.compile(rf"^({re.escape(name)})=(yes|no)\s*$", re.MULTILINE)
    if not pattern.search(content):
        raise DaemonsError(f"daemons 文件中未找到 {name} 配置项")

    new_value = "yes" if enabled else "no"
    new_content = pattern.sub(f"{name}={new_value}", content, count=1)
    if new_content == content and ((enabled and f"{name}=yes" in content) or (not enabled and f"{name}=no" in content)):
        pass  # already in desired state

    backup = _backup_daemons()
    path.write_text(new_content, encoding="utf-8")

    result: dict[str, Any] = {
        "daemon": name,
        "enabled": enabled,
        "backup_path": backup,
        "restarted": False,
        "message": f"{name} 已设置为 {'启用' if enabled else '禁用'}",
    }

    if restart:
        restart_frr()
        result["restarted"] = True
        result["message"] += "，FRR 已重启"

    result["running"] = is_daemon_running(name) if enabled else False
    return result


def restart_frr() -> dict[str, Any]:
    result = subprocess.run(
        ["/usr/lib/frr/frrinit.sh", "restart"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise DaemonsError(
            f"FRR 重启失败: {(result.stdout + result.stderr).strip()}"
        )
    return {
        "message": "FRR 服务已重启",
        "stdout": result.stdout.strip(),
    }


def get_frr_service_status() -> dict[str, Any]:
    result = subprocess.run(
        ["systemctl", "is-active", "frr"],
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "service": "frr",
        "active": result.stdout.strip() == "active",
        "status": result.stdout.strip(),
    }
