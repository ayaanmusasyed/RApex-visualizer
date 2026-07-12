# ui/graph_component.py
#
# Declares the custom React + Cytoscape.js component that replaces
# streamlit_cytoscapejs. Both editors (problem graph, rulebook) reuse the
# same compiled frontend bundle and are told apart by the "mode" prop.
#
# NOTE: Streamlit custom components keep returning the *last* value the
# frontend sent on every rerun -- they don't reset to None on their own.
# Without _dedupe below, a single click would get dispatched over and
# over on every later rerun (including ones triggered by unrelated
# sidebar edits), against state that's already changed -- that's what
# caused the "Unknown rule 'r1'" / "Invalid equivalence class selection"
# crashes. index.jsx stamps a unique _seq onto every event; we just
# remember the last _seq we've already handled per component key.

from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

# Flip to False while running `npm run dev` in viz/frontend, flip back to
# True once `npm run build` has been run for a release.
_RELEASE = False

_FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"

if _RELEASE:
    _component = components.declare_component(
        "graph_editor",
        path=str(_FRONTEND_DIR / "build"),
    )
else:
    _component = components.declare_component(
        "graph_editor",
        url="http://localhost:5173",
    )


# Ignore an event we've already dispatched once.
def _dedupe(raw_event, dedupe_key):
    if raw_event is None:
        return None

    seen_key = f"_graph_component_last_seq::{dedupe_key}"
    seq = raw_event.get("_seq")

    if seq is not None and seq == st.session_state.get(seen_key):
        return None

    st.session_state[seen_key] = seq
    return raw_event


# Render the interactive problem graph editor.
# Returns one event dict (see viz/ui/problem_graph_dispatch.py) or None
# if nothing happened since the last rerun.
def problem_graph_editor(elements, stylesheet, rule_names, key=None):
    raw_event = _component(
        mode="problem_graph",
        elements=elements,
        stylesheet=stylesheet,
        rule_names=rule_names,
        key=key,
        default=None,
    )
    return _dedupe(raw_event, key or "problem_graph")


# Render the interactive rulebook editor.
# Returns one event dict (see viz/ui/rulebook_dispatch.py) or None
# if nothing happened since the last rerun.
def rulebook_editor(elements, stylesheet, key=None):
    raw_event = _component(
        mode="rulebook",
        elements=elements,
        stylesheet=stylesheet,
        key=key,
        default=None,
    )
    return _dedupe(raw_event, key or "rulebook")
