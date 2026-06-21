import pandas as pd


PREC_COLS = ["Higher Priority", "Lower Priority"]

# Clean the precedence table after user edits.
# Removes empty rows, self-edges, duplicate edges, and missing columns.
def normalize_prec_df(prec_df):
    if prec_df is None:
        return pd.DataFrame(columns=PREC_COLS)

    df = prec_df.copy()

    for col in PREC_COLS:
        if col not in df.columns:
            df[col] = ""

    df = df[PREC_COLS]

    rows = []
    seen = set()

    for _, row in df.iterrows():
        hi = str(row["Higher Priority"]).strip()
        lo = str(row["Lower Priority"]).strip()

        if not hi or not lo:
            continue

        if hi == lo:
            continue

        edge = (hi, lo)

        if edge in seen:
            continue

        seen.add(edge)
        rows.append({
            "Higher Priority": hi,
            "Lower Priority": lo,
        })

    return pd.DataFrame(rows, columns=PREC_COLS)


# Add a new rule/objective name.
def add_rule(rule_names, name):
    name = str(name).strip()

    if not name:
        raise ValueError("Rule name cannot be empty.")

    if name in rule_names:
        raise ValueError(f"Rule '{name}' already exists.")

    return rule_names + [name]


# Rename a rule and update all rulebook edges that mention it.
def rename_rule(rule_names, prec_df, old, new):
    old = str(old).strip()
    new = str(new).strip()

    if old not in rule_names:
        raise ValueError(f"Unknown rule '{old}'.")

    if not new:
        raise ValueError("New rule name cannot be empty.")

    if new in rule_names and new != old:
        raise ValueError(f"Rule '{new}' already exists.")

    new_rule_names = [
        new if rule == old else rule
        for rule in rule_names
    ]

    df = normalize_prec_df(prec_df)

    df["Higher Priority"] = df["Higher Priority"].replace(old, new)
    df["Lower Priority"] = df["Lower Priority"].replace(old, new)

    return new_rule_names, normalize_prec_df(df)


# Delete a rule and remove all rulebook edges touching it.
def delete_rule(rule_names, prec_df, name):
    name = str(name).strip()

    if name not in rule_names:
        raise ValueError(f"Unknown rule '{name}'.")

    new_rule_names = [
        rule for rule in rule_names
        if rule != name
    ]

    df = normalize_prec_df(prec_df)

    df = df[
        (df["Higher Priority"] != name)
        & (df["Lower Priority"] != name)
    ]

    return new_rule_names, normalize_prec_df(df)


# Add one directed priority edge: hi > lo.
def add_rulebook_edge(prec_df, hi, lo):
    hi = str(hi).strip()
    lo = str(lo).strip()

    if not hi or not lo:
        raise ValueError("Both rules are required.")

    if hi == lo:
        raise ValueError("Cannot add a self-edge.")

    df = normalize_prec_df(prec_df)

    new_row = pd.DataFrame([
        {"Higher Priority": hi, "Lower Priority": lo}
    ])

    df = pd.concat([df, new_row], ignore_index=True)

    return normalize_prec_df(df)



# Remove one directed priority edge: hi > lo.
def delete_rulebook_edge(prec_df, hi, lo):
    hi = str(hi).strip()
    lo = str(lo).strip()

    df = normalize_prec_df(prec_df)

    df = df[
        ~(
            (df["Higher Priority"] == hi)
            & (df["Lower Priority"] == lo)
        )
    ]

    return normalize_prec_df(df)