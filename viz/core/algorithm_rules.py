from algorithm_config import ALGORITHMS

def allowed_algorithms(k):
    out = []
    for name, cfg in ALGORITHMS.items():
        max_k = cfg["max_k"]
        min_k = cfg["min_k"]
        if k >= min_k and (max_k is None or k <= max_k):
            out.append(name)
    return out