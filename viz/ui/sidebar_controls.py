# ui/sidebar_controls.py

import streamlit as st
from viz.core.algorithm_rules import allowed_algorithms

def render_sidebar_controls(mode):
    with st.sidebar:
        st.header("1) Rules")

        k = st.number_input(
            "Number of rules (dimensions)",
            min_value=0,
            max_value=100,
            step=1,
            key="k"
        )

        if len(st.session_state.eps_values) != k:
            old = st.session_state.eps_values
            if len(old) < k:
                st.session_state.eps_values = old + [0.0] * (k - len(old))
            else:
                st.session_state.eps_values = old[:k]

        current_names = [x.strip() for x in st.session_state.rule_names_csv.split(",") if x.strip()]
        if len(current_names) != k:
            st.session_state.rule_names_csv = ",".join(f"r{i}" for i in range(k))

        rule_names_csv = st.text_input(
            "Rule names (comma-separated)",
            key="rule_names_csv"
        )
        rule_names = [x.strip() for x in rule_names_csv.split(",") if x.strip()]

        st.header("2) Start / Goal")
        start_label = st.text_input("Start node label", key="start_label")
        goal_label = st.text_input("Goal node label", key="goal_label")

        st.header("3) epsilon")
        eps = []
        for i in range(k):
            eps_i = st.number_input(
                f"eps[{i}]",
                min_value=0.0,
                step=0.1,
                value=float(st.session_state.eps_values[i]),
                key=f"eps_{i}"
            )
            eps.append(float(eps_i))

        st.session_state.eps_values = eps

        st.header("4) Run options")
        cutoff = int(st.number_input("cutoffTime (sec)", min_value=1, value=10, step=1))
        merge = st.selectbox("merge strategy", ["RANDOM", "SMALLER_G2", "MORE_SLACK"], index=0)

        if mode == "Compare Algorithms":
            st.header("5) Compare")

            algo_left = "RApex"

            algo_right = st.selectbox(
                "Compare RApex against",
                [a for a in allowed_algorithms(k) if a != "RApex"],
                index=0
            )

    return {
        "k": k,
        "rule_names": rule_names,
        "start_label": start_label,
        "goal_label": goal_label,
        "eps": eps,
        "cutoff": cutoff,
        "merge": merge,
        "algo_left": "RApex" if mode == "Compare Algorithms" else None,
        "algo_right": algo_right if mode == "Compare Algorithms" else None,
    }