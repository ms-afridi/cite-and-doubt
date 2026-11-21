import json, os
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from core import llm, synth, data, pipeline, evaluate

load_dotenv()
ROOT = os.path.dirname(os.path.abspath(__file__))
SYN = os.path.join(ROOT, "data", "synthetic")
st.set_page_config(page_title="Cite & Doubt", page_icon="🩺", layout="wide")

BADGE = {"supported": ("#e6f6ec", "#1f7a45", "✅ Well supported by the records"),
         "conflicting": ("#fff1e0", "#b45f06", "⚠️ The records disagree with each other"),
         "insufficient": ("#eceef2", "#4b5160", "❔ Not enough evidence in the records")}
STANCE = {"supports": "🟢 supports", "contradicts": "🔴 contradicts"}


@st.cache_data(show_spinner=False)
def load_synth():
    return synth.load(SYN)


def bar(m):
    return (f"<div style='display:flex;height:16px;border-radius:6px;overflow:hidden'>"
            f"<div style='width:{m['S']*100:.0f}%;background:#2e9e5b'></div>"
            f"<div style='width:{m['C']*100:.0f}%;background:#d64545'></div>"
            f"<div style='width:{m['U']*100:.0f}%;background:#b9bcc4'></div></div>"
            f"<small>🟢 Supported {m['S']*100:.0f}% &nbsp; 🔴 Contradicted {m['C']*100:.0f}% "
            f"&nbsp; ⚪ Don't know {m['U']*100:.0f}%</small>")


def render(res, client):
    bg, fg, label = BADGE[res["status"]]
    st.markdown(f"<div style='background:{bg};color:{fg};padding:14px 18px;border-radius:10px;"
                f"font-size:1.15rem;font-weight:600'>{label}</div>", unsafe_allow_html=True)
    st.markdown("#### Answer")
    st.info(res["answer"] or "(no answer)")
    c1, c2, c3 = st.columns(3)
    c1.metric("Overall doubt (our method)", f"{res['risk']*100:.0f}%", help="0% = safe to rely on, 100% = do not rely on")
    c2.metric("AI's own confidence (plain method)", f"{res['self_confidence']*100:.0f}%",
              help="Just a single number the AI reports about itself. It cannot tell you WHY.")
    c3.metric("Passages read", f"{res['passages_read']} of {res['passages_total']}")
    st.markdown("#### Claim by claim")
    st.caption("The answer is split into small facts. Each fact is checked against every passage in the record.")
    for i, c in enumerate(res["claims"], 1):
        icon = {"supported": "✅", "conflicting": "⚠️", "unknown": "❔", "contradicted": "❌"}[c["status"]]
        with st.expander(f"{icon} Claim {i}: {c['text']}", expanded=True):
            st.markdown(bar(c["mass"]), unsafe_allow_html=True)
            if c["conflict"] >= 0.35:
                st.warning(f"Sources disagree about this claim (disagreement level {c['conflict']*100:.0f}%).")
            if not c["judgements"]:
                st.write("No passage in the record states or contradicts this.")
            for j in c["judgements"]:
                p = res["passages"][j["id"]]
                st.markdown(f"**{STANCE.get(j['stance'], j['stance'])}** · `{p['doc']}` · strength {float(j.get('strength', 0))*100:.0f}%")
                st.markdown(f"> {p['text']}")
    st.markdown("#### 💬 Why is the AI unsure?")
    style = st.radio("Explanation style", ["simple", "clinician"], horizontal=True,
                     format_func=lambda s: "Simple words" if s == "simple" else "Detailed (clinician)")
    if st.button("Explain this result"):
        with st.spinner("Writing explanation..."):
            st.success(pipeline.explain(client, res, style))


# ---------------- sidebar ----------------
def get_key():
    k = os.getenv("GROQ_API_KEY", "")
    if not k:
        try:
            k = st.secrets.get("GROQ_API_KEY", "")  # used when deployed on Streamlit Cloud
        except Exception:
            k = ""
    return k


with st.sidebar:
    st.header("⚙️ Settings")
    key = get_key()
    if key:
        st.success("API key loaded")
    else:
        st.error("No API key found. Add GROQ_API_KEY to your .env file (local) or to Streamlit Secrets (deployed).")
    st.caption(f"Model: `{llm.MODEL}`")
    k = st.slider("Max passages read from long records", 6, 20, 10,
                  help="Short records are read completely. Long ones: only the most relevant passages.")
client = llm.get_client(key) if key else None
patients, questions = load_synth()

st.title("🩺 Cite & Doubt")
st.caption("An AI assistant for patient records that shows its evidence AND tells you how much to trust it.")
t0, t1, t2, t3 = st.tabs(["🏠 Start here", "🔎 Ask a question", "📊 Evaluation", "ℹ️ Limits & honesty"])

with t0:
    st.markdown("""
### The problem
AI can give a wrong answer in a very confident voice. In healthcare that is dangerous.
**A doctor needs to know *when* to trust the AI.**

### What this tool does differently
1. **Finds evidence** in the patient's documents (notes, labs, summaries).
2. **Answers in small facts ("claims")** and points to the exact sentences it used.
3. **Checks each fact** against *all* documents, not only the one it quoted.
4. **Shows doubt in 3 parts** instead of one vague percentage:
   🟢 *supported*, 🔴 *contradicted*, ⚪ *don't know*. It also warns when documents **disagree**.

### How to use it (3 steps)
**Step 1** open the tab **🔎 Ask a question** · **Step 2** pick a sample patient *or upload your own files* ·
**Step 3** ask a question and read the colour-coded result.

### Three kinds of situations it is built to recognise
| Situation | Example | What you should see |
|---|---|---|
| Answer is in the record | "What dose of metformin?" | ✅ green, high support |
| Answer is *not* in the record | "Is the patient a smoker?" | ❔ grey, "don't know" |
| Documents disagree | "Any drug allergies?" | ⚠️ orange, conflict warning |

*All sample patients are fake (synthetic). You can also upload one person's report in the next tab.*
""")

