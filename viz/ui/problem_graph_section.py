import streamlit as st
import pandas as pd

from core.solution_utils import compute_rulebook_nondominated_paths

from core.problem_graph_state import sync_edge_cost_columns

def render_problem_graph_section(k, rule_names, start_label, goal_label, prec_df, eps):

    st.header("Problem graph edges")

    need_cols = ["u", "v"] + [f"c{i}" for i in range(k)]

    if "edges_df" not in st.session_state:
        seed = pd.DataFrame([
            {"u": "S", "v": "A"},
            {"u": "A", "v": "T"},
        ])
        st.session_state.edges_df = sync_edge_cost_columns(seed, k)
    else:
        st.session_state.edges_df = sync_edge_cost_columns(
            st.session_state.edges_df,
            k,
        )

    edges_df = st.data_editor(
        st.session_state.edges_df,
        key="edges_editor",
        use_container_width=True,
        num_rows="dynamic"
    )
    st.session_state.edges_df = edges_df

    with st.expander("Rulebook-nondominated path sanity check"):
        try:
            nondom = compute_rulebook_nondominated_paths(
                edges_df,
                start_label,
                goal_label,
                k,
                rule_names,
                prec_df,
                eps,
            )

            if nondom:
                rows = []
                for path, cost in nondom:
                    row = {"Path": " -> ".join(path)}
                    for i, rn in enumerate(rule_names):
                        row[rn] = cost[i]
                    rows.append(row)

                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            else:
                st.caption("No complete start-to-goal paths found.")
        except Exception as e:
            st.warning(f"Could not compute sanity check: {e}")
    
    return edges_df