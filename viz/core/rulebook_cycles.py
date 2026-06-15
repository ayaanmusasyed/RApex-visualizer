import pandas as pd 

# ---- Functions for cycle detection w/ SCCs ----
# Used Kosaraju's Alg 
def find_sccs(rule_names, prec_df):
    name_set = set(rule_names)
    G = {r: [] for r in rule_names}
    GR = {r: [] for r in rule_names}

    for _, row in prec_df.iterrows():
        a = str(row.get("Higher Priority", "")).strip()
        b = str(row.get("Lower Priority", "")).strip()
        if a in name_set and b in name_set:
            G[a].append(b)
            GR[b].append(a)

    seen = set()
    order = []

    def dfs(u):
        seen.add(u)
        for v in G[u]:
            if v not in seen:
                dfs(v)
        order.append(u)

    for r in rule_names:
        if r not in seen:
            dfs(r)

    seen.clear()
    comps = []

    def rdfs(u, comp):
        seen.add(u)
        comp.append(u)
        for v in GR[u]:
            if v not in seen:
                rdfs(v, comp)

    for r in reversed(order):
        if r not in seen:
            comp = []
            rdfs(r, comp)
            comps.append(comp)

    return [c for c in comps if len(c) > 1]


def edges_inside_component(prec_df, comp):
    comp = set(comp)
    out = []
    for idx, row in prec_df.iterrows():
        a = str(row.get("Higher Priority", "")).strip()
        b = str(row.get("Lower Priority", "")).strip()
        if a in comp and b in comp:
            out.append((idx, a, b))
    return out


def remove_internal_cycle_edges(prec_df, comp):
    comp = set(comp)
    keep_rows = []
    for _, row in prec_df.iterrows():
        a = str(row.get("Higher Priority", "")).strip()
        b = str(row.get("Lower Priority", "")).strip()
        if not (a in comp and b in comp):
            keep_rows.append(row)
    return pd.DataFrame(keep_rows, columns=prec_df.columns)


def collapse_cycle_to_equivalence_class(prec_df, comp):
    """
    UI-side approximation:
    remove all priority edges inside the cycle.
    The rules remain separate columns, but no longer claim priority over each other.
    This represents 'same priority' at the UI level.
    """
    return remove_internal_cycle_edges(prec_df, comp)