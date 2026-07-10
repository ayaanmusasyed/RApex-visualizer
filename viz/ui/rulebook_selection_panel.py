import streamlit as st

from core.rulebook_classes import (
    class_label,
    find_class_index,
    remove_edges_inside_classes,
)
from core.rulebook_edit import (
    split_equivalence_class,
    add_class_edge,
    delete_class_edge,
    merge_class_indices,
)

def get_building_class_indices():
    return st.session_state.get("eq_build_class_indices", [])


def render_equivalence_class_builder(class_idx):
    active = st.session_state.get("eq_build_active", False)
    selected_indices = get_building_class_indices()

    st.divider()
    st.markdown("#### Equivalence class")

    if not active:
        if st.button(
            "Create equivalence class",
            key="start_equivalence_builder",
        ):
            st.session_state.eq_build_active = True
            st.session_state.eq_build_class_indices = [class_idx]
            st.rerun()

        return

    valid_indices = [
        i
        for i in selected_indices
        if 0 <= i < len(st.session_state.eq_classes)
    ]

    st.session_state.eq_build_class_indices = valid_indices

    building_rules = []

    for i in valid_indices:
        building_rules.extend(st.session_state.eq_classes[i])

    st.caption("Currently building:")
    st.write(f"`{class_label(building_rules)}`")

    current_is_selected = class_idx in valid_indices

    c1, c2 = st.columns(2)

    if not current_is_selected:
        if c1.button(
            "Add selected class to group",
            key="add_selected_to_equivalence_group",
        ):
            st.session_state.eq_build_class_indices = (
                valid_indices + [class_idx]
            )
            st.rerun()
    else:
        c1.caption("Selected class is already included.")

    if len(valid_indices) > 1:
        if c2.button(
            "Finish equivalence class",
            key="finish_equivalence_builder",
        ):
            try:
                new_eq_classes = merge_class_indices(
                    st.session_state.eq_classes,
                    valid_indices,
                )

                st.session_state.eq_classes = new_eq_classes

                st.session_state.prec_df = remove_edges_inside_classes(
                    st.session_state.prec_df,
                    new_eq_classes,
                )

                st.session_state.eq_build_active = False
                st.session_state.eq_build_class_indices = []

                st.rerun()

            except Exception as e:
                st.warning(str(e))
    else:
        c2.caption("Add at least one more class.")

    if st.button(
        "Cancel equivalence class",
        key="cancel_equivalence_builder",
    ):
        st.session_state.eq_build_active = False
        st.session_state.eq_build_class_indices = []
        st.rerun()


def render_rulebook_selection_panel(selected, prec_df):
    if not selected or "selected_node_id" not in selected:
        if st.session_state.get("eq_build_active", False):
            st.info(
                "Equivalence-class creation is active. "
                "Click another rule class in the graph."
            )
        return

    node_id = selected["selected_node_id"]

    if not node_id.startswith("class_"):
        return

    class_idx = int(node_id.replace("class_", ""))

    if class_idx >= len(st.session_state.eq_classes):
        st.caption(
            "Selection is stale after the rulebook changed. "
            "Click a node again."
        )
        return

    selected_class = st.session_state.eq_classes[class_idx]

    st.subheader("Selected rule class")
    st.write(f"Class {class_idx}: `{class_label(selected_class)}`")

    outgoing = []
    incoming = []

    for _, row in st.session_state.prec_df.iterrows():
        hi = str(row["Higher Priority"]).strip()
        lo = str(row["Lower Priority"]).strip()

        hi_idx = find_class_index(st.session_state.eq_classes,hi,)
        lo_idx = find_class_index(st.session_state.eq_classes,lo,)

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

    other_class_options = [i for i in range(len(st.session_state.eq_classes)) if i != class_idx]

    if other_class_options:
        target_idx = st.selectbox(
            "Target class",
            other_class_options,
            format_func=lambda i: class_label(
                st.session_state.eq_classes[i]
            ),
            key="cyto_target_class",
        )

        c1, c2 = st.columns(2)

        if c1.button(
            "Add selected > target",
            key="cyto_add_out_edge",
        ):
            st.session_state.prec_df = add_class_edge(st.session_state.prec_df,st.session_state.eq_classes,class_idx,target_idx,)
            st.rerun()

        if c2.button(
            "Add target > selected",
            key="cyto_add_in_edge",
        ):
            st.session_state.prec_df = add_class_edge(st.session_state.prec_df,st.session_state.eq_classes,target_idx,class_idx,)
            st.rerun()

        if st.button(
            "Delete edge selected > target",
            key="cyto_delete_out_edge",
        ):
            st.session_state.prec_df = delete_class_edge(st.session_state.prec_df, st.session_state.eq_classes, class_idx, target_idx,)
            st.rerun()

    render_equivalence_class_builder(class_idx)

    if len(selected_class) > 1:
        if st.button(
            "Split equivalence class",
            key="cyto_split_class",
        ):
            st.session_state.eq_classes = split_equivalence_class(st.session_state.eq_classes, class_idx,)

            st.session_state.eq_build_active = False
            st.session_state.eq_build_class_indices = []

            st.rerun()