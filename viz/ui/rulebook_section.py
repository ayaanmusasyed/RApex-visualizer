import streamlit as st
import pandas as pd

from render.graphviz_render import dot_for_rule_graph
from core.rulebook_cycles import (
    find_sccs,
    edges_inside_component,
    collapse_cycle_to_equivalence_class,
)

def render_rulebook_section(rule_names):
    st.header("Rule precedence graph")
    st.caption("State rule graph edges to explicitly define rule priority. Rules with no edges remain incomparable.")
    if "prec_df" not in st.session_state:
        st.session_state.prec_df = pd.DataFrame(columns=["Higher Priority", "Lower Priority"])

    prec_df = st.data_editor(
        st.session_state.prec_df,
        key="prec_editor",
        use_container_width=True,
        num_rows="dynamic"
    )
    st.session_state.prec_df = prec_df
    st.subheader("Rule graph preview")
    st.caption("Direct edges define priority. Rules with no arrows are incomparable.")
    st.graphviz_chart(dot_for_rule_graph(rule_names, prec_df))

    # ---- Cycle warning -------
    cycle_components = find_sccs(rule_names, prec_df)

    if cycle_components:
        st.error("Cycle detected in the rulebook.")

        for comp in cycle_components:
            st.markdown(
                "**Involved rules:** " + ", ".join(f"`{r}`" for r in comp)
            )

            internal_edges = edges_inside_component(prec_df, comp)

            if len(comp) == 2:
                r1, r2 = comp

                st.warning(
                    f"Rules `{r1}` and `{r2}` currently claim priority over each other."
                )

                st.markdown(
                    """
            Choose one:

            **A)** Treat the two rules as having equal priority.

            **B)** Remove one of the conflicting preferences.
            """
                )

                c1, c2, c3 = st.columns(3)

                if c1.button(
                    f"Treat {r1} and {r2} as equal priority",
                    key=f"eq_{r1}_{r2}"
                ):
                    st.session_state.prec_df = collapse_cycle_to_equivalence_class(
                        prec_df,
                        comp
                    )
                    st.rerun()

                # find the two cycle edges
                edge_lookup = {(a, b): idx for idx, a, b in internal_edges}

                if (r1, r2) in edge_lookup:
                    if c2.button(
                        f"Remove {r1} > {r2}",
                        key=f"remove_{r1}_{r2}"
                    ):
                        st.session_state.prec_df = prec_df.drop(
                            edge_lookup[(r1, r2)]
                        ).reset_index(drop=True)
                        st.rerun()

                if (r2, r1) in edge_lookup:
                    if c3.button(
                        f"Remove {r2} > {r1}",
                        key=f"remove_{r2}_{r1}"
                    ):
                        st.session_state.prec_df = prec_df.drop(
                            edge_lookup[(r2, r1)]
                        ).reset_index(drop=True)
                        st.rerun()
            else:
                st.warning(
                    "For 3 or more rules, this cycle is ambiguous. You can either collapse the involved "
                    "rules into one equal-priority group, or manually remove edges to make the rulebook acyclic."
                )

                c_a, c_b = st.columns(2)

                if c_a.button(
                    "Treat involved rules as same priority",
                    key=f"collapse_{'_'.join(comp)}"
                ):
                    st.session_state.prec_df = collapse_cycle_to_equivalence_class(prec_df, comp)
                    st.rerun()

                if c_b.button(
                    "Show edges to edit manually",
                    key=f"show_edges_{'_'.join(comp)}"
                ):
                    st.session_state[f"show_cycle_edges_{'_'.join(comp)}"] = True

                if st.session_state.get(f"show_cycle_edges_{'_'.join(comp)}", False):
                    st.markdown("Edges involved in the cycle:")
                    for _, a, b in internal_edges:
                        st.markdown(f"- `{a} > {b}`")

        st.stop()

    return prec_df