with t1:
    if not client:
        st.warning("No API key found. Add GROQ_API_KEY to your .env file or Streamlit Secrets, then restart the app.")
    src = st.radio("1️⃣ Where are the patient records from?", ["Sample (synthetic) patient", "Upload my own files"], horizontal=True)
    docs, sugg = {}, []
    if src.startswith("Sample"):
        pid = st.selectbox("Choose a patient", list(patients))
        docs, sugg = patients[pid], [q["question"] for q in questions if q["patient"] == pid]
    else:
        st.info("**What can I upload?** One person's medical report(s): discharge summary, doctor notes, lab results "
                "or medication list. Formats: .txt, .md, .pdf, .csv, .json. If you upload several files, "
                "they are treated as the records of **one patient**.")
        ex = open(os.path.join(ROOT, "examples", "example_patient_report.txt"), encoding="utf-8").read()
        with st.expander("📎 See an example report (and download it to try)"):
            st.text(ex)
            st.download_button("⬇️ Download example report", ex, file_name="example_patient_report.txt")
            st.markdown("**Questions you can try on it:** What is the patient's metformin dose? · "
                        "Does the patient have any drug allergies? *(the two notes disagree)* · "
                        "Is the patient a smoker? *(not in the record)*")
        files = st.file_uploader("Drop files here", accept_multiple_files=True, type=["txt", "md", "pdf", "csv", "json"])
        docs = {f.name: data.read_file(f.name, f.read()) for f in files}
    with st.expander(f"📄 Records loaded ({len(docs)} documents) - click to read"):
        for name, text in docs.items():
            st.markdown(f"**{name}**")
            st.text(text[:3000])
    st.markdown("2️⃣ **Ask a question**")
    pick = st.selectbox("Pick a suggested question, or write your own", ["✍️ Write my own"] + sugg)
    q = st.text_input("Your question", value="" if pick.startswith("✍️") else pick, key=f"q_{pick}")
    if st.button("3️⃣ Get answer", type="primary", disabled=not (client and docs and q.strip())):
        try:
            with st.spinner("Reading records, answering, checking every claim..."):
                st.session_state["res"] = pipeline.answer_question(client, q.strip(), docs, k)
        except Exception as e:
            st.error(f"Something went wrong: {e}")
    if "res" in st.session_state:
        st.divider()
        render(st.session_state["res"], client)

with t2:
    st.markdown("""
### Does our method really work better?
We test on **synthetic patients where we know the right answer**: answerable, unanswerable (information removed),
and conflicting (two notes disagree). We compare **our belief-based doubt** with the **plain AI confidence number**.
A higher **AUROC** (max 1.0) means better at warning about risky cases.
""")
    n = st.slider("Number of test questions (more = slower, uses more API calls)", 6, 60, 12, step=3)
    if st.button("▶️ Run evaluation", disabled=not client):
        bar_ = st.progress(0.0)
        try:
            df = evaluate.run_eval(client, questions, patients, n, k, progress=bar_.progress)
            st.session_state["eval"] = df
            os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
            df.to_json(os.path.join(ROOT, "data", "last_eval.json"), orient="records", indent=1)
        except Exception as e:
            st.error(f"Evaluation stopped: {e}")
    if "eval" in st.session_state:
        df = st.session_state["eval"]
        s = evaluate.summarize(df)
        a, b, c, d = st.columns(4)
        a.metric("Situation recognised correctly", f"{s['status_accuracy']*100:.0f}%")
        if "auroc_belief" in s:
            b.metric("AUROC - our method", f"{s['auroc_belief']:.2f}")
            c.metric("AUROC - plain confidence", f"{s['auroc_baseline']:.2f}")
        if s["answer_accuracy"] is not None:
            d.metric("Answers correct (answerable)", f"{s['answer_accuracy']*100:.0f}%")
        st.markdown("**Average doubt per situation** (good = low for answerable, high for the other two)")
        st.bar_chart(s["by_type"].rename(columns={"belief_doubt": "Our method", "baseline_doubt": "Plain confidence"}))
        st.dataframe(df, use_container_width=True)

with t3:
    st.markdown("""
### Limits (please read)
- Sample data is **synthetic** and simplified. Nothing here is **clinically validated** and it must not be used for patient care.
- The checking of claims is done by a language model, so the checker itself can make mistakes.
- Evidence strength numbers come from the model's judgement; they are **not calibrated probabilities**.
- Long records use keyword retrieval (TF-IDF), which can miss relevant passages.
- Dempster's rule assumes passages are independent; copied text in several notes can inflate support.
- The belief-vs-confidence comparison uses a small test set; treat it as a pilot, not proof.

### Ideas for future work
Calibrating belief masses on real annotations · user study with clinicians · tables and images ·
tool-using agent that searches records itself · other uncertainty theories (possibility measures, ranking functions).
""")
