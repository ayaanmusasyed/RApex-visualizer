# import streamlit as st
# import pandas as pd
# import json, heapq, itertools
# from dataclasses import dataclass
# from typing import Any, List, Dict, Union
# import subprocess, tempfile
# from pathlib import Path

# Number = Union[int, float]

# SCALE = 1.0
# INF_THRESHOLD = 1e9

# @dataclass
# class TraceStepper:
#     trace: List[Dict]
#     i: int
#     OPEN: list           # heap of (key, tiebreak, item)
#     tiebreak: Any
#     last_pop: Dict | None
#     events: list

# def load_trace_jsonl(uploaded_file) -> list[dict]:
#     raw_lines = uploaded_file.read().decode("utf-8").splitlines()
#     fixed = []
#     for line in raw_lines:
#         if '"rp":{{' in line:
#             line = line.replace('"rp":{{', '"rp":[{')
#             if line.endswith("}}}"):
#                 line = line[:-3] + "}]}"

#         fixed.append(json.loads(line))
#     return fixed

# def _keyer(fvec: List[Number]):
#     # simple lex key; later you can implement rulebook-lex ordering if needed
#     return tuple(float(x) for x in fvec)

# def extract_realization(evt: Dict) -> Dict:
#     rp = evt.get("rp")
#     if isinstance(rp, list) and len(rp) >= 2:
#         rz = rp[1]
#     elif isinstance(rp, dict):
#         # fallback if emitter changes format
#         rz = rp
#     else:
#         rz = {}

#     return {
#         "state": int(rz.get("id", -1)),
#         "g": list(rz.get("cost_until_now", [])),
#         "h": list(rz.get("heuristic_cost", [])),
#         "f": list(rz.get("full_cost", [])),
#     }

# def apply_trace_step(stp: TraceStepper) -> None:
#     if stp.i >= len(stp.trace):
#         return

#     evt = stp.trace[stp.i]
#     stp.i += 1
#     t = evt.get("type")

#     if t == "meta":
#         stp.events.append({"kind":"meta", "solver": evt.get("solver","?")})
#         return

#     if t == "pop":
#         item = extract_realization(evt)
#         key = _keyer(item["f"])
#         stp.last_pop = {"state": item["state"], "f": item["f"], "key": key}
#         stp.events.append({"kind":"pop", "state": item["state"], "f": item["f"], "key": key})

#         # remove one matching (state,f) from OPEN if present
#         for j, (k, tb, it) in enumerate(stp.OPEN):
#             if it["state"] == item["state"] and it["f"] == item["f"]:
#                 stp.OPEN.pop(j)
#                 heapq.heapify(stp.OPEN)
#                 break
#         return

#     if t == "enqueue":
#         item = extract_realization(evt)
#         key = _keyer(item["f"])
#         heapq.heappush(stp.OPEN, (key, next(stp.tiebreak), item))
#         stp.events.append({"kind":"enqueue", "from": evt.get("from"), "to": evt.get("to"), "f": item["f"]})
#         return

#     stp.events.append({"kind":"other", "raw": evt})

# def init_from_trace(trace: List[Dict]) -> TraceStepper:
#     return TraceStepper(
#         trace=trace,
#         i=0,
#         OPEN=[],
#         tiebreak=itertools.count(0),
#         last_pop=None,
#         events=[]
#     )

# def _normalize_rule_name_or_index(x: str, rule_names: List[str]) -> int:
#     x = str(x).strip()
#     if x == "":
#         raise ValueError("Empty rule reference.")
#     if x.isdigit():
#         i = int(x)
#         if not (0 <= i < len(rule_names)):
#             raise ValueError(f"Rule index {i} out of range.")
#         return i
#     if x in rule_names:
#         return rule_names.index(x)
#     raise ValueError(f"Unknown rule '{x}'. Use indices 0..{len(rule_names)-1} or names {rule_names}.")

