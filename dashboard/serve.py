#!/usr/bin/env python3
"""Read-only results dashboard for the self-improving-agent experiments.

Serves the committed record under results/ — experiments over generations over
rounds — as JSON for the static page in static/. Stdlib only, loopback only,
strictly read-only: it renders what the runner recorded and computes display
aggregates from τ's own recorded rewards. The reportable number remains
`make grade` (tau2 evaluate-trajs); this server never grades anything.

    python3 dashboard/serve.py            # config.json supplies results_root + port
    python3 dashboard/serve.py --open     # also open the browser
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

DASHBOARD_DIR = Path(__file__).resolve().parent
STATIC_DIR = DASHBOARD_DIR / "static"
CONFIG_PATH = DASHBOARD_DIR / "config.json"

# Mirror of fidelity.lane_report.NORMAL_TERMINATIONS: the repo's stricter completion
# verdict. Rates below follow τ's own metric convention instead (only
# infrastructure_error is excluded); non-normal terminations are surfaced as flags.
NORMAL_TERMINATIONS = {"user_stop", "agent_stop"}
INFRASTRUCTURE = "infrastructure_error"

SUCCESS_EPSILON = 1e-6  # τ's own definition: success = reward within 1e-6 of 1.0

# The only rounds that count as experiment evidence inside a generation are the
# improvement batches. The authority is the runner's own record — run.py writes
# split: batch_NN into run_metadata.json exclusively for `--batch` rounds — so the
# classification never rests on directory naming. Everything else that lands under a
# generation directory (calibration pilots, mock smokes, single-task probes,
# concurrency smokes, legacy bring-up trials) is a diagnostic: shown, badged, and
# excluded from every task set, statistic and aggregate.
BATCH_SPLIT_RE = re.compile(r"^batch_\d+$")

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
}

_round_cache: dict[str, tuple[tuple, dict]] = {}


# ---------------------------------------------------------------- small helpers


def load_config() -> dict:
    config = (
        json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if CONFIG_PATH.exists()
        else {}
    )
    root = Path(config.get("results_root", "../results"))
    if not root.is_absolute():
        root = (DASHBOARD_DIR / root).resolve()
    return {"results_root": root, "port": int(config.get("port", 8787))}


def clean(value):
    """Make a parsed-JSON tree strictly serialisable: NaN/Inf become null.

    τ writes NaN costs on the platform lane (AG-UI events carry no usage), and
    json.dumps would otherwise emit invalid JSON the browser refuses.
    """
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, list):
        return [clean(v) for v in value]
    return value


def parse_flat_yaml(text: str) -> dict:
    """Parse the flat, two-level YAML this repo writes (experiment.yaml).

    Deliberately not a YAML parser: the dashboard is stdlib-only, and the files it
    reads are controlled. Anything deeper than one nested mapping comes back as
    strings under best effort.
    """
    root: dict = {}
    current: dict | None = None
    for raw in text.splitlines():
        if raw.lstrip().startswith("#") or not raw.strip():
            continue
        indent = len(raw) - len(raw.lstrip())
        key, sep, value = raw.strip().partition(":")
        if not sep:
            continue
        value = value.strip().strip("'\"")
        if indent == 0:
            if value:
                root[key] = value
                current = None
            else:
                current = {}
                root[key] = current
        elif current is not None:
            current[key] = value
    return root


def normalise_termination(value) -> str:
    text = str(value or "unknown")
    return text.rsplit(".", 1)[-1].lower()


def is_success(reward) -> bool:
    return (
        isinstance(reward, (int, float))
        and math.isfinite(reward)
        and abs(reward - 1.0) <= SUCCESS_EPSILON
    )


def task_description(task: dict) -> str:
    description = task.get("description")
    if isinstance(description, dict):
        description = description.get("purpose") or next(iter(description.values()), "")
    return str(description or "")[:240]


# ---------------------------------------------------------------- aggregation


def pass1(task_stats: list[tuple[int, int]]) -> float | None:
    """pass¹: mean over tasks of the per-task pass proportion c/n."""
    proportions = [c / n for c, n in task_stats if n > 0]
    return round(sum(proportions) / len(proportions), 4) if proportions else None


def pass1_interval(task_stats: list[tuple[int, int]]) -> list | None:
    """≈95% interval on pass^1 over per-task proportions (normal approximation)."""
    proportions = [c / n for c, n in task_stats if n > 0]
    count = len(proportions)
    if count < 2:
        return None
    mean = sum(proportions) / count
    variance = sum((p - mean) ** 2 for p in proportions) / (count - 1)
    half = 1.96 * math.sqrt(variance / count)
    return [max(0.0, mean - half), min(1.0, mean + half)]


def summarise_sim(sim: dict) -> dict:
    reward_info = sim.get("reward_info") or {}
    reward = reward_info.get("reward")
    if isinstance(reward, float) and not math.isfinite(reward):
        reward = None
    termination = normalise_termination(sim.get("termination_reason"))
    messages = sim.get("messages") or []
    tool_counts: dict[str, int] = {}
    platform_ref = None
    for message in messages:
        for tool_call in message.get("tool_calls") or []:
            name = str(tool_call.get("name") or "?")
            tool_counts[name] = tool_counts.get(name, 0) + 1
        raw = message.get("raw_data") or {}
        if raw.get("pi_session_ref"):
            platform_ref = str(raw["pi_session_ref"])
    return {
        "sim_id": str(sim.get("id") or ""),
        "task_id": str(sim.get("task_id") or "?"),
        "trial": sim.get("trial"),
        "reward": reward,
        "success": is_success(reward),
        "termination": termination,
        "graded": termination != INFRASTRUCTURE,
        "normal_completion": termination in NORMAL_TERMINATIONS and reward is not None,
        "messages": len(messages),
        "duration": clean(sim.get("duration")),
        "agent_cost": clean(sim.get("agent_cost")),
        "user_cost": clean(sim.get("user_cost")),
        "tool_calls": sum(tool_counts.values()),
        "kb_search": tool_counts.get("KB_search", 0),
        "tool_counts": tool_counts,
        "platform_ref": platform_ref,
    }


def read_manifest_rows(round_dir: Path) -> dict[tuple, dict]:
    """episode_manifest.jsonl keyed by (task, trial) — the W3 evidence join, if the round
    emitted one. Absent for pre-M2 rounds; the page renders those without the extra flags."""
    path = round_dir / "episode_manifest.jsonl"
    if not path.exists():
        return {}
    rows: dict[tuple, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        rows[(str(row.get("tau_task_id")), row.get("trial"))] = row
    return rows


def summarise_round(round_dir: Path, results_root: Path) -> dict:
    results_path = round_dir / "results.json"
    metadata_path = round_dir / "run_metadata.json"
    manifest_path = round_dir / "episode_manifest.jsonl"
    signature = (
        results_path.stat().st_mtime_ns,
        metadata_path.stat().st_mtime_ns if metadata_path.exists() else 0,
        manifest_path.stat().st_mtime_ns if manifest_path.exists() else 0,
    )
    cache_key = str(round_dir)
    cached = _round_cache.get(cache_key)
    if cached and cached[0] == signature:
        return cached[1]

    results = json.loads(results_path.read_text(encoding="utf-8"))
    metadata = (
        json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata_path.exists()
        else None
    )
    info = results.get("info") or {}
    sims = [summarise_sim(sim) for sim in results.get("simulations") or []]

    accounting = ((metadata or {}).get("platform") or {}).get("accounting") or {}
    manifest_rows = read_manifest_rows(round_dir)
    for sim in sims:
        account = accounting.get(sim["platform_ref"] or "") or {}
        sim["recipe_sha"] = account.get("recipe_git_commit_sha")
        sim["evidence_complete"] = account.get("evidence_complete")
        cost = account.get("cost")
        if isinstance(cost, dict):  # the conversation record reports {"usd": ...}
            cost = cost.get("usd") or cost.get("total") or cost.get("total_cost")
        sim["platform_cost"] = clean(cost)
        usage = account.get("usage") or {}
        sim["tokens"] = (
            clean(usage.get("total_tokens")) if isinstance(usage, dict) else None
        )
        row = manifest_rows.get((sim["task_id"], sim["trial"])) or {}
        sim["label"] = row.get("label")
        sim["arm_sha_ok"] = row.get("arm_sha_ok")
        sim["stall_warnings"] = row.get("stall_warnings") or 0
        incidents = row.get("incidents") or {}
        sim["incident_count"] = sum(v for v in incidents.values() if isinstance(v, int))

    graded = [s for s in sims if s["graded"]]
    task_stats_map: dict[str, list[int]] = {}
    for sim in graded:
        entry = task_stats_map.setdefault(sim["task_id"], [0, 0])
        entry[0] += 1 if sim["success"] else 0
        entry[1] += 1
    task_stats = [(c, n) for c, n in task_stats_map.values()]

    def _avg(values):
        values = [v for v in values if isinstance(v, (int, float)) and math.isfinite(v)]
        return round(sum(values) / len(values), 4) if values else None

    terminations: dict[str, int] = {}
    for sim in sims:
        terminations[sim["termination"]] = terminations.get(sim["termination"], 0) + 1

    incident_totals = ((metadata or {}).get("incidents") or {}).get("totals") or {}
    arm = (metadata or {}).get("arm") or {}
    platform_meta = (metadata or {}).get("platform") or {}
    name = round_dir.name
    summary = {
        "path": str(round_dir.relative_to(results_root)),
        "name": name,
        "domain": (metadata or {}).get("domain")
        or ((info.get("environment_info") or {}).get("domain_name")),
        # The runner's run_metadata.json record is the only split source (absent → null).
        "split": (metadata or {}).get("split"),
        # Improvement batch iff the runner recorded a batch split. Only batch rounds
        # enter metrics; see BATCH_SPLIT_RE for the rationale.
        "batch": bool(
            BATCH_SPLIT_RE.fullmatch(str((metadata or {}).get("split") or ""))
        ),
        "mode": (metadata or {}).get("mode")
        or ("locked" if info.get("retrieval_config") else None),
        # Diagnostic rounds (mock-domain smokes, materialised-recipe runs) are shown
        # but never counted: they are seam checks, not experiment evidence.
        "diagnostic": (
            (
                (metadata or {}).get("mode")
                or ("locked" if info.get("retrieval_config") else None)
            )
            != "locked"
            or (
                (metadata or {}).get("domain")
                or ((info.get("environment_info") or {}).get("domain_name"))
            )
            == "mock"
        ),
        "incident_totals": incident_totals,
        "incident_count": sum(
            v for v in incident_totals.values() if isinstance(v, int)
        ),
        "arm_sha": arm.get("sha"),
        "arm_dirty": bool(arm.get("dirty_paths")),
        "arm_mismatches": len(platform_meta.get("arm_sha_mismatches") or []),
        "orphaned": len(platform_meta.get("orphaned_task_ids") or []),
        "resumed": bool((metadata or {}).get("resumed")),
        "has_manifest": bool(manifest_rows),
        "transport": (metadata or {}).get("transport")
        or ("platform" if name.endswith("_platform") else "local"),
        "experiment_field": (metadata or {}).get("experiment"),
        "has_sentinel": metadata is not None,
        "elapsed_seconds": clean((metadata or {}).get("elapsed_seconds")),
        "episodes": len(sims),
        "graded": len(graded),
        "infra_errors": sum(1 for s in sims if not s["graded"]),
        "abnormal": sum(1 for s in sims if s["graded"] and not s["normal_completion"]),
        "evidence_incomplete": sum(
            1 for s in sims if s.get("evidence_complete") is False
        ),
        "pass1": pass1(task_stats),
        "pass1_interval": pass1_interval(task_stats),
        "avg_cost": _avg(
            [
                s["platform_cost"]
                if s["platform_cost"] is not None
                else ((s["agent_cost"] or 0) + (s["user_cost"] or 0)) or None
                for s in sims
            ]
        ),
        "avg_messages": _avg([s["messages"] for s in sims]),
        "avg_kb_search": _avg([s["kb_search"] for s in sims]),
        "avg_duration": _avg([s["duration"] for s in sims]),
        "terminations": terminations,
        "shas": sorted({s["recipe_sha"] for s in sims if s.get("recipe_sha")}),
        "agent_llm": ((info.get("agent_info") or {}).get("llm")),
        "user_llm": ((info.get("user_info") or {}).get("llm")),
        "retrieval_config": info.get("retrieval_config"),
        "seed": info.get("seed"),
        "num_trials": info.get("num_trials"),
        "tasks": {task: {"c": c, "n": n} for task, (c, n) in task_stats_map.items()},
        "task_descriptions": {
            str(t.get("id")): task_description(t) for t in results.get("tasks") or []
        },
        "sims": sims,
    }
    summary = clean(summary)
    _round_cache[cache_key] = (signature, summary)
    return summary


def round_dirs(generation_dir: Path):
    """Every directory holding a results.json, up to two levels down.

    Depth tolerance exists for the legacy bring-up layout (task_001_trials/trial_7).
    """
    for results_path in sorted(generation_dir.rglob("results.json")):
        if len(results_path.relative_to(generation_dir).parts) <= 3:
            yield results_path.parent


def generation_extras(generation_dir: Path) -> dict:
    extras: dict = {"gates": []}
    gates_dir = generation_dir / "gates"
    if gates_dir.is_dir():
        for path in sorted(gates_dir.glob("*.json")):
            try:
                extras["gates"].append(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                continue
    return extras


IMPROVEMENT_RECORD_RE = re.compile(r"^gen_(\d+)_to_(\d+)\.yaml$")


def read_improvement_records(experiment_dir: Path) -> list[dict]:
    """The per-transition evidence chain: improvement_records/gen_<g>_to_<g+1>.yaml.

    Raw text plus best-effort flat fields — the schema's authority stays with
    tau_adapter/records.py; this only shows what was written.
    """
    records = []
    records_dir = experiment_dir / "improvement_records"
    if not records_dir.is_dir():
        return records
    for path in sorted(records_dir.glob("gen_*_to_*.yaml")):
        match = IMPROVEMENT_RECORD_RE.match(path.name)
        if not match:
            continue
        text = path.read_text(encoding="utf-8")
        fields = parse_flat_yaml(text)
        records.append(
            {
                "name": path.name,
                "from_generation": int(match.group(1)),
                "to_generation": int(match.group(2)),
                "outcome": fields.get("outcome"),
                "fields": fields,
                "raw": text,
            }
        )
    return records


def read_held_out(experiment_dir: Path) -> dict | None:
    """The revealed progression artifacts: held_out/ CSVs plus summary.md.

    These files exist only after `make reveal`; until then this returns None and the
    page shows the sealed notice. The vault is never read from here — the dashboard
    renders held-out views exclusively from revealed artifacts (plan D9).
    """
    held_dir = experiment_dir / "held_out"
    by_gen_path = held_dir / "results_by_generation.csv"
    matrix_path = held_dir / "task_generation_matrix.csv"
    if not by_gen_path.exists() or not matrix_path.exists():
        return None
    with by_gen_path.open(encoding="utf-8", newline="") as handle:
        generations = [
            {
                "generation": row["generation"],
                "passed": int(row["passed"]),
                "total": int(row["total"]),
                "percent": float(row["percent"]),
                "carried": row["basis"] == "carried",
            }
            for row in csv.DictReader(handle)
        ]
    with matrix_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    transitions = _read_csv_rows(
        held_dir / "transitions.csv",
        lambda row: {
            "transition": row["transition"],
            "gains": int(row["gains"]),
            "retained": int(row["retained"]),
            "regressions": int(row["regressions"]),
            "unresolved": int(row["unresolved"]),
            "net": int(row["net"]),
            "identity": row["identity"] == "true",
        },
    )
    retention = _read_csv_rows(
        held_dir / "retention.csv",
        lambda row: {
            "generation": row["generation"],
            "currently": int(row["currently_solved"]),
            "ever": int(row["ever_solved"]),
        },
    )

    def _num(value: str):
        if value in ("", None):
            return None
        return float(value) if "." in value else int(value)

    process_by_generation = _read_csv_rows(
        held_dir / "process_metrics_by_generation.csv",
        lambda row: {
            key: (row[key] if key == "generation" else _num(row[key])) for key in row
        },
    )
    process_by_task = _read_csv_rows(
        held_dir / "process_metrics_by_task.csv",
        lambda row: {
            key: (
                row[key]
                if key in ("generation", "task_id", "reward_basis")
                else (row[key] == "true")
                if key in ("passed", "db_match") and row[key] != ""
                else None
                if row[key] == ""
                else _num(row[key])
            )
            for key in row
        },
    )
    total = generations[0]["total"] if generations else 0
    summary_path = experiment_dir / "summary.md"
    return {
        "generations": generations,
        "matrix_generations": rows[0][1:] if rows else [],
        "matrix": [
            {"task_id": row[0], "results": [int(v) for v in row[1:]]}
            for row in rows[1:]
        ],
        "transitions": transitions,
        "retention": retention,
        # Mirror of tau_adapter.reveal.noise_band_pp: one binomial SE at p=0.5, in pp (D2).
        "noise_band_pp": round(100 * 0.5 / math.sqrt(total)) if total else None,
        "process": (
            {"by_generation": process_by_generation, "by_task": process_by_task}
            if process_by_generation
            else None
        ),
        "summary": summary_path.read_text(encoding="utf-8")
        if summary_path.exists()
        else None,
    }


def _read_csv_rows(path: Path, shape) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return [shape(row) for row in csv.DictReader(handle)]


# The runner derives experiment directories as experiment_<seq>_<name> (seq zero-padded to
# three digits, from benchmark_lock.yaml experiment.seq/name). Legacy bring-up directories
# (experiment_dummy) predate the sequence and carry only a name.
EXPERIMENT_DIR_RE = re.compile(r"^experiment_(\d{3})_(.+)$")


def experiment_identity(dirname: str) -> dict:
    """Split a results directory name into the experiment's id, sequence and name."""
    suffix = dirname.removeprefix("experiment_")
    match = EXPERIMENT_DIR_RE.match(dirname)
    return {
        "id": suffix,
        "seq": match.group(1) if match else None,
        "name": match.group(2) if match else suffix,
    }


