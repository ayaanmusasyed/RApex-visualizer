import streamlit as st
import pandas as pd

from render.graphviz_render import dot_for_rule_graph, dot_for_rule_class_graph
from core.rulebook_cycles import (
    find_sccs,
    edges_inside_component,
    collapse_cycle_to_equivalence_class,
)

from core.rulebook_state import normalize_prec_df

from core.rulebook_state import (
    normalize_prec_df,
    add_rulebook_edge,
    delete_rulebook_edge,
)

from render.cytoscape_rulebook import rulebook_to_cytoscape_elements

from core.rulebook_classes import default_eq_classes, class_label

from core.rulebook_classes import (
    default_eq_classes,
    class_label,
    collapse_rules_into_class,
    remove_edges_inside_classes,
)

from streamlit_cytoscapejs import st_cytoscapejs
from render.cytoscape_render import (
    rulebook_class_cytoscape_elements,
    rulebook_cytoscape_stylesheet,
)

from core.rulebook_edit import (
    split_equivalence_class,
    add_class_edge,
    delete_class_edge,
)

from core.rulebook_classes import find_class_index

from ui.rule_management_panel import render_rule_management_panel

def render_rulebook_section(rule_names):

    # Keep same-priority rule groups in session state.
    if "prec_df" not in st.session_state:
        st.session_state.prec_df = pd.DataFrame(
            columns=["Higher Priority", "Lower Priority"]
        )

    if "eps_values" not in st.session_state:
        st.session_state.eps_values = [0.0] * len(rule_names)

    if "eq_classes" not in st.session_state:
        st.session_state.eq_classes = default_eq_classes(rule_names)

    # If the rule list changes, reset classes for now.
    # Later we can make this smarter for rename/add/delete.
    flat_rules = {
        rule
        for cls in st.session_state.eq_classes
        for rule in cls
    }

    if set(rule_names) != flat_rules:
        st.session_state.eq_classes = default_eq_classes(rule_names)

    # Call rulebook edit panel
    render_rule_management_panel(rule_names, st.session_state.prec_df, st.session_state.eps_values) 

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

    # Clean table edits before using the rulebook anywhere else.
    st.session_state.prec_df = normalize_prec_df(prec_df)
    prec_df = st.session_state.prec_df
    
    st.subheader("Rule graph preview")
    st.caption("Direct edges define priority. Rules with no arrows are incomparable.")
    st.graphviz_chart(
        dot_for_rule_class_graph(
            rule_names,
            prec_df,
            st.session_state.eq_classes,
        )
    )

    st.subheader("Interactive rulebook preview")
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

    st.write("Selected:", selected)
    if selected and "selected_node_id" in selected:
        node_id = selected["selected_node_id"]

        if node_id.startswith("class_"):
            class_idx = int(node_id.replace("class_", ""))

            if class_idx >= len(st.session_state.eq_classes):
                st.caption("Selection is stale after the rulebook changed. Click a node again.")
                return prec_df

            selected_class = st.session_state.eq_classes[class_idx]

            st.subheader("Selected rule class")
            st.write(f"Class {class_idx}: `{class_label(selected_class)}`")
            
            outgoing = []
            incoming = []

            for _, row in st.session_state.prec_df.iterrows():
                hi = str(row["Higher Priority"]).strip()
                lo = str(row["Lower Priority"]).strip()

                hi_idx = find_class_index(st.session_state.eq_classes, hi)
                lo_idx = find_class_index(st.session_state.eq_classes, lo)

                if hi_idx == class_idx:
                    outgoing.append(lo_idx)

                if lo_idx == class_idx:
                    incoming.append(hi_idx)

            st.caption("Current priority relations for selected class:")

            if outgoing:
                st.write(
                    "Higher than: "
                    + ", ".join(
                        f"`{class_label(st.session_state.eq_classes[i])}`"
                        for i in sorted(set(outgoing))
                        if i is not None
                    )
                )
            else:
                st.write("Higher than: none")

            if incoming:
                st.write(
                    "Lower than: "
                    + ", ".join(
                        f"`{class_label(st.session_state.eq_classes[i])}`"
                        for i in sorted(set(incoming))
                        if i is not None
                    )
                )
            else:
                st.write("Lower than: none")

            if len(selected_class) == 1:
                st.caption("This is a single-rule class.")
            else:
                st.caption("This is a same-priority equivalence class.")
                
            other_class_options = [
                i for i in range(len(st.session_state.eq_classes))
                if i != class_idx
            ]

            if other_class_options:
                target_idx = st.selectbox(
                    "Target class",
                    other_class_options,
                    format_func=lambda i: class_label(st.session_state.eq_classes[i]),
                    key="cyto_target_class",
                )

                c1, c2 = st.columns(2)

                if c1.button("Add selected > target", key="cyto_add_out_edge"):
                    try:
                        st.session_state.prec_df = add_class_edge(
                            st.session_state.prec_df,
                            st.session_state.eq_classes,
                            class_idx,
                            target_idx,
                        )
                        st.rerun()
                    except Exception as e:
                        st.warning(str(e))

                if c2.button("Add target > selected", key="cyto_add_in_edge"):
                    try:
                        st.session_state.prec_df = add_class_edge(
                            st.session_state.prec_df,
                            st.session_state.eq_classes,
                            target_idx,
                            class_idx,
                        )
                        st.rerun()
                    except Exception as e:
                        st.warning(str(e))

                if st.button("Delete edge selected > target", key="cyto_delete_out_edge"):
                    st.session_state.prec_df = delete_class_edge(
                        st.session_state.prec_df,
                        st.session_state.eq_classes,
                        class_idx,
                        target_idx,
                    )
                    st.rerun()

            if len(selected_class) > 1:
                if st.button("Split equivalence class", key="cyto_split_class"):
                    try:
                        st.session_state.eq_classes = split_equivalence_class(
                            st.session_state.eq_classes,
                            class_idx,
                        )
                        st.rerun()
                    except Exception as e:
                        st.warning(str(e))

    with st.expander("Same-priority groups"):
        st.caption("Rules in the same bracket are treated as equivalent priority.")

        for i, cls in enumerate(st.session_state.eq_classes):
            st.write(f"Class {i}: `{class_label(cls)}`")
        
    # --- Debug for rulebook state functions --- 
    with st.expander("Debug: rulebook state actions"):
        c1, c2 = st.columns(2)

        with c1:
            add_hi = st.selectbox("Higher rule", rule_names, key="debug_add_hi")
            add_lo = st.selectbox("Lower rule", rule_names, key="debug_add_lo")

            if st.button("Debug add edge", key="debug_add_rulebook_edge"):
                try:
                    st.session_state.prec_df = add_rulebook_edge(
                        st.session_state.prec_df,
                        add_hi,
                        add_lo,
                    )
                    st.rerun()
                except Exception as e:
                    st.warning(str(e))

        with c2:
            if len(prec_df) > 0:
                edge_labels = [
                    f"{row['Higher Priority']} > {row['Lower Priority']}"
                    for _, row in prec_df.iterrows()
                ]

                selected_edge = st.selectbox(
                    "Edge to delete",
                    edge_labels,
                    key="debug_delete_edge_select",
                )

                if st.button("Debug delete edge", key="debug_delete_rulebook_edge"):
                    hi, lo = selected_edge.split(" > ")

                    st.session_state.prec_df = delete_rulebook_edge(
                        st.session_state.prec_df,
                        hi,
                        lo,
                    )
                    st.rerun()
            else:
                st.caption("No rulebook edges to delete.")
    
    # --- Cytoscape Converter Debug ----
    with st.expander("Debug: Cytoscape elements"):
        st.json(rulebook_to_cytoscape_elements(rule_names, prec_df))


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
                    # Collapse the cycle into a real same-priority class.
                    st.session_state.eq_classes = collapse_rules_into_class(
                        st.session_state.eq_classes,
                        comp,
                    )

                    # Remove priority edges inside that same-priority class.
                    st.session_state.prec_df = remove_edges_inside_classes(
                        prec_df,
                        st.session_state.eq_classes,
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
                    # Collapse all rules in this cycle into one same-priority class.
                    st.session_state.eq_classes = collapse_rules_into_class(
                        st.session_state.eq_classes,
                        comp,
                    )

                    # Remove priority edges inside that same-priority class.
                    st.session_state.prec_df = remove_edges_inside_classes(
                        prec_df,
                        st.session_state.eq_classes,
                    )

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