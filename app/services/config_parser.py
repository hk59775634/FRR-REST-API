import re
from typing import Any


_SKIP_PREFIXES = (
    "Building configuration",
    "Current configuration",
)


def _strip_preamble(lines: list[str]) -> list[str]:
    started = False
    result: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not started:
            if stripped in ("!", "") or any(stripped.startswith(p) for p in _SKIP_PREFIXES):
                if stripped == "!":
                    started = True
                continue
            started = True
        if stripped == "end":
            break
        result.append(line.rstrip())
    return result


def _parse_global_line(line: str, global_cfg: dict[str, Any]) -> None:
    stripped = line.strip()
    if not stripped or stripped == "!":
        return

    if stripped.startswith("frr version "):
        global_cfg["frr_version"] = stripped.removeprefix("frr version ").strip()
        return
    if stripped.startswith("frr defaults "):
        global_cfg["frr_defaults"] = stripped.removeprefix("frr defaults ").strip()
        return
    if stripped.startswith("hostname "):
        global_cfg["hostname"] = stripped.removeprefix("hostname ").strip()
        return
    if stripped.startswith("log "):
        global_cfg.setdefault("logging", []).append(stripped.removeprefix("log ").strip())
        return
    if stripped == "no ip forwarding":
        global_cfg.setdefault("forwarding", {})["ipv4"] = False
        return
    if stripped == "ip forwarding":
        global_cfg.setdefault("forwarding", {})["ipv4"] = True
        return
    if stripped == "no ipv6 forwarding":
        global_cfg.setdefault("forwarding", {})["ipv6"] = False
        return
    if stripped == "ipv6 forwarding":
        global_cfg.setdefault("forwarding", {})["ipv6"] = True
        return
    if stripped.startswith("service "):
        global_cfg.setdefault("services", []).append(stripped.removeprefix("service ").strip())
        return

    global_cfg.setdefault("commands", []).append(stripped)


def _parse_block(lines: list[str]) -> dict[str, Any] | None:
    if not lines:
        return None

    header = lines[0].strip()
    if not header or header == "!":
        return None

    body: list[str] = []
    exited = False
    for line in lines[1:]:
        stripped = line.strip()
        if stripped == "exit":
            exited = True
            break
        if stripped and stripped != "!":
            body.append(stripped)

    block: dict[str, Any] = {"header": header, "commands": body}
    if exited:
        block["exit"] = True

    match = re.match(r"^(router|interface|vrf|key chain)\s+(.+)$", header)
    if match:
        block["type"] = match.group(1)
        block["name"] = match.group(2)

    return block


def parse_running_config(raw: str) -> dict[str, Any]:
    """将 vtysh show running-config 输出解析为结构化 JSON。"""
    lines = _strip_preamble(raw.splitlines())

    sections: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if line.strip() == "!":
            if current:
                sections.append(current)
                current = []
            continue
        current.append(line)
    if current:
        sections.append(current)

    global_cfg: dict[str, Any] = {
        "frr_version": None,
        "frr_defaults": None,
        "hostname": None,
        "forwarding": {},
        "logging": [],
        "services": [],
        "commands": [],
    }
    blocks: list[dict[str, Any]] = []

    for i, section in enumerate(sections):
        if i == 0:
            for line in section:
                _parse_global_line(line, global_cfg)
        else:
            block = _parse_block(section)
            if block:
                blocks.append(block)

    # 清理空字段
    for key in ("logging", "services", "commands"):
        if not global_cfg[key]:
            del global_cfg[key]
    if not global_cfg["forwarding"]:
        del global_cfg["forwarding"]
    for key in ("frr_version", "frr_defaults", "hostname"):
        if global_cfg[key] is None:
            del global_cfg[key]

    clean_lines = [ln.strip() for ln in lines if ln.strip() and ln.strip() not in ("!", "end")]

    return {
        "global": global_cfg,
        "blocks": blocks,
        "lines": clean_lines,
    }
