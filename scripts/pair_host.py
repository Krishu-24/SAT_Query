#!/usr/bin/env python3
"""Pair a Model Host from the Controller CLI (used by startup scripts)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

from app.node.client import NodeClient  # noqa: E402
from app.node.config_store import (  # noqa: E402
    DeviceRole,
    load_device_config,
    new_device_config,
    save_device_config,
)
from app.node.registry import RegisteredNode, get_registry  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Pair SatQuery Model Host")
    p.add_argument("address")
    p.add_argument("port", type=int, nargs="?", default=8100)
    p.add_argument("code")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    cfg = load_device_config()
    if not cfg:
        cfg = new_device_config(DeviceRole.CONTROLLER)
        save_device_config(cfg)
    if cfg.role == DeviceRole.MODEL_HOST.value:
        print("This machine is a Model Host — pair from a Controller instead.", file=sys.stderr)
        return 1

    client = NodeClient()
    result = client.pair(args.address, args.port, args.code, cfg.node_id)
    if not result.get("ok"):
        print(json.dumps(result, indent=2) if args.json else f"Pairing failed: {result}")
        return 1

    node = RegisteredNode(
        node_id=str(result["node_id"]),
        address=args.address,
        port=int(args.port),
        auth_token=str(result.get("auth_token") or ""),
        capabilities=list(result.get("capabilities") or []),
        models=list(result.get("models") or []),
        healthy=True,
    )
    get_registry().upsert(node, persist=True)
    out = {
        "ok": True,
        "node_id": node.node_id,
        "address": node.address,
        "port": node.port,
        "capabilities": node.capabilities,
        "models": node.models,
    }
    print(json.dumps(out, indent=2) if args.json else f"Paired {node.node_id} @ {node.address}:{node.port}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
