# Turn Python rulebook state into the format Cytoscape understands

# Convert rule_names + prec_df into Cytoscape elements.
# Cytoscape elements are just dictionaries representing nodes and edges.
def rulebook_to_cytoscape_elements(rule_names, prec_df):
    elements = []

    # Add one node per rule.
    for rule in rule_names:
        rule = str(rule).strip()

        if not rule:
            continue

        elements.append({
            "data": {
                "id": rule,
                "label": rule,
                "kind": "rule",
            }
        })

    # Add one directed edge per precedence relation.
    if prec_df is not None:
        for _, row in prec_df.iterrows():
            hi = str(row.get("Higher Priority", "")).strip()
            lo = str(row.get("Lower Priority", "")).strip()

            if not hi or not lo or hi == lo:
                continue

            elements.append({
                "data": {
                    "id": f"{hi}__to__{lo}",
                    "source": hi,
                    "target": lo,
                    "label": f"{hi} > {lo}",
                    "kind": "precedence",
                }
            })

    return elements