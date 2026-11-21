CAP = 0.95  # never allow 100% certainty from one passage


def evidence_mass(stance, strength):
    s = max(0.0, min(CAP, float(strength or 0)))
    if stance == "supports":
        return {"S": s, "C": 0.0, "U": 1 - s}
    if stance == "contradicts":
        return {"S": 0.0, "C": s, "U": 1 - s}
    return {"S": 0.0, "C": 0.0, "U": 1.0}


def combine(a, b):
    k = a["S"] * b["C"] + a["C"] * b["S"]
    if 1 - k < 1e-9:
        return {"S": 0.0, "C": 0.0, "U": 1.0}, 1.0
    n = 1 - k
    return {
        "S": (a["S"] * b["S"] + a["S"] * b["U"] + a["U"] * b["S"]) / n,
        "C": (a["C"] * b["C"] + a["C"] * b["U"] + a["U"] * b["C"]) / n,
        "U": (a["U"] * b["U"]) / n,
    }, k


def combine_all(judgements):
    mass, keep = {"S": 0.0, "C": 0.0, "U": 1.0}, 1.0
    for j in judgements:
        mass, k = combine(mass, evidence_mass(j.get("stance"), j.get("strength")))
        keep *= (1 - k)
    return mass, 1 - keep  # total conflict


def claim_status(mass, conflict):
    if conflict >= 0.35:
        return "conflicting"
    if mass["U"] >= 0.5:
        return "unknown"
    return "supported" if mass["S"] >= mass["C"] else "contradicted"


def claim_risk(mass, conflict):
    """0 = safe to rely on, 1 = do not rely on."""
    return max(1 - mass["S"], conflict)
