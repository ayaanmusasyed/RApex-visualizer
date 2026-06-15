from core.trace_utils import extract_realization
from core.formatting import unscale_vec


def approx_equal_vec(a, b, tol=1e-4):
    return len(a) == len(b) and all(abs(float(a[i]) - float(b[i])) <= tol for i in range(len(a)))


def collect_goal_vectors(trace):
    sols = []

    for evt in trace:
        if evt.get("type") == "solution":
            item = extract_realization(evt)
            sols.append(unscale_vec(item["f"]))

    uniq = []
    for s in sols:
        if not any(approx_equal_vec(s, t) for t in uniq):
            uniq.append(s)

    return uniq


def collect_final_solution_vectors(trace):
    for evt in trace:
        if evt.get("type") == "final_solutions":
            sols = []

            for sol in evt.get("solutions", []):

                # New Apex-style format:
                # {"state": ..., "f": [...]}
                if isinstance(sol, dict) and "f" in sol:
                    sols.append(unscale_vec(list(sol.get("f", []))))
                    continue

                # Old RApex-style format:
                # [apex_node, realization_node]
                if isinstance(sol, list) and len(sol) >= 2:
                    rz = sol[1]
                    sols.append(unscale_vec(list(rz.get("full_cost", []))))
                    continue

                # Fallback dict format:
                if isinstance(sol, dict) and "full_cost" in sol:
                    sols.append(unscale_vec(list(sol.get("full_cost", []))))

            return sols

    return []


def enumerate_paths_from_edges_df(edges_df, start_name, goal_name, k):
    G = {}

    for _, row in edges_df.iterrows():
        u = str(row["u"]).strip()
        v = str(row["v"]).strip()

        if not u or not v:
            continue

        cost = [float(row[f"c{i}"]) for i in range(k)]

        G.setdefault(u, []).append((v, cost))
        G.setdefault(v, [])

    stack = [(start_name, [start_name], set([start_name]), [0.0] * k)]
    out = []

    while stack:
        u, path, seen, cost = stack.pop()

        if u == goal_name:
            out.append((path, cost))
            continue

        for v, w in G.get(u, []):
            if v in seen:
                continue

            new_cost = [cost[i] + w[i] for i in range(k)]
            stack.append((v, path + [v], seen | {v}, new_cost))

    return out


def compute_solution_edges(trace, edges_df, name_to_id, start_label, goal_label, k):
    sol_vecs = collect_final_solution_vectors(trace)

    if not sol_vecs:
        return set()

    all_paths = enumerate_paths_from_edges_df(edges_df, start_label, goal_label, k)

    sol_edges = set()

    for path, cost in all_paths:
        if any(approx_equal_vec(cost, sv, tol=1e-5) for sv in sol_vecs):
            for a, b in zip(path, path[1:]):
                sol_edges.add((a, b))

    return sol_edges


def compute_solution_paths(trace, edges_df, name_to_id, start_label, goal_label, k):
    sol_vecs = collect_final_solution_vectors(trace)
    all_paths = enumerate_paths_from_edges_df(edges_df, start_label, goal_label, k)

    sol_paths = []

    for path, cost in all_paths:
        if any(approx_equal_vec(cost, sv, tol=1e-5) for sv in sol_vecs):
            sol_paths.append(path)

    uniq = []
    seen = set()

    for p in sol_paths:
        tp = tuple(p)
        if tp not in seen:
            seen.add(tp)
            uniq.append(p)

    return uniq


