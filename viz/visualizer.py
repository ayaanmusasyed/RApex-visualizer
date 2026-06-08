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

from examples import EXAMPLES 

# ---- Functions for cycle detection w/ SCCs ----
def find_sccs(rule_names, prec_df):
    name_set = set(rule_names)
    G = {r: [] for r in rule_names}
    GR = {r: [] for r in rule_names}

    for _, row in prec_df.iterrows():
        a = str(row.get("Higher Priority", "")).strip()
        b = str(row.get("Lower Priority", "")).strip()
        if a in name_set and b in name_set:
            G[a].append(b)
            GR[b].append(a)

    seen = set()
    order = []

    def dfs(u):
        seen.add(u)
        for v in G[u]:
            if v not in seen:
                dfs(v)
        order.append(u)

    for r in rule_names:
        if r not in seen:
            dfs(r)

    seen.clear()
    comps = []

    def rdfs(u, comp):
        seen.add(u)
        comp.append(u)
        for v in GR[u]:
            if v not in seen:
                rdfs(v, comp)

    for r in reversed(order):
        if r not in seen:
            comp = []
            rdfs(r, comp)
            comps.append(comp)

    return [c for c in comps if len(c) > 1]


def edges_inside_component(prec_df, comp):
    comp = set(comp)
    out = []
    for idx, row in prec_df.iterrows():
        a = str(row.get("Higher Priority", "")).strip()
        b = str(row.get("Lower Priority", "")).strip()
        if a in comp and b in comp:
            out.append((idx, a, b))
    return out


def remove_internal_cycle_edges(prec_df, comp):
    comp = set(comp)
    keep_rows = []
    for _, row in prec_df.iterrows():
        a = str(row.get("Higher Priority", "")).strip()
        b = str(row.get("Lower Priority", "")).strip()
        if not (a in comp and b in comp):
            keep_rows.append(row)
    return pd.DataFrame(keep_rows, columns=prec_df.columns)


def collapse_cycle_to_equivalence_class(prec_df, comp):
    """
    UI-side approximation:
    remove all priority edges inside the cycle.
    The rules remain separate columns, but no longer claim priority over each other.
    This represents 'same priority' at the UI level.
    """
    return remove_internal_cycle_edges(prec_df, comp)
# -----------------------------------------------
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

# ---------------- Tabs ------------------
st.title("Multi Objective Search Visualizer")

tab_rapex, tab_tool = st.tabs(["RA*pex", "Tool"])

with tab_rapex:
    st.header("What is RA*pex?")

    st.markdown("""
                RA*pex is a rulebook-based multi-objective search algorithm.

                In a normal shortest-path problem, each edge has one cost, like distance.  
                Here, each edge has a **cost vector**, such as:

                `[distance, energy, time]`

                The goal is to find paths that are good according to a **rulebook**, not just one number.
                """)

    st.subheader("Rulebook")
    st.markdown("""
                A rulebook defines which objectives have priority.

                For example:

                `distance > energy`

                means distance is considered before energy when comparing paths.

                The rulebook can also be a partial order, meaning some objectives may be incomparable.
                """)

    st.subheader("Rule-dominance")
    st.markdown("""
    Rulebooks change how paths are compared.

    A path can be worse in a lower-priority objective and still be preferred if it is better in a higher-priority objective.

    For example, if:

    `safety > distance`

    then a path with better safety may dominate another path even though it has worse distance.
    """)

    st.subheader("OPEN queue")
    st.markdown("""
                RA*pex uses a priority queue called **OPEN** to manage the search frontier.

                Each node has:

                - `g`: cost accumulated so far
                - `h`: heuristic estimate to the goal
                - `f = g + h`: estimated total cost

                Nodes in OPEN are ordered lexicographically using some topological ordering of the rulebook graph.
                """)


    st.subheader("Pruning Nodes")
    st.markdown("""
                RA*pex does not expand every possible path.

                When a candidate is popped from OPEN, the algorithm checks whether it is already covered by:
                - a previously expanded pair at the same state, or
                - an existing representative solution.

                If so, the candidate is pruned because continuing from it cannot produce a meaningfully better solution.
                """)

    st.subheader("Apex vs realization")
    st.markdown("""
                A **realization** is an actual path in the graph.

                An **apex** is an idealized summary vector. It may combine the best compatible cost components from multiple paths.

                So the visualization shows a representative realization, while the apex summarizes what is achievable under the rulebook.
                """)

    st.subheader("Epsilon approximation")
    st.markdown("""
                `ε` controls approximation.

                With larger epsilon, near-optimal paths may be treated as acceptable. This can reduce the number of nodes expanded and focus the search on more relevant solutions.
                """)
    
    st.subheader("Path merging")
    st.markdown("""
                RA*pex can merge compatible search pairs.

                When two pairs represent similar sets of paths, the algorithm keeps one representative realization and updates the apex using the component-wise minimum of their apex vectors.

                As a result, the apex does not correspond to one single path on the graph, but instead acts as a summary of the best components from multiple paths. 
                """)


with tab_tool: 
    mode = st.radio("Mode", ["Single Run", "Compare Algorithms"], horizontal=True)

    # ------------ JSON input ----------
    st.header("Import / Export JSON")

    with st.expander("Upload or paste JSON problem"):

        uploaded_json = st.file_uploader("Upload JSON", type=["json"],key="problem_json")

        example_name = st.selectbox("Use example", [""] + list(EXAMPLES.keys()))

        if st.button("Load selected example"):
            if example_name:
                st.session_state.sample_json_text = EXAMPLES[example_name]
                st.rerun()

        pasted_json = st.text_area("Or paste JSON here", value=st.session_state.get("sample_json_text", ""),height=220)

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
    # --------------------------
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
            f"with estimated total cost **f = {pretty_vec(stp.last_pop['f'])}** "
            f"and lexicographic queue key **{pretty_vec(stp.last_pop['key'])}**."
        )
    else:
        st.caption("No pop yet.")

    st.subheader("OPEN (Priority Queue)")
    # show key used in pq 
    ordered_rules = getattr(stp, "ordered_rules", None)

    if not ordered_rules:
        for evt in st.session_state.get("trace", []):
            if evt.get("type") == "meta" and evt.get("ordered_rules") is not None:
                ordered_rules = evt.get("ordered_rules")
                break


    if ordered_rules:
        ordered_rule_names = [
            rule_names[i] if 0 <= int(i) < len(rule_names) else f"r{i}"
            for i in ordered_rules
        ]

        st.caption(
            "Nodes in OPEN are ordered lexicographically by the rulebook topological order: "
            + " → ".join(ordered_rule_names)
        )
    else:
        st.caption(
            "Nodes in OPEN are ordered using the rulebook comparison key. "
            "The exact topological order will appear after the trace metadata is loaded."
        )

    open_rows = []
    for key, tb, it in stp.OPEN[:200]:
        f_unscaled = unscale_vec(it["f"])
        key_unscaled = unscale_vec(list(key))

        row = {
            "state": id_to_label(it["state"]),
            "lex key f": pretty_vec(key_unscaled),
        }

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
        st.write("Trace meta:", [e for e in st.session_state.get("trace", []) if e.get("type") == "meta"])

        