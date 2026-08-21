"""Document retrieval tool: search_documents(query, account_id).

ponytail: corpus is 5 active single-page PDFs. A vector DB / hybrid
BM25+dense+rerank stack solves a scale problem this corpus doesn't have.
TF-IDF + cosine similarity over paragraph-sized chunks, built once in memory
at import time, is enough and needs no external service.

Access control: 05/06 are one customer's signed agreement each. A chunk from
an agreement file is only ever returned if it belongs to the requesting
account — enforced here by filtering on config.ACCOUNT_AGREEMENTS, not by
asking the model nicely not to mention the other customer's contract.

02_Support_Policy_v2_DEPRECATED.pdf is never loaded at all (see config.ACTIVE_DOCS).
"""
from dataclasses import dataclass

from pypdf import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from . import config

_AGREEMENT_FILES = set(config.ACCOUNT_AGREEMENTS.values())


@dataclass
class Chunk:
    source: str
    section: int
    text: str


def _extract_chunks(pdf_name: str) -> list[Chunk]:
    reader = PdfReader(config.DATA_DIR / pdf_name)
    full_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    paragraphs = [p.strip() for p in full_text.split("\n\n") if p.strip()]
    return [Chunk(source=pdf_name, section=i, text=p) for i, p in enumerate(paragraphs)]


def _build_index():
    chunks: list[Chunk] = []
    for doc in config.ACTIVE_DOCS:
        chunks.extend(_extract_chunks(doc))
    vectorizer = TfidfVectorizer(stop_words="english")
    matrix = vectorizer.fit_transform([c.text for c in chunks])
    return chunks, vectorizer, matrix


_CHUNKS, _VECTORIZER, _MATRIX = _build_index()


def search_documents(query: str, account_id: str, top_k: int = 5) -> list[dict]:
    """Return the top_k most relevant passages, scoped so a chunk from
    another account's agreement can never appear in the results.
    """
    allowed_agreement = config.ACCOUNT_AGREEMENTS.get(account_id)
    candidate_idx = [
        i
        for i, c in enumerate(_CHUNKS)
        if c.source not in _AGREEMENT_FILES or c.source == allowed_agreement
    ]
    query_vec = _VECTORIZER.transform([query])
    scores = cosine_similarity(query_vec, _MATRIX[candidate_idx]).flatten()
    ranked = sorted(zip(candidate_idx, scores), key=lambda pair: pair[1], reverse=True)[:top_k]
    return [
        {
            "source": _CHUNKS[i].source,
            "section": _CHUNKS[i].section,
            "text": _CHUNKS[i].text,
            "relevance": round(float(score), 4),
        }
        for i, score in ranked
        if score > 0
    ]
