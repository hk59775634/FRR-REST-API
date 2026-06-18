import re
from typing import Any, Literal

from app.services.protocol_common import (
    action_result,
    apply_commands,
    get_router_block,
    parse_network_area,
    require_daemon,
    safe_show,
)


def _router_cmd(vrf: str | None = None) -> str:
    if vrf and vrf != "default":
        return f"router ospf vrf {vrf}"
    return "router ospf"


def _parse_instance(commands: list[str]) -> dict[str, Any]:
    networks: list[dict[str, str]] = []
    router_id: str | None = None
    redistributes: list[str] = []

    for cmd in commands:
        if cmd.startswith("ospf router-id "):
            router_id = cmd.removeprefix("ospf router-id ").strip()
        elif cmd.startswith("network "):
            net = parse_network_area(cmd)
            if net:
                networks.append(net)
        elif cmd.startswith("redistribute "):
            redistributes.append(cmd.removeprefix("redistribute ").strip())

    return {
        "router_id": router_id,
        "networks": networks,
        "redistributes": redistributes,
    }


def get_instance(vrf: str | None = None) -> dict[str, Any]:
    header, commands = get_router_block("router ospf")
    configured = header is not None
    parsed = _parse_instance(commands) if configured else {}
    return {
        "configured": configured,
        "vrf": vrf or "default",
        "header": header,
        "commands": commands,
        **parsed,
    }


def get_summary() -> dict[str, Any]:
    result = safe_show("show ip ospf", "ospfd")
    if not result.get("running"):
        return result
    result["lines"] = result["raw"].splitlines()
    return result


def get_neighbors() -> dict[str, Any]:
    result = safe_show("show ip ospf neighbor", "ospfd")
    if not result.get("running"):
        return {**result, "neighbors": [], "total": 0}
    raw = result["raw"]
    neighbors = [
        line.strip()
        for line in raw.splitlines()
        if line.strip() and not line.startswith("Neighbor ID")
    ]
    return {"running": True, "neighbors": neighbors, "total": len(neighbors), "raw": raw}


def get_routes() -> dict[str, Any]:
    result = safe_show("show ip ospf route", "ospfd")
    if not result.get("running"):
        return {**result, "routes": [], "total": 0}
    routes = [
        line.strip()
        for line in result["raw"].splitlines()
        if line.strip() and not line.startswith("============")
    ]
    return {"running": True, "routes": routes, "total": len(routes), "raw": result["raw"]}


def create_instance(
    *,
    router_id: str | None = None,
    vrf: str | None = None,
    write_memory: bool = False,
) -> dict[str, Any]:
    require_daemon("ospfd")
    inst = get_instance(vrf)
    if inst["configured"]:
        raise ValueError("OSPF 实例已存在，请使用 PATCH 更新或先删除")

    commands = [_router_cmd(vrf)]
    if router_id:
        commands.append(f"ospf router-id {router_id}")
    apply_commands(commands, write_memory=write_memory)
    return action_result("OSPF 实例已创建", write_memory=write_memory)


def update_instance(
    *,
    router_id: str | None = None,
    vrf: str | None = None,
    write_memory: bool = False,
) -> dict[str, Any]:
    require_daemon("ospfd")
    inst = get_instance(vrf)
    if not inst["configured"]:
        raise ValueError("OSPF 实例未配置，请先 POST /instance 创建")

    if router_id is None:
        raise ValueError("未提供需要更新的字段")

    commands = [_router_cmd(vrf), f"ospf router-id {router_id}"]
    apply_commands(commands, write_memory=write_memory)
    return action_result("OSPF 实例已更新", write_memory=write_memory)


def delete_instance(*, vrf: str | None = None, write_memory: bool = False) -> dict[str, Any]:
    require_daemon("ospfd")
    inst = get_instance(vrf)
    if not inst["configured"]:
        raise ValueError("OSPF 实例未配置")

    apply_commands([f"no {_router_cmd(vrf)}"], write_memory=write_memory)
    return action_result("OSPF 实例已删除", write_memory=write_memory)


def add_network(
    prefix: str,
    area: str,
    *,
    vrf: str | None = None,
    write_memory: bool = False,
) -> dict[str, Any]:
    require_daemon("ospfd")
    inst = get_instance(vrf)
    if not inst["configured"]:
        commands = [_router_cmd(vrf), f"network {prefix} area {area}"]
    else:
        commands = [_router_cmd(vrf), f"network {prefix} area {area}"]
    apply_commands(commands, write_memory=write_memory)
    return action_result(f"OSPF 网络 {prefix} area {area} 已添加", write_memory=write_memory)


def delete_network(
    prefix: str,
    area: str,
    *,
    vrf: str | None = None,
    write_memory: bool = False,
) -> dict[str, Any]:
    require_daemon("ospfd")
    inst = get_instance(vrf)
    if not inst["configured"]:
        raise ValueError("OSPF 实例未配置")

    apply_commands(
        [_router_cmd(vrf), f"no network {prefix} area {area}"],
        write_memory=write_memory,
    )
    return action_result(f"OSPF 网络 {prefix} area {area} 已删除", write_memory=write_memory)


def set_redistribute(
    protocol: Literal["static", "connected", "bgp", "kernel", "rip", "isis"],
    *,
    enabled: bool = True,
    metric_type: Literal["1", "2"] | None = None,
    vrf: str | None = None,
    write_memory: bool = False,
) -> dict[str, Any]:
    require_daemon("ospfd")
    inst = get_instance(vrf)
    if not inst["configured"]:
        raise ValueError("OSPF 实例未配置")

    if enabled:
        cmd = f"redistribute {protocol}"
        if metric_type:
            cmd += f" metric-type {metric_type}"
        commands = [_router_cmd(vrf), cmd]
        msg = f"OSPF redistribute {protocol} 已启用"
    else:
        commands = [_router_cmd(vrf), f"no redistribute {protocol}"]
        msg = f"OSPF redistribute {protocol} 已禁用"

    apply_commands(commands, write_memory=write_memory)
    return action_result(msg, write_memory=write_memory)


def set_interface_area(
    interface: str,
    area: str,
    *,
    network_type: Literal["broadcast", "point-to-point", "non-broadcast"] | None = None,
    write_memory: bool = False,
) -> dict[str, Any]:
    require_daemon("ospfd")
    commands = [f"interface {interface}", f"ip ospf area {area}"]
    if network_type:
        commands.append(f"ip ospf network {network_type}")
    apply_commands(commands, write_memory=write_memory)
    return action_result(f"接口 {interface} 已加入 OSPF area {area}", write_memory=write_memory)


def delete_interface_area(
    interface: str,
    area: str,
    *,
    write_memory: bool = False,
) -> dict[str, Any]:
    require_daemon("ospfd")
    apply_commands(
        [f"interface {interface}", f"no ip ospf area {area}"],
        write_memory=write_memory,
    )
    return action_result(f"接口 {interface} 已从 OSPF area {area} 移除", write_memory=write_memory)
