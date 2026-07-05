import streamlit as st
import json
import pandas as pd

from examples.examples import EXAMPLES

from core.json_problem import parse_problem_json, problem_state_to_json
# ------------ JSON input ----------

def render_json_import_section():

    st.header("Import / Export JSON")

    with st.expander("Upload or paste JSON problem"):
        
        uploaded_json = st.file_uploader(
            "Upload JSON",
            type=["json"],
            key="problem_json",
        )

        example_name = st.selectbox(
            "Use example",
            [""] + list(EXAMPLES.keys()),
        )

        if st.button("Load selected example"):
            if example_name:
                st.session_state.sample_json_text = EXAMPLES[example_name]
                st.rerun()

        pasted_json = st.text_area(
            "Or paste JSON here",
            value=st.session_state.get("sample_json_text", ""),
            height=220,
        )

        if st.button("Load JSON problem"):
            try:
                raw = None

                if uploaded_json is not None:
                    raw = uploaded_json.read().decode("utf-8")
                elif pasted_json.strip():
                    raw = pasted_json

                if not raw:
                    st.warning("Provide a JSON file or paste JSON text.")

                else:
                    parsed = parse_problem_json(raw)

                    loaded_rule_names = parsed["rule_names"]
                    loaded_eps = parsed["eps"]

                    old_k = st.session_state.get(
                        "k",
                        len(loaded_rule_names),
                    )

                    st.session_state.k = len(loaded_rule_names)
                    st.session_state.rule_names_csv = ",".join(loaded_rule_names)

                    st.session_state.start_label = parsed["start"]
                    st.session_state.goal_label = parsed["goal"]

                    st.session_state.eps_values = loaded_eps
                    st.session_state.eq_classes = parsed["eq_classes"]
                    st.session_state.prec_df = parsed["prec_df"]
                    st.session_state.edges_df = parsed["edges_df"]

                    for i, val in enumerate(loaded_eps):
                        st.session_state[f"eps_{i}"] = float(val)

                    for i in range(len(loaded_rule_names), old_k):
                        st.session_state.pop(f"eps_{i}", None)

                    st.success("Loaded problem from JSON.")
                    st.rerun()

            except Exception as e:
                st.exception(e)
                
    with st.expander("Export current JSON"):
        required_keys = [
            "rule_names_csv",
            "eq_classes",
            "prec_df",
            "edges_df",
            "start_label",
            "goal_label",
            "eps_values",
        ]

        if all(key in st.session_state for key in required_keys):
            rule_names = [
                r.strip()
                for r in st.session_state.rule_names_csv.split(",")
                if r.strip()
            ]

            exported_json = problem_state_to_json(
                rule_names=rule_names,
                eq_classes=st.session_state.eq_classes,
                prec_df=st.session_state.prec_df,
                edges_df=st.session_state.edges_df,
                start=st.session_state.start_label,
                goal=st.session_state.goal_label,
                eps=st.session_state.eps_values,
            )

            st.code(exported_json, language="json")

            st.download_button(
                "Download JSON",
                data=exported_json,
                file_name="rulebook_problem.json",
                mime="application/json",
                key="download_problem_json",
            )
        else:
            st.caption("Build or load a problem before exporting JSON.")