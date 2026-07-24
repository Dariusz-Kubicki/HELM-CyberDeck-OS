# Feature Reference

This document explains every user-facing HELM subsystem.

## Global shell

- **Boot sequence:** animated initialization of core fabric, telemetry, hardware, network, storage, workspaces, local AI and security envelope; any key bypasses it.
- **Header:** health state, telemetry state, last collection duration and skipped overlapping cycles.
- **Signature rail:** active module, context, workspace and combined core status with state-dependent colors.
- **Sidebar:** grouped navigation plus live Core Health/Data and workspace state.
- **Ctrl+K:** global navigation, workspace activation, deterministic diagnostics and Core Health report actions.

## SYSTEM — Core Telemetry

- Host, user, OS, kernel and online state.
- CPU usage/temperature, GPU usage/temperature/power, RAM and root storage cards.
- CPU, RAM and GPU history with current/average/maximum values.
- Load averages, swap, logical/physical cores, per-core usage/frequency and top processes.
- Threshold alerts with state-transition logging.
- Actions: `btop`, `sensors`, `nvidia-smi`, full shell diagnostic.

## NETWORK — Network Fabric

- Active interface, IPv4, link state/speed, download/upload rate and byte totals.
- Transfer history.
- Gateway and DNS discovery, latency and packet loss.
- Remote connection and listening-socket tables with process names.
- Actions: ping gateway/internet, trace route, DNS query and socket monitor.

## STORAGE — Data Vault

- Root usage, free capacity and read/write throughput.
- I/O history graphs.
- Physical drive and partition inventory.
- NVMe temperature, cached SMART state and aggregate health.
- Actions: SMART report, drive map, home usage, open mountpoint and refresh.
- Missing SMART telemetry is not treated as proof of disk failure.

## DEVICES — Hardware Matrix

- USB and serial inventory with VID/PID, driver and permissions.
- Hot-plug event timeline.
- UART device selection, baud-rate cycling, connect/disconnect, RX/TX transcript, send and clear.
- Actions: Arduino IDE, port info and refresh.

## MODES — Workspace Engine

- Built-in CHILL, MAKER, DEVELOPMENT, FOCUS and COMMAND profiles.
- Edit telemetry interval, target screen, navigation logging, workload, power profile, objective, description and features.
- Create, clone, delete and activate workspaces.
- Application manifest: enable/disable, launch selected, add web app, remove, or launch all enabled entries on activation.
- Supports `{project_root}` and `{home}` placeholders.

## PROJECTS — Mission Control

- Summary counts, focus project, active/completed tables.
- Create/edit/delete records; status, priority and progress controls.
- Technology list, path, GitHub URL, description and next action.
- `STABLE` and `DONE` records move to the completed table.
- Actions: open folder, terminal, editor and validated HTTPS GitHub URL.

## LOGS — Event Archive

- Thread-safe persistent log with file rotation.
- Level/source/text filters.
- Pause/resume with pending count.
- Row inspector, jump newest, clear view, export filtered and guarded file clear.

## AI — Local Intelligence

### Deterministic core

Predictable reports for system, CPU, GPU, RAM, storage, network, devices, projects and host data, plus quick diagnostic buttons.

### Local Ollama core

- Provider/version/model state.
- Streaming `/api/chat` responses.
- Configurable model, context and keep-alive.
- Live read-only `SystemSnapshot` context.
- Bounded history, stop generation, clear/export session and token/time metrics.
- Prompt safeguards against false execution claims and overinterpretation of missing telemetry.

## SETTINGS — System Control

- Telemetry interval, startup screen, log rows and navigation logging.
- Ollama model, context window and keep-alive.
- Validate/apply without restart.
- Automatic/manual backup, export, latest-backup restore and defaults reset with confirmations.
- Diagnostics for config validity, paths, backups/exports, active mode and Ollama state.

## Core Health Service

Runs after the first usable snapshot and checks telemetry state/performance, JSON configuration, workspace consistency, directories, system tools, Python, Ollama service/API/model, Git state and previous-session errors. Reports can be shown in AI and exported as Markdown.
