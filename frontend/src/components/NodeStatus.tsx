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
}

/**
 * Minimal multi-device status for Debug Mode / sidebar — not a redesign.
 */
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
        const t = setInterval(refresh, 15000);
        return () => clearInterval(t);
    }, [refresh]);

    if (collapsed) {
        return (
            <button
                type="button"
                onClick={refresh}
                className="flex w-full items-center justify-center rounded-2xl px-0 py-2.5 text-slate-400 hover:bg-white/10"
                title="Refresh node status"
                aria-label="Node status"
            >
                <Server className="h-4 w-4" />
            </button>
        );
    }

    const role = data?.device?.role ?? "unconfigured";
    const nodes = data?.nodes ?? [];

    return (
        <div className="mx-3 mb-3 rounded-2xl border border-white/10 bg-white/5 px-3 py-2.5 text-[11px] text-slate-400">
            <div className="mb-1.5 flex items-center justify-between gap-2">
                <span className="font-medium uppercase tracking-wide text-slate-500">
                    Device
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
            {error && <p className="mt-1 text-rose-400/90">Status: {error}</p>}
            {!error && (
                <div className="mt-2 space-y-1.5">
                    <p className="text-slate-500">Remote nodes</p>
                    {nodes.length === 0 ? (
                        <p className="text-slate-500">None paired</p>
                    ) : (
                        nodes.map((n) => (
                            <div key={n.node_id} className="rounded-xl bg-black/20 px-2 py-1.5">
                                <p className="text-slate-200">{n.node_id}</p>
                                <p>
                                    {(n.capabilities || []).join(", ") || "—"} ·{" "}
                                    {n.healthy === true
                                        ? "Ready"
                                        : n.healthy === false
                                          ? "Offline"
                                          : "Unknown"}
                                </p>
                            </div>
                        ))
                    )}
                </div>
            )}
        </div>
    );
}
