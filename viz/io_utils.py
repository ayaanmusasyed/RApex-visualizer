import pandas as pd
from pathlib import Path
from typing import Dict, List

SCALE = 1.0


def _normalize_rule_name_or_index(x: str, rule_names: List[str]) -> int:
    x = str(x).strip()

    if x == "":
        raise ValueError("Empty rule reference.")

    if x.isdigit():
        i = int(x)
        if not (0 <= i < len(rule_names)):
            raise ValueError(f"Rule index {i} out of range.")
        return i

    if x in rule_names:
        return rule_names.index(x)

    raise ValueError(f"Unknown rule '{x}'.")


def build_node_ids(edges_df: pd.DataFrame, start_label: str, goal_label: str):

    labels = set()

    labels.add(str(start_label).strip())
    labels.add(str(goal_label).strip())

    for _, r in edges_df.iterrows():

        u = str(r["u"]).strip()
        v = str(r["v"]).strip()

        if u:
            labels.add(u)
        if v:
            labels.add(v)

    labels = sorted(labels)

    return {name: i + 1 for i, name in enumerate(labels)}


def write_queries_txt(path: Path, s_id: int, t_id: int):
    path.write_text(f"{s_id},{t_id}\n", encoding="utf-8")


def write_rules_txt(path: Path, rule_names: List[str], eps: List[float], precedence_edges_df: pd.DataFrame):

    k = len(rule_names)

    if len(eps) != k:
        raise ValueError("eps length must match rules")

    eq_classes = [[i] for i in range(k)]

    rels = []

    if precedence_edges_df is not None and len(precedence_edges_df) > 0:

        for _, r in precedence_edges_df.iterrows():

            hi = str(r.get("Higher Priority", "")).strip()
            lo = str(r.get("Lower Priority", "")).strip()

            if not hi or not lo:
                continue

            a = _normalize_rule_name_or_index(hi, rule_names)
            b = _normalize_rule_name_or_index(lo, rule_names)

            if a == b:
                raise ValueError("Self-edge in precedence graph.")

            rels.append((a, b))

    lines = []

    lines.append(str(k))
    lines.append(" ".join(str(float(x)) for x in eps))

    lines.append(str(len(eq_classes)))

    for cls in eq_classes:
        lines.append(str(len(cls)) + " " + " ".join(str(i) for i in cls))

    lines.append(str(len(rels)))

    for a, b in rels:
        lines.append(f"{a} {b}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_gr_files(out_dir: Path, edges_df: pd.DataFrame, name_to_id: Dict[str, int], k: int):

    arcs = []

    for _, r in edges_df.iterrows():

        u = str(r["u"]).strip()
        v = str(r["v"]).strip()

        if not u or not v:
            continue

        cu = name_to_id[u]
        cv = name_to_id[v]

        cost = [float(r[f"c{i}"]) for i in range(k)]

        arcs.append((cu, cv, cost))

    n_nodes = max(name_to_id.values())
    n_edges = len(arcs)

    gr_paths = []

    for i in range(k):

        p = out_dir / f"w{i}.gr"

        gr_paths.append(p)

        lines = [
            f"c objective {i}",
            f"p sp {n_nodes} {n_edges}",
        ]

        for cu, cv, cost in arcs:
            w = cost[i]
            lines.append(f"a {cu} {cv} {int(round(w * SCALE))}")

        p.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return gr_paths