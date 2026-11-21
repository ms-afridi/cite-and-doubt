# Cite & Doubt

**An AI assistant for patient records that shows its evidence and tells you how much to trust each answer.**

---

## What is this?

AI chatbots can read long medical records and answer questions about them. The problem: they can be **wrong while
sounding completely sure**. In healthcare, that is dangerous.

Cite & Doubt tries to fix this. When you ask a question about a patient, it does not just give an answer. It also shows:

1. **Where the answer came from** (the exact sentences in the records)
2. **How sure it really is** (and why)
3. **When the records disagree with each other**

Think of a good student in an exam: *"I think the answer is X. Here is the page where I found it. But I am less sure
about this part, because two notes say different things."* That is what this tool does.

---

## A quick example

Question: **"Does the patient have any drug allergies?"**

- The *admission note* says: "No known drug allergies."
- The *pharmacy note* says: "Patient reports a penicillin allergy (rash)."

A normal chatbot may pick one and answer confidently. Cite & Doubt shows a **⚠️ "The records disagree"** warning,
displays both notes side by side, and explains the conflict, so the doctor knows to check.

---

## How it works (in 4 simple steps)

| Step | What happens | In plain words |
|---|---|---|
| 1. **Find** | The records are cut into small numbered pieces. Short records are read fully; long ones are searched for the most relevant pieces. | Like finding the right pages in a long file |
| 2. **Answer** | The AI writes its answer as small separate facts ("claims") and cites the pieces it used. | One answer, broken into checkable facts |
| 3. **Check** | A second pass checks every claim against **every** piece of the record: does it support, contradict, or say nothing? | Like a fact-checker double-checking the first writer |
| 4. **Score** | Each check becomes a small piece of evidence. They are combined into three numbers per claim. | Doubt shown in 3 parts instead of 1 |

### The three numbers

Instead of one vague "87% confident", every claim gets:

- 🟢 **Supported**: the records back this up
- 🔴 **Contradicted**: the records say the opposite
- ⚪ **Don't know**: the records do not say

They always add up to 100%. A separate **disagreement level** appears when different notes conflict.
(The maths behind this is called *Dempster-Shafer belief theory*, a way of combining pieces of evidence that
also lets you say "I don't know" honestly.)

---

## What you see in the app

- **Status badge:** ✅ well supported · ⚠️ records disagree · ❔ not enough evidence
- **Answer** in simple words
- **Claim cards** with a colour bar (green / red / grey) and the quoted evidence from each document
- **"Why is the AI unsure?" button** that explains the result in simple words or in a more detailed clinical style
- **Evaluation tab** that tests the tool on questions where the right answer is known

---

## Try it yourself

```bash
pip install -r requirements.txt
cp .env.example .env        # then add your Groq API key inside .env
streamlit run app.py
```

