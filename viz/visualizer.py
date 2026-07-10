import json
import streamlit as st
import pandas as pd

from viz.backend.backend_runner import run_algorithm
from viz.backend.algorithm_config import ALGORITHMS

from viz.examples.examples import EXAMPLES 

from viz.core.rulebook_cycles import (
    find_sccs,
    edges_inside_component,
    collapse_cycle_to_equivalence_class,
)
from viz.core.algorithm_rules import allowed_algorithms
from viz.core.labels import id_to_label
from viz.core.trace_utils import apply_trace_step, init_from_trace, extract_realization
from viz.core.solution_utils import (
    collect_goal_vectors,
    collect_final_solution_pairs,
    compute_rulebook_nondominated_paths,
)
from viz.core.formatting import unscale_vec, pretty_vec

from viz.ui.rulebook_section import render_rulebook_section
from viz.ui.json_import_section import render_json_import_section
from viz.ui.RAstarpex_info_tab import render_RAstarpex_info_tab
from viz.ui.sidebar_controls import render_sidebar_controls
from viz.ui.problem_graph_section import render_problem_graph_section
from viz.ui.run_controls import render_run_controls
from viz.ui.comparison_view import render_comparison_view
from viz.ui.single_run_view import render_single_run_view

from viz.render.graphviz_render import dot_for_graph, dot_for_rule_graph

# ---------------- UI ----------------
st.set_page_config(page_title="RApex Visualizer", layout="wide")

# ---------------- Tabs ------------------
st.title("Multi Objective Search Visualizer")

tab_rapex, tab_tool = st.tabs(["RA*pex", "Tool"])

with tab_rapex:
    render_RAstarpex_info_tab()

with tab_tool: 
    mode = st.radio("Mode", ["Single Run", "Compare Algorithms"], horizontal=True)
    render_json_import_section()

    # ---------------- Inputs ----------------
    if "k" not in st.session_state:
        st.session_state.k = 0
    if "rule_names_csv" not in st.session_state:
        st.session_state.rule_names_csv = ""
    if "start_label" not in st.session_state:
        st.session_state.start_label = ""
    if "goal_label" not in st.session_state:
        st.session_state.goal_label = ""
    if "eps_values" not in st.session_state:
        st.session_state.eps_values = [0.0, 0.0]


    # Sync w/ rulebook 
        
    if "pending_rule_names_csv" in st.session_state:
        st.session_state.rule_names_csv = st.session_state.pop("pending_rule_names_csv")

    if "pending_eps_values" in st.session_state:
        eps = st.session_state.pop("pending_eps_values")
        st.session_state.eps_values = eps

        for i, val in enumerate(eps):
            st.session_state[f"eps_{i}"] = float(val)

        j = len(eps)
        while f"eps_{j}" in st.session_state:
            st.session_state.pop(f"eps_{j}", None)
            j += 1

    if "pending_k" in st.session_state:
        st.session_state.k = st.session_state.pop("pending_k")

    controls = render_sidebar_controls(mode)

    k = controls["k"]
    rule_names = controls["rule_names"]
    start_label = controls["start_label"]
    goal_label = controls["goal_label"]
    eps = controls["eps"]
    cutoff = controls["cutoff"]
    merge = controls["merge"]
    algo_left = controls["algo_left"]
    algo_right = controls["algo_right"]

    prec_df = render_rulebook_section(rule_names)

    edges_df = render_problem_graph_section(
        k, rule_names, start_label, goal_label, prec_df, eps
    )

    # ---------------- Run buttons ----------------
    render_run_controls(
        mode,
        edges_df,
        rule_names,
        eps,
        prec_df,
        start_label,
        goal_label,
        cutoff,
        merge,
        algo_left,
        algo_right,
        eq_classes=st.session_state.get("eq_classes"),
    )

    # ---------------- Compare mode display ----------------
    if mode == "Compare Algorithms":
        render_comparison_view(edges_df, algo_right)
        st.stop()
    
    # ---------------- Single run display ----------------
    render_single_run_view(edges_df, rule_names)


        