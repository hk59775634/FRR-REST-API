from typing import Any, Literal

from app.services.protocol_common import (
    action_result,
    apply_commands,
    get_router_block,
    require_daemon,
    safe_show,
)


def _parse_instance(commands: list[str]) -> dict[str, Any]:
    interfaces: list[str] = []
    redistributes: list[str] = []

    for cmd in commands:
        if cmd.startswith("network "):
            interfaces.append(cmd.removeprefix("network ").strip())
        elif cmd.startswith("redistribute "):
            redistributes.append(cmd.removeprefix("redistribute ").strip())

    return {"interfaces": interfaces, "redistributes": redistributes}


def get_instance() -> dict[str, Any]:
    header, commands = get_router_block("router ripng")
    configured = header is not None
    parsed = _parse_instance(commands) if configured else {}
    return {"configured": configured, "commands": commands, **parsed}


def get_status() -> dict[str, Any]:
    return safe_show("show ipv6 ripng", "ripngd")


def create_instance(*, write_memory: bool = False) -> dict[str, Any]:
    require_daemon("ripngd")
    if get_instance()["configured"]:
        raise ValueError("RIPng 实例已存在")
    apply_commands(["router ripng"], write_memory=write_memory)
    return action_result("RIPng 实例已创建", write_memory=write_memory)


def delete_instance(*, write_memory: bool = False) -> dict[str, Any]:
    require_daemon("ripngd")
    if not get_instance()["configured"]:
        raise ValueError("RIPng 实例未配置")
    apply_commands(["no router ripng"], write_memory=write_memory)
    return action_result("RIPng 实例已删除", write_memory=write_memory)


def add_interface(interface: str, *, write_memory: bool = False) -> dict[str, Any]:
    require_daemon("ripngd")
    commands = ["router ripng", f"network {interface}"]
    apply_commands(commands, write_memory=write_memory)
    return action_result(f"RIPng 接口 {interface} 已添加", write_memory=write_memory)


def delete_interface(interface: str, *, write_memory: bool = False) -> dict[str, Any]:
    require_daemon("ripngd")
    if not get_instance()["configured"]:
        raise ValueError("RIPng 实例未配置")
    apply_commands(["router ripng", f"no network {interface}"], write_memory=write_memory)
    return action_result(f"RIPng 接口 {interface} 已删除", write_memory=write_memory)


def set_redistribute(
    protocol: Literal["static", "connected", "bgp", "ospf6", "kernel"],
    *,
    enabled: bool = True,
    write_memory: bool = False,
) -> dict[str, Any]:
    require_daemon("ripngd")
    if not get_instance()["configured"]:
        raise ValueError("RIPng 实例未配置")

    if enabled:
        commands = ["router ripng", f"redistribute {protocol}"]
        msg = f"RIPng redistribute {protocol} 已启用"
    else:
        commands = ["router ripng", f"no redistribute {protocol}"]
        msg = f"RIPng redistribute {protocol} 已禁用"

    apply_commands(commands, write_memory=write_memory)
    return action_result(msg, write_memory=write_memory)
