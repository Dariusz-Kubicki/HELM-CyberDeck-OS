import platform
import socket
import getpass
import subprocess


def get_system_info():
    try:
        uptime = subprocess.check_output(
            ["uptime", "-p"], text=True
        ).strip().replace("up ", "")
    except Exception:
        uptime = "Unknown"

    return {
        "host": socket.gethostname(),
        "user": getpass.getuser(),
        "os": platform.system(),
        "kernel": platform.release(),
        "uptime": uptime,
    }
