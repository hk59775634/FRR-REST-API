#!/bin/bash
# FRR REST API systemd 服务管理
#
# 用法:
#   ./systemctl.sh install    安装并启用服务（注册 unit、enable、start）
#   ./systemctl.sh remove     停止、禁用并删除服务
#   ./systemctl.sh start      启动服务
#   ./systemctl.sh stop       停止服务
#   ./systemctl.sh restart    重启服务
#   ./systemctl.sh status     查看服务状态
#   ./systemctl.sh enable     设置开机自启
#   ./systemctl.sh disable    取消开机自启

set -euo pipefail

SERVICE_NAME="frr-rest-api"
INSTALL_DIR="$(cd "$(dirname "$0")" && pwd)"
UNIT_PATH="/etc/systemd/system/${SERVICE_NAME}.service"
TEMPLATE="${INSTALL_DIR}/deploy/frr-rest-api.service"

die() {
    echo "错误: $*" >&2
    exit 1
}

need_root() {
    if [[ "${EUID}" -ne 0 ]]; then
        die "此操作需要 root 权限，请使用: sudo $0 $*"
    fi
}

ensure_venv() {
    if [[ ! -d "${INSTALL_DIR}/.venv" ]]; then
        echo ">>> 创建 Python 虚拟环境..."
        python3 -m venv "${INSTALL_DIR}/.venv"
    fi
    echo ">>> 安装 Python 依赖..."
    "${INSTALL_DIR}/.venv/bin/pip" install -q -r "${INSTALL_DIR}/requirements.txt"
}

generate_unit() {
    sed "s|@INSTALL_DIR@|${INSTALL_DIR}|g" "${TEMPLATE}"
}

cmd_install() {
    need_root install
    [[ -f "${TEMPLATE}" ]] || die "未找到单元模板: ${TEMPLATE}"
    [[ -f "${INSTALL_DIR}/.env" ]] || die "未找到 .env，请先配置 ${INSTALL_DIR}/.env"

    ensure_venv

    echo ">>> 写入 systemd 单元: ${UNIT_PATH}"
    generate_unit > "${UNIT_PATH}"
    chmod 644 "${UNIT_PATH}"

    echo ">>> 重新加载 systemd..."
    systemctl daemon-reload

    echo ">>> 启用开机自启..."
    systemctl enable "${SERVICE_NAME}"

    echo ">>> 启动服务..."
    systemctl start "${SERVICE_NAME}"

    echo ""
    echo "安装完成。服务已注册并启动。"
    systemctl status "${SERVICE_NAME}" --no-pager -l || true
    echo ""
    echo "常用命令:"
    echo "  systemctl status ${SERVICE_NAME}"
    echo "  journalctl -u ${SERVICE_NAME} -f"
}

cmd_remove() {
    need_root remove

    if systemctl is-active --quiet "${SERVICE_NAME}" 2>/dev/null; then
        echo ">>> 停止服务..."
        systemctl stop "${SERVICE_NAME}"
    fi

    if systemctl is-enabled --quiet "${SERVICE_NAME}" 2>/dev/null; then
        echo ">>> 禁用开机自启..."
        systemctl disable "${SERVICE_NAME}"
    fi

    if [[ -f "${UNIT_PATH}" ]]; then
        echo ">>> 删除单元文件: ${UNIT_PATH}"
        rm -f "${UNIT_PATH}"
    else
        echo ">>> 单元文件不存在，跳过删除"
    fi

    echo ">>> 重新加载 systemd..."
    systemctl daemon-reload
    systemctl reset-failed "${SERVICE_NAME}" 2>/dev/null || true

    echo ""
    echo "服务已移除（项目文件保留在 ${INSTALL_DIR}）。"
}

cmd_start() {
    need_root start
    systemctl start "${SERVICE_NAME}"
    systemctl status "${SERVICE_NAME}" --no-pager -l
}

cmd_stop() {
    need_root stop
    systemctl stop "${SERVICE_NAME}"
    echo "服务已停止。"
}

cmd_restart() {
    need_root restart
    systemctl restart "${SERVICE_NAME}"
    systemctl status "${SERVICE_NAME}" --no-pager -l
}

cmd_status() {
    systemctl status "${SERVICE_NAME}" --no-pager -l || true
}

cmd_enable() {
    need_root enable
    systemctl enable "${SERVICE_NAME}"
    echo "已设置开机自启。"
}

cmd_disable() {
    need_root disable
    systemctl disable "${SERVICE_NAME}"
    echo "已取消开机自启。"
}

usage() {
    sed -n '3,12p' "$0" | sed 's/^# \{0,1\}//'
    exit 1
}

main() {
    local action="${1:-}"
    case "${action}" in
        install)  cmd_install ;;
        remove)   cmd_remove ;;
        start)    cmd_start ;;
        stop)     cmd_stop ;;
        restart)  cmd_restart ;;
        status)   cmd_status ;;
        enable)   cmd_enable ;;
        disable)  cmd_disable ;;
        -h|--help|help|"") usage ;;
        *) die "未知命令: ${action}（使用 --help 查看帮助）" ;;
    esac
}

main "$@"
