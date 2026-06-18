"""FRR 动态路由协议守护进程注册表。"""

from typing import Any

# always_on: watchfrr/zebra/staticd 由 FRR 始终启动，不可通过 API 关闭
DAEMON_REGISTRY: dict[str, dict[str, Any]] = {
    "bgpd": {
        "protocol": "bgp",
        "name_zh": "BGP",
        "description": "边界网关协议",
        "api_prefix": "/api/v1/bgp",
    },
    "ospfd": {
        "protocol": "ospf",
        "name_zh": "OSPFv2",
        "description": "开放最短路径优先（IPv4）",
        "api_prefix": "/api/v1/ospf",
    },
    "ospf6d": {
        "protocol": "ospf6",
        "name_zh": "OSPFv3",
        "description": "开放最短路径优先（IPv6）",
        "api_prefix": "/api/v1/ospf6",
    },
    "ripd": {
        "protocol": "rip",
        "name_zh": "RIPv2",
        "description": "路由信息协议（IPv4）",
        "api_prefix": "/api/v1/rip",
    },
    "ripngd": {
        "protocol": "ripng",
        "name_zh": "RIPng",
        "description": "路由信息协议（IPv6）",
        "api_prefix": "/api/v1/ripng",
    },
    "isisd": {
        "protocol": "isis",
        "name_zh": "IS-IS",
        "description": "中间系统到中间系统",
        "api_prefix": "/api/v1/isis",
    },
    "ldpd": {
        "protocol": "ldp",
        "name_zh": "LDP",
        "description": "标签分发协议",
        "api_prefix": None,
    },
    "pimd": {
        "protocol": "pim",
        "name_zh": "PIM",
        "description": "协议无关组播（IPv4）",
        "api_prefix": None,
    },
    "pim6d": {
        "protocol": "pim6",
        "name_zh": "PIMv6",
        "description": "协议无关组播（IPv6）",
        "api_prefix": None,
    },
    "nhrpd": {
        "protocol": "nhrp",
        "name_zh": "NHRP",
        "description": "下一跳解析协议",
        "api_prefix": None,
    },
    "eigrpd": {
        "protocol": "eigrp",
        "name_zh": "EIGRP",
        "description": "增强内部网关路由协议",
        "api_prefix": None,
    },
    "babeld": {
        "protocol": "babel",
        "name_zh": "Babel",
        "description": "Babel 路由协议",
        "api_prefix": None,
    },
    "bfdd": {
        "protocol": "bfd",
        "name_zh": "BFD",
        "description": "双向转发检测",
        "api_prefix": None,
    },
}

ALWAYS_ON_DAEMONS = frozenset({"zebra", "staticd", "watchfrr"})
