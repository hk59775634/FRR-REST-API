import re
from typing import Any, Literal

from app.services.vtysh import run_vtysh, run_vtysh_commands


def _parse_route_line(line: str) -> dict[str, Any] | None:
    stripped = line.strip()
    for family, keyword in (("ipv4", "ip route"), ("ipv6", "ipv6 route")):
        if not stripped.startswith(keyword + " "):
            continue
        rest = stripped[len(keyword) + 1 :]
        tokens = rest.split()
        if len(tokens) < 2:
            return None

        prefix = tokens[0]
        route: dict[str, Any] = {"family": family, "prefix": prefix, "raw": stripped}

        if tokens[1] in ("blackhole", "reject"):
            route["type"] = tokens[1]
            if len(tokens) > 2 and tokens[2].isdigit():
                route["distance"] = int(tokens[2])
            return route

        route["type"] = "unicast"
        idx = 1
        if len(tokens) > 2 and not tokens[1].replace(".", "").replace(":", "").isdigit():
            if "/" not in tokens[1] and not tokens[1][0].isdigit():
                route["interface"] = tokens[1]
                idx = 2

        if idx < len(tokens):
            route["nexthop"] = tokens[idx]
            idx += 1
        if idx < len(tokens) and tokens[idx].isdigit():
            route["distance"] = int(tokens[idx])

        return route
    return None


def build_route_command(
    *,
    family: Literal["ipv4", "ipv6"],
    prefix: str,
    type: Literal["unicast", "blackhole", "reject"] = "unicast",
    nexthop: str | None = None,
    interface: str | None = None,
    distance: int | None = None,
    negate: bool = False,
) -> str:
    keyword = "ip route" if family == "ipv4" else "ipv6 route"
    parts = [keyword, prefix]

    if type in ("blackhole", "reject"):
        parts.append(type)
    else:
        if interface:
            parts.append(interface)
        if not nexthop:
            raise ValueError("单播静态路由必须指定 nexthop")
        parts.append(nexthop)

    if distance is not None:
        parts.append(str(distance))

    cmd = " ".join(parts)
    return f"no {cmd}" if negate else cmd


def list_static_routes() -> list[dict[str, Any]]:
    raw = run_vtysh("show running-config")
    routes: list[dict[str, Any]] = []
    for line in raw.splitlines():
        parsed = _parse_route_line(line)
        if parsed:
            routes.append(parsed)
    return routes


def list_static_routes_in_table() -> list[dict[str, Any]]:
    raw = run_vtysh("show ip route static")
    routes: list[dict[str, Any]] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("Codes:"):
            continue
        if stripped[0] in "SKCRIOIBENTvfFAqrbto" and ">" in stripped[:3]:
            routes.append({"raw": stripped, "installed": "*" in stripped[:3]})
    return routes


def add_static_route(
    *,
    family: Literal["ipv4", "ipv6"],
    prefix: str,
    type: Literal["unicast", "blackhole", "reject"] = "unicast",
    nexthop: str | None = None,
    interface: str | None = None,
    distance: int | None = None,
    write_memory: bool = False,
) -> dict[str, Any]:
    cmd = build_route_command(
        family=family,
        prefix=prefix,
        type=type,
        nexthop=nexthop,
        interface=interface,
        distance=distance,
    )
    run_vtysh_commands([cmd], write_memory=write_memory)
    return {
        "command": cmd,
        "message": "静态路由已添加" + ("，已写入 frr.conf" if write_memory else ""),
    }


def delete_static_route(
    *,
    family: Literal["ipv4", "ipv6"],
    prefix: str,
    type: Literal["unicast", "blackhole", "reject"] = "unicast",
    nexthop: str | None = None,
    interface: str | None = None,
    distance: int | None = None,
    write_memory: bool = False,
) -> dict[str, Any]:
    cmd = build_route_command(
        family=family,
        prefix=prefix,
        type=type,
        nexthop=nexthop,
        interface=interface,
        distance=distance,
        negate=True,
    )
    run_vtysh_commands([cmd], write_memory=write_memory)
    return {
        "command": cmd,
        "message": "静态路由已删除" + ("，已写入 frr.conf" if write_memory else ""),
    }


def find_static_route(prefix: str, family: str | None = None) -> dict[str, Any] | None:
    for route in list_static_routes():
        if route["prefix"] != prefix:
            continue
        if family and route["family"] != family:
            continue
        return route
    return None
