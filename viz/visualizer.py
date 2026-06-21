import json
import streamlit as st
import pandas as pd

from backend.backend_runner import run_algorithm
from backend.algorithm_config import ALGORITHMS

from examples.examples import EXAMPLES 

from core.rulebook_cycles import (
    find_sccs,
    edges_inside_component,
    collapse_cycle_to_equivalence_class,
)
from core.algorithm_rules import allowed_algorithms
from core.labels import id_to_label
from core.trace_utils import apply_trace_step, init_from_trace, extract_realization
from core.solution_utils import (
    collect_goal_vectors,
    collect_final_solution_pairs,
    compute_rulebook_nondominated_paths,
)
from core.formatting import unscale_vec, pretty_vec

from ui.rulebook_section import render_rulebook_section
from ui.json_import_section import render_json_import_section
from ui.RAstarpex_info_tab import render_RAstarpex_info_tab
from ui.sidebar_controls import render_sidebar_controls
from ui.problem_graph_section import render_problem_graph_section
from ui.run_controls import render_run_controls
from ui.comparison_view import render_comparison_view
from ui.single_run_view import render_single_run_view

from render.graphviz_render import dot_for_graph, dot_for_rule_graph

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
        st.session_state.k = 2
    if "rule_names_csv" not in st.session_state:
        st.session_state.rule_names_csv = "r0,r1"
    if "start_label" not in st.session_state:
        st.session_state.start_label = "S"
    if "goal_label" not in st.session_state:
        st.session_state.goal_label = "T"
    if "eps_values" not in st.session_state:
        st.session_state.eps_values = [0.0, 0.0]

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
    render_run_controls(prec_df)
    
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
    )

    # ---------------- Compare mode display ----------------
    if mode == "Compare Algorithms":
        render_comparison_view(edges_df, algo_right)
        st.stop()
    
    # ---------------- Single run display ----------------
    render_single_run_view(edges_df, rule_names)


        