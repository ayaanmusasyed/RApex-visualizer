from viz.core.rulebook_classes import class_label, find_class_index

# Convert equivalence-class rulebook state into Cytoscape nodes and edges.
def rulebook_class_cytoscape_elements(rule_names, prec_df, eq_classes):
    elements = []

    for i, cls in enumerate(eq_classes):
        elements.append({
            "data": {
                "id": f"class_{i}",
                "label": class_label(cls),
                "kind": "rule_class",
                "classIndex": i,
                "rules": cls,
            },
            "position": {
                "x": 180 * i + 80,
                "y": 100,
            },
        })

    seen_edges = set()

    if prec_df is not None:
        for _, row in prec_df.iterrows():
            hi = str(row.get("Higher Priority", "")).strip()
            lo = str(row.get("Lower Priority", "")).strip()

            hi_i = find_class_index(eq_classes, hi)
            lo_i = find_class_index(eq_classes, lo)

            if hi_i is None or lo_i is None:
                continue

            if hi_i == lo_i:
                continue

            edge = (hi_i, lo_i)

            if edge in seen_edges:
                continue

            seen_edges.add(edge)

            elements.append({
                "data": {
                    "id": f"class_{hi_i}__to__class_{lo_i}",
                    "source": f"class_{hi_i}",
                    "target": f"class_{lo_i}",
                    "label": "priority",
                    "kind": "precedence",
                }
            })

    return elements


# Define visual styling for the rulebook Cytoscape graph.
def rulebook_cytoscape_stylesheet():
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
                "shape": "round-rectangle",
                "width": "label",
                "height": "label",
                "padding": "14px",
            },
        },
        {
            "selector": "edge",
            "style": {
                "curve-style": "bezier",
                "target-arrow-shape": "triangle",
                "line-color": "#555555",
                "target-arrow-color": "#555555",
                "width": 2,
                "label": "data(label)",
                "font-size": "10px",
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
