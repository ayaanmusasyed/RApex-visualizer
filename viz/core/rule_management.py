import pandas as pd

from viz.core.rulebook_state import normalize_prec_df

# Add a new rule/objective and create a singleton equivalence class for it.
def add_rule(rule_names, eq_classes, eps, new_rule_name):
    new_rule_name = str(new_rule_name).strip()

    if not new_rule_name:
        raise ValueError("Rule name cannot be empty.")

    if new_rule_name in rule_names:
        raise ValueError(f"Rule '{new_rule_name}' already exists.")

    new_rule_names = rule_names + [new_rule_name]
    new_eq_classes = eq_classes + [[new_rule_name]]
    new_eps = eps + [0.0]

    return new_rule_names, new_eq_classes, new_eps


# Rename a rule everywhere it appears: rule list, equivalence classes, and precedence table.
def rename_rule(rule_names, eq_classes, prec_df, old_name, new_name):
    old_name = str(old_name).strip()
    new_name = str(new_name).strip()

    if old_name not in rule_names:
        raise ValueError(f"Unknown rule '{old_name}'.")

    if not new_name:
        raise ValueError("New rule name cannot be empty.")

    if new_name in rule_names and new_name != old_name:
        raise ValueError(f"Rule '{new_name}' already exists.")

    new_rule_names = [
        new_name if rule == old_name else rule
        for rule in rule_names
    ]

    new_eq_classes = []

    for cls in eq_classes:
        new_eq_classes.append([
            new_name if rule == old_name else rule
            for rule in cls
        ])

    df = normalize_prec_df(prec_df)

    df["Higher Priority"] = df["Higher Priority"].replace(old_name, new_name)
    df["Lower Priority"] = df["Lower Priority"].replace(old_name, new_name)

    return new_rule_names, new_eq_classes, normalize_prec_df(df)


# Delete a rule and remove all precedence edges touching that rule.
def delete_rule(rule_names, eq_classes, prec_df, eps, rule_to_delete):
    rule_to_delete = str(rule_to_delete).strip()

    if rule_to_delete not in rule_names:
        raise ValueError(f"Unknown rule '{rule_to_delete}'.")

    delete_idx = rule_names.index(rule_to_delete)

    new_rule_names = [
        rule for rule in rule_names
        if rule != rule_to_delete
    ]

    new_eps = [
        val for i, val in enumerate(eps)
        if i != delete_idx
    ]

    new_eq_classes = []

    for cls in eq_classes:
        new_cls = [
            rule for rule in cls
            if rule != rule_to_delete
        ]

        if new_cls:
            new_eq_classes.append(new_cls)

    df = normalize_prec_df(prec_df)

    df = df[
        (df["Higher Priority"] != rule_to_delete)
        & (df["Lower Priority"] != rule_to_delete)
    ]

    return new_rule_names, new_eq_classes, normalize_prec_df(df), new_eps