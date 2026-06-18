from typing import Any, Literal

from app.services.protocol_common import (
    action_result,
    apply_commands,
    get_router_block,
    require_daemon,
    safe_show,
)


def _parse_instance(commands: list[str]) -> dict[str, Any]:
    networks: list[str] = []
    version: int | None = None
    redistributes: list[str] = []

    for cmd in commands:
        if cmd.startswith("network "):
            networks.append(cmd.removeprefix("network ").strip())
        elif cmd.startswith("version "):
            version = int(cmd.split()[-1])
        elif cmd.startswith("redistribute "):
            redistributes.append(cmd.removeprefix("redistribute ").strip())

    return {"networks": networks, "version": version, "redistributes": redistributes}


def get_instance() -> dict[str, Any]:
    header, commands = get_router_block("router rip")
    configured = header is not None
    parsed = _parse_instance(commands) if configured else {}
    return {"configured": configured, "commands": commands, **parsed}


def get_status() -> dict[str, Any]:
    return safe_show("show ip rip", "ripd")


def create_instance(
    *,
    version: int = 2,
    write_memory: bool = False,
) -> dict[str, Any]:
    require_daemon("ripd")
    if get_instance()["configured"]:
        raise ValueError("RIP 实例已存在")

    apply_commands(["router rip", f"version {version}"], write_memory=write_memory)
    return action_result("RIP 实例已创建", write_memory=write_memory)


def delete_instance(*, write_memory: bool = False) -> dict[str, Any]:
    require_daemon("ripd")
    if not get_instance()["configured"]:
        raise ValueError("RIP 实例未配置")
    apply_commands(["no router rip"], write_memory=write_memory)
    return action_result("RIP 实例已删除", write_memory=write_memory)


def add_network(prefix: str, *, write_memory: bool = False) -> dict[str, Any]:
    require_daemon("ripd")
    inst = get_instance()
    commands = ["router rip"]
    if not inst["configured"]:
        commands.append("version 2")
    commands.append(f"network {prefix}")
    apply_commands(commands, write_memory=write_memory)
    return action_result(f"RIP 网络 {prefix} 已添加", write_memory=write_memory)


def delete_network(prefix: str, *, write_memory: bool = False) -> dict[str, Any]:
    require_daemon("ripd")
    if not get_instance()["configured"]:
        raise ValueError("RIP 实例未配置")
    apply_commands(["router rip", f"no network {prefix}"], write_memory=write_memory)
    return action_result(f"RIP 网络 {prefix} 已删除", write_memory=write_memory)


def set_redistribute(
    protocol: Literal["static", "connected", "bgp", "ospf", "isis", "kernel"],
    *,
    enabled: bool = True,
    write_memory: bool = False,
) -> dict[str, Any]:
    require_daemon("ripd")
    if not get_instance()["configured"]:
        raise ValueError("RIP 实例未配置")

    if enabled:
        commands = ["router rip", f"redistribute {protocol}"]
        msg = f"RIP redistribute {protocol} 已启用"
    else:
        commands = ["router rip", f"no redistribute {protocol}"]
        msg = f"RIP redistribute {protocol} 已禁用"

    apply_commands(commands, write_memory=write_memory)
    return action_result(msg, write_memory=write_memory)
