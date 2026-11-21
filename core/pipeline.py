from . import llm, data, belief

ANSWER_SYS = """You are a careful clinical record assistant. Answer ONLY from the numbered evidence passages.
Never use outside knowledge about the patient. Return JSON:
{"answer": "short answer", "enough_evidence": true/false, "self_confidence": 0.0-1.0,
 "claims": [{"text": "one atomic factual statement", "evidence_ids": ["D1.2"]}]}
If passages disagree with each other, do NOT silently pick one: mention the disagreement in "answer" and cite the passages from BOTH sides.
Split the answer into at most 4 atomic claims. If the passages do not contain the answer, say so in
"answer", set enough_evidence=false, and give one claim saying the record does not mention it (empty evidence_ids)."""

VERIFY_SYS = """You are a strict fact checker. For each claim, judge EVERY passage:
"supports" = the passage clearly states the claim; "contradicts" = it states something incompatible with the claim
(e.g. "no known allergies" contradicts "has a penicillin allergy"; "continue X" contradicts "X was discontinued").
Check each passage independently: a passage that contradicts the claim MUST be listed even if other passages support it.
Otherwise omit the passage. strength = 0-1, how explicit the passage is. A claim that says the record
does NOT mention something has no supporting passage. Return JSON:
{"claims": [{"index": 0, "judgements": [{"id": "D1.2", "stance": "supports", "strength": 0.9}]}]}"""


def _fmt(passages):
    return "\n\n".join(f"[{p['id']}] ({p['doc']})\n{p['text']}" for p in passages)


def answer_question(client, question, docs, k=10):
    allp = data.build_passages(docs)
    sel = data.retrieve(question, allp, k)
    pmap = {p["id"]: p for p in sel}
    a = llm.chat_json(client, ANSWER_SYS, f"EVIDENCE:\n{_fmt(sel)}\n\nQUESTION: {question}")
    raw_claims = (a.get("claims") or [])[:4]
    verdicts = {}
    if raw_claims:
        claims_txt = "\n".join(f"{i}. {c.get('text','')}" for i, c in enumerate(raw_claims))
        v = llm.chat_json(client, VERIFY_SYS, f"PASSAGES:\n{_fmt(sel)}\n\nCLAIMS:\n{claims_txt}")
        for item in v.get("claims", []):
            verdicts[item.get("index")] = [j for j in item.get("judgements", []) if j.get("id") in pmap]
    claims = []
    for i, c in enumerate(raw_claims):
        js = verdicts.get(i, [])
        mass, conflict = belief.combine_all(js)
        claims.append({
            "text": c.get("text", ""), "cited": [e for e in c.get("evidence_ids", []) if e in pmap],
            "judgements": js, "mass": mass, "conflict": conflict,
            "status": belief.claim_status(mass, conflict), "risk": belief.claim_risk(mass, conflict)})
    statuses = [c["status"] for c in claims]
    if not claims:
        qstatus, risk = "insufficient", 1.0
    elif "conflicting" in statuses:
        qstatus, risk = "conflicting", max(c["risk"] for c in claims)
    elif "unknown" in statuses or "contradicted" in statuses:
        qstatus, risk = "insufficient", max(c["risk"] for c in claims)
    else:
        qstatus, risk = "supported", max(c["risk"] for c in claims)
    try:
        conf = max(0.0, min(1.0, float(a.get("self_confidence", 0.5))))
    except (TypeError, ValueError):
        conf = 0.5
    return {"question": question, "answer": a.get("answer", ""), "claims": claims, "passages": pmap,
            "status": qstatus, "risk": risk, "self_confidence": conf, "baseline_risk": 1 - conf,
            "passages_read": len(sel), "passages_total": len(allp)}


def explain(client, res, style="simple"):
    summary = [{"claim": c["text"], "supported": round(c["mass"]["S"], 2),
                "contradicted": round(c["mass"]["C"], 2), "unknown": round(c["mass"]["U"], 2),
                "disagreement_between_sources": round(c["conflict"], 2),
                "evidence": [{"doc": res["passages"][j["id"]]["doc"], "text": res["passages"][j["id"]]["text"],
                              "stance": j["stance"]} for j in c["judgements"]]} for c in res["claims"]]
    how = ("Plain everyday language, max 4 sentences, no jargon." if style == "simple" else
           "Clinician-level, precise, mention which documents agree or disagree, max 6 sentences.")
    sys = ("You explain why an AI answer is or is not reliable, using ONLY the data given. "
           "Do not add medical facts. " + how)
    return llm.chat_text(client, sys, f"Question: {res['question']}\nAnswer: {res['answer']}\nData: {summary}")
