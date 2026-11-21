import random
import pandas as pd
from sklearn.metrics import roc_auc_score
from . import pipeline

STATUS_TO_TYPE = {"supported": "answerable", "conflicting": "conflicting", "insufficient": "unanswerable"}


def _norm(s):
    return "".join(str(s).lower().split())


def run_eval(client, questions, patients, n=15, k=10, progress=None):
    by = {}
    for q in questions:
        by.setdefault(q["type"], []).append(q)
    rng, chosen = random.Random(1), []
    for t, lst in by.items():
        chosen += rng.sample(lst, min(len(lst), max(1, n // 3)))
    rows = []
    for i, q in enumerate(chosen):
        r = pipeline.answer_question(client, q["question"], patients[q["patient"]], k)
        rows.append({"question": q["question"], "true_type": q["type"], "predicted": STATUS_TO_TYPE[r["status"]],
                     "belief_doubt": r["risk"], "baseline_doubt": r["baseline_risk"],
                     "answer": r["answer"],
                     "correct": (_norm(q["expected"]) in _norm(r["answer"])) if q["type"] == "answerable" else None})
        if progress:
            progress((i + 1) / len(chosen))
    return pd.DataFrame(rows)


def summarize(df):
    out = {"status_accuracy": float((df.true_type == df.predicted).mean())}
    y = (df.true_type != "answerable").astype(int)
    if y.nunique() == 2:
        out["auroc_belief"] = float(roc_auc_score(y, df.belief_doubt))
        out["auroc_baseline"] = float(roc_auc_score(y, df.baseline_doubt))
    ans = df[df.true_type == "answerable"].correct.dropna()
    out["answer_accuracy"] = float(ans.mean()) if len(ans) else None
    out["by_type"] = df.groupby("true_type")[["belief_doubt", "baseline_doubt"]].mean()
    return out
