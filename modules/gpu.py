import subprocess


def get_gpu_info():
    try:
        result = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=temperature.gpu,utilization.gpu,memory.used,power.draw",
                "--format=csv,noheader,nounits",
            ],
            text=True,
        )

        temp, usage, memory, power = result.strip().split(",")

        return {
            "temp": temp.strip(),
            "usage": usage.strip(),
            "memory": memory.strip(),
            "power": power.strip(),
        }

    except Exception:
        return {
            "temp": "N/A",
            "usage": "N/A",
            "memory": "N/A",
            "power": "N/A",
        }
