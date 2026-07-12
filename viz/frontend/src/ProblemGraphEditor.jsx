// ProblemGraphEditor.jsx
//
// Interaction model:
//   - tap an empty spot on the canvas       -> add a new node
//   - tap a node once                        -> mark it as the pending edge source (highlighted)
//   - tap a second, different node            -> completes the edge: prompts for costs, emits add_edge
//   - tap the same node again                 -> cancels the pending edge
//   - tap empty canvas while a source pending -> cancels the pending edge (does NOT add a node)
//   - double-click a node                     -> rename
//   - tap an edge                             -> edit its costs
//   - right-click a node                      -> set start / set goal / delete
//   - right-click an edge                     -> reverse / delete
//
// IMPORTANT: cytoscape node ids are "node::<name>" (see
// render/cytoscape_problem_graph.py), the real name lives in
// data("node_name"). Edge ids are "edge::<edge_index>", the real row
// index lives in data("edge_index"). Always read the *_name / edge_index
// fields, never .id(), when building an event -- using .id() directly
// was the earlier bug that made delete/rename/reverse silently fail.

import React, { useCallback, useRef } from "react";
import GraphCanvas from "./GraphCanvas";

const PENDING_SOURCE_STYLE = {
  "border-color": "#f9a825",
  "border-width": 4,
};

function parseCosts(raw, ruleNames) {
  if (raw === null) return null; // user hit Cancel

  const costs = raw.split(",").map((s) => parseFloat(s.trim()));

  if (costs.length !== ruleNames.length || costs.some(Number.isNaN)) {
    window.alert(
      `Expected ${ruleNames.length} comma-separated numbers (${ruleNames.join(", ")}), got: "${raw}"`,
    );
    return null;
  }

  return costs;
}

export default function ProblemGraphEditor({ elements, stylesheet, ruleNames, onEvent }) {
  const pendingSourceRef = useRef(null); // holds a cytoscape node, or null

  const clearPendingSource = () => {
    if (pendingSourceRef.current) {
      pendingSourceRef.current.removeStyle("border-color border-width");
    }
    pendingSourceRef.current = null;
  };

  const handleReady = useCallback(
    (cy) => {
      // Tap a node: first tap marks the pending source, second tap
      // (on a different node) completes the edge.
      cy.on("tap", "node", (event) => {
        const node = event.target;

        if (!pendingSourceRef.current) {
          pendingSourceRef.current = node;
          node.style(PENDING_SOURCE_STYLE);
          return;
        }

        if (pendingSourceRef.current.same(node)) {
          clearPendingSource();
          return;
        }

        const sourceName = pendingSourceRef.current.data("node_name");
        const targetName = node.data("node_name");
        clearPendingSource();

        const raw = window.prompt(
          `Edge costs, ${ruleNames.join(", ")} in that order (comma-separated):`,
        );
        const costs = parseCosts(raw, ruleNames);
        if (costs === null) return;

        onEvent({ action: "add_edge", source: sourceName, target: targetName, costs });
      });

      // Tap an edge: edit its costs directly.
      cy.on("tap", "edge", (event) => {
        const edge = event.target;

        const raw = window.prompt(
          `Edit costs, ${ruleNames.join(", ")} in that order (comma-separated):`,
          (edge.data("costs") || []).join(", "),
        );
        const costs = parseCosts(raw, ruleNames);
        if (costs === null) return;

        onEvent({ action: "update_edge", edge_index: edge.data("edge_index"), costs });
      });

      // Double-click a node -> rename.
      cy.on("dbltap", "node", (event) => {
        const node = event.target;
        const oldName = node.data("node_name");
        // TODO: replace with an absolutely-positioned <input> overlay
        // at node.renderedPosition() instead of window.prompt.
        const newName = window.prompt("Rename node:", oldName);
        if (newName && newName !== oldName) {
          onEvent({ action: "rename_node", old: oldName, new: newName });
        }
      });

      // Tap empty canvas: cancel a pending edge if one's in progress,
      // otherwise add a new node.
      cy.on("tap", (event) => {
        if (event.target !== cy) return;

        if (pendingSourceRef.current) {
          clearPendingSource();
          return;
        }

        const name = window.prompt("New node name:");
        if (name) {
          onEvent({ action: "add_node", name });
        }
      });

      // Right-click a node -> set start / set goal / delete.
      cy.cxtmenu({
        selector: "node",
        commands: [
          {
            content: "Set start",
            select: (node) => onEvent({ action: "set_start", name: node.data("node_name") }),
          },
          {
            content: "Set goal",
            select: (node) => onEvent({ action: "set_goal", name: node.data("node_name") }),
          },
          {
            content: "Delete",
            select: (node) => {
              if (pendingSourceRef.current && pendingSourceRef.current.same(node)) {
                clearPendingSource();
              }
              onEvent({ action: "delete_node", name: node.data("node_name") });
            },
          },
        ],
      });

      // Right-click an edge -> reverse / delete.
      cy.cxtmenu({
        selector: "edge",
        commands: [
          {
            content: "Reverse",
            select: (edge) => onEvent({ action: "reverse_edge", edge_index: edge.data("edge_index") }),
          },
          {
            content: "Delete",
            select: (edge) => onEvent({ action: "delete_edge", edge_index: edge.data("edge_index") }),
          },
        ],
      });
    },
    [onEvent, ruleNames],
  );

  return (
    <GraphCanvas
      elements={elements}
      stylesheet={stylesheet}
      layout={{ name: "cose", animate: false }}
      onReady={handleReady}
    />
  );
}
