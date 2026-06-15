import streamlit as st

from render.graphviz_render import dot_for_graph

def render_comparison_view(edges_df, algo_right):
    if "compare_left" not in st.session_state or "compare_right" not in st.session_state:
        st.info("Build a graph and click **Run Comparison**.")
        st.stop()

    left = st.session_state.compare_left
    right = st.session_state.compare_right

    st.subheader("Comparison summary")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### RApex")
        st.code(left["stats_text"] or "(no stats)")

        if left["has_trace"]:
            dot_left = dot_for_graph(edges_df, solution_edges=left["solution_edges"], candidate_edges=left["candidate_edges"],)
            st.graphviz_chart(dot_left)

            if left["solution_paths"]:
                st.markdown("**Representative realization(s)**")
                for p in left["solution_paths"]:
                    st.write(" -> ".join(p))

            if left["candidate_paths"]:
                st.markdown("**Also considered under epsilon**")
                for p in left["candidate_paths"]:
                    st.write(" -> ".join(p))
        else:
            st.info("No trace available for this algorithm yet.")
            st.code(left["stdout"] or "(no stdout)")

    with c2:
        st.markdown(f"### {algo_right}")
        st.code(right["stats_text"] or "(no stats)")

        if right["has_trace"]:
            dot_right = dot_for_graph(edges_df, solution_edges=right["solution_edges"], candidate_edges=right["candidate_edges"],)
            st.graphviz_chart(dot_right)

            if right["solution_paths"]:
                st.markdown("**Representative realization(s)**")
                for p in right["solution_paths"]:
                    st.write(" -> ".join(p))

            if right["candidate_paths"]:
                st.markdown("**Also considered under epsilon**")
                for p in right["candidate_paths"]:
                    st.write(" -> ".join(p))
        else:
            st.info("No trace available for this algorithm yet.")
            st.code(right["stdout"] or "(no stdout)")

    st.markdown("### Stats legend")

    st.markdown(
    """
    **Output format**

    `Algorithm-eps (...) | objectives | nodes | edges | node expansions | solutions | runtime (seconds)`

    Example:

    `RApex-eps (0,0,0) 3 4 5 4 1 0.000409`

    means:

    - **3** → number of objectives
    - **4** → nodes in the graph
    - **5** → edges in the graph
    - **4** → nodes expanded during search
    - **1** → number of solutions returned
    - **0.000409** → runtime in seconds
    """
    )