def experiment_payload(results_root: Path, dirname: str) -> dict:
    experiment_dir = (results_root / dirname).resolve()
    experiment_dir.relative_to(results_root)  # traversal guard: must stay inside
    snapshot_path = experiment_dir / "experiment.yaml"
    snapshot = (
        parse_flat_yaml(snapshot_path.read_text(encoding="utf-8"))
        if snapshot_path.exists()
        else None
    )
    readme_path = experiment_dir / "README.md"
    readme = readme_path.read_text(encoding="utf-8") if readme_path.exists() else None

    generations = []
    for generation_dir in sorted(experiment_dir.iterdir()):
        if not generation_dir.is_dir() or not generation_dir.name.startswith(
            "generation"
        ):
            continue
        rounds = [summarise_round(r, results_root) for r in round_dirs(generation_dir)]
        generations.append(
            {
                "name": generation_dir.name,
                "rounds": rounds,
                **generation_extras(generation_dir),
            }
        )

    # Only improvement batches reach the experiment-level task set and statistics.
    # Non-batch rounds — calibration pilots included, which run on the locked domain
    # and would otherwise pass a domain/mode test — are diagnostics, not evidence.
    tasks = sorted(
        {
            t
            for g in generations
            for r in g["rounds"]
            if r.get("batch")
            for t in r["tasks"]
        }
    )
    descriptions: dict[str, str] = {}
    for generation in generations:
        for round_summary in generation["rounds"]:
            if not round_summary.get("batch"):
                continue
            descriptions.update(
                {k: v for k, v in round_summary["task_descriptions"].items() if v}
            )
    return clean(
        {
            "dirname": dirname,
            **experiment_identity(dirname),
            "snapshot": snapshot,
            "readme": readme,
            "generations": generations,
            "held_out": read_held_out(experiment_dir),
            "improvement_records": read_improvement_records(experiment_dir),
            "tasks": tasks,
            "task_descriptions": {t: descriptions.get(t, "") for t in tasks},
        }
    )


