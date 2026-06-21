# This file handles equivalence classes like [r1, r2].

# Create default equivalence classes where every rule starts alone.
def default_eq_classes(rule_names):
    return [[str(r).strip()] for r in rule_names if str(r).strip()]


# Convert an equivalence class like ["r1", "r2"] into display text "[r1, r2]".
def class_label(cls):
    return "[" + ", ".join(cls) + "]"


# Find which equivalence class contains a given rule.
def find_class_index(eq_classes, rule):
    for i, cls in enumerate(eq_classes):
        if rule in cls:
            return i
    return None

# Collapse a detected cycle into one same-priority equivalence class.
def collapse_rules_into_class(eq_classes, rules_to_collapse):
    rules_to_collapse = set(rules_to_collapse)

    merged = []
    remaining = []

    for cls in eq_classes:
        if any(rule in rules_to_collapse for rule in cls):
            merged.extend(cls)
        else:
            remaining.append(cls)

    merged = sorted(set(merged))

    return remaining + [merged]


# Remove priority edges inside a new equivalence class.
def remove_edges_inside_classes(prec_df, eq_classes):
    rows = []

    for _, row in prec_df.iterrows():
        hi = str(row.get("Higher Priority", "")).strip()
        lo = str(row.get("Lower Priority", "")).strip()

        hi_class = find_class_index(eq_classes, hi)
        lo_class = find_class_index(eq_classes, lo)

        if hi_class is not None and hi_class == lo_class:
            continue

        rows.append(row)

    return prec_df.iloc[0:0].append(rows, ignore_index=True) if rows else prec_df.iloc[0:0]