# def build_node_ids(edges_df: pd.DataFrame, start_label: str, goal_label: str):
#     # Collect all labels from the table + start/goal, map to 1..N for .gr
#     labels = set()
#     labels.add(str(start_label).strip())
#     labels.add(str(goal_label).strip())
#     for _, r in edges_df.iterrows():
#         u = str(r["u"]).strip()
#         v = str(r["v"]).strip()
#         if u: labels.add(u)
#         if v: labels.add(v)
#     labels = sorted(labels)
#     name_to_id = {name: i+1 for i, name in enumerate(labels)}  # 1-indexed
#     return name_to_id

# def write_queries_txt(path: Path, s_id: int, t_id: int):
#     path.write_text(f"{s_id},{t_id}\n", encoding="utf-8")

# def write_rules_txt(path: Path, rule_names: List[str], eps: List[float], precedence_edges_df: pd.DataFrame):
#     k = len(rule_names)
#     if len(eps) != k:
#         raise ValueError("eps length must match number of rules.")

#     # Equivalence classes: simplest = each rule alone
#     eq_classes = [[i] for i in range(k)]

#     # Priority relations: pairs (fromRule, toRule) by index
#     rels = []
#     if precedence_edges_df is not None and len(precedence_edges_df) > 0:
#         for _, r in precedence_edges_df.iterrows():
#             hi = str(r.get("Higher Priority", "")).strip()
#             lo = str(r.get("Lower Priority", "")).strip()
#             if not hi or not lo:
#                 continue
#             a = _normalize_rule_name_or_index(hi, rule_names)
#             b = _normalize_rule_name_or_index(lo, rule_names)
#             if a == b:
#                 raise ValueError("Self-edge in precedence graph.")
#             rels.append((a, b))

#     # Format matches your C++ load_rules()
#     lines = []
#     lines.append(str(k))
#     lines.append(" ".join(str(float(x)) for x in eps))

#     lines.append(str(len(eq_classes)))
#     for cls in eq_classes:
#         lines.append(str(len(cls)) + " " + " ".join(str(i) for i in cls))

#     lines.append(str(len(rels)))
#     for a, b in rels:
#         lines.append(f"{a} {b}")

#     path.write_text("\n".join(lines) + "\n", encoding="utf-8")

# def write_gr_files(out_dir: Path, edges_df: pd.DataFrame, name_to_id: Dict[str, int], k: int):
#     # Build arc list once
#     arcs = []
#     for _, r in edges_df.iterrows():
#         u = str(r["u"]).strip()
#         v = str(r["v"]).strip()
#         if not u or not v:
#             continue
#         cu = name_to_id[u]
#         cv = name_to_id[v]
#         cost = [float(r[f"c{i}"]) for i in range(k)]
#         arcs.append((cu, cv, cost))

#     n_nodes = max(name_to_id.values()) if name_to_id else 0
#     n_edges = len(arcs)

#     gr_paths = []
#     for i in range(k):
#         p = out_dir / f"w{i}.gr"
#         gr_paths.append(p)
#         lines = []
#         lines.append(f"c objective {i}")
#         lines.append(f"p sp {n_nodes} {n_edges}")
#         for (cu, cv, cost) in arcs:
#             w = cost[i]
#             # Scale by 1000 for decimals 
#             lines.append(f"a {cu} {cv} {int(round(w * SCALE))}")
#         p.write_text("\n".join(lines) + "\n", encoding="utf-8")
#     return gr_paths

# def unscale_vec(vec):
#     return [float(x) / SCALE for x in vec]

# def id_to_label(state_id: int) -> str:
#     name_to_id = st.session_state.get("name_to_id", {})
#     rev = {v: k for k, v in name_to_id.items()}
#     return rev.get(state_id, str(state_id))

# def pretty_num(x):
#     x = float(x)

#     if x >= INF_THRESHOLD:
#         return "∞"

#     return f"{x / SCALE:.4g}"

# def pretty_vec(vec):
#     vals = []
#     for x in vec:
#         vals.append(pretty_num(x))
#     return "[" + ", ".join(vals) + "]"