def experiments_index(results_root: Path) -> list[dict]:
    entries = []
    if not results_root.exists():
        return entries
    for path in sorted(results_root.iterdir()):
        if not path.is_dir() or not path.name.startswith("experiment_"):
            continue
        generation_names = sorted(
            p.name
            for p in path.iterdir()
            if p.is_dir() and p.name.startswith("generation")
        )
        snapshot_path = path / "experiment.yaml"
        entries.append(
            {
                "dirname": path.name,
                **experiment_identity(path.name),
                "has_snapshot": snapshot_path.exists(),
                "snapshot": parse_flat_yaml(snapshot_path.read_text(encoding="utf-8"))
                if snapshot_path.exists()
                else None,
                "generations": generation_names,
            }
        )
    return entries


def episode_payload(results_root: Path, round_rel: str, sim_id: str) -> dict | None:
    round_dir = (results_root / round_rel).resolve()
    round_dir.relative_to(results_root)  # traversal guard
    results = json.loads((round_dir / "results.json").read_text(encoding="utf-8"))
    for sim in results.get("simulations") or []:
        key = f"{sim.get('task_id')}:{sim.get('trial')}"
        if str(sim.get("id")) == sim_id or key == sim_id:
            return clean(sim)
    return None


# ---------------------------------------------------------------- http server


