import streamlit as st

from backend.backend_runner import run_algorithm

def render_run_controls(
    mode,
    edges_df,
    rule_names,
    eps,
    prec_df,
    start_label,
    goal_label,
    cutoff,
    merge,
    algo_left=None,
    algo_right=None,
):
    if mode == "Single Run":
        run_btn = st.button("Run RApex")

        if run_btn:
            try:
                result = run_algorithm(
                    algorithm_name="RApex",
                    edges_df=edges_df,
                    rule_names=rule_names,
                    eps=eps,
                    prec_df=prec_df,
                    start_label=start_label,
                    goal_label=goal_label,
                    cutoff=cutoff,
                    merge=merge,
                )

                st.session_state.trace = result["trace"]
                st.session_state.trace_stepper = result["trace_stepper"]
                st.session_state.last_run_stdout = result["stdout"]
                st.session_state.last_run_stderr = result["stderr"]
                st.session_state.last_run_stats = result["stats_text"]
                st.session_state.name_to_id = result["name_to_id"]
                st.session_state.solution_edges = result["solution_edges"]
                st.session_state.solution_paths = result["solution_paths"]
                st.session_state.candidate_edges = result["candidate_edges"]
                st.session_state.candidate_paths = result["candidate_paths"]

                st.success(f"Loaded {len(result['trace'])} trace events.")
            except Exception as e:
                st.exception(e)

    else:
        compare_btn = st.button("Run RApex vs Benchmark")

        if compare_btn:
            try:
                left = run_algorithm(
                    algorithm_name=algo_left,
                    edges_df=edges_df,
                    rule_names=rule_names,
                    eps=eps,
                    prec_df=prec_df,
                    start_label=start_label,
                    goal_label=goal_label,
                    cutoff=cutoff,
                    merge=merge,
                )

                right = run_algorithm(
                    algorithm_name=algo_right,
                    edges_df=edges_df,
                    rule_names=rule_names,
                    eps=eps,
                    prec_df=prec_df,
                    start_label=start_label,
                    goal_label=goal_label,
                    cutoff=cutoff,
                    merge=merge,
                )

                st.session_state.compare_left = left
                st.session_state.compare_right = right

                st.success("Loaded comparison results.")
            except Exception as e:
                st.exception(e)
