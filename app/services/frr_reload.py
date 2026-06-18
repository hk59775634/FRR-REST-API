import subprocess
import tempfile
from pathlib import Path

from app.config import settings
from app.services.config_parser import parse_running_config
from app.services.vtysh import VtyshError, run_vtysh


class FrrReloadError(VtyshError):
    pass


def _base_cmd() -> list[str]:
    return [
        settings.frr_reload_script,
        "--bindir",
        settings.frr_bindir,
        "--confdir",
        settings.frr_conf_dir,
        "--rundir",
        settings.frr_run_dir,
        "--stdout",
    ]


def run_frr_reload(config_content: str, *, apply: bool) -> dict:
    """调用 frr-reload.py 预览或应用配置变更。"""
    mode_flag = "--reload" if apply else "--test"

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".conf",
        prefix="frr-reload-",
        delete=False,
        encoding="utf-8",
    ) as tmp:
        tmp.write(config_content)
        tmp_path = tmp.name

    try:
        cmd = _base_cmd() + [mode_flag, tmp_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return {
        "success": result.returncode == 0,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "mode": "reload" if apply else "test",
    }


def read_frr_conf() -> str:
    path = Path(settings.frr_conf_path)
    if not path.exists():
        raise FrrReloadError(f"配置文件不存在: {path}")
    return path.read_text(encoding="utf-8")


def write_frr_conf(content: str, *, backup: bool = True) -> str | None:
    path = Path(settings.frr_conf_path)
    backup_path = None

    if backup and path.exists():
        backup_path = str(path.with_suffix(path.suffix + ".bak"))
        path.rename(backup_path)

    path.write_text(content, encoding="utf-8")
    return backup_path
