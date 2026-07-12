# ui/problem_graph_dispatch.py
#
# Takes one event dict back from the React problem graph editor and
# applies it to session state. All real mutations already live in
# core/problem_graph_edit.py -- this is just the lookup table.
#
# Edge actions carry "edge_index" directly (read off the cytoscape
# element's data("edge_index") in React) rather than re-finding the row
# by (source, target) strings -- matching by name broke silently on
# parallel edges and was needlessly fragile.

import streamlit as st

from viz.core.problem_graph_edit import (
    add_node,
    rename_node,
    delete_node,
    add_edge,
    update_edge,
    delete_edge,
    reverse_edge,
)


# Apply one event dict from the problem graph editor.
def dispatch_problem_graph_event(event, rule_names, start_label, goal_label):
    action = event.get("action")

    if action == "add_node":
        st.session_state.node_names = add_node(
            st.session_state.node_names, event["name"],
        )
        return

    if action == "rename_node":
        st.session_state.node_names, st.session_state.edges_df = rename_node(
            st.session_state.node_names, st.session_state.edges_df,
            event["old"], event["new"],
        )
        return

    if action == "delete_node":
        st.session_state.node_names, st.session_state.edges_df = delete_node(
            st.session_state.node_names, st.session_state.edges_df,
            event["name"],
        )
        return

    if action == "set_start":
        st.session_state.pending_start_label = event["name"]
        return

    if action == "set_goal":
        st.session_state.pending_goal_label = event["name"]
        return

    if action == "add_edge":
        st.session_state.edges_df = add_edge(
            st.session_state.edges_df, event["source"], event["target"],
            event["costs"], len(rule_names),
        )
        return

    if action == "update_edge":
        row = st.session_state.edges_df.loc[event["edge_index"]]
        st.session_state.edges_df = update_edge(
            st.session_state.edges_df, event["edge_index"],
            row["u"], row["v"], event["costs"], len(rule_names),
        )
        return

    if action == "delete_edge":
        st.session_state.edges_df = delete_edge(
            st.session_state.edges_df, event["edge_index"],
        )
        return

    if action == "reverse_edge":
        st.session_state.edges_df = reverse_edge(
            st.session_state.edges_df, event["edge_index"],
        )
        return

    raise ValueError(f"Unknown problem graph event: {action!r}")
