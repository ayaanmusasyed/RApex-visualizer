import streamlit as st
import pandas as pd

from core.trace_utils import apply_trace_step, init_from_trace, extract_realization
from core.formatting import unscale_vec, pretty_vec
from render.graphviz_render import dot_for_graph
from core.solution_utils import collect_goal_vectors, collect_final_solution_pairs
from core.labels import id_to_label

def render_single_run_view(edges_df, rule_names):
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
    st.caption("Nodes in the priority queue have a key f, where f = g + h. g is the cost to reach node thus far and h is a heuristic to represent the estimated cost to go.")
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
            "f + g + h": pretty_vec(key_unscaled),
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

    