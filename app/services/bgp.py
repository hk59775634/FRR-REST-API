import re
from typing import Any, Literal

from app.services.vtysh import run_vtysh, run_vtysh_commands


def get_bgp_asn() -> int | None:
    raw = run_vtysh("show running-config")
    match = re.search(r"^router bgp (\d+)", raw, re.MULTILINE)
    return int(match.group(1)) if match else None


def _get_bgp_block_commands() -> list[str]:
    raw = run_vtysh("show running-config")
    in_bgp = False
    commands: list[str] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.startswith("router bgp "):
            in_bgp = True
            continue
        if in_bgp:
            if stripped in ("exit", "!", "end"):
                break
            if stripped:
                commands.append(stripped)
    return commands


def _parse_neighbors_from_config(commands: list[str]) -> dict[str, dict[str, Any]]:
    neighbors: dict[str, dict[str, Any]] = {}
    for cmd in commands:
        match = re.match(r"neighbor (\S+) (.+)", cmd)
        if not match:
            continue
        address, rest = match.group(1), match.group(2)
        neighbor = neighbors.setdefault(address, {"address": address, "config": {}})

        if rest.startswith("remote-as "):
            neighbor["remote_as"] = int(rest.removeprefix("remote-as "))
        elif rest.startswith("description "):
            neighbor["description"] = rest.removeprefix("description ")
        elif rest.startswith("update-source "):
            neighbor["update_source"] = rest.removeprefix("update-source ")
        elif rest.startswith("password "):
            neighbor["password"] = "***"
        elif rest.startswith("timers "):
            parts = rest.removeprefix("timers ").split()
            if len(parts) >= 2:
                neighbor["timers"] = {"keepalive": int(parts[0]), "holdtime": int(parts[1])}
        else:
            neighbor["config"][rest] = True
    return neighbors


def _parse_bgp_summary(raw: str) -> dict[str, Any]:
    result: dict[str, Any] = {"router_id": None, "local_as": None, "neighbors": []}

    for line in raw.splitlines():
        stripped = line.strip()
        if "BGP router identifier" in stripped:
            rid = re.search(r"identifier (\S+)", stripped)
            asn = re.search(r"local AS number (\d+)", stripped)
            if rid:
                result["router_id"] = rid.group(1)
            if asn:
                result["local_as"] = int(asn.group(1))
            continue

        if re.match(r"^Neighbor\s+V\s+AS", stripped):
            continue
        if stripped.startswith("Neighbor") or stripped.startswith("Total"):
            continue

        parts = stripped.split()
        if len(parts) >= 10 and re.match(r"[\d.a-fA-F:]+", parts[0]):
            neighbor: dict[str, Any] = {
                "address": parts[0],
                "version": int(parts[1]) if parts[1].isdigit() else parts[1],
                "remote_as": int(parts[2]),
                "msg_rcvd": int(parts[3]),
                "msg_sent": int(parts[4]),
                "table_version": int(parts[5]),
                "inq": int(parts[6]),
                "outq": int(parts[7]),
                "uptime": parts[8],
                "state": parts[9],
            }
            if len(parts) == 11:
                neighbor["prefix_rcvd"] = parts[10]
                neighbor["prefix_sent"] = "0"
                neighbor["description"] = None
            elif len(parts) == 12:
                neighbor["prefix_rcvd"] = parts[10]
                neighbor["prefix_sent"] = "0"
                neighbor["description"] = parts[11]
            else:
                neighbor["prefix_rcvd"] = parts[10]
                neighbor["prefix_sent"] = parts[11]
                neighbor["description"] = " ".join(parts[12:]) if len(parts) > 12 else None
            result["neighbors"].append(neighbor)
    return result


def _parse_bgp_neighbor_detail(raw: str) -> dict[str, Any]:
    detail: dict[str, Any] = {"raw_lines": []}
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        detail["raw_lines"].append(stripped)

        if stripped.startswith("BGP neighbor is "):
            match = re.search(
                r"BGP neighbor is (\S+), remote AS (\d+), local AS (\d+)", stripped
            )
            if match:
                detail["address"] = match.group(1)
                detail["remote_as"] = int(match.group(2))
                detail["local_as"] = int(match.group(3))
        elif stripped.startswith("Description:"):
            detail["description"] = stripped.removeprefix("Description:").strip()
        elif stripped.startswith("BGP state ="):
            detail["state"] = stripped.removeprefix("BGP state =").strip()
        elif stripped.startswith("BGP version"):
            detail["bgp_version"] = stripped
    return detail


def _parse_bgp_routes(raw: str) -> list[dict[str, Any]]:
    routes: list[dict[str, Any]] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("BGP table") or stripped.startswith("Status"):
            continue
        if stripped.startswith("Network") or stripped.startswith("Displayed"):
            continue
        if stripped.startswith("Total number"):
            continue

        parts = stripped.split()
        if len(parts) >= 2 and ("/" in parts[0] or parts[0] == "Network"):
            if parts[0] == "Network":
                continue
            routes.append(
                {
                    "network": parts[0],
                    "next_hop": parts[1] if len(parts) > 1 else None,
                    "metric": parts[2] if len(parts) > 2 else None,
                    "locprf": parts[3] if len(parts) > 3 else None,
                    "weight": parts[4] if len(parts) > 4 else None,
                    "path": " ".join(parts[5:]) if len(parts) > 5 else None,
                    "raw": stripped,
                }
            )
    return routes


