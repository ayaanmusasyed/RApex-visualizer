import pandas as pd

from viz.core.problem_graph_state import sync_edge_cost_columns


# Add one standalone graph node.
def add_node(node_names, name):
    name = str(name).strip()

    if not name:
        raise ValueError("Node name cannot be empty.")

    if name in node_names:
        raise ValueError(f"Node '{name}' already exists.")

    return list(node_names) + [name]


# Rename a node and every edge endpoint that uses it.
def rename_node(node_names, edges_df, old_name, new_name):
    old_name = str(old_name).strip()
    new_name = str(new_name).strip()

    if old_name not in node_names:
        raise ValueError(f"Unknown node '{old_name}'.")

    if not new_name:
        raise ValueError("New node name cannot be empty.")

    if new_name in node_names and new_name != old_name:
        raise ValueError(f"Node '{new_name}' already exists.")

    new_nodes = [
        new_name if node == old_name else node
        for node in node_names
    ]

    df = edges_df.copy()

    df["u"] = df["u"].replace(old_name, new_name)
    df["v"] = df["v"].replace(old_name, new_name)

    return new_nodes, df.reset_index(drop=True)


# Delete a node and all incident edges.
def delete_node(node_names, edges_df, name):
    name = str(name).strip()

    if name not in node_names:
        raise ValueError(f"Unknown node '{name}'.")

    new_nodes = [
        node
        for node in node_names
        if node != name
    ]

    df = edges_df[
        (edges_df["u"].astype(str).str.strip() != name)
        & (edges_df["v"].astype(str).str.strip() != name)
    ]

    return new_nodes, df.reset_index(drop=True)


# Add one directed graph edge.
def add_edge(edges_df, source, target, costs, k):
    source = str(source).strip()
    target = str(target).strip()

    if not source or not target:
        raise ValueError("Source and target nodes are required.")

    if len(costs) != k:
        raise ValueError(
            "Cost vector length must match the number of rules."
        )

    df = sync_edge_cost_columns(edges_df, k)

    row = {
        "u": source,
        "v": target,
    }

    for i, cost in enumerate(costs):
        row[f"c{i}"] = float(cost)

    return pd.concat(
        [df, pd.DataFrame([row])],
        ignore_index=True,
    )


# Update one edge's endpoints and cost vector.
def update_edge(edges_df, edge_idx, source, target, costs, k):
    if edge_idx < 0 or edge_idx >= len(edges_df):
        raise ValueError("Invalid edge selection.")

    if len(costs) != k:
        raise ValueError(
            "Cost vector length must match the number of rules."
        )

    df = sync_edge_cost_columns(edges_df, k)

    df.at[edge_idx, "u"] = str(source).strip()
    df.at[edge_idx, "v"] = str(target).strip()

    for i, cost in enumerate(costs):
        df.at[edge_idx, f"c{i}"] = float(cost)

    return df.reset_index(drop=True)


# Delete one graph edge by row index.
def delete_edge(edges_df, edge_idx):
    if edge_idx < 0 or edge_idx >= len(edges_df):
        raise ValueError("Invalid edge selection.")

    return edges_df.drop(
        index=edge_idx
    ).reset_index(drop=True)

# Reverse one graph edge.
def reverse_edge(edges_df, edge_idx):
    if edge_idx < 0 or edge_idx >= len(edges_df):
        raise ValueError("Invalid edge selection.")

    df = edges_df.copy()

    source = df.at[edge_idx, "u"]
    target = df.at[edge_idx, "v"]

    df.at[edge_idx, "u"] = target
    df.at[edge_idx, "v"] = source

    return df.reset_index(drop=True)