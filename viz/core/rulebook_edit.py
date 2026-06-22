# This file has functions to support editing of the interactive rulebook 

import pandas as pd

from core.rulebook_classes import find_class_index
from core.rulebook_state import normalize_prec_df

# Split one equivalence class back into singleton classes.
def split_equivalence_class(eq_classes, class_idx):
    if class_idx < 0 or class_idx >= len(eq_classes):
        raise ValueError("Invalid class index.")

    target = eq_classes[class_idx]

    if len(target) <= 1:
        raise ValueError("This class already contains only one rule.")

    new_classes = []

    for i, cls in enumerate(eq_classes):
        if i == class_idx:
            for rule in cls:
                new_classes.append([rule])
        else:
            new_classes.append(cls)

    return new_classes


# Add a priority edge from one equivalence class to another.
def add_class_edge(prec_df, eq_classes, from_class_idx, to_class_idx):
    if from_class_idx == to_class_idx:
        raise ValueError("Cannot add a priority edge inside the same class.")

    if from_class_idx < 0 or from_class_idx >= len(eq_classes):
        raise ValueError("Invalid source class.")

    if to_class_idx < 0 or to_class_idx >= len(eq_classes):
        raise ValueError("Invalid target class.")

    source_rep = eq_classes[from_class_idx][0]
    target_rep = eq_classes[to_class_idx][0]

    df = normalize_prec_df(prec_df)

    new_row = pd.DataFrame([
        {
            "Higher Priority": source_rep,
            "Lower Priority": target_rep,
        }
    ])

    df = pd.concat([df, new_row], ignore_index=True)

    return normalize_prec_df(df)


# Remove any priority edge from one equivalence class to another.
def delete_class_edge(prec_df, eq_classes, from_class_idx, to_class_idx):
    if from_class_idx < 0 or from_class_idx >= len(eq_classes):
        raise ValueError("Invalid source class.")

    if to_class_idx < 0 or to_class_idx >= len(eq_classes):
        raise ValueError("Invalid target class.")

    df = normalize_prec_df(prec_df)

    rows = []

    for _, row in df.iterrows():
        hi = str(row["Higher Priority"]).strip()
        lo = str(row["Lower Priority"]).strip()

        hi_idx = find_class_index(eq_classes, hi)
        lo_idx = find_class_index(eq_classes, lo)

        if hi_idx == from_class_idx and lo_idx == to_class_idx:
            continue

        rows.append({
            "Higher Priority": hi,
            "Lower Priority": lo,
        })

    return pd.DataFrame(rows, columns=["Higher Priority", "Lower Priority"])