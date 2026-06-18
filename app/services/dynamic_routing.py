import re
from typing import Any

from app.services.vtysh import VtyshError, run_vtysh


def _daemon_running_hint(protocol: str) -> str:
    return f"{protocol} 守护进程未运行，请先通过 /api/v1/daemons 启用"


def _safe_show(command: str, daemon: str) -> dict[str, Any]:
    try:
        raw = run_vtysh(command)
        return {"running": True, "raw": raw.strip()}
    except VtyshError as exc:
        combined = f"{exc} {exc.stdout} {exc.stderr}".lower()
        if "not running" in combined:
            return {"running": False, "message": _daemon_running_hint(daemon)}
        raise


def _get_router_block(router_keyword: str) -> list[str]:
    raw = run_vtysh("show running-config")
    in_block = False
    commands: list[str] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.startswith(router_keyword):
            in_block = True
            continue
        if in_block:
            if stripped in ("exit", "!", "end"):
                break
            if stripped:
                commands.append(stripped)
    return commands


def _protocol_not_running(exc: VtyshError, protocol: str) -> bool:
    combined = f"{exc} {exc.stdout} {exc.stderr}".lower()
    return "not running" in combined


# --- OSPFv2 ---


def get_ospf_instance() -> dict[str, Any]:
    raw = run_vtysh("show running-config")
    match = re.search(r"^router ospf(?:\s+(\S+))?", raw, re.MULTILINE)
    commands = _get_router_block("router ospf")
    return {
        "configured": match is not None,
        "vrf": match.group(1) if match and match.group(1) else "default",
        "commands": commands,
    }


def get_ospf_summary() -> dict[str, Any]:
    result = _safe_show("show ip ospf", "ospfd")
    if not result.get("running"):
        return result
    result["lines"] = result["raw"].splitlines()
    return result


def get_ospf_neighbors() -> dict[str, Any]:
    result = _safe_show("show ip ospf neighbor", "ospfd")
    if not result.get("running"):
        return {**result, "neighbors": [], "total": 0}
    raw = result["raw"]
    neighbors = [
        line.strip()
        for line in raw.splitlines()
        if line.strip() and not line.startswith("Neighbor ID")
    ]
    return {"running": True, "neighbors": neighbors, "total": len(neighbors), "raw": raw}


# --- OSPFv3 ---


def get_ospf6_instance() -> dict[str, Any]:
    raw = run_vtysh("show running-config")
    match = re.search(r"^router ospf6", raw, re.MULTILINE)
    commands = _get_router_block("router ospf6")
    return {"configured": match is not None, "commands": commands}


def get_ospf6_summary() -> dict[str, Any]:
    return _safe_show("show ipv6 ospf6", "ospf6d")


# --- RIPv2 ---


def get_rip_instance() -> dict[str, Any]:
    raw = run_vtysh("show running-config")
    configured = bool(re.search(r"^router rip", raw, re.MULTILINE))
    commands = _get_router_block("router rip")
    return {"configured": configured, "commands": commands}


def get_rip_status() -> dict[str, Any]:
    return _safe_show("show ip rip", "ripd")


# --- RIPng ---


def get_ripng_instance() -> dict[str, Any]:
    raw = run_vtysh("show running-config")
    configured = bool(re.search(r"^router ripng", raw, re.MULTILINE))
    commands = _get_router_block("router ripng")
    return {"configured": configured, "commands": commands}


def get_ripng_status() -> dict[str, Any]:
    return _safe_show("show ipv6 ripng", "ripngd")


# --- IS-IS ---


def get_isis_instance() -> dict[str, Any]:
    raw = run_vtysh("show running-config")
    match = re.search(r"^router isis (\S+)", raw, re.MULTILINE)
    commands = _get_router_block("router isis")
    return {
        "configured": match is not None,
        "tag": match.group(1) if match else None,
        "commands": commands,
    }


def get_isis_summary() -> dict[str, Any]:
    return _safe_show("show isis summary", "isisd")


def get_isis_neighbors() -> dict[str, Any]:
    result = _safe_show("show isis neighbor", "isisd")
    if not result.get("running"):
        return {**result, "neighbors": [], "total": 0}
    raw = result["raw"]
    lines = [
        line.strip()
        for line in raw.splitlines()
        if line.strip() and "Interface" not in line and "---" not in line
    ]
    return {"running": True, "neighbors": lines, "total": len(lines), "raw": raw}
