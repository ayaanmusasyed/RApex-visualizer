import streamlit as st

from core.rulebook_classes import class_label, find_class_index
from core.rulebook_edit import (
    split_equivalence_class,
    add_class_edge,
    delete_class_edge,
)


# Show controls for the currently selected Cytoscape rule class.
def render_rulebook_selection_panel(selected, prec_df):
    st.write("Selected:", selected)

    if not selected or "selected_node_id" not in selected:
        return

    node_id = selected["selected_node_id"]

    if not node_id.startswith("class_"):
        return

    class_idx = int(node_id.replace("class_", ""))

    if class_idx >= len(st.session_state.eq_classes):
        st.caption("Selection is stale after the rulebook changed. Click a node again.")
        return

    selected_class = st.session_state.eq_classes[class_idx]

    st.subheader("Selected rule class")
    st.write(f"Class {class_idx}: `{class_label(selected_class)}`")

    outgoing = []
    incoming = []

    for _, row in st.session_state.prec_df.iterrows():
        hi = str(row["Higher Priority"]).strip()
        lo = str(row["Lower Priority"]).strip()

        hi_idx = find_class_index(st.session_state.eq_classes, hi)
        lo_idx = find_class_index(st.session_state.eq_classes, lo)

        if hi_idx == class_idx and lo_idx is not None:
            outgoing.append(lo_idx)

        if lo_idx == class_idx and hi_idx is not None:
            incoming.append(hi_idx)

    st.caption("Current priority relations for selected class:")

    if outgoing:
        st.write(
            "Higher than: "
            + ", ".join(
                f"`{class_label(st.session_state.eq_classes[i])}`"
                for i in sorted(set(outgoing))
            )
        )
    else:
        st.write("Higher than: none")

    if incoming:
        st.write(
            "Lower than: "
            + ", ".join(
                f"`{class_label(st.session_state.eq_classes[i])}`"
                for i in sorted(set(incoming))
            )
        )
    else:
        st.write("Lower than: none")

    if len(selected_class) == 1:
        st.caption("This is a single-rule class.")
    else:
        st.caption("This is a same-priority equivalence class.")

    other_class_options = [
        i for i in range(len(st.session_state.eq_classes))
        if i != class_idx
    ]

    if other_class_options:
        target_idx = st.selectbox(
            "Target class",
            other_class_options,
            format_func=lambda i: class_label(st.session_state.eq_classes[i]),
            key="cyto_target_class",
        )

        c1, c2 = st.columns(2)

        if c1.button("Add selected > target", key="cyto_add_out_edge"):
            st.session_state.prec_df = add_class_edge(
                st.session_state.prec_df,
                st.session_state.eq_classes,
                class_idx,
                target_idx,
            )
            st.rerun()

        if c2.button("Add target > selected", key="cyto_add_in_edge"):
            st.session_state.prec_df = add_class_edge(
                st.session_state.prec_df,
                st.session_state.eq_classes,
                target_idx,
                class_idx,
            )
            st.rerun()

        if st.button("Delete edge selected > target", key="cyto_delete_out_edge"):
            st.session_state.prec_df = delete_class_edge(
                st.session_state.prec_df,
                st.session_state.eq_classes,
                class_idx,
                target_idx,
            )
            st.rerun()

    if len(selected_class) > 1:
        if st.button("Split equivalence class", key="cyto_split_class"):
            st.session_state.eq_classes = split_equivalence_class(
                st.session_state.eq_classes,
                class_idx,
            )
            st.rerun()