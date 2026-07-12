// RulebookEditor.jsx
//
// Interaction model (mirrors ProblemGraphEditor.jsx):
//   - tap a class once            -> mark it as the pending edge source (highlighted)
//   - tap a second, different class -> completes a priority edge, emits add_class_edge
//   - tap the same class again     -> cancels the pending edge
//   - tap empty canvas while pending -> cancels the pending edge
//   - shift-click two classes      -> merge them (unrelated to the pending-edge state)
//   - double-click a class         -> rename its representative rule
//   - right-click a class          -> split into singletons
//   - right-click a priority edge  -> delete it
//
// Class node ids are "class_<i>" and already carry a clean "classIndex"
// field (added in render/cytoscape_render.py) -- no id-prefix bug here
// the way the problem graph had.

import React, { useCallback, useRef } from "react";
import GraphCanvas from "./GraphCanvas";

const PENDING_SOURCE_STYLE = {
  "border-color": "#f9a825",
  "border-width": 4,
};

export default function RulebookEditor({ elements, stylesheet, onEvent }) {
  const pendingSourceRef = useRef(null); // holds a cytoscape node, or null
  const shiftSelectedRef = useRef([]); // class indices picked for a merge

  const clearPendingSource = () => {
    if (pendingSourceRef.current) {
      pendingSourceRef.current.removeStyle("border-color border-width");
    }
    pendingSourceRef.current = null;
  };

  const handleReady = useCallback(
    (cy) => {
      cy.on("tap", "node", (event) => {
        const node = event.target;

        // Shift-click two classes -> merge them. Independent of the
        // pending-edge-source state below.
        if (event.originalEvent.shiftKey) {
          shiftSelectedRef.current.push(node.data("classIndex"));

          if (shiftSelectedRef.current.length === 2) {
            onEvent({ action: "merge_classes", class_indices: [...shiftSelectedRef.current] });
            shiftSelectedRef.current = [];
          }
          return;
        }

        if (!pendingSourceRef.current) {
          pendingSourceRef.current = node;
          node.style(PENDING_SOURCE_STYLE);
          return;
        }

        if (pendingSourceRef.current.same(node)) {
          clearPendingSource();
          return;
        }

        const fromClass = pendingSourceRef.current.data("classIndex");
        const toClass = node.data("classIndex");
        clearPendingSource();

        onEvent({ action: "add_class_edge", from_class: fromClass, to_class: toClass });
      });

      // Double-click a class -> rename its representative rule.
      // TODO: for multi-rule classes, show a small picker instead of
      // renaming the first rule in the class.
      cy.on("dbltap", "node", (event) => {
        const node = event.target;
        const oldName = node.data("rules")[0];
        const newName = window.prompt("Rename rule:", oldName);
        if (newName && newName !== oldName) {
          onEvent({ action: "rename_rule", old: oldName, new: newName });
        }
      });

      // Tap empty canvas: cancel a pending edge if one's in progress.
      cy.on("tap", (event) => {
        if (event.target === cy && pendingSourceRef.current) {
          clearPendingSource();
        }
      });

      // Right-click a class -> split into singletons.
      cy.cxtmenu({
        selector: "node",
        commands: [
          {
            content: "Split into singletons",
            select: (node) => {
              if (pendingSourceRef.current && pendingSourceRef.current.same(node)) {
                clearPendingSource();
              }
              onEvent({ action: "split_class", class_idx: node.data("classIndex") });
            },
          },
        ],
      });

      // Right-click a priority edge -> delete it.
      cy.cxtmenu({
        selector: "edge",
        commands: [
          {
            content: "Delete priority edge",
            select: (edge) =>
              onEvent({
                action: "delete_class_edge",
                from_class: edge.source().data("classIndex"),
                to_class: edge.target().data("classIndex"),
              }),
          },
        ],
      });
    },
    [onEvent],
  );

  return (
    <GraphCanvas
      elements={elements}
      stylesheet={stylesheet}
      layout={{ name: "dagre", animate: false }}
      onReady={handleReady}
    />
  );
}
