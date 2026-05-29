# viz/visualizer.py

import json
import streamlit as st
import pandas as pd

from trace_utils import apply_trace_step, init_from_trace, extract_realization
from render_utils import unscale_vec, pretty_vec, dot_for_graph, dot_for_rule_graph
from solution_utils import (
    collect_goal_vectors,
    collect_final_solution_pairs,
    compute_rulebook_nondominated_paths,
)
from backend_runner import run_algorithm


from algorithm_config import ALGORITHMS

def allowed_algorithms(k):
    out = []
    for name, cfg in ALGORITHMS.items():
        max_k = cfg["max_k"]
        min_k = cfg["min_k"]
        if k >= min_k and (max_k is None or k <= max_k):
            out.append(name)
    return out

def id_to_label(state_id: int) -> str:
    name_to_id = st.session_state.get("name_to_id", {})
    rev = {v: k for k, v in name_to_id.items()}
    return rev.get(state_id, str(state_id))


# ---------------- UI ----------------

st.set_page_config(page_title="RApex Visualizer", layout="wide")
st.title("RApex Visualizer")

mode = st.radio("Mode", ["Single Run", "Compare Algorithms"], horizontal=True)

# ------------ JSON input ----------
st.header("Import / Export JSON")

with st.expander("Upload or paste JSON problem"):
    uploaded_json = st.file_uploader("Upload JSON", type=["json"], key="problem_json")
    pasted_json = st.text_area("Or paste JSON here", height=220)

    def _rulebook_layers_to_edges(layers):
        edges = []
        for i in range(len(layers)):
            for j in range(i + 1, len(layers)):
                for hi in layers[i]:
                    for lo in layers[j]:
                        edges.append((hi, lo))
        return edges

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
                    prec_edges = _rulebook_layers_to_edges(loaded_rulebook["layers"])
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

