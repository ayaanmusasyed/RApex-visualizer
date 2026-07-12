# ui/problem_graph_section.py
#
# CHANGES vs. the Streamlit-only version:
#   - st_cytoscapejs(...) -> problem_graph_editor(...)   (new component, returns an event dict)
#   - problem_graph_editor(...) now also takes rule_names, so React can
#     label the cost-entry prompts with the actual rule order
#   - added: dispatch_problem_graph_event(...) + st.rerun() right after
#   - render_problem_graph_selection_panel(...) call removed -- its job is
#     now done in-graph by React.

import pandas as pd
import streamlit as st

from viz.core.problem_graph_state import (
    sync_edge_cost_columns,
    sync_node_names,
)
from viz.render.cytoscape_problem_graph import (
    problem_graph_cytoscape_elements,
    problem_graph_cytoscape_stylesheet,
)
from viz.ui.graph_component import problem_graph_editor
from viz.ui.problem_graph_dispatch import dispatch_problem_graph_event
from viz.ui.problem_graph_creation_panel import (
    render_problem_graph_creation_panel,
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
        "Click empty space to add a node. Click a node, then click "
        "another node, to connect them. Click an edge to edit its "
        "costs. Double-click a node to rename. Right-click for more "
        "actions."
    )

    event = problem_graph_editor(
        elements=problem_graph_cytoscape_elements(
            st.session_state.node_names,
            st.session_state.edges_df,
            rule_names,
            start_label,
            goal_label,
        ),
        stylesheet=problem_graph_cytoscape_stylesheet(),
        rule_names=rule_names,
        key="problem_graph_editor",
    )

    if event is not None:
        dispatch_problem_graph_event(event, rule_names, start_label, goal_label)
        st.rerun()

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
# Left as plain Streamlit on purpose -- typing exact float costs is
# fiddly on a canvas. This is the power-user fallback for bulk edits.
def render_advanced_edge_table(k):
    with st.expander("Advanced: graph edge table"):
        st.caption(
            "Manual edge list. Each row stores one "
            "directed edge and its cost vector."
        )

        edited_edges = st.data_editor(st.session_state.edges_df, key="edges_editor", use_container_width=True, num_rows="dynamic",)

        st.session_state.edges_df = sync_edge_cost_columns(edited_edges, k,)

        st.session_state.node_names = sync_node_names(st.session_state.node_names, st.session_state.edges_df, st.session_state.get("start_label", ""), st.session_state.get("goal_label", ""),)
