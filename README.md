# FRR REST API

基于 [FRRouting](https://frrouting.org/) 的 REST API 服务，封装 `frr-reload.py` 与 `vtysh`，提供 HTTP 接口管理 FRR 配置、静态路由、BGP 及动态路由守护进程开关。

## 功能

- FRR 运行配置查询与 `frr-reload` 重载
- 静态路由 CRUD（支持 `write_memory` 持久化）
- BGP 邻居、network、路由表管理
- **动态路由开关**：通过 API 编辑 `/etc/frr/daemons` 启用/禁用 bgpd、ospfd、ripd 等
- OSPF / OSPFv6 / RIP / RIPng / IS-IS 状态查询
- ReDoc API 文档（中文）
- systemd 服务安装脚本

## 快速开始

```bash
cp .env.example .env   # 修改 API_KEY
./run.sh               # 前台启动

# 或安装为 systemd 服务
sudo ./systemctl.sh install
```

## API 文档

启动后访问：`http://<host>:8080/redoc`

认证：请求头 `X-API-Key: <your-key>`

## 动态路由开关示例

```bash
# 查看所有守护进程状态
curl -H "X-API-Key: your-key" http://localhost:8080/api/v1/daemons

# 启用 OSPF（修改 daemons 并重启 FRR）
curl -X PUT http://localhost:8080/api/v1/daemons/ospfd \
  -H "X-API-Key: your-key" -H "Content-Type: application/json" \
  -d '{"enabled": true, "restart": true}'

# 禁用 RIP
curl -X PUT http://localhost:8080/api/v1/daemons/ripd \
  -H "X-API-Key: your-key" -H "Content-Type: application/json" \
  -d '{"enabled": false, "restart": true}'
```

## 自检

```bash
./scripts/api_selftest.sh
```

## License

MIT
