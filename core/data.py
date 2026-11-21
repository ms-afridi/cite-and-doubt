import io, json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

READ_ALL_LIMIT = 30  # records up to this many passages are read completely


def read_file(name, raw):
    ext = name.lower().rsplit(".", 1)[-1]
    if ext == "pdf":
        from pypdf import PdfReader
        return "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(raw)).pages)
    text = raw.decode("utf-8", errors="ignore")
    if ext == "json":
        try:
            text = json.dumps(json.loads(text), indent=1)
        except Exception:
            pass
    return text


def build_passages(docs, max_chars=350):
    """docs: {filename: text}  ->  [{id:'D1.3', doc:filename, text:...}]"""
    out = []
    for di, (name, text) in enumerate(docs.items(), 1):
        pieces = []
        for line in text.splitlines():
            line = line.strip()
            while len(line) > max_chars * 1.5:
                cut = line.rfind(". ", 0, max_chars)
                cut = cut + 1 if cut > 0 else max_chars
                pieces.append(line[:cut].strip())
                line = line[cut:].strip()
            if line:
                pieces.append(line)
        buf, n = "", 0
        for p in pieces:
            if buf and len(buf) + len(p) > max_chars:
                n += 1
                out.append({"id": f"D{di}.{n}", "doc": name, "text": buf})
                buf = p
            else:
                buf = (buf + "\n" + p) if buf else p
        if buf:
            n += 1
            out.append({"id": f"D{di}.{n}", "doc": name, "text": buf})
    return out


def retrieve(question, passages, k=10):
    """Short records: read everything. Long records: keep the k most relevant passages."""
    if len(passages) <= READ_ALL_LIMIT:
        return passages
    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    m = vec.fit_transform([p["text"] for p in passages] + [question])
    sims = cosine_similarity(m[-1], m[:-1]).ravel()
    top = sorted(sims.argsort()[::-1][:k])
    return [passages[i] for i in top]
