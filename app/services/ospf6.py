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
    router_id: str | None = None

    for cmd in commands:
        if cmd.startswith("ospf6 router-id "):
            router_id = cmd.removeprefix("ospf6 router-id ").strip()
        elif cmd.startswith("interface "):
            interfaces.append(cmd.removeprefix("interface ").strip())
        elif cmd.startswith("redistribute "):
            redistributes.append(cmd.removeprefix("redistribute ").strip())

    return {"router_id": router_id, "interfaces": interfaces, "redistributes": redistributes}


def get_instance() -> dict[str, Any]:
    header, commands = get_router_block("router ospf6")
    configured = header is not None
    parsed = _parse_instance(commands) if configured else {}
    return {"configured": configured, "header": header, "commands": commands, **parsed}


def get_summary() -> dict[str, Any]:
    return safe_show("show ipv6 ospf6", "ospf6d")


def create_instance(*, router_id: str | None = None, write_memory: bool = False) -> dict[str, Any]:
    require_daemon("ospf6d")
    if get_instance()["configured"]:
        raise ValueError("OSPFv3 实例已存在")

    commands = ["router ospf6"]
    if router_id:
        commands.append(f"ospf6 router-id {router_id}")
    apply_commands(commands, write_memory=write_memory)
    return action_result("OSPFv3 实例已创建", write_memory=write_memory)


def delete_instance(*, write_memory: bool = False) -> dict[str, Any]:
    require_daemon("ospf6d")
    if not get_instance()["configured"]:
        raise ValueError("OSPFv3 实例未配置")
    apply_commands(["no router ospf6"], write_memory=write_memory)
    return action_result("OSPFv3 实例已删除", write_memory=write_memory)


def set_interface(
    interface: str,
    area: str,
    *,
    write_memory: bool = False,
) -> dict[str, Any]:
    require_daemon("ospf6d")
    inst = get_instance()
    router_cmds = ["router ospf6"]
    if not inst["configured"]:
        router_cmds  # will create via interface config below

    apply_commands(
        [
            f"interface {interface}",
            "ipv6 ospf6 area " + area,
        ],
        write_memory=write_memory,
    )
    return action_result(f"接口 {interface} 已加入 OSPFv3 area {area}", write_memory=write_memory)


def delete_interface(
    interface: str,
    area: str,
    *,
    write_memory: bool = False,
) -> dict[str, Any]:
    require_daemon("ospf6d")
    apply_commands(
        [f"interface {interface}", f"no ipv6 ospf6 area {area}"],
        write_memory=write_memory,
    )
    return action_result(f"接口 {interface} 已从 OSPFv3 area {area} 移除", write_memory=write_memory)


def set_redistribute(
    protocol: Literal["static", "connected", "bgp", "kernel"],
    *,
    enabled: bool = True,
    write_memory: bool = False,
) -> dict[str, Any]:
    require_daemon("ospf6d")
    if not get_instance()["configured"]:
        raise ValueError("OSPFv3 实例未配置")

    if enabled:
        commands = ["router ospf6", f"redistribute {protocol}"]
        msg = f"OSPFv3 redistribute {protocol} 已启用"
    else:
        commands = ["router ospf6", f"no redistribute {protocol}"]
        msg = f"OSPFv3 redistribute {protocol} 已禁用"

    apply_commands(commands, write_memory=write_memory)
    return action_result(msg, write_memory=write_memory)