# # Function for drawing graph
# def dot_for_graph(
#     edges_df,
#     highlight_nodes=None,
#     highlight_edges=None,
#     open_nodes=None,
#     pruned_nodes=None,
#     solution_edges=None,
#     candidate_edges=None,
# ):
#     highlight_nodes = set(highlight_nodes or [])
#     highlight_edges = set(highlight_edges or [])
#     open_nodes = set(open_nodes or [])
#     pruned_nodes = set(pruned_nodes or [])
#     solution_edges = set(solution_edges or [])
#     candidate_edges = set(candidate_edges or [])

#     node_names = set()
#     for _, row in edges_df.iterrows():
#         u = str(row["u"]).strip()
#         v = str(row["v"]).strip()
#         if u:
#             node_names.add(u)
#         if v:
#             node_names.add(v)

#     node_lines, edge_lines = [], []

#     for name in sorted(node_names):
#         fill = 'fillcolor="white"'
#         style_bits = ["filled"]
#         extra = []

#         if name in open_nodes:
#             fill = 'fillcolor="lightyellow"'
#         if name in highlight_nodes:
#             fill = 'fillcolor="cyan"'
#         if name in pruned_nodes:
#             extra += ['color="red"', 'penwidth=2']
#             style_bits.append("dashed")

#         node_lines.append(
#             f'"{name}" [shape=circle, style="{",".join(style_bits)}", {fill}'
#             + (", " + ", ".join(extra) if extra else "")
#             + "];"
#         )

#     for _, row in edges_df.iterrows():
#         u = str(row["u"]).strip()
#         v = str(row["v"]).strip()
#         if not u or not v:
#             continue

#         label = "[" + ",".join(str(row[c]) for c in edges_df.columns if str(c).startswith("c")) + "]"

#         edge_color = "gray"
#         penwidth = "1"

#         if (u, v) in solution_edges:
#             edge_color = "green"
#             penwidth = "4"
#         elif (u, v) in candidate_edges:
#             edge_color = "orange"
#             penwidth = "3"
#         elif (u, v) in highlight_edges:
#             edge_color = "blue"
#             penwidth = "3"

#         edge_lines.append(
#             f'"{u}" -> "{v}" [label="{label}", color="{edge_color}", penwidth={penwidth}];'
#         )

#     lines = [
#         "digraph G {",
#         'rankdir="LR";',
#         "node [fontname=Helvetica];",
#         "edge [fontname=Helvetica];",
#         *node_lines,
#         *edge_lines,
#         "}",
#     ]
#     return "\n".join(lines)

# def approx_equal_vec(a, b, tol=1e-4):
#     return len(a) == len(b) and all(abs(float(a[i]) - float(b[i])) <= tol for i in range(len(a)))

# def collect_goal_vectors(trace):
#     sols = []
#     for evt in trace:
#         if evt.get("type") == "solution":
#             item = extract_realization(evt)
#             sols.append(unscale_vec(item["f"]))

#     uniq = []
#     for s in sols:
#         if not any(approx_equal_vec(s, t) for t in uniq):
#             uniq.append(s)
            
#     return uniq

# def enumerate_paths_from_edges_df(edges_df, start_name, goal_name, k):
#     G = {}
#     for _, row in edges_df.iterrows():
#         u = str(row["u"]).strip()
#         v = str(row["v"]).strip()
#         if not u or not v:
#             continue
#         cost = [float(row[f"c{i}"]) for i in range(k)]
#         G.setdefault(u, []).append((v, cost))
#         G.setdefault(v, [])

#     stack = [(start_name, [start_name], set([start_name]), [0.0] * k)]
#     out = []

#     while stack:
#         u, path, seen, cost = stack.pop()
#         if u == goal_name:
#             out.append((path, cost))
#             continue

#         for v, w in G.get(u, []):
#             if v in seen:
#                 continue
#             new_cost = [cost[i] + w[i] for i in range(k)]
#             stack.append((v, path + [v], seen | {v}, new_cost))

#     return out

