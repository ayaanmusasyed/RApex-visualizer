import streamlit as st

from viz.core.problem_graph_edit import add_node

# Render controls for adding standalone graph nodes.
def render_problem_graph_creation_panel():
    with st.expander("Manage graph nodes"):
        new_node_name = st.text_input(
            "New node name",
            key="problem_new_node_name",
        )

        if st.button(
            "Add node",
            key="problem_add_node",
        ):
            try:
                st.session_state.node_names = add_node(
                    st.session_state.node_names,
                    new_node_name,
                )

                st.session_state.problem_new_node_name = ""
                st.rerun()

            except Exception as e:
                st.warning(str(e))