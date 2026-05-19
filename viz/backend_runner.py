# viz/backend_runner.py

import subprocess
import tempfile
from pathlib import Path

from io_utils import build_node_ids, write_queries_txt, write_rules_txt, write_gr_files
from trace_utils import init_from_trace, parse_trace_lines
from solution_utils import (
    compute_solution_edges,
    compute_solution_paths,
    compute_candidate_paths,
    paths_to_edges,
)

# Helper function to verify file paths and binary
def ensure_binary(repo_root: Path):
    bin_path = repo_root / "build" / "multiobj"
    build_dir = repo_root / "build"

    if bin_path.exists():
        return bin_path

    build_dir.mkdir(exist_ok=True)

    configure = subprocess.run(
        ["cmake", "-S", str(repo_root), "-B", str(build_dir)],
        capture_output=True,
        text=True,
    )

    if configure.returncode != 0:
        raise RuntimeError(
            "CMake configure failed.\n\n"
            f"STDOUT:\n{configure.stdout}\n\n"
            f"STDERR:\n{configure.stderr}"
        )

    build = subprocess.run(
        ["cmake", "--build", str(build_dir)],
        capture_output=True,
        text=True,
    )

    if build.returncode != 0:
        raise RuntimeError(
            "CMake build failed.\n\n"
            f"STDOUT:\n{build.stdout}\n\n"
            f"STDERR:\n{build.stderr}"
        )

    if not bin_path.exists():
        raise FileNotFoundError("Build finished but build/multiobj was not created.")

    return bin_path

def run_algorithm(
    algorithm_name,
    edges_df,
    rule_names,
    eps,
    prec_df,
    start_label,
    goal_label,
    cutoff,
    merge,
):
    if len(rule_names) != len(eps):
        raise ValueError("Rule names count must match epsilon length.")

    k = len(rule_names)

    name_to_id = build_node_ids(edges_df, start_label, goal_label)
    s_id = name_to_id[str(start_label).strip()]
    t_id = name_to_id[str(goal_label).strip()]


    repo_root = Path(__file__).resolve().parents[1]
    bin_path = ensure_binary(repo_root)

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)

        trace_path = td / f"trace_{algorithm_name}.jsonl"
        stats_path = td / f"stats_{algorithm_name}.txt"
        rules_path = td / "rules.txt"
        queries_path = td / "queries.txt"

        write_queries_txt(queries_path, s_id, t_id)
        write_rules_txt(rules_path, rule_names, eps, prec_df)
        gr_paths = write_gr_files(td, edges_df, name_to_id, k)

        cmd = [
            str(bin_path),
            "--algorithm", algorithm_name,
            "--merge", merge,
            "--cutoffTime", str(cutoff),
            "--trace", str(trace_path),
            "--output", str(stats_path),
            "--query", str(queries_path),
            "--rules", str(rules_path),
            "--map",
            *[str(p) for p in gr_paths],
        ]

        res = subprocess.run(cmd, capture_output=True, text=True, cwd=td)

        if res.returncode != 0:
            raise RuntimeError(
                "multiobj failed.\n"
                f"STDOUT:\n{res.stdout or '(no stdout)'}\n\n"
                f"STDERR:\n{res.stderr or '(no stderr)'}"
            )

        trace = []
        trace_stepper = None
        solution_edges = set()
        solution_paths = []
        candidate_edges = set()
        candidate_paths = []

        # Only parse trace if the algorithm actually produced one
        if trace_path.exists():
            raw_lines = trace_path.read_text(encoding="utf-8").splitlines()
            trace = parse_trace_lines(raw_lines)
            trace_stepper = init_from_trace(trace)

            solution_edges = compute_solution_edges(
                trace, edges_df, name_to_id, start_label, goal_label, k
            )
            solution_paths = compute_solution_paths(
                trace, edges_df, name_to_id, start_label, goal_label, k
            )
            candidate_paths = compute_candidate_paths(
                trace, edges_df, name_to_id, start_label, goal_label, k, eps
            )
            candidate_edges = paths_to_edges(candidate_paths)

        return {
            "algorithm": algorithm_name,
            "trace": trace,
            "trace_stepper": trace_stepper,
            "has_trace": trace_path.exists(),
            "stdout": res.stdout,
            "stderr": res.stderr,
            "stats_text": stats_path.read_text(encoding="utf-8") if stats_path.exists() else "",
            "name_to_id": name_to_id,
            "solution_edges": solution_edges,
            "solution_paths": solution_paths,
            "candidate_edges": candidate_edges,
            "candidate_paths": candidate_paths,
        }