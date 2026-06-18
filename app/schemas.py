from typing import Any, Literal

from pydantic import BaseModel, Field


class ConfigContent(BaseModel):
    content: str = Field(
        ...,
        description="FRR 配置文本内容（与 frr.conf 格式相同）",
        examples=["frr version 8.4\nfrr defaults traditional\nhostname router\n"],
    )
    save_to_file: bool = Field(
        default=False,
        description="是否在重载前将配置保存到 frr.conf 文件",
    )
    backup: bool = Field(
        default=True,
        description="保存到文件时是否自动备份原 frr.conf 为 frr.conf.bak",
    )


class ReloadResult(BaseModel):
    success: bool = Field(description="操作是否成功")
    returncode: int = Field(description="frr-reload.py 退出码，0 表示成功")
    stdout: str = Field(description="标准输出（配置差异或执行日志）")
    stderr: str = Field(description="标准错误输出")
    mode: str = Field(description="执行模式：test（预览）或 reload（应用）")
    backup_path: str | None = Field(
        default=None,
        description="若保存了配置文件，此处为备份文件路径",
    )


class RunningConfig(BaseModel):
    global_: dict = Field(
        alias="global",
        description="全局配置项（hostname、版本、转发等）",
    )
    blocks: list[dict] = Field(
        default_factory=list,
        description="配置块列表（如 router bgp、interface 等）",
    )
    lines: list[str] = Field(
        description="去除 vtysh 提示信息后的配置行列表",
    )

    model_config = {"populate_by_name": True}


class ConfigFile(BaseModel):
    path: str = Field(description="配置文件路径")
    global_: dict = Field(
        alias="global",
        description="全局配置项",
    )
    blocks: list[dict] = Field(
        default_factory=list,
        description="配置块列表",
    )
    lines: list[str] = Field(description="配置文件行列表")
    content: str = Field(description="配置文件原始文本")

    model_config = {"populate_by_name": True}


class FrrStatus(BaseModel):
    version: str = Field(description="FRR 版本信息")
    running: bool = Field(description="FRR 服务是否可用")


class HealthResponse(BaseModel):
    status: str = Field(description="服务健康状态")
    message: str = Field(description="状态说明")


class StaticRoute(BaseModel):
    family: Literal["ipv4", "ipv6"] = Field(default="ipv4", description="地址族：ipv4 或 ipv6")
    prefix: str = Field(..., description="目标网段，如 10.0.0.0/24", examples=["10.0.0.0/24"])
    type: Literal["unicast", "blackhole", "reject"] = Field(
        default="unicast",
        description="路由类型：单播、黑洞或拒绝",
    )
    nexthop: str | None = Field(default=None, description="下一跳地址", examples=["192.168.1.1"])
    interface: str | None = Field(default=None, description="出接口（可选）", examples=["eth0"])
    distance: int | None = Field(default=None, description="管理距离（1-255）", ge=1, le=255)


class StaticRouteCreate(StaticRoute):
    write_memory: bool = Field(
        default=False,
        description="是否执行 write memory 将配置持久化到 frr.conf",
    )


class StaticRouteResponse(StaticRoute):
    raw: str | None = Field(default=None, description="原始配置行")


class StaticRouteList(BaseModel):
    configured: list[StaticRouteResponse] = Field(description="运行配置中的静态路由")
    installed: list[dict[str, Any]] = Field(description="路由表中已安装的静态路由")


class StaticRouteActionResult(BaseModel):
    success: bool = Field(default=True, description="操作是否成功")
    message: str = Field(description="操作结果说明")
    command: str = Field(description="执行的 vtysh 命令")
    write_memory: bool = Field(default=False, description="是否已持久化到 frr.conf")


class BgpNeighborCreate(BaseModel):
    address: str = Field(..., description="邻居地址（IP 或接口名）", examples=["192.168.1.2"])
    remote_as: int = Field(..., description="对端 AS 号", examples=[65001])
    description: str | None = Field(default=None, description="邻居描述")
    update_source: str | None = Field(default=None, description="BGP 更新源地址/接口")
    write_memory: bool = Field(default=False, description="是否持久化到 frr.conf")


class BgpNeighborUpdate(BaseModel):
    description: str | None = Field(default=None, description="邻居描述")
    update_source: str | None = Field(default=None, description="BGP 更新源")
    write_memory: bool = Field(default=False, description="是否持久化到 frr.conf")


class BgpNetworkCreate(BaseModel):
    network: str = Field(..., description="宣告网段", examples=["10.0.0.0/24"])
    write_memory: bool = Field(default=False, description="是否持久化到 frr.conf")


class BgpActionResult(BaseModel):
    success: bool = Field(default=True, description="操作是否成功")
    message: str = Field(description="操作结果说明")


class BgpInstance(BaseModel):
    local_as: int | None = Field(description="本地 AS 号")
    configured: bool = Field(description="是否已配置 BGP")
    neighbors: list[dict[str, Any]] = Field(description="已配置的邻居列表")
    networks: list[str] = Field(description="已宣告的网络列表")
    commands: list[str] = Field(description="BGP 配置命令列表")


class BgpNeighborList(BaseModel):
    neighbors: list[dict[str, Any]] = Field(description="邻居列表（含配置与运行状态）")
    total: int = Field(description="邻居总数")


class BgpRouteList(BaseModel):
    afi: str = Field(description="地址族")
    routes: list[dict[str, Any]] = Field(description="BGP 路由表条目")
    total: int = Field(description="路由条目数")