# def compute_solution_edges(trace, edges_df, name_to_id, start_label, goal_label, k):
#     sol_vecs = collect_final_solution_vectors(trace)
#     if not sol_vecs:
#         return set()

#     all_paths = enumerate_paths_from_edges_df(edges_df, start_label, goal_label, k)

#     sol_edges = set()
#     for path, cost in all_paths:
#         if any(approx_equal_vec(cost, sv, tol=1e-5) for sv in sol_vecs):
#             for a, b in zip(path, path[1:]):
#                 sol_edges.add((a, b))
#     return sol_edges

# def compute_solution_paths(trace, edges_df, name_to_id, start_label, goal_label, k):
#     sol_vecs = collect_final_solution_vectors(trace)
#     all_paths = enumerate_paths_from_edges_df(edges_df, start_label, goal_label, k)

#     sol_paths = []
#     for path, cost in all_paths:
#         if any(approx_equal_vec(cost, sv, tol=1e-5) for sv in sol_vecs):
#             sol_paths.append(path)

#     uniq = []
#     seen = set()
#     for p in sol_paths:
#         tp = tuple(p)
#         if tp not in seen:
#             seen.add(tp)
#             uniq.append(p)
#     return uniq

# def collect_final_solution_vectors(trace):
#     for evt in trace:
#         if evt.get("type") == "final_solutions":
#             sols = []
#             for rp in evt.get("solutions", []):
#                 # rp is [rule_apex_node, realization_node]
#                 if isinstance(rp, list) and len(rp) >= 2:
#                     rz = rp[1]
#                 elif isinstance(rp, dict):
#                     rz = rp
#                 else:
#                     continue

#                 sols.append(unscale_vec(list(rz.get("full_cost", []))))
#             return sols
#     return []

# def approx_equal(cost, apex, eps):
#     for i in range(len(cost)):
#         if cost[i] > (1 + eps[i]) * apex[i]:
#             return False
#     return True

# def compute_candidate_paths(trace, edges_df, name_to_id, start_label, goal_label, k):
#     final_vecs = collect_final_solution_vectors(trace)
#     if not final_vecs:
#         return []

#     all_paths = enumerate_paths_from_edges_df(edges_df, start_label, goal_label, k)
#     sol_paths = compute_solution_paths(trace, edges_df, name_to_id, start_label, goal_label, k)
#     sol_path_tuples = {tuple(p) for p in sol_paths}

#     candidate_paths = []
#     eps_vals = st.session_state.get("eps_values", [0.0] * k)

#     for path, cost in all_paths:
#         if tuple(path) in sol_path_tuples:
#             continue

#         for fv in final_vecs:
#             ok = True
#             for i in range(len(cost)):
#                 if float(cost[i]) > (1 + float(eps_vals[i])) * float(fv[i]):
#                     ok = False
#                     break
#             if ok:
#                 candidate_paths.append(path)
#                 break

#     # dedupe
#     uniq = []
#     seen = set()
#     for p in candidate_paths:
#         tp = tuple(p)
#         if tp not in seen:
#             seen.add(tp)
#             uniq.append(p)
#     return uniq

# def paths_to_edges(paths):
#     edges = set()
#     for path in paths:
#         for a, b in zip(path, path[1:]):
#             edges.add((a, b))
#     return edges

# # ---------------- UI ----------------

# st.set_page_config(page_title="RApex Visualizer", layout="wide")
# st.title("RApex Visualizer")


# # ------------ JSON input (easier for me to test viz) ----------
# st.header("Import / Export JSON")

# with st.expander("Upload or paste JSON problem"):
#     uploaded_json = st.file_uploader("Upload JSON", type=["json"], key="problem_json")
#     pasted_json = st.text_area("Or paste JSON here", height=220)

#     def _rulebook_layers_to_edges(layers):
#         edges = []
#         for i in range(len(layers)):
#             for j in range(i + 1, len(layers)):
#                 for hi in layers[i]:
#                     for lo in layers[j]:
#                         edges.append((hi, lo))
#         return edges