Then open the link shown in the terminal (usually http://localhost:8501).

- The AI model is `openai/gpt-oss-120b`, run through [Groq](https://console.groq.com).
- **Deploying on Streamlit Cloud?** Add `GROQ_API_KEY` in the app's *Secrets* settings instead of using `.env`.
- The `.env` file is private and is never uploaded to GitHub.

### Using your own patient records

Go to **Ask a question** and choose **Upload my own files**. You can upload one person's discharge summary, doctor
notes, lab results or medication list (`.txt`, `.md`, `.pdf`, `.csv`, `.json`). Several files are treated as the
records of **one patient**. An example report is built into the app.

---

## About the data

**No real patient data is used.** The project includes 20 made-up patients (5 notes each) and 100 test questions,
all created by `core/synth.py`. Because we wrote the records ourselves, we **know the correct answer** to every
question. There are three kinds:

| Type | Example | What the tool should do |
|---|---|---|
| **Answerable** | "What dose of metformin at discharge?" | Show ✅ with high support |
| **Unanswerable** | "Is the patient a smoker?" (never written anywhere) | Show ❔ "don't know" |
| **Conflicting** | "Any drug allergies?" (two notes disagree) | Show ⚠️ conflict warning |

---

## How it is tested

The **Evaluation** tab runs these questions and compares two ways of expressing doubt:

- **Our method:** the three-part belief score above
- **Plain method:** just asking the AI "how confident are you?"

It reports how often the situation is recognised correctly and how well each method warns about risky answers
(AUROC). Results are saved after every question, so you can run it in small batches, which is useful on free API plans.

---

## Limitations (please read)

- The data is made up and simple. This is **not clinically validated** and **must not be used for real patient care**.
- The fact-checking step is done by an AI model, so it can make mistakes.
- The strength numbers are the model's judgement, **not calibrated probabilities**.
- Searching long records by keywords can miss relevant passages.
- The maths assumes each piece of evidence is independent. Copied text across notes can inflate support.
- The test set is small, so results are indicative, not conclusive.

---

## Project layout

```
app.py              the Streamlit web app
core/pipeline.py    find -> answer -> check -> score
core/belief.py      the three-part belief maths and conflict
core/data.py        reading files, cutting into pieces, searching
core/synth.py       generator for the made-up patients
core/evaluate.py    batch testing and metrics
core/llm.py         connection to the Groq API (with rate-limit handling)
data/synthetic/     made-up patients and test questions
examples/           an example report you can upload
```

## Future research directions

The current version is a small, text-only study on synthetic data. The directions below describe how the idea could
grow into research that works on real clinical settings. They are plans, not results.

### 1. Adapting a model to medical data
The system currently uses a general-purpose model through an online API. A natural next step is to **fine-tune an
open-weight model on medical text** (for example with parameter-efficient methods such as LoRA), so that it
reads clinical language, abbreviations and units more reliably. The key research questions:

- Does domain adaptation improve **claim verification** (supports / contradicts), not just answer quality?
- Does it make the belief scores **better calibrated**, so that "80% supported" really means right about 80% of the time?
- Can the model be trained so that disagreement between notes is reported rather than silently resolved?

### 2. Running locally to protect patient data
Sending patient records to an external service is not acceptable in most hospitals. The fine-tuned model could be
**deployed on a hospital's own server**, so records never leave the institution. This brings its own questions:

- How much accuracy is lost when using a smaller model that fits on local hardware?
- Can the pipeline (retrieve, answer, verify, score) run fast enough on modest GPUs?
- How should the system be protected against **leaking training data** and against misuse? Privacy-preserving
  methods such as de-identification and differential privacy are worth studying here.

### 3. From synthetic to real clinical records
Real records are messier than our synthetic ones: abbreviations, copy-pasted text, conflicting dates, scanned pages.
Working with real data would require **ethics approval, data-protection compliance and clinician involvement**.
The main goals would be to build annotated test sets, measure how often the system's doubt matches expert judgement,
and **calibrate the belief scores on real annotations** instead of relying on the model's own judgement.

### 4. Multimodal records: images, PDFs, tables and more
The app currently reads **text only**. PDFs are read only as extractable text, so scanned pages are not understood.
Clinical records also contain:

- scanned documents and handwritten notes (needs OCR or vision-language models)
- structured tables such as lab results and medication lists
- medical images (X-rays, scans) and their reports
- long timelines of events across many visits

The research question is how to **cite and check evidence across different modalities**: for example, highlighting
a region of an image or a row of a table as the source of a claim, and combining evidence from text and image
in one belief score.

### 5. Better ways to represent uncertainty
Belief functions are only one option. Other formalisms may fit clinical reasoning better, such as possibility
measures, ranking functions, or structured and graph-based representations of uncertainty. A related question is
**which display actually helps people**: comparing different ways of showing doubt in controlled studies.

### 6. Studies with clinicians and multi-site trials
The most important test is whether the tool helps people decide **when to rely on the AI**. A plan could be:

1. Small usability studies with clinicians or medical students.
2. A controlled study comparing decisions with and without the evidence and doubt display.
3. A **pilot with several hospitals**, each running the system on its own local server, with remote coordination
   of the study (shared protocol and evaluation, not shared patient data).

Outcomes to measure would include decision accuracy, time taken, trust calibration and clinician workload.
Any use with real patients would need regulatory and ethical review, and the system would remain a decision
aid, never a replacement for clinical judgement.

### 7. Agents that look for evidence themselves
Instead of receiving a fixed set of passages, an assistant could **use tools to search the record**: open a
specific document, filter lab values by date, or ask a follow-up question when evidence is missing, and then
explain which steps it took.
