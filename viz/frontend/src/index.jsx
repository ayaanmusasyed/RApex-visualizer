// index.jsx
//
// Streamlit component entry point. Listens for Streamlit's RENDER_EVENT,
// pulls args.mode / args.elements / args.stylesheet / args.rule_names
// out of the payload Python sent, and mounts the right editor. Any user
// interaction calls emit(eventDict), which stamps a unique _seq onto the
// event and forwards it to Streamlit.setComponentValue -- graph_component.py
// uses that _seq to ignore replays of the same value on later reruns
// (Streamlit keeps returning the last component value until a new one
// is sent, it does not reset to None on its own).

import React from "react";
import ReactDOM from "react-dom/client";
import { Streamlit } from "streamlit-component-lib";

import "./cytoscapeSetup";
import "./styles.css";
import ProblemGraphEditor from "./ProblemGraphEditor";
import RulebookEditor from "./RulebookEditor";

const root = ReactDOM.createRoot(document.getElementById("root"));

let _eventSeq = 0;

// Send one event dict back to Python. Mirrors the shapes documented in
// PLAN.md / consumed by problem_graph_dispatch.py and rulebook_dispatch.py.
function emit(eventDict) {
  _eventSeq += 1;
  Streamlit.setComponentValue({ ...eventDict, _seq: _eventSeq });
}

function render(event) {
  const { mode, elements, stylesheet, rule_names } = event.detail.args;

  const editor =
    mode === "rulebook" ? (
      <RulebookEditor elements={elements} stylesheet={stylesheet} onEvent={emit} />
    ) : (
      <ProblemGraphEditor
        elements={elements}
        stylesheet={stylesheet}
        ruleNames={rule_names || []}
        onEvent={emit}
      />
    );

  root.render(<React.StrictMode>{editor}</React.StrictMode>);

  // Cytoscape needs a real pixel height; keep it fixed for now, matching
  // the width=700, height=400 the old st_cytoscapejs calls used.
  Streamlit.setFrameHeight(mode === "rulebook" ? 350 : 400);
}

Streamlit.events.addEventListener(Streamlit.RENDER_EVENT, render);
Streamlit.setComponentReady();
