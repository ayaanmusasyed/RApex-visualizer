import streamlit as st
import pandas as pd

from streamlit_cytoscapejs import st_cytoscapejs

from viz.render.graphviz_render import dot_for_rule_class_graph
from viz.render.cytoscape_render import (
    rulebook_class_cytoscape_elements,
    rulebook_cytoscape_stylesheet,
)

from viz.core.rulebook_state import normalize_prec_df
from viz.core.rulebook_classes import default_eq_classes, class_label

from viz.ui.rule_management_panel import render_rule_management_panel
from viz.ui.rulebook_selection_panel import render_rulebook_selection_panel
from viz.ui.rulebook_cycle_panel import render_rulebook_cycle_panel


# Purpose:
# Render the rulebook editor section.
# Cytoscape is the main editor, while the table/Graphviz views are advanced previews.
def render_rulebook_section(rule_names):
    if "prec_df" not in st.session_state:
        st.session_state.prec_df = pd.DataFrame(
            columns=["Higher Priority", "Lower Priority"]
        )

    if "eps_values" not in st.session_state:
        st.session_state.eps_values = [0.0] * len(rule_names)

    if "eq_classes" not in st.session_state:
        st.session_state.eq_classes = default_eq_classes(rule_names)

    flat_rules = {
        rule
        for cls in st.session_state.eq_classes
        for rule in cls
    }

    if set(rule_names) != flat_rules:
        st.session_state.eq_classes = default_eq_classes(rule_names)

    st.header("Rulebook editor")

    render_rule_management_panel(
        rule_names,
        st.session_state.prec_df,
        st.session_state.eps_values,
    )

    prec_df = normalize_prec_df(st.session_state.prec_df)
    st.session_state.prec_df = prec_df

    st.subheader("Interactive rulebook preview")
    st.caption(
        "Click a rule class to add/delete priority edges or split equivalence classes."
    )
    st.caption(
    "Click a rule class to select it. Use the selected-class panel to add/remove "
    "priority edges or split equivalence classes."
    )

    selected = st_cytoscapejs(
        elements=rulebook_class_cytoscape_elements(
            rule_names,
            prec_df,
            st.session_state.eq_classes,
        ),
        stylesheet=rulebook_cytoscape_stylesheet(),
        width=700,
        height=350,
        key="rulebook_cytoscape",
    )

    render_rulebook_selection_panel(selected, prec_df)

    has_cycle = render_rulebook_cycle_panel(rule_names, prec_df)

    if has_cycle:
        st.stop()

    with st.expander("Same-priority groups"):
        st.caption("Rules in the same bracket are treated as equivalent priority.")

        for i, cls in enumerate(st.session_state.eq_classes):
            st.write(f"Class {i}: `{class_label(cls)}`")

    with st.expander("Advanced: rule precedence table"):
        st.caption(
            "Manual edge list. Each row means Higher Priority > Lower Priority."
        )

        edited_prec_df = st.data_editor(
            st.session_state.prec_df,
            key="prec_editor",
            use_container_width=True,
            num_rows="dynamic",
        )

        st.session_state.prec_df = normalize_prec_df(edited_prec_df)
        prec_df = st.session_state.prec_df

    with st.expander("Static rule graph preview"):
        st.caption("Graphviz preview of the same rulebook state.")

        st.graphviz_chart(
            dot_for_rule_class_graph(
                rule_names,
                prec_df,
                st.session_state.eq_classes,
            )
        )

    return prec_df