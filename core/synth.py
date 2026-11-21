import json, os, random

FIRST = ["Aarav", "Maria", "John", "Fatima", "Chen", "Olga", "David", "Priya", "Luca", "Amina",
         "Sven", "Rosa", "Kenji", "Nora", "Omar", "Elena", "Tomas", "Leila", "Mark", "Sofia"]
LAST = ["Sharma", "Garcia", "Smith", "Khan", "Wang", "Ivanova", "Cohen", "Nair", "Rossi", "Diallo",
        "Berg", "Lopez", "Sato", "Hansen", "Haddad", "Petrova", "Novak", "Rahimi", "Evans", "Costa"]
ADMIT = [("community-acquired pneumonia", "cough, fever and shortness of breath", "pneumonia"),
         ("heart failure exacerbation", "leg swelling and breathlessness", "heart failure"),
         ("urinary tract infection", "painful urination and fever", "urinary"),
         ("cellulitis of the left leg", "redness and pain in the left leg", "cellulitis")]
CHRONIC = [("type 2 diabetes", "metformin", [500, 850, 1000]), ("hypertension", "lisinopril", [5, 10, 20, 40]),
           ("hyperlipidemia", "atorvastatin", [10, 20, 40, 80]), ("hypothyroidism", "levothyroxine", [50, 75, 100, 125])]
FILLER = ["Vital signs were checked every four hours and remained stable overnight.",
          "The patient was encouraged to walk in the corridor twice daily with assistance.",
          "Diet: regular, low salt. Fluids encouraged.",
          "Nursing staff reported the patient slept well and had no falls.",
          "Bed rails were up and the call bell was within reach.",
          "Physiotherapy reviewed mobility and advised gradual increase in activity.",
          "The patient's daughter visited in the afternoon and was updated by the team.",
          "Wound and skin checks were performed with no new concerns noted."]
UNANS = ["What is the patient's smoking status?", "Does the patient have a family history of cancer?",
         "What is the patient's occupation?", "Has the patient received the influenza vaccine this year?",
         "How much alcohol does the patient drink per week?"]


def generate(root, n=20, seed=7):
    rng = random.Random(seed)
    os.makedirs(root, exist_ok=True)
    questions = []
    for i in range(n):
        pid = f"patient_{i+1:02d}"
        name = f"{FIRST[i % 20]} {LAST[(i * 7) % 20]}"
        age, sex = rng.randint(45, 88), rng.choice(["male", "female"])
        dx, sym, dxkey = rng.choice(ADMIT)
        ch = rng.sample(CHRONIC, 2)
        meds = [(c[1], rng.choice(c[2])) for c in ch]
        hba1c, creat = round(rng.uniform(6.5, 10.5), 1), round(rng.uniform(0.7, 1.6), 1)
        sbp, dbp = rng.randint(110, 165), rng.randint(65, 95)
        conflict = "allergy" if i % 2 == 0 else "aspirin"
        medtxt = "; ".join(f"{m} {d} mg daily" for m, d in meds)
        f = lambda: " ".join(rng.sample(FILLER, 3))
        docs = {}
        docs["01_admission_note.txt"] = (
            f"ADMISSION NOTE\nPatient: {name}, {age}-year-old {sex}.\n"
            f"Presenting complaint: {sym}. Working diagnosis: {dx}.\n"
            f"Past history: {ch[0][0]}, {ch[1][0]}.\nHome medications: {medtxt}"
            + ("; aspirin 81 mg daily" if conflict == "aspirin" else "") + ".\n"
            f"Allergies: {'No known drug allergies.' if conflict == 'allergy' else 'None recorded.'}\n{f()}")
        docs["02_progress_note.txt"] = (
            f"PROGRESS NOTE (day 2)\nPatient improving on treatment for {dx}.\n"
            f"Blood pressure {sbp}/{dbp} mmHg.\nPlan: continue home medications"
            + (", including aspirin 81 mg daily" if conflict == "aspirin" else "") + f".\n{f()}")
        docs["03_lab_report.txt"] = (
            f"LABORATORY REPORT\nHbA1c: {hba1c} %\nCreatinine: {creat} mg/dL\n"
            f"White cell count: {rng.randint(6, 16)} x10^9/L\n{f()}")
        docs["04_pharmacy_note.txt"] = (
            "PHARMACY MEDICATION RECONCILIATION\nHome medication list verified with the patient's pharmacy.\n"
            + ("Allergy reconciliation: patient reports a penicillin allergy (rash).\n" if conflict == "allergy" else
               "Aspirin 81 mg was discontinued on day 2 because of bleeding risk.\n") + f())
        docs["05_discharge_summary.txt"] = (
            f"DISCHARGE SUMMARY\nDiagnosis: {dx}. Condition at discharge: stable.\n"
            f"Discharge medications: {medtxt}.\nFollow-up with primary care in two weeks.\n{f()}")
        pdir = os.path.join(root, pid)
        os.makedirs(pdir, exist_ok=True)
        for fn, txt in docs.items():
            with open(os.path.join(pdir, fn), "w", encoding="utf-8") as fh:
                fh.write(txt)
        q = lambda t, text, exp="": questions.append(
            {"id": f"{pid}_{len(questions)}", "patient": pid, "question": text, "type": t, "expected": exp})
        q("answerable", f"What dose of {meds[0][0]} is the patient discharged on?", str(meds[0][1]))
        q("answerable", "What was the patient's HbA1c on the lab report?", str(hba1c))
        q("answerable", "Why was the patient admitted to hospital?", dxkey)
        q("unanswerable", rng.choice(UNANS))
        q("conflicting", "Does the patient have any drug allergies?" if conflict == "allergy"
          else "Is the patient currently taking aspirin?")
    with open(os.path.join(root, "test_questions.json"), "w", encoding="utf-8") as fh:
        json.dump(questions, fh, indent=1)
    return questions


def load(root):
    qp = os.path.join(root, "test_questions.json")
    if not os.path.exists(qp):
        generate(root)
    patients = {}
    for pid in sorted(d for d in os.listdir(root) if d.startswith("patient_")):
        pdir = os.path.join(root, pid)
        patients[pid] = {fn: open(os.path.join(pdir, fn), encoding="utf-8").read() for fn in sorted(os.listdir(pdir))}
    return patients, json.load(open(qp, encoding="utf-8"))
