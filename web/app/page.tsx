"use client";
import { useEffect, useState } from "react";

type Event = { id: number; tool: string; decision: string; reason: string; matched_rule: string };
const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export default function Page() {
  const [task, setTask] = useState("Clean stale sessions and inspect the sandbox.");
  const [events, setEvents] = useState<Event[]>([]);
  const [status, setStatus] = useState("Draft a policy before running the agent.");
  useEffect(() => { const source = new EventSource(`${API}/stream`); source.onmessage = e => setEvents(v => [...v, JSON.parse(e.data)]); return () => source.close(); }, []);
  async function confirm() { const draft = await fetch(`${API}/policy`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ task }) }).then(r => r.json()); await fetch(`${API}/policy`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ...draft, confirmed: true }) }); setStatus("Policy confirmed. Agent runs are now guarded."); }
  return <main><h1>Interlock</h1><p>Deterministic circuit breaker for agent tool calls.</p><textarea value={task} onChange={e => setTask(e.target.value)} /><button onClick={confirm}>Confirm policy</button><p>{status}</p><h2>Live verdicts</h2>{events.map(e => <article key={e.id}><b>{e.decision.toUpperCase()}</b> · {e.tool} — {e.reason} <small>{e.matched_rule}</small></article>)}</main>;
}