#     if st.button("Load JSON problem"):
#         try:
#             raw = None
#             if uploaded_json is not None:
#                 raw = uploaded_json.read().decode("utf-8")
#             elif pasted_json.strip():
#                 raw = pasted_json

#             if not raw:
#                 st.warning("Provide a JSON file or paste JSON text.")
#             else:
#                 cfg = json.loads(raw)

#                 loaded_rule_names = cfg["rules"]
#                 loaded_rulebook = cfg.get("rulebook", {})
#                 loaded_edges = cfg["graph"]["edges"]
#                 loaded_start = cfg["start"]
#                 loaded_goal = cfg["goal"]
#                 loaded_eps = cfg.get("eps", 0.0)

#                 if isinstance(loaded_eps, (int, float)):
#                     loaded_eps = [float(loaded_eps)] * len(loaded_rule_names)
#                 else:
#                     loaded_eps = [float(x) for x in loaded_eps]

#                 if "layers" in loaded_rulebook:
#                     prec_edges = _rulebook_layers_to_edges(loaded_rulebook["layers"])
#                 elif "edges" in loaded_rulebook:
#                     prec_edges = [(a, b) for a, b in loaded_rulebook["edges"]]
#                 else:
#                     prec_edges = []

#                 rows = []
#                 for e in loaded_edges:
#                     row = {"u": e["u"], "v": e["v"]}
#                     c = e["c"]
#                     if len(c) != len(loaded_rule_names):
#                         raise ValueError(
#                             f"Edge {e['u']}->{e['v']} has {len(c)} costs, "
#                             f"but there are {len(loaded_rule_names)} rules."
#                         )
#                     for i, val in enumerate(c):
#                         row[f"c{i}"] = float(val)
#                     rows.append(row)

#                 # Update the table and sidebar values as well when I import JSON
#                 old_k = st.session_state.get("k", len(loaded_rule_names))

#                 st.session_state.k = len(loaded_rule_names)
#                 st.session_state.rule_names_csv = ",".join(loaded_rule_names)
#                 st.session_state.start_label = loaded_start
#                 st.session_state.goal_label = loaded_goal
#                 st.session_state.eps_values = loaded_eps

#                 for i, val in enumerate(loaded_eps):
#                     st.session_state[f"eps_{i}"] = float(val)

#                 for i in range(len(loaded_rule_names), old_k):
#                     st.session_state.pop(f"eps_{i}", None)
                
#                 st.session_state.prec_df = pd.DataFrame([{"Higher Priority": a, "Lower Priority": b} for a, b in prec_edges],columns=["Higher Priority", "Lower Priority"])
#                 st.session_state.edges_df = pd.DataFrame(rows)

#                 st.success("Loaded problem from JSON.")
#                 st.rerun()
#         except Exception as e:
#             st.exception(e)
            
# # ---------------- Inputs ----------------
# if "k" not in st.session_state:
#     st.session_state.k = 2
# if "rule_names_csv" not in st.session_state:
#     st.session_state.rule_names_csv = "r0,r1"
# if "start_label" not in st.session_state:
#     st.session_state.start_label = "S"
# if "goal_label" not in st.session_state:
#     st.session_state.goal_label = "T"
# if "eps_values" not in st.session_state:
#     st.session_state.eps_values = [0.0, 0.0]

# with st.sidebar:
#     st.header("1) Rules")

#     k = st.number_input(
#         "Number of rules (dimensions)",
#         min_value=1,
#         max_value=12,
#         step=1,
#         key="k"
#     )

#     # keep epsilon vector length synced to k
#     if len(st.session_state.eps_values) != k:
#         old = st.session_state.eps_values
#         if len(old) < k:
#             st.session_state.eps_values = old + [0.0] * (k - len(old))
#         else:
#             st.session_state.eps_values = old[:k]

#     # keep rule names count synced to k
#     current_names = [x.strip() for x in st.session_state.rule_names_csv.split(",") if x.strip()]
#     if len(current_names) != k:
#         st.session_state.rule_names_csv = ",".join(f"r{i}" for i in range(k))

