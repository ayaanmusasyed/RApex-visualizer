INF_THRESHOLD = 1e9
SCALE = 1.0


def unscale_vec(vec):
    return [float(x) / SCALE for x in vec]

def pretty_num(x):

    x = float(x)

    if x >= INF_THRESHOLD:
        return "∞"

    return f"{x / SCALE:.4g}"

def pretty_vec(vec):

    vals = []

    for x in vec:
        vals.append(pretty_num(x))

    return "[" + ", ".join(vals) + "]"