class Handler(BaseHTTPRequestHandler):
    config: dict = {}

    def log_message(self, fmt, *args):  # quiet by default; errors still surface
        pass

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, payload, code: int = 200) -> None:
        body = json.dumps(payload, allow_nan=False).encode("utf-8")
        self._send(code, body, CONTENT_TYPES[".json"])

    def do_GET(self):  # noqa: N802 - http.server contract
        parsed = urlparse(self.path)
        query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        results_root = self.config["results_root"]
        try:
            if parsed.path == "/api/config":
                self._json(
                    {
                        "results_root": str(results_root),
                        "exists": results_root.exists(),
                    }
                )
            elif parsed.path == "/api/experiments":
                self._json(experiments_index(results_root))
            elif parsed.path == "/api/experiment":
                self._json(experiment_payload(results_root, query.get("dir", "")))
            elif parsed.path == "/api/episode":
                payload = episode_payload(
                    results_root, query.get("round", ""), query.get("sim", "")
                )
                if payload is None:
                    self._json({"error": "episode not found"}, 404)
                else:
                    self._json(payload)
            else:
                self._static(parsed.path)
        except (ValueError, OSError, json.JSONDecodeError) as exc:
            self._json({"error": f"{type(exc).__name__}: {exc}"}, 500)

    def _static(self, path: str) -> None:
        relative = path.lstrip("/") or "index.html"
        target = (STATIC_DIR / relative).resolve()
        try:
            target.relative_to(STATIC_DIR)
        except ValueError:
            self._send(404, b"not found", "text/plain")
            return
        if not target.is_file():
            self._send(404, b"not found", "text/plain")
            return
        content_type = CONTENT_TYPES.get(target.suffix, "application/octet-stream")
        self._send(200, target.read_bytes(), content_type)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--results-root", default=None, help="override config.json results_root"
    )
    parser.add_argument(
        "--port", type=int, default=None, help="override config.json port"
    )
    parser.add_argument(
        "--open", action="store_true", help="open the browser after starting"
    )
    args = parser.parse_args()

    config = load_config()
    if args.results_root:
        config["results_root"] = Path(args.results_root).resolve()
    if args.port:
        config["port"] = args.port

    Handler.config = config
    server = ThreadingHTTPServer(("127.0.0.1", config["port"]), Handler)
    url = f"http://127.0.0.1:{config['port']}/"
    print(f"── dashboard: {url}")
    print(f"   results    {config['results_root']}")
    print("   read-only — reward stays owned by `make grade` (tau2 evaluate-trajs)")
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