with st.sidebar:
    st.header("1) Rules")

    k = st.number_input(
        "Number of rules (dimensions)",
        min_value=1,
        max_value=12,
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

st.header("Problem graph edges")

need_cols = ["u", "v"] + [f"c{i}" for i in range(k)]

if "edges_df" not in st.session_state:
    seed = pd.DataFrame([
        {"u": "S", "v": "A", **{f"c{i}": 0.0 for i in range(k)}},
        {"u": "A", "v": "T", **{f"c{i}": 0.0 for i in range(k)}},
    ])
    st.session_state.edges_df = seed[need_cols]
else:
    df_old = st.session_state.edges_df.copy()
    for c in need_cols:
        if c not in df_old.columns:
            df_old[c] = 0.0 if c.startswith("c") else ""
    st.session_state.edges_df = df_old[need_cols]

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


# ---------------- Run buttons ----------------

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


# ---------------- Compare mode display ----------------

if mode == "Compare Algorithms":
    if "compare_left" not in st.session_state or "compare_right" not in st.session_state:
        st.info("Build a graph and click **Run Comparison**.")
        st.stop()

    left = st.session_state.compare_left
    right = st.session_state.compare_right

    st.subheader("Comparison summary")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### RApex")
        st.code(left["stats_text"] or "(no stats)")

        if left["has_trace"]:
            dot_left = dot_for_graph(edges_df, solution_edges=left["solution_edges"], candidate_edges=left["candidate_edges"],)
            st.graphviz_chart(dot_left)

            if left["solution_paths"]:
                st.markdown("**Representative realization(s)**")
                for p in left["solution_paths"]:
                    st.write(" -> ".join(p))

            if left["candidate_paths"]:
                st.markdown("**Also considered under epsilon**")
                for p in left["candidate_paths"]:
                    st.write(" -> ".join(p))
        else:
            st.info("No trace available for this algorithm yet.")
            st.code(left["stdout"] or "(no stdout)")

    with c2:
        st.markdown(f"### {algo_right}")
        st.code(right["stats_text"] or "(no stats)")

        if right["has_trace"]:
            dot_right = dot_for_graph(edges_df, solution_edges=right["solution_edges"], candidate_edges=right["candidate_edges"],)
            st.graphviz_chart(dot_right)

            if right["solution_paths"]:
                st.markdown("**Representative realization(s)**")
                for p in right["solution_paths"]:
                    st.write(" -> ".join(p))

            if right["candidate_paths"]:
                st.markdown("**Also considered under epsilon**")
                for p in right["candidate_paths"]:
                    st.write(" -> ".join(p))
        else:
            st.info("No trace available for this algorithm yet.")
            st.code(right["stdout"] or "(no stdout)")

    st.markdown("### Stats legend")

    st.markdown(
    """
    **Output format**

    `Algorithm-eps (...) | objectives | nodes | edges | node expansions | solutions | runtime (seconds)`

    Example:

    `RApex-eps (0,0,0) 3 4 5 4 1 0.000409`

    means:

    - **3** → number of objectives
    - **4** → nodes in the graph
    - **5** → edges in the graph
    - **4** → nodes expanded during search
    - **1** → number of solutions returned
    - **0.000409** → runtime in seconds
    """
    )

# ---------------- Single run display ----------------

if "trace_stepper" not in st.session_state:
    st.info("Build a graph and click **Run RApex**.")
    st.stop()

stp = st.session_state.trace_stepper

with st.expander("Last run output"):
    st.code(st.session_state.get("last_run_stdout", ""))
    st.code(st.session_state.get("last_run_stderr", ""))
    st.code(st.session_state.get("last_run_stats", ""))

c1, c2, c3, c4 = st.columns(4)

if c1.button("Reset"):
    st.session_state.trace_stepper = init_from_trace(st.session_state.trace)
    st.rerun()

if c2.button("Next Iteration"):
    apply_trace_step(stp)

if c3.button("Run 10 iterations"):
    for _ in range(10):
        apply_trace_step(stp)

if c4.button("Instant solve"):
    while stp.i < len(stp.trace):
        apply_trace_step(stp)

st.divider()

name_to_id = st.session_state.get("name_to_id", {})
id_to_name = {v: k for k, v in name_to_id.items()}

cur_node = set()
if stp.last_pop:
    cur_node = {id_to_name.get(stp.last_pop["state"], str(stp.last_pop["state"]))}

open_nodes = {
    id_to_name.get(it["state"], str(it["state"]))
    for (_, _, it) in stp.OPEN
}

highlight_edges = set()
pruned_nodes = set()

for e in reversed(stp.events):
    if e["kind"] == "pop" and e is not stp.events[-1]:
        break
    if e["kind"] == "enqueue":
        frm = id_to_name.get(e["from"], str(e["from"])) if e.get("from") is not None else None
        to = id_to_name.get(e["to"], str(e["to"])) if e.get("to") is not None else None
        if frm and to:
            highlight_edges.add((frm, to))
    if e["kind"] == "prune":
        s = e.get("state")
        if s is not None:
            pruned_nodes.add(id_to_name.get(s, str(s)))

shown_solution_edges = set()
shown_candidate_edges = set()

if stp.i >= len(stp.trace):
    shown_solution_edges = st.session_state.get("solution_edges", set())
    shown_candidate_edges = st.session_state.get("candidate_edges", set())

dot = dot_for_graph(
    edges_df,
    highlight_nodes=cur_node,
    highlight_edges=highlight_edges,
    open_nodes=open_nodes,
    pruned_nodes=pruned_nodes,
    solution_edges=shown_solution_edges,
    candidate_edges=shown_candidate_edges,
)
st.graphviz_chart(dot)

st.subheader("Current pop")
if stp.last_pop:
    node_name = id_to_label(stp.last_pop["state"])
    st.markdown(
        f"Currently expanding **{node_name}** "
        f"with cost vector **{pretty_vec(stp.last_pop['f'])}** "
        f"and lex-key **{pretty_vec(stp.last_pop['key'])}**."
    )
else:
    st.caption("No pop yet.")

st.subheader("OPEN (heap preview)")
open_rows = []
for key, tb, it in stp.OPEN[:200]:
    f_unscaled = unscale_vec(it["f"])
    key_unscaled = unscale_vec(list(key))

    row = {"state": id_to_label(it["state"]), "key": pretty_vec(key_unscaled)}

    for i, x in enumerate(f_unscaled):
        row[f"f{i}"] = x

    open_rows.append(row)

if open_rows:
    st.dataframe(pd.DataFrame(open_rows), use_container_width=True, hide_index=True)
else:
    st.caption("OPEN is empty.")

st.subheader("Event log")

def pretty_event(e):
    if e["kind"] == "meta":
        return f"Using solver **{e['solver']}**."

    if e["kind"] == "pop":
        return f"Popped **{id_to_label(e['state'])}** with cost {pretty_vec(e['f'])}."

    if e["kind"] == "enqueue":
        frm = id_to_label(e["from"]) if e.get("from") is not None else "?"
        to = id_to_label(e["to"]) if e.get("to") is not None else "?"
        return f"From **{frm}**, added **{to}** to OPEN with cost {pretty_vec(e['f'])}."

    if e["kind"] == "prune":
        return f"Pruned **{id_to_label(e['state'])}**."

    if e["kind"] == "other":
        raw = e.get("raw", {})
        t = raw.get("type", "unknown")

        if t == "goal":
            item = extract_realization(raw)
            return f"Reached goal **{id_to_label(item['state'])}** with cost {pretty_vec(item['f'])}."

        if t == "solution":
            item = extract_realization(raw)
            return f"Accepted representative realization at **{id_to_label(item['state'])}** with cost {pretty_vec(item['f'])}."

        if t == "prune":
            item = extract_realization(raw)
            where = raw.get("where", "search")
            return f"Pruned **{id_to_label(item['state'])}** during **{where}** with cost {pretty_vec(item['f'])}."

        if t == "final_solutions":
            return "Computed final RApex solution pair(s)."

        return f"Trace event: **{t}**."

    return str(e)

for e in stp.events[-50:]:
    st.markdown(f"- {pretty_event(e)}")

if st.session_state.get("solution_paths"):
    st.subheader("Representative realization(s)")
    for p in st.session_state["solution_paths"]:
        st.write(" -> ".join(p))

if st.session_state.get("candidate_paths"):
    st.subheader("Also considered under epsilon")
    for p in st.session_state["candidate_paths"]:
        st.write(" -> ".join(p))

st.markdown("### Legend")
st.markdown(
    """
    <div style="display:flex; gap:24px; flex-wrap:wrap; align-items:center; margin-bottom:8px;">
      <div><span style="display:inline-block; width:18px; height:18px; background:cyan; border:1px solid #333; margin-right:8px;"></span>Current pop</div>
      <div><span style="display:inline-block; width:18px; height:18px; background:lightyellow; border:1px solid #333; margin-right:8px;"></span>In OPEN / frontier</div>
      <div><span style="display:inline-block; width:18px; height:18px; background:white; border:2px dashed red; margin-right:8px;"></span>Pruned node</div>
      <div><span style="display:inline-block; width:28px; height:0; border-top:4px solid green; margin-right:8px; vertical-align:middle;"></span>Representative realization</div>
      <div><span style="display:inline-block; width:28px; height:0; border-top:4px solid orange; margin-right:8px; vertical-align:middle;"></span>Also considered under ε</div>
      <div><span style="display:inline-block; width:28px; height:0; border-top:4px solid blue; margin-right:8px; vertical-align:middle;"></span>Currently explored edge</div>
      <div><span style="display:inline-block; width:28px; height:0; border-top:2px solid gray; margin-right:8px; vertical-align:middle;"></span>Unhighlighted edge</div>
    </div>
    """,
    unsafe_allow_html=True,
)

if st.session_state.get("trace"):
    final_pairs = collect_final_solution_pairs(st.session_state.trace)

    if final_pairs:
        st.subheader("Final RApex solution pair(s)")

        rows = []
        for i, pair in enumerate(final_pairs):
            row = {
                "pair": i,
                "apex": pretty_vec(pair["apex"]),
                "realization": pretty_vec(pair["realization"]),
            }
            rows.append(row)

        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        
with st.expander("Debug"):
    st.write("Collected solution vectors:", collect_goal_vectors(st.session_state.trace))
    st.write("Computed solution edges:", st.session_state.get("solution_edges", set()))
    st.write("Computed solution paths:", st.session_state.get("solution_paths", []))

    