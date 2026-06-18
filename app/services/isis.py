import re
from typing import Any, Literal

from app.services.protocol_common import (
    action_result,
    apply_commands,
    get_router_block,
    require_daemon,
    safe_show,
)


def _parse_instance(commands: list[str]) -> dict[str, Any]:
    net: str | None = None
    is_type: str | None = None
    redistributes: list[str] = []

    for cmd in commands:
        if cmd.startswith("net "):
            net = cmd.removeprefix("net ").strip()
        elif cmd.startswith("is-type "):
            is_type = cmd.removeprefix("is-type ").strip()
        elif cmd.startswith("redistribute "):
            redistributes.append(cmd.removeprefix("redistribute ").strip())

    return {"net": net, "is_type": is_type, "redistributes": redistributes}


def _get_tag() -> str | None:
    header, _ = get_router_block("router isis")
    if not header:
        return None
    match = re.match(r"router isis (\S+)", header)
    return match.group(1) if match else None


def get_instance() -> dict[str, Any]:
    header, commands = get_router_block("router isis")
    configured = header is not None
    tag = _get_tag()
    parsed = _parse_instance(commands) if configured else {}
    return {"configured": configured, "tag": tag, "header": header, "commands": commands, **parsed}


def get_summary() -> dict[str, Any]:
    return safe_show("show isis summary", "isisd")


def get_neighbors() -> dict[str, Any]:
    result = safe_show("show isis neighbor", "isisd")
    if not result.get("running"):
        return {**result, "neighbors": [], "total": 0}
    raw = result["raw"]
    lines = [
        line.strip()
        for line in raw.splitlines()
        if line.strip() and "Interface" not in line and "---" not in line
    ]
    return {"running": True, "neighbors": lines, "total": len(lines), "raw": raw}


def create_instance(
    tag: str,
    *,
    net: str | None = None,
    is_type: Literal["level-1", "level-2-only", "level-1-2"] | None = "level-2-only",
    write_memory: bool = False,
) -> dict[str, Any]:
    require_daemon("isisd")
    if get_instance()["configured"]:
        raise ValueError("IS-IS 实例已存在")

    commands = [f"router isis {tag}"]
    if is_type:
        commands.append(f"is-type {is_type}")
    if net:
        commands.append(f"net {net}")
    apply_commands(commands, write_memory=write_memory)
    return action_result(f"IS-IS 实例 {tag} 已创建", write_memory=write_memory)


def update_instance(
    *,
    net: str | None = None,
    is_type: Literal["level-1", "level-2-only", "level-1-2"] | None = None,
    write_memory: bool = False,
) -> dict[str, Any]:
    require_daemon("isisd")
    inst = get_instance()
    if not inst["configured"] or not inst["tag"]:
        raise ValueError("IS-IS 实例未配置")

    tag = inst["tag"]
    commands = [f"router isis {tag}"]
    if net is not None:
        commands.append(f"net {net}")
    if is_type is not None:
        commands.append(f"is-type {is_type}")
    if len(commands) == 1:
        raise ValueError("未提供需要更新的字段")

    apply_commands(commands, write_memory=write_memory)
    return action_result(f"IS-IS 实例 {tag} 已更新", write_memory=write_memory)


def delete_instance(*, write_memory: bool = False) -> dict[str, Any]:
    require_daemon("isisd")
    inst = get_instance()
    if not inst["configured"] or not inst["tag"]:
        raise ValueError("IS-IS 实例未配置")
    apply_commands([f"no router isis {inst['tag']}"], write_memory=write_memory)
    return action_result(f"IS-IS 实例 {inst['tag']} 已删除", write_memory=write_memory)


def set_interface(
    interface: str,
    *,
    write_memory: bool = False,
) -> dict[str, Any]:
    require_daemon("isisd")
    inst = get_instance()
    if not inst["configured"] or not inst["tag"]:
        raise ValueError("IS-IS 实例未配置")

    tag = inst["tag"]
    apply_commands(
        [f"interface {interface}", f"ip router isis {tag}", f"ipv6 router isis {tag}"],
        write_memory=write_memory,
    )
    return action_result(f"接口 {interface} 已启用 IS-IS {tag}", write_memory=write_memory)


def delete_interface(
    interface: str,
    *,
    write_memory: bool = False,
) -> dict[str, Any]:
    require_daemon("isisd")
    inst = get_instance()
    if not inst["configured"] or not inst["tag"]:
        raise ValueError("IS-IS 实例未配置")

    tag = inst["tag"]
    apply_commands(
        [
            f"interface {interface}",
            f"no ip router isis {tag}",
            f"no ipv6 router isis {tag}",
        ],
        write_memory=write_memory,
    )
    return action_result(f"接口 {interface} 已从 IS-IS 移除", write_memory=write_memory)


def set_redistribute(
    protocol: Literal["static", "connected", "bgp", "ospf", "rip", "kernel"],
    *,
    enabled: bool = True,
    write_memory: bool = False,
) -> dict[str, Any]:
    require_daemon("isisd")
    inst = get_instance()
    if not inst["configured"] or not inst["tag"]:
        raise ValueError("IS-IS 实例未配置")

    tag = inst["tag"]
    if enabled:
        commands = [f"router isis {tag}", f"redistribute {protocol}"]
        msg = f"IS-IS redistribute {protocol} 已启用"
    else:
        commands = [f"router isis {tag}", f"no redistribute {protocol}"]
        msg = f"IS-IS redistribute {protocol} 已禁用"

    apply_commands(commands, write_memory=write_memory)
    return action_result(msg, write_memory=write_memory)
