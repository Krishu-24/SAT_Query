"use client";

import { useCallback, useEffect, useState } from "react";
import { Server } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface NodeRow {
    node_id: string;
    address: string;
    port: number;
    capabilities?: string[];
    models?: string[];
    healthy?: boolean | null;
    last_error?: string | null;
}

interface StatusPayload {
    device?: {
        role?: string | null;
        node_id?: string | null;
    };
    nodes?: NodeRow[];
    model_host_connected?: boolean;
    vlm_ready?: boolean;
}

/** Minimal connection strip in the existing sidebar — no layout redesign. */
export default function NodeStatus({ collapsed = false }: { collapsed?: boolean }) {
    const [data, setData] = useState<StatusPayload | null>(null);
    const [error, setError] = useState<string | null>(null);

    const refresh = useCallback(async () => {
        try {
            const res = await fetch(`${API}/api/nodes/status`, { cache: "no-store" });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            setData(await res.json());
            setError(null);
        } catch (e) {
            setError(e instanceof Error ? e.message : "unreachable");
        }
    }, []);

    useEffect(() => {
        refresh();
        const t = setInterval(refresh, 8000);
        return () => clearInterval(t);
    }, [refresh]);

    const connected = Boolean(data?.model_host_connected);
    const vlmReady = Boolean(data?.vlm_ready);
    const role = data?.device?.role ?? "unconfigured";

    if (collapsed) {
        return (
            <button
                type="button"
                onClick={refresh}
                className={`flex w-full items-center justify-center rounded-2xl px-0 py-2.5 ${
                    connected ? "text-emerald-400" : "text-slate-400"
                } hover:bg-white/10`}
                title={
                    connected
                        ? "Model Host connected"
                        : "Model Host not connected"
                }
                aria-label="Node status"
            >
                <Server className="h-4 w-4" />
            </button>
        );
    }

    const nodes = data?.nodes ?? [];

    return (
        <div className="mx-3 mb-3 rounded-2xl border border-white/10 bg-white/5 px-3 py-2.5 text-[11px] text-slate-400">
            <div className="mb-1.5 flex items-center justify-between gap-2">
                <span className="font-medium uppercase tracking-wide text-slate-500">
                    Connection
                </span>
                <button
                    type="button"
                    onClick={refresh}
                    className="text-[10px] text-slate-500 hover:text-slate-300"
                >
                    refresh
                </button>
            </div>
            <p className="text-slate-300">
                Role: <span className="text-slate-100">{role}</span>
            </p>
            <p className="mt-1">
                Model Host:{" "}
                <span className={connected ? "text-emerald-300" : "text-amber-300"}>
                    {connected ? "connected" : "not connected"}
                </span>
            </p>
            <p className="mt-0.5">
                VLM:{" "}
                <span className={vlmReady ? "text-emerald-300" : "text-slate-500"}>
                    {vlmReady ? "ready (remote)" : "not ready"}
                </span>
            </p>
            {error && <p className="mt-1 text-rose-400/90">Status: {error}</p>}
            {!error && nodes.length > 0 && (
                <div className="mt-2 space-y-1.5">
                    {nodes.map((n) => (
                        <div key={n.node_id} className="rounded-xl bg-black/20 px-2 py-1.5">
                            <p className="text-slate-200">{n.node_id}</p>
                            <p>
                                {n.address}:{n.port} ·{" "}
                                {n.healthy === true
                                    ? "Ready"
                                    : n.healthy === false
                                      ? n.last_error || "Offline"
                                      : "Unknown"}
                            </p>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
