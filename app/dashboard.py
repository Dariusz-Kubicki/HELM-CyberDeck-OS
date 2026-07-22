from textual.containers import Horizontal
from textual.app import ComposeResult

from app.widgets import InfoBox
from modules.hardware import (
    get_cpu_usage,
    get_ram_usage,
    get_disk_usage,
)

from modules.gpu import get_gpu_info


class Dashboard(Horizontal):

    def compose(self) -> ComposeResult:
        yield InfoBox("CPU")
        yield InfoBox("GPU")
        yield InfoBox("RAM")
        yield InfoBox("SSD")

    def on_mount(self):
        self.set_interval(1, self.update_stats)

    def update_stats(self):

        gpu = get_gpu_info()

        boxes = list(self.query(InfoBox))

        boxes = list(self.query(InfoBox))

        boxes[0].update_value(
            f"{get_cpu_usage()} %"
        )

        boxes[1].update_value(
            f"{gpu['usage']} %\n"
            f"{gpu['temp']} °C\n"
            f"{gpu['power']} W"
        )

        boxes[2].update_value(
            f"{get_ram_usage()} %"
        )

        boxes[3].update_value(
            f"{get_disk_usage()} %"
        )
