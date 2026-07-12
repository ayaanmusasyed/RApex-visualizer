import streamlit as st

from viz.core.rulebook_state import rename_rule
from viz.core.rulebook_edit import (
    add_class_edge,
    delete_class_edge,
    merge_class_indices,
    split_equivalence_class,
)


# Apply one event dict from the rulebook editor.
def dispatch_rulebook_event(event, rule_names, prec_df, eq_classes):
    action = event.get("action")

    if action == "rename_rule":
        new_rule_names, new_prec_df = rename_rule(
            rule_names, prec_df, event["old"], event["new"],
        )
        st.session_state.pending_rule_names_csv = ",".join(new_rule_names)
        st.session_state.prec_df = new_prec_df
        return

    if action == "add_class_edge":
        st.session_state.prec_df = add_class_edge(
            prec_df, eq_classes, event["from_class"], event["to_class"],
        )
        return

    if action == "delete_class_edge":
        st.session_state.prec_df = delete_class_edge(
            prec_df, eq_classes, event["from_class"], event["to_class"],
        )
        return

    if action == "merge_classes":
        st.session_state.eq_classes = merge_class_indices(
            eq_classes, event["class_indices"],
        )
        return

    if action == "split_class":
        st.session_state.eq_classes = split_equivalence_class(
            eq_classes, event["class_idx"],
        )
        return

    raise ValueError(f"Unknown rulebook event: {action!r}")