#     rule_names_csv = st.text_input(
#         "Rule names (comma-separated)",
#         key="rule_names_csv"
#     )
#     rule_names = [x.strip() for x in rule_names_csv.split(",") if x.strip()]

#     st.header("2) Start / Goal")
#     start_label = st.text_input("Start node label", key="start_label")
#     goal_label  = st.text_input("Goal node label", key="goal_label")

#     st.header("3) epsilon")
#     eps = []
#     for i in range(k):
#         eps_i = st.number_input(
#             f"eps[{i}]",
#             min_value=0.0,
#             step=0.1,
#             value=float(st.session_state.eps_values[i]),
#             key=f"eps_{i}"
#         )
#         eps.append(float(eps_i))

#     st.session_state.eps_values = eps

#     st.header("4) Run options")
#     cutoff = int(st.number_input("cutoffTime (sec)", min_value=1, value=10, step=1))
#     merge = st.selectbox("merge strategy", ["RANDOM", "SMALLER_G2", "MORE_SLACK"], index=0)

# st.header("Rule precedence graph (optional)")
# if "prec_df" not in st.session_state:
#     st.session_state.prec_df = pd.DataFrame(columns=["Higher Priority", "Lower Priority"])

# prec_df = st.data_editor(
#     st.session_state.prec_df,
#     key="prec_editor",
#     use_container_width=True,
#     num_rows="dynamic"
# )
# st.session_state.prec_df = prec_df

# st.header("Problem graph edges")

# need_cols = ["u", "v"] + [f"c{i}" for i in range(k)]

# if "edges_df" not in st.session_state:
#     seed = pd.DataFrame([
#         {"u": "S", "v": "A", **{f"c{i}": 0.0 for i in range(k)}},
#         {"u": "A", "v": "T", **{f"c{i}": 0.0 for i in range(k)}},
#     ])
#     st.session_state.edges_df = seed[need_cols]
# else:
#     df_old = st.session_state.edges_df.copy()
#     for c in need_cols:
#         if c not in df_old.columns:
#             df_old[c] = 0.0 if c.startswith("c") else ""
#     st.session_state.edges_df = df_old[need_cols]

# edges_df = st.data_editor(
#     st.session_state.edges_df,
#     key="edges_editor",
#     use_container_width=True,
#     num_rows="dynamic"
# )
# st.session_state.edges_df = edges_df

# # ---------------- Run C++ and auto-load trace ----------------
# run_btn = st.button("Run RApex")

# if run_btn:
#     try:
#         if len(rule_names) != k:
#             st.error("Rule names count must match number of dimensions.")
#             st.stop()

#         name_to_id = build_node_ids(edges_df, start_label, goal_label)
#         s_id = name_to_id[str(start_label).strip()]
#         t_id = name_to_id[str(goal_label).strip()]

#         repo_root = Path(__file__).resolve().parents[1]
#         bin_path = repo_root / "build" / "multiobj"
#         if not bin_path.exists():
#             st.error("Could not find build/multiobj. Build the C++ project first.")
#             st.stop()

#         with tempfile.TemporaryDirectory() as td:
#             td = Path(td)

#             trace_path = td / "trace.jsonl"
#             stats_path = td / "stats.txt"
#             rules_path = td / "rules.txt"
#             queries_path = td / "queries.txt"

#             write_queries_txt(queries_path, s_id, t_id)
#             write_rules_txt(rules_path, rule_names, eps, prec_df)
#             gr_paths = write_gr_files(td, edges_df, name_to_id, k)

#             cmd = [
#                 str(bin_path),
#                 "--algorithm", "RApex",
#                 "--merge", merge,
#                 "--cutoffTime", str(cutoff),
#                 "--trace", str(trace_path),
#                 "--output", str(stats_path),
#                 "--query", str(queries_path),
#                 "--rules", str(rules_path),
#                 "--map",
#                 *[str(p) for p in gr_paths],
#             ]