class DaemonStatus(BaseModel):
    daemon: str = Field(description="守护进程名称，如 bgpd、ospfd")
    protocol: str = Field(description="协议标识")
    name_zh: str = Field(description="中文名称")
    description: str = Field(description="协议说明")
    enabled: bool = Field(description="是否在 daemons 中启用")
    running: bool = Field(description="进程是否正在运行")
    manageable: bool = Field(description="是否可通过 API 开关")
    api_prefix: str | None = Field(default=None, description="对应协议 API 路径前缀")


class DaemonList(BaseModel):
    daemons: list[DaemonStatus] = Field(description="守护进程列表")
    frr_service: dict[str, Any] = Field(description="FRR systemd 服务状态")


class DaemonToggle(BaseModel):
    enabled: bool = Field(..., description="是否启用该守护进程")
    restart: bool = Field(
        default=True,
        description="修改 daemons 后是否重启 FRR 服务使变更生效",
    )


class DaemonActionResult(BaseModel):
    success: bool = Field(default=True, description="操作是否成功")
    message: str = Field(description="操作结果说明")
    daemon: str = Field(description="守护进程名称")
    enabled: bool = Field(description="当前启用状态")
    running: bool = Field(description="当前运行状态")
    restarted: bool = Field(default=False, description="是否已重启 FRR")
    backup_path: str | None = Field(default=None, description="daemons 备份文件路径")


class ProtocolInstance(BaseModel):
    configured: bool = Field(description="运行配置中是否已配置该协议")
    commands: list[str] = Field(default_factory=list, description="协议配置命令")
    running: bool | None = Field(default=None, description="守护进程是否运行中")


class WriteMemoryOption(BaseModel):
    write_memory: bool = Field(default=False, description="是否持久化到 frr.conf")


class ProtocolActionResult(BaseModel):
    success: bool = Field(default=True, description="操作是否成功")
    message: str = Field(description="操作结果说明")
    write_memory: bool = Field(default=False, description="是否已写入 frr.conf")


class OspfInstanceCreate(WriteMemoryOption):
    router_id: str | None = Field(default=None, description="OSPF Router ID", examples=["1.1.1.1"])
    vrf: str | None = Field(default=None, description="VRF 名称，默认 default")


class OspfInstanceUpdate(WriteMemoryOption):
    router_id: str = Field(..., description="OSPF Router ID")
    vrf: str | None = Field(default=None, description="VRF 名称")


class OspfNetworkBody(WriteMemoryOption):
    prefix: str = Field(..., description="网段", examples=["10.0.0.0/24"])
    area: str = Field(..., description="OSPF 区域", examples=["0"])
    vrf: str | None = Field(default=None, description="VRF 名称")


class OspfRedistributeBody(WriteMemoryOption):
    protocol: Literal["static", "connected", "bgp", "kernel", "rip", "isis"] = Field(
        ..., description="重分发源协议"
    )
    enabled: bool = Field(default=True, description="启用或禁用重分发")
    metric_type: Literal["1", "2"] | None = Field(default=None, description="外部路由 metric-type")
    vrf: str | None = Field(default=None, description="VRF 名称")


class OspfInterfaceBody(WriteMemoryOption):
    area: str = Field(..., description="OSPF 区域")
    network_type: Literal["broadcast", "point-to-point", "non-broadcast"] | None = Field(
        default=None, description="接口网络类型"
    )


class Ospf6InstanceCreate(WriteMemoryOption):
    router_id: str | None = Field(default=None, description="OSPFv3 Router ID")


class Ospf6InterfaceBody(WriteMemoryOption):
    area: str = Field(..., description="OSPFv3 区域")


class Ospf6RedistributeBody(WriteMemoryOption):
    protocol: Literal["static", "connected", "bgp", "kernel"] = Field(..., description="重分发源协议")
    enabled: bool = Field(default=True, description="启用或禁用")


class RipInstanceCreate(WriteMemoryOption):
    version: int = Field(default=2, description="RIP 版本", ge=1, le=2)


class RipNetworkBody(WriteMemoryOption):
    prefix: str = Field(..., description="宣告网段", examples=["100.64.0.0/24"])


class RipRedistributeBody(WriteMemoryOption):
    protocol: Literal["static", "connected", "bgp", "ospf", "isis", "kernel"] = Field(
        ..., description="重分发源协议"
    )
    enabled: bool = Field(default=True, description="启用或禁用")


class RipngInterfaceBody(WriteMemoryOption):
    interface: str = Field(..., description="参与 RIPng 的接口名", examples=["ens18"])


class RipngRedistributeBody(WriteMemoryOption):
    protocol: Literal["static", "connected", "bgp", "ospf6", "kernel"] = Field(
        ..., description="重分发源协议"
    )
    enabled: bool = Field(default=True, description="启用或禁用")


class IsisInstanceCreate(WriteMemoryOption):
    tag: str = Field(..., description="IS-IS 实例标签", examples=["FRR"])
    net: str | None = Field(
        default=None,
        description="NET 地址",
        examples=["49.0001.0000.0000.0001.00"],
    )
    is_type: Literal["level-1", "level-2-only", "level-1-2"] | None = Field(
        default="level-2-only", description="IS 类型"
    )


class IsisInstanceUpdate(WriteMemoryOption):
    net: str | None = Field(default=None, description="NET 地址")
    is_type: Literal["level-1", "level-2-only", "level-1-2"] | None = Field(
        default=None, description="IS 类型"
    )


class IsisRedistributeBody(WriteMemoryOption):
    protocol: Literal["static", "connected", "bgp", "ospf", "rip", "kernel"] = Field(
        ..., description="重分发源协议"
    )
    enabled: bool = Field(default=True, description="启用或禁用")
