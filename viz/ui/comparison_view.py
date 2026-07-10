import pandas as pd
import streamlit as st

from viz.render.graphviz_render import dot_for_graph


def parse_stats_text(stats_text):
    if not stats_text or not stats_text.strip():
        return None

    lines = [
        line.strip()
        for line in stats_text.splitlines()
        if line.strip()
    ]

    if not lines:
        return None

    # Use the final non-empty line.
    parts = lines[-1].split()

    if len(parts) < 7:
        return None

    try:
        return {
            "Node expansions": int(parts[-3]),
            "No. of Solutions": int(parts[-2]),
            "Runtime (seconds)": float(parts[-1]),
        }
    except (TypeError, ValueError):
        return None


def build_transposed_stats_table(
    left_name,
    left_stats_text,
    right_name,
    right_stats_text,
):
    left_stats = parse_stats_text(left_stats_text)
    right_stats = parse_stats_text(right_stats_text)

    columns = [
        "Algorithm",
        "Node expansions",
        "No. of Solutions",
        "Runtime (seconds)",
    ]

    def algorithm_row(name, stats):
        if stats is None:
            return {
                "Algorithm": name,
                "Node expansions": "—",
                "No. of Solutions": "—",
                "Runtime (seconds)": "—",
            }

        return {
            "Algorithm": name,
            "Node expansions": stats["Node expansions"],
            "No. of Solutions": stats["No. of Solutions"],
            "Runtime (seconds)": f"{stats['Runtime (seconds)']:.6f}",
        }

    return pd.DataFrame(
        [
            algorithm_row(left_name, left_stats),
            algorithm_row(right_name, right_stats),
        ],
        columns=columns,
    )


def render_algorithm_result(edges_df, result):
    if result["has_trace"]:
        dot = dot_for_graph(
            edges_df,
            solution_edges=result["solution_edges"],
        )

        st.graphviz_chart(dot)

        if result["solution_paths"]:
            st.markdown("**Representative realization(s)**")

            for path in result["solution_paths"]:
                st.write(" → ".join(path))
    else:
        st.info("No trace available for this algorithm yet.")
        st.code(result["stdout"] or "(no stdout)")


def render_comparison_view(edges_df, algo_right):
    if (
        "compare_left" not in st.session_state
        or "compare_right" not in st.session_state
    ):
        st.info("Build a graph and click **Run Comparison**.")
        st.stop()

    left = st.session_state.compare_left
    right = st.session_state.compare_right

    left_name = left.get("algorithm", "RApex")
    right_name = right.get("algorithm", algo_right)

    st.subheader("Comparison summary")

    comparison_df = build_transposed_stats_table(
        left_name=left_name,
        left_stats_text=left.get("stats_text", ""),
        right_name=right_name,
        right_stats_text=right.get("stats_text", ""),
    )

    st.dataframe(
        comparison_df,
        use_container_width=True,
        hide_index=True,
    )

    c1, c2 = st.columns(2)

    with c1:
        st.markdown(f"### {left_name}")
        render_algorithm_result(edges_df, left)

    with c2:
        st.markdown(f"### {right_name}")
        render_algorithm_result(edges_df, right)