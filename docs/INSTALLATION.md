# Installation

## Target environment

HELM v1.0 was built and tested on Arch Linux, KDE Plasma/Wayland, Konsole, NVIDIA telemetry and a local Ollama service. Other Linux systems may work, but package names and desktop actions can differ.

## 1. Clone

```bash
git clone https://github.com/Dariusz-Kubicki/HELM-CyberDeck-OS.git
cd HELM-CyberDeck-OS
```

The repository may live anywhere; `~/.cyberdeck/nexus` is optional.

## 2. Python environment

```bash
python -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Arch also packages the dependencies as `python-textual`, `python-psutil` and `python-pyserial`, but the virtual environment reproduces the pinned v1.0 versions.

## 3. Linux integrations

Practical Arch base:

```bash
sudo pacman -S --needed \
    python git iproute2 iputils networkmanager \
    lm_sensors smartmontools btop usbutils
```

Optional actions:

```bash
sudo pacman -S --needed traceroute bind ncdu power-profiles-daemon
```

HELM detects supported terminal emulators, file managers, code editors and Arduino IDE alternatives at runtime.

```bash
sudo sensors-detect
```

## 4. Ollama — optional

Install Ollama, enable the local service and pull the default model:

```bash
sudo systemctl enable --now ollama.service
ollama pull qwen3:8b
```

Verify:

```bash
ollama list
curl http://127.0.0.1:11434/api/version
```

The model, context and keep-alive are editable in SETTINGS. Model weights are not bundled.

## 5. Serial permissions

Arch serial ports commonly require the `uucp` group:

```bash
sudo usermod -aG uucp "$USER"
```

Log out and back in, then verify:

```bash
groups
ls -l /dev/ttyUSB* /dev/ttyACM* 2>/dev/null
```

## 6. Run

```bash
source venv/bin/activate
python -m app.main
```

or:

```bash
./scripts/run-helm.sh
```

## 7. Terminal size

The intended layout was tuned around **122 columns × 57 lines**. Smaller terminals remain scrollable but some rails may wrap.

## 8. Verify

Press **Ctrl+K** and run `Run HELM health diagnostic`. Missing optional tools produce warnings; critical configuration failures are reported separately.

## SMART access

`smartctl` may require root privileges. HELM reports `RESTRICTED` or `UNAVAILABLE` rather than prompting inside the telemetry worker. The optional helper path `/usr/local/lib/helm/helm-smart-status` is supported but not installed automatically.

## Troubleshooting

```bash
systemctl status ollama.service
journalctl -u ollama.service -n 100 --no-pager
sensors
python -m serial.tools.list_ports -v
python -m compileall -q app modules services
```

## Runtime data directory

On first start HELM creates or migrates mutable JSON under:

```text
~/.local/share/helm
```

Use an isolated location for testing:

```bash
export HELM_DATA_DIR="$HOME/.local/share/helm-test"
./scripts/run-helm.sh
```

Do not copy live `config/*.json` into the repository for normal operation. The
tracked `config/*.example.json` files are templates; migration from old ignored
files is automatic and non-destructive.
