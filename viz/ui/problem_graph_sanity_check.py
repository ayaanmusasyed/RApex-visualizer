import pandas as pd
import streamlit as st

from viz.core.solution_utils import (
    compute_rulebook_nondominated_paths,
)


# Render the rulebook-nondominated path sanity check.
def render_problem_graph_sanity_check(
    edges_df,
    start_label,
    goal_label,
    rule_names,
    prec_df,
    eps,
):
    with st.expander(
        "Rulebook-nondominated path sanity check"
    ):
        try:
            nondominated = compute_rulebook_nondominated_paths(
                edges_df,
                start_label,
                goal_label,
                len(rule_names),
                rule_names,
                prec_df,
                eps,
            )

            if not nondominated:
                st.caption(
                    "No complete start-to-goal paths found."
                )
                return

            rows = []

            for path, cost in nondominated:
                row = {
                    "Path": " → ".join(path),
                }

                for i, rule_name in enumerate(rule_names):
                    row[rule_name] = cost[i]

                rows.append(row)

            st.dataframe(
                pd.DataFrame(rows),
                use_container_width=True,
                hide_index=True,
            )

        except Exception as e:
            st.warning(
                f"Could not compute sanity check: {e}"
            )