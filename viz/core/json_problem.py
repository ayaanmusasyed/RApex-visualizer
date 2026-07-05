import json
import pandas as pd


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
    graph_edges = cfg["graph"]["edges"]
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
        eq_classes = [[r] for r in rule_names]

    if "edges" in rulebook:
        prec_edges = [(a, b) for a, b in rulebook["edges"]]
    elif "layers" in rulebook:
        prec_edges = rulebook_layers_to_edges(rulebook["layers"])
    else:
        prec_edges = []

    prec_df = pd.DataFrame(
        [{"Higher Priority": a, "Lower Priority": b} for a, b in prec_edges],
        columns=["Higher Priority", "Lower Priority"],
    )

    rows = []

    for edge in graph_edges:
        row = {"u": edge["u"], "v": edge["v"]}
        costs = edge["c"]

        if len(costs) != len(rule_names):
            raise ValueError(
                f"Edge {edge['u']}->{edge['v']} has {len(costs)} costs, "
                f"but there are {len(rule_names)} rules."
            )

        for i, val in enumerate(costs):
            row[f"c{i}"] = float(val)

        rows.append(row)

    edges_df = pd.DataFrame(rows)

    return {
        "rule_names": rule_names,
        "eq_classes": eq_classes,
        "prec_df": prec_df,
        "edges_df": edges_df,
        "start": start,
        "goal": goal,
        "eps": eps,
    }


# Convert the current app state back into shareable JSON.
def problem_state_to_json(rule_names, eq_classes, prec_df, edges_df, start, goal, eps):
    rulebook_edges = []

    if prec_df is not None:
        for _, row in prec_df.iterrows():
            hi = str(row.get("Higher Priority", "")).strip()
            lo = str(row.get("Lower Priority", "")).strip()

            if hi and lo:
                rulebook_edges.append([hi, lo])

    graph_edges = []

    for _, row in edges_df.iterrows():
        u = str(row.get("u", "")).strip()
        v = str(row.get("v", "")).strip()

        if not u or not v:
            continue

        costs = []

        for i in range(len(rule_names)):
            costs.append(float(row.get(f"c{i}", 0.0)))

        graph_edges.append({
            "u": u,
            "v": v,
            "c": costs,
        })

    out = {
        "rules": rule_names,
        "rulebook": {
            "classes": eq_classes,
            "edges": rulebook_edges,
        },
        "graph": {
            "edges": graph_edges,
        },
        "start": start,
        "goal": goal,
        "eps": eps,
    }

    return json.dumps(out, indent=2)