def get_bgp_instance() -> dict[str, Any]:
    asn = get_bgp_asn()
    commands = _get_bgp_block_commands()
    neighbors = _parse_neighbors_from_config(commands)
    networks = [
        cmd.removeprefix("network ").split()[0]
        for cmd in commands
        if cmd.startswith("network ")
    ]
    return {
        "local_as": asn,
        "configured": asn is not None,
        "neighbors": list(neighbors.values()),
        "networks": networks,
        "commands": commands,
    }


def get_bgp_summary() -> dict[str, Any]:
    raw = run_vtysh("show bgp summary")
    result = _parse_bgp_summary(raw)
    if result["local_as"] is None:
        instance = get_bgp_instance()
        result["local_as"] = instance["local_as"]
        result["configured"] = instance["configured"]
    if not result["neighbors"] and "No BGP neighbors" in raw:
        result["message"] = "当前无 BGP 邻居"
    return result


def list_bgp_neighbors() -> list[dict[str, Any]]:
    instance = get_bgp_instance()
    summary = get_bgp_summary()
    summary_map = {n["address"]: n for n in summary.get("neighbors", [])}

    merged: list[dict[str, Any]] = []
    for neighbor in instance["neighbors"]:
        address = neighbor["address"]
        item = {**neighbor, "operational": summary_map.get(address)}
        merged.append(item)
    return merged


def get_bgp_neighbor(address: str) -> dict[str, Any]:
    instance = get_bgp_instance()
    config_neighbor = next(
        (n for n in instance["neighbors"] if n["address"] == address), None
    )
    if not config_neighbor:
        raise ValueError(f"BGP 邻居 {address} 未在配置中找到")

    detail_raw = run_vtysh(f"show bgp neighbors {address}")
    detail = _parse_bgp_neighbor_detail(detail_raw)
    return {"config": config_neighbor, "operational": detail}


def get_bgp_routes(afi: Literal["ipv4", "ipv6"] = "ipv4") -> list[dict[str, Any]]:
    if afi == "ipv6":
        raw = run_vtysh("show bgp ipv6 unicast")
    else:
        raw = run_vtysh("show bgp ipv4 unicast")
    return _parse_bgp_routes(raw)


def add_bgp_neighbor(
    *,
    address: str,
    remote_as: int,
    description: str | None = None,
    update_source: str | None = None,
    write_memory: bool = False,
) -> dict[str, Any]:
    asn = get_bgp_asn()
    if asn is None:
        raise ValueError("未配置 BGP 实例，请先配置 router bgp <AS>")

    commands = [
        f"router bgp {asn}",
        f"neighbor {address} remote-as {remote_as}",
    ]
    if description:
        commands.append(f"neighbor {address} description {description}")
    if update_source:
        commands.append(f"neighbor {address} update-source {update_source}")

    run_vtysh_commands(commands, write_memory=write_memory)
    return {"message": f"BGP 邻居 {address} 已添加", "local_as": asn, "remote_as": remote_as}


def update_bgp_neighbor(
    address: str,
    *,
    description: str | None = None,
    update_source: str | None = None,
    write_memory: bool = False,
) -> dict[str, Any]:
    asn = get_bgp_asn()
    if asn is None:
        raise ValueError("未配置 BGP 实例")

    get_bgp_neighbor(address)

    commands = [f"router bgp {asn}"]
    if description is not None:
        commands.append(f"neighbor {address} description {description}")
    if update_source is not None:
        commands.append(f"neighbor {address} update-source {update_source}")

    if len(commands) == 1:
        raise ValueError("未提供需要更新的字段")

    run_vtysh_commands(commands, write_memory=write_memory)
    return {"message": f"BGP 邻居 {address} 已更新"}


def delete_bgp_neighbor(address: str, *, write_memory: bool = False) -> dict[str, Any]:
    asn = get_bgp_asn()
    if asn is None:
        raise ValueError("未配置 BGP 实例")

    commands = [f"router bgp {asn}", f"no neighbor {address}"]
    run_vtysh_commands(commands, write_memory=write_memory)
    return {"message": f"BGP 邻居 {address} 已删除"}


def add_bgp_network(
    network: str,
    *,
    write_memory: bool = False,
) -> dict[str, Any]:
    asn = get_bgp_asn()
    if asn is None:
        raise ValueError("未配置 BGP 实例")

    commands = [f"router bgp {asn}", f"network {network}"]
    run_vtysh_commands(commands, write_memory=write_memory)
    return {"message": f"BGP 网络 {network} 已宣告", "network": network}


def delete_bgp_network(
    network: str,
    *,
    write_memory: bool = False,
) -> dict[str, Any]:
    asn = get_bgp_asn()
    if asn is None:
        raise ValueError("未配置 BGP 实例")

    commands = [f"router bgp {asn}", f"no network {network}"]
    run_vtysh_commands(commands, write_memory=write_memory)
    return {"message": f"BGP 网络 {network} 已撤销", "network": network}