#             res = subprocess.run(cmd, capture_output=True, text=True, cwd=td)

#             if res.returncode != 0:
#                 st.error("multiobj failed.")
#                 st.code(res.stdout or "(no stdout)")
#                 st.code(res.stderr or "(no stderr)")
#                 st.stop()

#             if not trace_path.exists():
#                 st.error("Run succeeded but trace.jsonl was not created.")
#                 st.code(res.stdout or "(no stdout)")
#                 st.code(res.stderr or "(no stderr)")
#                 st.stop()

#             # keep your fixer for now because current C++ trace format is slightly malformed
#             raw_lines = trace_path.read_text(encoding="utf-8").splitlines()
#             fixed = []

#             for line in raw_lines:
#                 # Fix malformed "rp":{{...},{...}}  ->  "rp":[{...},{...}]
#                 if '"rp":{{' in line:
#                     line = line.replace('"rp":{{', '"rp":[{')
#                     if line.endswith("}}}"):
#                         line = line[:-3] + "}]}"

#                 # Fix malformed "solutions":[{{...},{...}},{{...},{...}}]
#                 if '"solutions":[{{' in line:
#                     line = line.replace('"solutions":[{{', '"solutions":[[{')
#                     line = line.replace('}},{{', '}],[{')
#                     if line.endswith('}}]}'):
#                         line = line[:-4] + '}]]}'

#                 fixed.append(json.loads(line))

#             st.session_state.trace = fixed
#             st.session_state.trace_stepper = init_from_trace(fixed)
#             st.session_state.last_run_stdout = res.stdout
#             st.session_state.last_run_stderr = res.stderr
#             st.session_state.last_run_stats = stats_path.read_text(encoding="utf-8") if stats_path.exists() else ""
#             st.session_state.name_to_id = name_to_id

#             st.session_state.solution_edges = compute_solution_edges(fixed, edges_df, name_to_id, start_label, goal_label, k)
#             st.session_state.solution_paths = compute_solution_paths(fixed, edges_df, name_to_id, start_label, goal_label, k)

#             st.session_state.candidate_paths = compute_candidate_paths(fixed, edges_df, name_to_id, start_label, goal_label, k)
#             st.session_state.candidate_edges = paths_to_edges(st.session_state.candidate_paths)

#             st.success(f"Loaded {len(fixed)} trace events.")
#     except Exception as e:
#         st.exception(e)

# if "trace_stepper" not in st.session_state:
#     st.info("Build a graph and click **Run RApex**.")
#     st.stop()

# stp = st.session_state.trace_stepper

# with st.expander("Last run output"):
#     st.code(st.session_state.get("last_run_stdout", ""))
#     st.code(st.session_state.get("last_run_stderr", ""))
#     st.code(st.session_state.get("last_run_stats", ""))

# c1, c2, c3, c4= st.columns(4)
# if c1.button("Reset"):
#     st.session_state.trace_stepper = init_from_trace(st.session_state.trace)
#     st.rerun()

# if c2.button("Next Iteration"):
#     apply_trace_step(stp)

# if c3.button("Run 10 iterations"):
#     for _ in range(10):
#         apply_trace_step(stp)

# if c4.button("Instant solve"):
#     while stp.i < len(stp.trace):
#         apply_trace_step(stp)

# st.divider()

# name_to_id = st.session_state.get("name_to_id", {})
# id_to_name = {v: k for k, v in name_to_id.items()}

# cur_node = set()
# if stp.last_pop:
#     cur_node = {id_to_name.get(stp.last_pop["state"], str(stp.last_pop["state"]))}

# open_nodes = {
#     id_to_name.get(it["state"], str(it["state"]))
#     for (_, _, it) in stp.OPEN
# }

# highlight_edges = set()
# pruned_nodes = set()

