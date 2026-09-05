#!/usr/bin/env python3
"""Interactive / non-interactive device role configurator.

Used by startup scripts. Persists to <repo>/.satquery/device.json.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running as `python scripts/configure_role.py` from repo root
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

from app.node.config_store import (  # noqa: E402
    DEFAULT_HOST_VLM_OLLAMA_TAG,
    HOST_VLM_DISPLAY_NAME,
    DeviceRole,
    clear_device_config,
    config_summary,
    device_config_path,
    load_device_config,
    local_ip,
    new_device_config,
    save_device_config,
)
from app.node.hardware import probe_hardware  # noqa: E402


def _print_banner(cfg) -> None:
    hw = probe_hardware()
    print()
    print("=" * 56)
    role = cfg.role
    if role == DeviceRole.MODEL_HOST.value:
        print("  SatQuery Model Host")
    elif role == DeviceRole.CONTROLLER.value:
        print("  SatQuery Controller")
    else:
        print("  SatQuery Full System")
    print("=" * 56)
    print(f"  Node ID:      {cfg.node_id}")
    print(f"  Role:         {cfg.role}")
    print(f"  LAN address:  {local_ip()}")
    if role == DeviceRole.MODEL_HOST.value:
        print(f"  Node port:    {cfg.node_port}")
        print(f"  Pairing code: {cfg.pairing_code}")
        print()
        print("  Capabilities:")
        for m in cfg.hosted_models or []:
            tasks = ", ".join(m.get("tasks") or [])
            tag = m.get("ollama_tag") or ""
            print(f"    ✓ {m.get('id')} ({tasks})")
            if tag:
                print(f"      Ollama: {tag}")
        print()
        print("  Hardware:")
        print(f"    GPU:  {hw.get('gpu_name') or ('yes' if hw.get('gpu_available') else 'no / unknown')}")
        print(f"    VRAM: {hw.get('vram_gb') if hw.get('vram_gb') is not None else 'unknown'} GB")
        print(f"    RAM:  {hw.get('ram_gb') if hw.get('ram_gb') is not None else 'unknown'} GB")
        print(f"    Qwen VQA: {hw.get('qwen_vl_support')}")
        print()
        print("  Waiting for Controller pairing...")
        print(f"  Pair from Controller with: {local_ip()}:{cfg.node_port} code {cfg.pairing_code}")
    elif role == DeviceRole.CONTROLLER.value:
        print(f"  Backend port: {cfg.port}")
        hosts = cfg.paired_hosts or []
        if hosts:
            print("  Paired hosts:")
            for h in hosts:
                print(f"    ✓ {h.get('node_id')} @ {h.get('address')}:{h.get('port')}")
        else:
            print("  No Model Host paired yet (pair via API or startup prompt).")
    else:
        print(f"  Backend port: {cfg.port}")
        print(f"  Node port:    {cfg.node_port}")
        print(f"  Pairing code: {cfg.pairing_code}")
    print("=" * 56)
    print()


def interactive_select() -> DeviceRole:
    print()
    print("Select this device's SatQuery role:")
    print()
    print("  1. Controller")
    print("  2. Model Host")
    print("  3. Full System")
    print()
    while True:
        raw = input("Enter 1, 2, or 3 (or 'q' to quit): ").strip().lower()
        if raw in ("q", "quit", "exit"):
            sys.exit(1)
        if raw in ("1", "controller"):
            return DeviceRole.CONTROLLER
        if raw in ("2", "model_host", "model-host", "host"):
            return DeviceRole.MODEL_HOST
        if raw in ("3", "full_system", "full-system", "full"):
            return DeviceRole.FULL_SYSTEM
        print("Invalid choice.")


def maybe_host_qwen(role: DeviceRole) -> bool:
    if role not in (DeviceRole.MODEL_HOST, DeviceRole.FULL_SYSTEM):
        return False
    hw = probe_hardware()
    print()
    print("Hardware probe:")
    print(f"  GPU:  {hw.get('gpu_name') or ('available' if hw.get('gpu_available') else 'not detected')}")
    print(f"  VRAM: {hw.get('vram_gb') if hw.get('vram_gb') is not None else 'unknown'} GB")
    print(f"  RAM:  {hw.get('ram_gb') if hw.get('ram_gb') is not None else 'unknown'} GB")
    print(f"  Qwen VQA support: {hw.get('qwen_vl_support')}")
    print()
    print("Select models to host:")
    print(f"  [✓] Qwen VQA / Captioning  ({HOST_VLM_DISPLAY_NAME})")
    print(f"      Ollama pull tag: {DEFAULT_HOST_VLM_OLLAMA_TAG}")
    raw = input("Enable Qwen VQA/Captioning on this host? [Y/n]: ").strip().lower()
    return raw not in ("n", "no", "0")


def main() -> int:
    parser = argparse.ArgumentParser(description="Configure SatQuery device role")
    parser.add_argument("--show", action="store_true", help="Show current config and exit")
    parser.add_argument("--reset", action="store_true", help="Clear saved role")
    parser.add_argument("--change", action="store_true", help="Force re-select role")
    parser.add_argument(
        "--role",
        choices=["controller", "model_host", "full_system"],
        help="Set role non-interactively",
    )
    parser.add_argument("--host-qwen-vl", action="store_true", default=None)
    parser.add_argument("--no-host-qwen-vl", action="store_true")
    parser.add_argument("--json", action="store_true", help="Print config as JSON")
    args = parser.parse_args()

    if args.reset:
        clear_device_config()
        print("Cleared device role config.")
        return 0

    if args.show:
        cfg = load_device_config()
        if not cfg:
            print("No device role configured.")
            return 1
        if args.json:
            print(json.dumps(cfg.to_dict(), indent=2))
        else:
            _print_banner(cfg)
        return 0

    existing = load_device_config()
    if existing and not args.change and not args.role:
        if args.json:
            print(json.dumps(config_summary(existing), indent=2))
        else:
            print(f"Using saved role: {existing.role} ({existing.node_id})")
            print(f"Config: {device_config_path()}")
            print("Pass --change to reconfigure, or choose 'Change device role' at startup.")
            _print_banner(existing)
        return 0

    if args.role:
        role = DeviceRole(args.role)
        host_qwen = True
        if args.no_host_qwen_vl:
            host_qwen = False
        elif args.host_qwen_vl:
            host_qwen = True
        elif role in (DeviceRole.MODEL_HOST, DeviceRole.FULL_SYSTEM):
            host_qwen = True
    else:
        role = interactive_select()
        host_qwen = maybe_host_qwen(role)

    paired = list(existing.paired_hosts) if existing else []
    cfg = new_device_config(role, hosted_qwen_vl=host_qwen)
    if role != DeviceRole.MODEL_HOST:
        cfg.paired_hosts = paired
    path = save_device_config(cfg)
    print(f"Saved role config → {path}")
    _print_banner(cfg)
    if args.json:
        print(json.dumps(config_summary(cfg), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
