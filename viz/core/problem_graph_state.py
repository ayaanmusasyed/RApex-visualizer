import pandas as pd

# make sure the edge table has one cost column per rule.
def sync_edge_cost_columns(edges_df, k):
    needed_cols = ["u", "v"] + [f"c{i}" for i in range(k)]

    if edges_df is None or len(edges_df) == 0:
        return pd.DataFrame(columns=needed_cols)

    df = edges_df.copy()

    for col in needed_cols:
        if col not in df.columns:
            df[col] = 0.0 if col.startswith("c") else ""

    return df[needed_cols].reset_index(drop=True)


# collect every node used by the graph or start/goal labels.
def infer_node_names(edges_df, start_label="", goal_label=""):
    nodes = []

    def add(name):
        name = str(name).strip()

        if name and name not in nodes:
            nodes.append(name)

    add(start_label)
    add(goal_label)

    if edges_df is not None:
        for _, row in edges_df.iterrows():
            add(row.get("u", ""))
            add(row.get("v", ""))

    return nodes


# keep explicit nodes and edge endpoints synchronized.
def sync_node_names(node_names, edges_df, start_label="", goal_label=""):
    nodes = []

    for name in node_names or []:
        name = str(name).strip()

        if name and name not in nodes:
            nodes.append(name)

    inferred_nodes = infer_node_names(edges_df, start_label,goal_label,)

    for name in inferred_nodes:
        if name not in nodes:
            nodes.append(name)

    return nodes