def compute_candidate_paths(trace, edges_df, name_to_id, start_label, goal_label, k, eps_vals):
    final_vecs = collect_final_solution_vectors(trace)

    if not final_vecs:
        return []

    all_paths = enumerate_paths_from_edges_df(edges_df, start_label, goal_label, k)
    sol_paths = compute_solution_paths(trace, edges_df, name_to_id, start_label, goal_label, k)
    sol_path_tuples = {tuple(p) for p in sol_paths}

    candidate_paths = []

    for path, cost in all_paths:
        if tuple(path) in sol_path_tuples:
            continue

    for fv in final_vecs:
        if len(fv) != len(cost):
            continue

        ok = True
        for i in range(len(cost)):
            if float(cost[i]) > (1 + float(eps_vals[i])) * float(fv[i]):
                ok = False
                break

        if ok:
            candidate_paths.append(path)
            break

    uniq = []
    seen = set()

    for p in candidate_paths:
        tp = tuple(p)
        if tp not in seen:
            seen.add(tp)
            uniq.append(p)

    return uniq


def paths_to_edges(paths):
    edges = set()

    for path in paths:
        for a, b in zip(path, path[1:]):
            edges.add((a, b))

    return edges

def collect_final_solution_pairs(trace):
    pairs = []

    for evt in trace:
        if evt.get("type") == "final_solutions":
            for rp in evt.get("solutions", []):
                if isinstance(rp, list) and len(rp) >= 2:
                    apex = rp[0]
                    realization = rp[1]

                    pairs.append({
                        "apex": unscale_vec(apex.get("full_cost", [])),
                        "realization": unscale_vec(realization.get("full_cost", [])),
                    })

            return pairs

    return []

def collect_final_solution_paths_from_trace(trace, id_to_name):
    paths = []

    for evt in trace:
        if evt.get("type") != "final_solutions":
            continue

        for sol in evt.get("solutions", []):
            if isinstance(sol, dict) and "path" in sol:
                path = [
                    id_to_name.get(int(node_id), str(node_id))
                    for node_id in sol["path"]
                ]
                paths.append(path)

        return paths

    return []

def rulebook_leq(x, y, rule_names, prec_df, eps):
    """
    Return True if x <=_R^eps y under partial-order rulebook.
    Smaller cost is better.
    """

    n = len(rule_names)
    eps = eps if isinstance(eps, list) else [float(eps)] * n

    # build rule graph
    succ = {i: set() for i in range(n)}
    pred_count = {i: 0 for i in range(n)}

    name_to_i = {name: i for i, name in enumerate(rule_names)}

    if prec_df is not None:
        for _, row in prec_df.iterrows():
            hi = str(row.get("Higher Priority", "")).strip()
            lo = str(row.get("Lower Priority", "")).strip()

            if not hi or not lo:
                continue

            a = name_to_i[hi] if hi in name_to_i else int(hi)
            b = name_to_i[lo] if lo in name_to_i else int(lo)

            if b not in succ[a]:
                succ[a].add(b)
                pred_count[b] += 1

    # topological queue
    q = [i for i in range(n) if pred_count[i] == 0]

    while q:
        r = q.pop(0)

        # If x is too much worse on this rule, x is not <= y
        if float(x[r]) > (1.0 + float(eps[r])) * float(y[r]):
            return False

        # If x is strictly better on this rule, remove successors from future consideration
        if float(x[r]) < (1.0 + float(eps[r])) * float(y[r]):
            blocked = list(succ[r])
            for b in blocked:
                if b in q:
                    q.remove(b)

        # normal topo progression
        for s in succ[r]:
            pred_count[s] -= 1
            if pred_count[s] == 0 and s not in q:
                q.append(s)

    return True


def compute_rulebook_nondominated_paths(edges_df, start_label, goal_label, k, rule_names, prec_df, eps):
    all_paths = enumerate_paths_from_edges_df(edges_df, start_label, goal_label, k)

    kept = []

    for path_i, cost_i in all_paths:
        dominated = False

        for path_j, cost_j in all_paths:
            if path_i == path_j:
                continue

            # j dominates i if j <= i and not i <= j
            if rulebook_leq(cost_j, cost_i, rule_names, prec_df, eps) and not rulebook_leq(cost_i, cost_j, rule_names, prec_df, eps):
                dominated = True
                break

        if not dominated:
            kept.append((path_i, cost_i))

    return kept