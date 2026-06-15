import json
import heapq
import itertools
from dataclasses import dataclass
from typing import Any, List, Dict, Union

Number = Union[int, float]


@dataclass
class TraceStepper:
    trace: List[Dict]
    i: int
    OPEN: list
    tiebreak: Any
    last_pop: Dict | None
    events: list
    ordered_rules: list | None = None

def _keyer(fvec: List[Number]):
    return tuple(float(x) for x in fvec)


def extract_realization(evt: Dict) -> Dict:
    rp = evt.get("rp")

    if isinstance(rp, list) and len(rp) >= 2:
        rz = rp[1]
    elif isinstance(rp, dict):
        rz = rp
    else:
        rz = {}

    return {
        "state": int(rz.get("id", -1)),
        "g": list(rz.get("cost_until_now", [])),
        "h": list(rz.get("heuristic_cost", [])),
        "f": list(rz.get("full_cost", [])),
    }


def init_from_trace(trace: List[Dict]) -> TraceStepper:
    return TraceStepper(
        trace=trace,
        i=0,
        OPEN=[],
        tiebreak=itertools.count(0),
        last_pop=None,
        events=[],
    )


def apply_trace_step(stp: TraceStepper) -> None:
    if stp.i >= len(stp.trace):
        return

    evt = stp.trace[stp.i]
    stp.i += 1
    t = evt.get("type")

    if t == "meta":
        stp.ordered_rules = evt.get("ordered_rules")
        stp.events.append({
            "kind": "meta",
            "solver": evt.get("solver", "?"),
            "ordered_rules": evt.get("ordered_rules"),
        })
        return

    if t == "pop":
        item = extract_realization(evt)
        key = _keyer(item["f"])

        stp.last_pop = {"state": item["state"], "f": item["f"], "key": key}
        stp.events.append({"kind": "pop", "state": item["state"], "f": item["f"], "key": key})

        for j, (k, tb, it) in enumerate(stp.OPEN):
            if it["state"] == item["state"] and it["f"] == item["f"]:
                stp.OPEN.pop(j)
                heapq.heapify(stp.OPEN)
                break

        return

    if t == "enqueue":
        item = extract_realization(evt)
        key = _keyer(item["f"])

        heapq.heappush(stp.OPEN, (key, next(stp.tiebreak), item))

        stp.events.append({
            "kind": "enqueue",
            "from": evt.get("from"),
            "to": evt.get("to"),
            "f": item["f"],
        })
        return

    stp.events.append({"kind": "other", "raw": evt})


def parse_trace_lines(raw_lines: List[str]) -> List[Dict]:
    fixed = []

    for line in raw_lines:

        if '"rp":{{' in line:
            line = line.replace('"rp":{{', '"rp":[{')
            if line.endswith("}}}"):
                line = line[:-3] + "}]}"

        if '"solutions":[{{' in line:
            line = line.replace('"solutions":[{{', '"solutions":[[{')
            line = line.replace('}},{{', '}],[{')
            if line.endswith('}}]}'):
                line = line[:-4] + '}]]}'

        fixed.append(json.loads(line))

    return fixed


def load_trace_jsonl(uploaded_file) -> List[Dict]:
    raw_lines = uploaded_file.read().decode("utf-8").splitlines()
    return parse_trace_lines(raw_lines)