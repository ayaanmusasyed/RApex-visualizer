import streamlit as st
import json
import pandas as pd

from examples import EXAMPLES
# ------------ JSON input ----------
def rulebook_layers_to_edges(layers):
    edges = []
    for i in range(len(layers)):
        for j in range(i + 1, len(layers)):
            for hi in layers[i]:
                for lo in layers[j]:
                    edges.append((hi, lo))
    return edges

def render_json_import_section(): 

    st.header("Import / Export JSON")

    with st.expander("Upload or paste JSON problem"):

        uploaded_json = st.file_uploader("Upload JSON", type=["json"],key="problem_json")

        example_name = st.selectbox("Use example", [""] + list(EXAMPLES.keys()))

        if st.button("Load selected example"):
            if example_name:
                st.session_state.sample_json_text = EXAMPLES[example_name]
                st.rerun()

        pasted_json = st.text_area("Or paste JSON here", value=st.session_state.get("sample_json_text", ""),height=220)

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
                    cfg = json.loads(raw)

                    loaded_rule_names = cfg["rules"]
                    loaded_rulebook = cfg.get("rulebook", {})
                    loaded_edges = cfg["graph"]["edges"]
                    loaded_start = cfg["start"]
                    loaded_goal = cfg["goal"]
                    loaded_eps = cfg.get("eps", 0.0)

                    if isinstance(loaded_eps, (int, float)):
                        loaded_eps = [float(loaded_eps)] * len(loaded_rule_names)
                    else:
                        loaded_eps = [float(x) for x in loaded_eps]

                    if "edges" in loaded_rulebook:
                        # Explicit edges are the general partial-order format.
                        # Rules not appearing here remain incomparable.
                        prec_edges = [(a, b) for a, b in loaded_rulebook["edges"]]
                    elif "layers" in loaded_rulebook:
                        # Layers are a convenience format for fully layered hierarchies only.
                        prec_edges = rulebook_layers_to_edges(loaded_rulebook["layers"])
                    else:
                        prec_edges = []

                    rows = []
                    for e in loaded_edges:
                        row = {"u": e["u"], "v": e["v"]}
                        c = e["c"]
                        if len(c) != len(loaded_rule_names):
                            raise ValueError(
                                f"Edge {e['u']}->{e['v']} has {len(c)} costs, "
                                f"but there are {len(loaded_rule_names)} rules."
                            )
                        for i, val in enumerate(c):
                            row[f"c{i}"] = float(val)
                        rows.append(row)

                    old_k = st.session_state.get("k", len(loaded_rule_names))

                    st.session_state.k = len(loaded_rule_names)
                    st.session_state.rule_names_csv = ",".join(loaded_rule_names)
                    st.session_state.start_label = loaded_start
                    st.session_state.goal_label = loaded_goal
                    st.session_state.eps_values = loaded_eps

                    for i, val in enumerate(loaded_eps):
                        st.session_state[f"eps_{i}"] = float(val)

                    for i in range(len(loaded_rule_names), old_k):
                        st.session_state.pop(f"eps_{i}", None)

                    st.session_state.prec_df = pd.DataFrame(
                        [{"Higher Priority": a, "Lower Priority": b} for a, b in prec_edges],
                        columns=["Higher Priority", "Lower Priority"]
                    )
                    st.session_state.edges_df = pd.DataFrame(rows)

                    st.success("Loaded problem from JSON.")
                    st.rerun()

            except Exception as e:
                st.exception(e)