def dot_for_graph(     
    edges_df,
    highlight_nodes=None,
    highlight_edges=None,
    open_nodes=None,
    pruned_nodes=None,
    solution_edges=None,
    candidate_edges=None,
):

    highlight_nodes = set(highlight_nodes or [])
    highlight_edges = set(highlight_edges or [])
    open_nodes = set(open_nodes or [])
    pruned_nodes = set(pruned_nodes or [])
    solution_edges = set(solution_edges or [])
    candidate_edges = set(candidate_edges or [])

    node_names = set()

    for _, row in edges_df.iterrows():

        u = str(row["u"]).strip()
        v = str(row["v"]).strip()

        if u:
            node_names.add(u)
        if v:
            node_names.add(v)

    node_lines = []
    edge_lines = []

    for name in sorted(node_names):

        fill = 'fillcolor="white"'
        style_bits = ["filled"]
        extra = []

        if name in open_nodes:
            fill = 'fillcolor="lightyellow"'

        if name in highlight_nodes:
            fill = 'fillcolor="cyan"'

        if name in pruned_nodes:
            extra += ['color="red"', 'penwidth=2']
            style_bits.append("dashed")

        node_lines.append(
            f'"{name}" [shape=circle, style="{",".join(style_bits)}", {fill}'
            + (", " + ", ".join(extra) if extra else "")
            + "];"
        )

    for _, row in edges_df.iterrows():

        u = str(row["u"]).strip()
        v = str(row["v"]).strip()

        if not u or not v:
            continue

        label = "[" + ",".join(
            str(row[c]) for c in edges_df.columns if str(c).startswith("c")
        ) + "]"

        edge_color = "gray"
        penwidth = "1"

        if (u, v) in solution_edges:
            edge_color = "green"
            penwidth = "4"

        elif (u, v) in candidate_edges:
            edge_color = "orange"
            penwidth = "3"

        elif (u, v) in highlight_edges:
            edge_color = "blue"
            penwidth = "3"

        edge_lines.append(
            f'"{u}" -> "{v}" [label="{label}", color="{edge_color}", penwidth={penwidth}];'
        )

    lines = [
        "digraph G {",
        'rankdir="LR";',
        "node [fontname=Helvetica];",
        "edge [fontname=Helvetica];",
        *node_lines,
        *edge_lines,
        "}",
    ]

    return "\n".join(lines)

def dot_for_rule_graph(rule_names, prec_df):
    rule_names = [str(r).strip() for r in rule_names if str(r).strip()]

    edges = []
    if prec_df is not None:
        for _, row in prec_df.iterrows():
            hi = str(row.get("Higher Priority", "")).strip()
            lo = str(row.get("Lower Priority", "")).strip()
            if hi and lo:
                edges.append((hi, lo))

    lines = [
        "digraph Rulebook {",
        'rankdir="TB";',
        "node [shape=box, style=filled, fillcolor=white, fontname=Helvetica];",
        "edge [fontname=Helvetica];",
    ]

    for r in rule_names:
        lines.append(f'"{r}";')

    for hi, lo in edges:
        lines.append(f'"{hi}" -> "{lo}";')

    lines.append("}")
    return "\n".join(lines)