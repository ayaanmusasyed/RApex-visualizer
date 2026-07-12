import json
import pandas as pd
from viz.core.problem_graph_state import infer_node_names

# Convert layered rulebook format into explicit priority edges.
def rulebook_layers_to_edges(layers):
    edges = []

    for i in range(len(layers)):
        for j in range(i + 1, len(layers)):
            for hi in layers[i]:
                for lo in layers[j]:
                    edges.append((hi, lo))

    return edges


# Parse JSON text into the app's internal state objects.
def parse_problem_json(raw_json):
    cfg = json.loads(raw_json)

    rule_names = cfg["rules"]
    rulebook = cfg.get("rulebook", {})
    graph = cfg["graph"]
    graph_edges = graph.get("edges", [])

    start = cfg["start"]
    goal = cfg["goal"]
    eps = cfg.get("eps", 0.0)

    if isinstance(eps, (int, float)):
        eps = [float(eps)] * len(rule_names)
    else:
        eps = [float(x) for x in eps]

    if "classes" in rulebook:
        eq_classes = rulebook["classes"]
    else:
        eq_classes = [[rule] for rule in rule_names]

    if "edges" in rulebook:
        prec_edges = [
            (higher, lower)
            for higher, lower in rulebook["edges"]
        ]

    elif "layers" in rulebook:
        prec_edges = rulebook_layers_to_edges(
            rulebook["layers"]
        )

    else:
        prec_edges = []

    prec_df = pd.DataFrame(
        [
            {
                "Higher Priority": higher,
                "Lower Priority": lower,
            }
            for higher, lower in prec_edges
        ],
        columns=[
            "Higher Priority",
            "Lower Priority",
        ],
    )

    rows = []

    for edge in graph_edges:
        row = {
            "u": edge["u"],
            "v": edge["v"],
        }

        costs = edge["c"]

        if len(costs) != len(rule_names):
            raise ValueError(
                f"Edge {edge['u']}->{edge['v']} has "
                f"{len(costs)} costs, but there are "
                f"{len(rule_names)} rules."
            )

        for i, value in enumerate(costs):
            row[f"c{i}"] = float(value)

        rows.append(row)

    edge_columns = [
        "u",
        "v",
        *[
            f"c{i}"
            for i in range(len(rule_names))
        ],
    ]

    edges_df = pd.DataFrame(
        rows,
        columns=edge_columns,
    )

    node_names = graph.get("nodes")

    if node_names is None:
        node_names = infer_node_names(
            edges_df,
            start,
            goal,
        )
    else:
        node_names = [
            str(node).strip()
            for node in node_names
            if str(node).strip()
        ]

        inferred_nodes = infer_node_names(
            edges_df,
            start,
            goal,
        )

        for node in inferred_nodes:
            if node not in node_names:
                node_names.append(node)

    return {
        "rule_names": rule_names,
        "eq_classes": eq_classes,
        "prec_df": prec_df,
        "node_names": node_names,
        "edges_df": edges_df,
        "start": start,
        "goal": goal,
        "eps": eps,
    }


# Convert the current app state into shareable JSON.
def problem_state_to_json(
    rule_names,
    eq_classes,
    prec_df,
    node_names,
    edges_df,
    start,
    goal,
    eps,
):
    rulebook_edges = []

    if prec_df is not None:
        for _, row in prec_df.iterrows():
            higher = str(
                row.get("Higher Priority", "")
            ).strip()

            lower = str(
                row.get("Lower Priority", "")
            ).strip()

            if higher and lower:
                rulebook_edges.append([
                    higher,
                    lower,
                ])

    graph_edges = []

    for _, row in edges_df.iterrows():
        source = str(
            row.get("u", "")
        ).strip()

        target = str(
            row.get("v", "")
        ).strip()

        if not source or not target:
            continue

        costs = [
            float(row.get(f"c{i}", 0.0))
            for i in range(len(rule_names))
        ]

        graph_edges.append({
            "u": source,
            "v": target,
            "c": costs,
        })

    nodes = []

    for node in node_names:
        node = str(node).strip()

        if node and node not in nodes:
            nodes.append(node)

    out = {
        "rules": rule_names,
        "rulebook": {
            "classes": eq_classes,
            "edges": rulebook_edges,
        },
        "graph": {
            "nodes": nodes,
            "edges": graph_edges,
        },
        "start": start,
        "goal": goal,
        "eps": eps,
    }

    return json.dumps(out, indent=2)