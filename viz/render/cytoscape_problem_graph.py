# Convert problem graph state into Cytoscape elements.
def problem_graph_cytoscape_elements(
    node_names,
    edges_df,
    rule_names,
    start_label,
    goal_label,
):
    elements = []

    for i, node in enumerate(node_names):
        kind = "node"

        if node == start_label:
            kind = "start"
        elif node == goal_label:
            kind = "goal"

        col = i % 4
        row = i // 4

        elements.append({
            "data": {
                "id": f"node::{node}",
                "label": node,
                "node_name": node,
                "kind": kind,
            },
            "position": {
                "x": 160 * col + 100,
                "y": 130 * row + 90,
            },
        })

    df = edges_df.reset_index(drop=True)

    for edge_idx, row in df.iterrows():
        source = str(row.get("u", "")).strip()
        target = str(row.get("v", "")).strip()

        if not source or not target:
            continue

        costs = [
            float(row.get(f"c{i}", 0.0))
            for i in range(len(rule_names))
        ]

        label = "[" + ", ".join(
            f"{cost:g}"
            for cost in costs
        ) + "]"

        elements.append({
            "data": {
                "id": f"edge::{edge_idx}",
                "source": f"node::{source}",
                "target": f"node::{target}",
                "edge_index": int(edge_idx),
                "costs": costs,
                "label": label,
                "kind": "problem_edge",
            }
        })

    return elements


# Define styling for the interactive problem graph.
def problem_graph_cytoscape_stylesheet():
    return [
        {
            "selector": "node",
            "style": {
                "label": "data(label)",
                "text-valign": "center",
                "text-halign": "center",
                "background-color": "#ffffff",
                "border-width": 2,
                "border-color": "#333333",
                "width": 48,
                "height": 48,
            },
        },
        {
            "selector": 'node[kind = "start"]',
            "style": {
                "background-color": "#d8f3dc",
                "border-color": "#2d6a4f",
            },
        },
        {
            "selector": 'node[kind = "goal"]',
            "style": {
                "background-color": "#ffe5d9",
                "border-color": "#9d0208",
            },
        },
        {
            "selector": "edge",
            "style": {
                "curve-style": "bezier",
                "target-arrow-shape": "triangle",
                "line-color": "#666666",
                "target-arrow-color": "#666666",
                "width": 2,
                "label": "data(label)",
                "font-size": "10px",
                "text-background-color": "#ffffff",
                "text-background-opacity": 0.85,
                "text-background-padding": "3px",
            },
        },
        {
            "selector": ":selected",
            "style": {
                "border-width": 4,
                "border-color": "#1f77b4",
                "line-color": "#1f77b4",
                "target-arrow-color": "#1f77b4",
            },
        },
    ]