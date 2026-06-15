import streamlit as st

# ---------- info tab for RA*pex ------------
def render_RAstarpex_info_tab():
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