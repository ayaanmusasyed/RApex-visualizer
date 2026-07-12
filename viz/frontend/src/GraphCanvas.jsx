// GraphCanvas.jsx
//
// Owns the actual cytoscape() instance. Both ProblemGraphEditor and
// RulebookEditor render one of these and attach their own interaction
// handlers via onReady(cy) -- this file only handles mount/teardown and
// redrawing when Python sends new elements/stylesheet after a rerun.

import React, { useEffect, useRef } from "react";
import cytoscape from "./cytoscapeSetup";

export default function GraphCanvas({ elements, stylesheet, layout, onReady }) {
  const containerRef = useRef(null);
  const cyRef = useRef(null);

  // Mount once.
  useEffect(() => {
    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: stylesheet,
      layout: layout || { name: "cose", animate: false },
    });

    cyRef.current = cy;

    if (onReady) {
      onReady(cy);
    }

    return () => cy.destroy();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Redraw when Python sends fresh state (after dispatch + st.rerun()).
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    cy.batch(() => {
      cy.elements().remove();
      cy.add(elements);
    });

    cy.style(stylesheet).update();
    cy.layout(layout || { name: "cose", animate: false }).run();
  }, [elements, stylesheet, layout]);

  return <div ref={containerRef} className="graph-canvas" />;
}
