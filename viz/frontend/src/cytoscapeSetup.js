// cytoscapeSetup.js
//
// Registers the cytoscape.js extensions the editors need. Imported once
// from index.jsx before any GraphCanvas is mounted.

import cytoscape from "cytoscape";
import edgehandles from "cytoscape-edgehandles";
import cxtmenu from "cytoscape-cxtmenu";
import dagre from "cytoscape-dagre";

cytoscape.use(edgehandles);
cytoscape.use(cxtmenu);
cytoscape.use(dagre);

export default cytoscape;
