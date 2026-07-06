import pandas as pd

# makes sure the problem graph edge table has exactly one cost column per rule.
def sync_edge_cost_columns(edges_df, k):
    needed_cols = ["u", "v"] + [f"c{i}" for i in range(k)]

    if edges_df is None or len(edges_df) == 0:
        return pd.DataFrame(columns=needed_cols)

    df = edges_df.copy()

    for col in needed_cols:
        if col not in df.columns:
            df[col] = 0.0 if col.startswith("c") else ""

    return df[needed_cols]