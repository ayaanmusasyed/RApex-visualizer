import pandas as pd
import streamlit as st

from streamlit_cytoscapejs import st_cytoscapejs

from viz.core.problem_graph_state import (
    sync_edge_cost_columns,
    sync_node_names,
)
from viz.render.cytoscape_problem_graph import (
    problem_graph_cytoscape_elements,
    problem_graph_cytoscape_stylesheet,
)
from viz.ui.problem_graph_creation_panel import (
    render_problem_graph_creation_panel,
)
from viz.ui.problem_graph_selection_panel import (
    render_problem_graph_selection_panel,
)
from viz.ui.problem_graph_sanity_check import (
    render_problem_graph_sanity_check,
)


# Render the interactive problem graph editor.
def render_problem_graph_section(
    k,
    rule_names,
    start_label,
    goal_label,
    prec_df,
    eps,
):
    initialize_problem_graph_state(k, start_label, goal_label,)

    st.header("Problem graph editor")

    render_problem_graph_creation_panel()

    st.subheader("Interactive problem graph")
    st.caption(
        "Click a node to rename it, set start or goal, "
        "create an edge, or delete it."
    )

    selected = st_cytoscapejs(
        elements=problem_graph_cytoscape_elements(
            st.session_state.node_names,
            st.session_state.edges_df,
            rule_names,
            start_label,
            goal_label,
        ),
        stylesheet=problem_graph_cytoscape_stylesheet(),
        width=700,
        height=400,
        key="problem_graph_cytoscape",
    )

    render_problem_graph_selection_panel(selected, rule_names, start_label, goal_label,)

    render_advanced_edge_table(k)

    render_problem_graph_sanity_check(st.session_state.edges_df, start_label, goal_label, rule_names, prec_df, eps,)

    return st.session_state.edges_df


# Initialize and synchronize problem graph state.
def initialize_problem_graph_state(
    k,
    start_label,
    goal_label,
):
    if "edges_df" not in st.session_state:
        st.session_state.edges_df = pd.DataFrame(
            columns=["u", "v"]
        )

    st.session_state.edges_df = sync_edge_cost_columns(st.session_state.edges_df, k,)

    if "node_names" not in st.session_state:
        st.session_state.node_names = []

    st.session_state.node_names = sync_node_names(st.session_state.node_names, st.session_state.edges_df, start_label, goal_label,)


# Render the editable edge table as an advanced option.
def render_advanced_edge_table(k):
    with st.expander("Advanced: graph edge table"):
        st.caption(
            "Manual edge list. Each row stores one "
            "directed edge and its cost vector."
        )

        edited_edges = st.data_editor(st.session_state.edges_df, key="edges_editor", use_container_width=True, num_rows="dynamic",)

        st.session_state.edges_df = sync_edge_cost_columns(edited_edges, k,)

        st.session_state.node_names = sync_node_names(st.session_state.node_names, st.session_state.edges_df, st.session_state.get("start_label", ""), st.session_state.get("goal_label", ""),)