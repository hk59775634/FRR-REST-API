import subprocess


class VtyshError(Exception):
    def __init__(self, message: str, returncode: int = 1, stdout: str = "", stderr: str = ""):
        super().__init__(message)
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def run_vtysh(command: str) -> str:
    result = subprocess.run(
        ["vtysh", "-c", command],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise VtyshError(
            f"vtysh 命令执行失败: {command}",
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )
    return result.stdout


def run_vtysh_commands(commands: list[str], *, write_memory: bool = False) -> str:
    """在 configure terminal 模式下执行多条命令。"""
    args = ["vtysh", "-c", "configure terminal"]
    for cmd in commands:
        args.extend(["-c", cmd])
    args.extend(["-c", "end"])
    if write_memory:
        args.extend(["-c", "write memory"])

    result = subprocess.run(args, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        output = (result.stdout + result.stderr).strip()
        raise VtyshError(
            f"配置命令执行失败: {output or commands}",
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )
    return result.stdout