# for e in reversed(stp.events):
#     if e["kind"] == "pop" and e is not stp.events[-1]:
#         break
#     if e["kind"] == "enqueue":
#         frm = id_to_name.get(e["from"], str(e["from"])) if e.get("from") is not None else None
#         to  = id_to_name.get(e["to"], str(e["to"])) if e.get("to") is not None else None
#         if frm and to:
#             highlight_edges.add((frm, to))
#     if e["kind"] == "prune":
#         s = e.get("state")
#         if s is not None:
#             pruned_nodes.add(id_to_name.get(s, str(s)))

# # Store frontier nodes 
# frontier_nodes = set()
# for key, tb, it in stp.OPEN:
#     frontier_nodes.add(it["state"])
    
# shown_solution_edges = set()
# shown_candidate_edges = set()

# if stp.i >= len(stp.trace):
#     shown_solution_edges = st.session_state.get("solution_edges", set())
#     shown_candidate_edges = st.session_state.get("candidate_edges", set())

# st.write("trace position:", stp.i, "/", len(stp.trace))
# st.write("stored solution_edges:", st.session_state.get("solution_edges", set()))
# st.write("stored candidate_edges:", st.session_state.get("candidate_edges", set()))
# st.write("shown solution_edges:", shown_solution_edges)
# st.write("shown candidate_edges:", shown_candidate_edges)

# dot = dot_for_graph(
#     edges_df,
#     highlight_nodes=cur_node,
#     highlight_edges=highlight_edges,
#     open_nodes=open_nodes,
#     pruned_nodes=pruned_nodes,
#     solution_edges=shown_solution_edges,
#     candidate_edges=shown_candidate_edges,
# )
# st.graphviz_chart(dot)

# st.subheader("Current pop")
# if stp.last_pop:
#     node_name = id_to_label(stp.last_pop["state"])
#     st.markdown(
#         f"Currently expanding **{node_name}** "
#         f"with cost vector **{pretty_vec(stp.last_pop['f'])}** "
#         f"and lex-key **{pretty_vec(stp.last_pop['key'])}**."
#     )
# else:
#     st.caption("No pop yet.")

# st.subheader("OPEN (heap preview)")
# open_rows = []
# for key, tb, it in stp.OPEN[:200]:

#     f_unscaled = unscale_vec(it["f"])
#     key_unscaled = unscale_vec(list(key))

#     row = {"state": id_to_label(it["state"]), "key": pretty_vec(key_unscaled)}

#     for i, x in enumerate(f_unscaled):
#         row[f"f{i}"] = x
#     open_rows.append(row)
# if open_rows:
#     st.dataframe(pd.DataFrame(open_rows), use_container_width=True, hide_index=True)
# else:
#     st.caption("OPEN is empty.")

# st.subheader("Event log")

# def pretty_event(e):
#     if e["kind"] == "meta":
#         return f"Using solver **{e['solver']}**."
#     if e["kind"] == "pop":
#         return (
#             f"Popped **{id_to_label(e['state'])}** "
#             f"with cost {pretty_vec(e['f'])}."
#         )
#     if e["kind"] == "enqueue":
#         frm = id_to_label(e["from"]) if e.get("from") is not None else "?"
#         to = id_to_label(e["to"]) if e.get("to") is not None else "?"
#         return (
#             f"From **{frm}**, added **{to}** to OPEN "
#             f"with cost {pretty_vec(e['f'])}."
#         )
#     if e["kind"] == "prune":
#         return f"Pruned **{id_to_label(e['state'])}**."
#     return str(e)

# for e in stp.events[-50:]:
#     st.markdown(f"- {pretty_event(e)}")

# if st.session_state.get("solution_paths"):
#     st.subheader("Solution path(s)")
#     for p in st.session_state["solution_paths"]:
#         st.write(" -> ".join(p))

# if st.session_state.get("candidate_paths"):
#     st.subheader("Also considered under epsilon")
#     for p in st.session_state["candidate_paths"]:
#         st.write(" -> ".join(p))

# st.write("Collected solution vectors:", collect_goal_vectors(st.session_state.trace))
# st.write("Computed solution edges:", st.session_state.get("solution_edges", set()))
# st.write("Computed solution paths:", st.session_state.get("solution_paths", []))