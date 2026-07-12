import streamlit as st

from viz.core.problem_graph_edit import (
    add_edge,
    rename_node,
    delete_node,
    update_edge,
    delete_edge,
    reverse_edge,
)


# Render controls for the selected problem graph node.
def render_problem_graph_selection_panel(selected, rule_names, start_label, goal_label):
    if not selected or "selected_node_id" not in selected:
        return

    node_id = selected["selected_node_id"]

    if not node_id.startswith("node::"):
        return

    node_name = node_id.replace("node::", "", 1)

    if node_name not in st.session_state.node_names:
        st.caption("Selection is stale after the graph changed. Click a node again.")
        return

    st.subheader("Selected graph node")
    st.write(f"Node: `{node_name}`")

    render_node_label_controls(node_name, start_label, goal_label)
    render_edge_creation_controls(node_name, rule_names)
    render_existing_edges(node_name, rule_names)
    render_node_delete_control(node_name, start_label, goal_label)

# Render rename and start/goal controls.
def render_node_label_controls(node_name, start_label, goal_label):
    new_name = st.text_input(
        "Rename node",
        value=node_name,
        key=f"problem_rename_{node_name}",
    )

    if st.button("Save node name", key=f"problem_save_name_{node_name}"):
        try:
            node_names, edges_df = rename_node(
                st.session_state.node_names,
                st.session_state.edges_df,
                node_name,
                new_name,
            )

            st.session_state.node_names = node_names
            st.session_state.edges_df = edges_df

            if start_label == node_name:
                st.session_state.pending_start_label = new_name

            if goal_label == node_name:
                st.session_state.pending_goal_label = new_name

            st.rerun()

        except Exception as e:
            st.warning(str(e))

    c1, c2 = st.columns(2)

    if c1.button("Set as start", key=f"problem_set_start_{node_name}"):
        st.session_state.pending_start_label = node_name
        st.rerun()

    if c2.button("Set as goal", key=f"problem_set_goal_{node_name}"):
        st.session_state.pending_goal_label = node_name
        st.rerun()

# Render controls for creating an outgoing edge.
def render_edge_creation_controls(node_name, rule_names):
    other_nodes = [
        node
        for node in st.session_state.node_names
        if node != node_name
    ]

    st.divider()
    st.markdown("#### Add outgoing edge")

    if not other_nodes:
        st.caption("Add another node before creating an edge.")
        return

    target = st.selectbox(
        "Target node",
        other_nodes,
        key=f"problem_edge_target_{node_name}",
    )

    costs = []

    for i, rule_name in enumerate(rule_names):
        cost = st.number_input(
            f"{rule_name} cost",
            value=0.0,
            step=1.0,
            key=f"problem_edge_cost_{node_name}_{i}",
        )

        costs.append(float(cost))

    if st.button(f"Add {node_name} → {target}", key=f"problem_add_edge_{node_name}"):
        try:
            st.session_state.edges_df = add_edge(
                st.session_state.edges_df,
                node_name,
                target,
                costs,
                len(rule_names),
            )

            st.rerun()

        except Exception as e:
            st.warning(str(e))

# Render controls for edges touching the selected node.
def render_existing_edges(node_name, rule_names):
    edge_options = []

    for edge_idx, row in st.session_state.edges_df.reset_index(drop=True).iterrows():
        source = str(row["u"]).strip()
        target = str(row["v"]).strip()

        if source == node_name or target == node_name:
            edge_options.append(edge_idx)

    st.divider()
    st.markdown("#### Edit existing edge")

    if not edge_options:
        st.caption("This node has no edges.")
        return

    edge_idx = st.selectbox(
        "Edge",
        edge_options,
        format_func=lambda i: edge_label(i),
        key=f"problem_existing_edge_{node_name}",
    )

    row = st.session_state.edges_df.iloc[edge_idx]

    source = st.selectbox(
        "Source",
        st.session_state.node_names,
        index=st.session_state.node_names.index(str(row["u"]).strip()),
        key=f"problem_edit_source_{node_name}_{edge_idx}",
    )

    target = st.selectbox(
        "Target",
        st.session_state.node_names,
        index=st.session_state.node_names.index(str(row["v"]).strip()),
        key=f"problem_edit_target_{node_name}_{edge_idx}",
    )

    costs = []

    for i, rule_name in enumerate(rule_names):
        cost = st.number_input(
            f"Edit {rule_name} cost",
            value=float(row[f"c{i}"]),
            step=1.0,
            key=f"problem_edit_cost_{node_name}_{edge_idx}_{i}",
        )

        costs.append(float(cost))

    c1, c2, c3 = st.columns(3)

    if c1.button("Save edge", key=f"problem_save_edge_{node_name}_{edge_idx}"):
        try:
            st.session_state.edges_df = update_edge(
                st.session_state.edges_df,
                edge_idx,
                source,
                target,
                costs,
                len(rule_names),
            )

            st.rerun()

        except Exception as e:
            st.warning(str(e))

    if c2.button("Reverse edge", key=f"problem_reverse_edge_{node_name}_{edge_idx}"):
        try:
            st.session_state.edges_df = reverse_edge(
                st.session_state.edges_df,
                edge_idx,
            )

            st.rerun()

        except Exception as e:
            st.warning(str(e))

    if c3.button("Delete edge", key=f"problem_delete_edge_{node_name}_{edge_idx}"):
        try:
            st.session_state.edges_df = delete_edge(
                st.session_state.edges_df,
                edge_idx,
            )

            st.rerun()

        except Exception as e:
            st.warning(str(e))

# Format one edge for the edge selector.
def edge_label(edge_idx):
    row = st.session_state.edges_df.iloc[edge_idx]

    source = str(row["u"]).strip()
    target = str(row["v"]).strip()

    return f"{source} → {target}"

# Render the selected node delete control.
def render_node_delete_control(node_name, start_label, goal_label):
    st.divider()

    if st.button("Delete node", key=f"problem_delete_node_{node_name}"):
        try:
            node_names, edges_df = delete_node(
                st.session_state.node_names,
                st.session_state.edges_df,
                node_name,
            )

            st.session_state.node_names = node_names
            st.session_state.edges_df = edges_df

            if start_label == node_name:
                st.session_state.pending_start_label = ""

            if goal_label == node_name:
                st.session_state.pending_goal_label = ""

            st.rerun()

        except Exception as e:
            st.warning(str(e))