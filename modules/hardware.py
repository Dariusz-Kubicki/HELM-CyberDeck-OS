import psutil
import subprocess
import re


def get_cpu_usage():
    return round(psutil.cpu_percent(interval=None), 1)


def get_ram_usage():
    return round(psutil.virtual_memory().percent, 1)


def get_disk_usage():
    return round(psutil.disk_usage("/").percent, 1)


def get_cpu_temp():
    try:
        output = subprocess.check_output(["sensors"], text=True)

        match = re.search(r"Tctl:\s+\+([0-9.]+)", output)

        if match:
            return float(match.group(1))

    except Exception:
        pass

    return None
