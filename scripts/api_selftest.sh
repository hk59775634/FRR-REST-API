#!/bin/bash
# FRR REST API 全量接口自检脚本
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8080}"
API_KEY="${API_KEY:-$(grep -E '^API_KEY=' /opt/frr-rest-api/.env 2>/dev/null | cut -d= -f2-)}"
HDR=(-H "X-API-Key: ${API_KEY}" -H "Content-Type: application/json")

PASS=0
FAIL=0
TEST_PREFIX="10.99.0.0/24"
TEST_NH="100.64.0.18"
TEST_NET="10.99.0.1/32"

log() { echo "[TEST] $*"; }
ok()  { PASS=$((PASS+1)); log "✓ $*"; }
bad() { FAIL=$((FAIL+1)); log "✗ $*"; exit 1; }

check_code() {
    local method="$1" path="$2" expect="$3"
    shift 3
    local code
    code=$(curl -s -o /tmp/api_test_body.json -w "%{http_code}" -X "$method" "${BASE_URL}${path}" "${HDR[@]}" "$@")
    if [[ "$code" == "$expect" ]]; then
        ok "${method} ${path} -> ${code}"
    else
        cat /tmp/api_test_body.json
        bad "${method} ${path} expected ${expect} got ${code}"
    fi
}

log "=== 系统 ==="
check_code GET /health 200
check_code GET / 200

log "=== FRR 配置 ==="
check_code GET /api/v1/status 200
check_code GET /api/v1/running-config 200
check_code GET /api/v1/config 200

log "=== 动态路由守护进程 ==="
check_code GET /api/v1/daemons 200
check_code GET /api/v1/daemons/bgpd 200

# 仅修改 daemons 文件，不重启 FRR（避免中断 BGP）
check_code PUT /api/v1/daemons/ripd 200 -d '{"enabled":true,"restart":false}'
grep -q '^ripd=yes' /etc/frr/daemons || bad "ripd=yes not in daemons"
check_code PUT /api/v1/daemons/ripd 200 -d '{"enabled":false,"restart":false}'
grep -q '^ripd=no' /etc/frr/daemons || bad "ripd=no not in daemons"
ok "daemons toggle without restart"

log "=== 静态路由 ==="
check_code GET /api/v1/routes/static 200
check_code POST /api/v1/routes/static 200 -d "{\"prefix\":\"${TEST_PREFIX}\",\"nexthop\":\"${TEST_NH}\"}"
check_code GET "/api/v1/routes/static/${TEST_PREFIX}" 200
check_code DELETE /api/v1/routes/static 200 -d "{\"prefix\":\"${TEST_PREFIX}\",\"nexthop\":\"${TEST_NH}\"}"

log "=== BGP ==="
check_code GET /api/v1/bgp/instance 200
check_code GET /api/v1/bgp/summary 200
check_code GET /api/v1/bgp/neighbors 200
check_code GET /api/v1/bgp/routes 200

# BGP 写操作（若已有邻居则跳过创建）
BGP_NEI=$(curl -s "${BASE_URL}/api/v1/bgp/neighbors" "${HDR[@]}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['neighbors'][0]['address'] if d.get('neighbors') else '')" 2>/dev/null || true)
if [[ -n "$BGP_NEI" ]]; then
    check_code GET "/api/v1/bgp/neighbors/${BGP_NEI}" 200
    ok "BGP neighbor detail ${BGP_NEI}"
else
    log "跳过 BGP 邻居写操作（无现有邻居）"
fi

log "=== OSPF / RIP / IS-IS 读接口 ==="
check_code GET /api/v1/ospf/instance 200
check_code GET /api/v1/ospf/summary 200
check_code GET /api/v1/ospf/neighbors 200
check_code GET /api/v1/ospf/routes 200
check_code GET /api/v1/ospf6/instance 200
check_code GET /api/v1/ospf6/summary 200
check_code GET /api/v1/rip/instance 200
check_code GET /api/v1/rip/status 200
check_code GET /api/v1/ripng/instance 200
check_code GET /api/v1/ripng/status 200
check_code GET /api/v1/isis/instance 200
check_code GET /api/v1/isis/summary 200
check_code GET /api/v1/isis/neighbors 200

log "=== 动态路由写接口（守护进程已运行时） ==="
OSPF_CFG=$(curl -s "${BASE_URL}/api/v1/ospf/instance" "${HDR[@]}")
if echo "$OSPF_CFG" | python3 -c "import sys,json; exit(0 if not json.load(sys.stdin).get('configured') else 1)" 2>/dev/null; then
    check_code POST /api/v1/ospf/instance 200 -d '{"router_id":"1.1.1.1"}'
fi
check_code POST /api/v1/ospf/networks 200 -d '{"prefix":"10.88.0.0/24","area":"0"}'
check_code DELETE /api/v1/ospf/networks 200 -d '{"prefix":"10.88.0.0/24","area":"0"}'
if echo "$OSPF_CFG" | python3 -c "import sys,json; exit(0 if not json.load(sys.stdin).get('configured') else 1)" 2>/dev/null; then
    check_code DELETE /api/v1/ospf/instance 200
fi

# RIP
RIP_CFG=$(curl -s "${BASE_URL}/api/v1/rip/instance" "${HDR[@]}")
if echo "$RIP_CFG" | python3 -c "import sys,json; exit(0 if json.load(sys.stdin).get('configured') else 1)" 2>/dev/null; then
    check_code POST /api/v1/rip/networks 200 -d '{"prefix":"10.88.1.0/24"}'
    check_code DELETE /api/v1/rip/networks 200 -d '{"prefix":"10.88.1.0/24"}'
else
    check_code POST /api/v1/rip/instance 200 -d '{"version":2}'
    check_code POST /api/v1/rip/networks 200 -d '{"prefix":"10.88.1.0/24"}'
    check_code DELETE /api/v1/rip/networks 200 -d '{"prefix":"10.88.1.0/24"}'
fi

# IS-IS
ISIS_CFG=$(curl -s "${BASE_URL}/api/v1/isis/instance" "${HDR[@]}")
if echo "$ISIS_CFG" | python3 -c "import sys,json; exit(0 if json.load(sys.stdin).get('configured') else 1)" 2>/dev/null; then
    check_code PATCH /api/v1/isis/instance 200 -d '{"is_type":"level-1-2"}'
    check_code PATCH /api/v1/isis/instance 200 -d '{"is_type":"level-2-only"}'
else
    check_code POST /api/v1/isis/instance 200 -d '{"tag":"TEST","net":"49.0001.0000.0000.0099.00"}'
    check_code DELETE /api/v1/isis/instance 200
fi

log "=== 认证失败 ==="
code=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/api/v1/status")
[[ "$code" == "401" ]] && ok "missing API key -> 401" || bad "expected 401 got ${code}"

log "=== reload test (dry-run) ==="
RUNNING=$(curl -s "${BASE_URL}/api/v1/running-config" "${HDR[@]}" | python3 -c "import sys,json; print(json.load(sys.stdin)['lines'][0])" 2>/dev/null || echo "frr version 8.4")
check_code POST /api/v1/reload/test 200 -d "{\"content\":\"frr version 8.4\\nfrr defaults traditional\\nhostname test\\n\"}"

echo ""
echo "=============================="
echo "自检完成: ${PASS} 通过, ${FAIL} 失败"
echo "=============================="
