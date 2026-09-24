import re
import hashlib
import math
import httpx
import threading
import uuid
import yaml
from qdrant_client import QdrantClient, models
from sklearn.feature_extraction.text import HashingVectorizer
from .schemas import Citation, Filters, DocumentInfo
from .security import sanitize

COLLECTION = "cloudbox_v1"
DIM = 4096


# Stable local lexical embeddings: no downloaded model, no charge, no vocabulary drift.
# Semantic embedding replacement requires a NEW collection and full reindex.
def normalize(text):
    text = text.lower().replace("read-only", "readonly")
    text = re.sub(r"\b(?:charged|charges)\b", "charge", text)
    text = re.sub(r"\bplans\b", "plan", text)
    text = re.sub(r"\b(?:supports|supported)\b", "support", text)
    text = re.sub(r"\b(?:integrate|integrates|integration)\b", "integrations", text)
    text = re.sub(r"\b(?:duplicated|duplicates)\b", "duplicate", text)
    text = re.sub(r"\b(?:sharing|shared)\b", "share", text)
    return text


def version_key(v):
    return tuple(int(n) for n in re.findall(r"\d+", v))


def parse_document(markdown, source_path):
    if sanitize(markdown) != markdown:
        raise ValueError("Document contains potentially sensitive content")
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", markdown, re.S)
    if not match:
        raise ValueError("Markdown must start with YAML front matter")
    raw = yaml.safe_load(match.group(1))
    if not isinstance(raw, dict):
        raise ValueError("Invalid metadata")
    meta = {k: str(raw[k]) for k in ("doc_id", "title", "product", "version", "source_type", "trust_level") if k in raw}
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", meta.get("doc_id", "")):
        raise ValueError("Invalid doc_id")
    if meta.get("trust_level") not in {"official", "internal", "untrusted"}:
        raise ValueError("Invalid trust level")
    if not re.fullmatch(r"\d+(?:[.\-]\d+)*", meta.get("version", "")):
        raise ValueError("Version must be numeric/date-like")
    meta["source_path"] = source_path
    DocumentInfo(**meta)
    body = match.group(2).strip()
    if not body:
        raise ValueError("Document is empty")
    return meta, body


def chunk_document(meta, body):
    # Sections remain atomic: tables, numbered workflows and their conditions are never severed.
    sections = re.split(r"\n(?=#{1,3} )", body)
    for idx, section in enumerate(sections):
        if len(section) > 12000:
            raise ValueError("Section exceeds 12000 characters; add semantic headings")
        yield dict(**meta, chunk_id=f"{meta['doc_id']}:{meta['version']}:{idx}", content=section.strip())


class Retriever:
    def __init__(self, settings, db, telemetry):
        self.collection = (
            COLLECTION
            if settings.embedding_mode == "hash"
            else "cloudbox_semantic_"
            + hashlib.sha256((settings.embedding_model + str(settings.embedding_dimensions)).encode()).hexdigest()[:12]
        )
        self.dimensions = DIM if settings.embedding_mode == "hash" else settings.embedding_dimensions
        self.settings = settings
        self.db = db
        self.telemetry = telemetry
        self.lock = threading.RLock()
        self.vectorizer = HashingVectorizer(
            n_features=DIM,
            alternate_sign=False,
            norm="l2",
            stop_words="english",
            ngram_range=(1, 2),
            preprocessor=normalize,
        )
        self.client = (
            QdrantClient(url=settings.qdrant_url, timeout=5)
            if settings.qdrant_url
            else QdrantClient(path=settings.qdrant_path)
        )
        if not self.client.collection_exists(self.collection):
            self.client.create_collection(
                self.collection,
                vectors_config=models.VectorParams(size=self.dimensions, distance=models.Distance.COSINE),
            )
        if settings.qdrant_url:
            for key in ["product", "version", "source_type", "trust_level", "doc_id"]:
                self.client.create_payload_index(
                    self.collection, key, field_schema=models.PayloadSchemaType.KEYWORD, wait=True
                )

    def embed(self, texts):
        if self.settings.embedding_mode == "hash":
            with self.telemetry.span(
                "embedding.local_hash", embedding_model="hash-word-bigram-4096", tokens=0, cost_usd=0
            ):
                return self.vectorizer.transform(texts).toarray().tolist()
        with self.telemetry.span(
            "embedding.api", kind="embedding", embedding_model=self.settings.embedding_model
        ) as span:
            with httpx.Client(timeout=15) as client:
                response = client.post(
                    self.settings.embedding_base_url.rstrip("/") + "/embeddings",
                    headers={"Authorization": "Bearer " + self.settings.embedding_api_key},
                    json={"model": self.settings.embedding_model, "input": texts, "dimensions": self.dimensions},
                )
                response.raise_for_status()
                data = response.json()
            vectors = [x["embedding"] for x in sorted(data["data"], key=lambda x: x["index"])]
            if len(vectors) != len(texts) or any(
                len(v) != self.dimensions or any(not math.isfinite(x) for x in v) for v in vectors
            ):
                raise ValueError("Invalid embedding response")
            tokens = data.get("usage", {}).get("total_tokens", 0)
            span["usage"] = {"input": tokens}
            span["model"] = self.settings.embedding_model
            if self.settings.embedding_cost_per_million:
                span["cost"] = {"input": tokens * self.settings.embedding_cost_per_million / 1e6}
            return vectors

    def ingest(self, markdown, path):
        meta, body = parse_document(markdown, path)
        chunks = list(chunk_document(meta, body))
        vectors = self.embed([x["title"] + " " + x["content"] for x in chunks])
        with self.lock:
            # Delete same document version to avoid stale chunks after an edit.
            selector = models.Filter(
                must=[
                    models.FieldCondition(key="doc_id", match=models.MatchValue(value=meta["doc_id"])),
                    models.FieldCondition(key="version", match=models.MatchValue(value=meta["version"])),
                ]
            )
            self.client.delete(self.collection, points_selector=models.FilterSelector(filter=selector), wait=True)
            self.client.upsert(
                self.collection,
                points=[
                    models.PointStruct(id=str(uuid.uuid5(uuid.NAMESPACE_URL, x["chunk_id"])), vector=v, payload=x)
                    for x, v in zip(chunks, vectors)
                ],
                wait=True,
            )
            self.db.put_document(meta, body)
        return meta

    def ingest_corpus(self, path):
        for file in sorted(path.glob("*.md")):
            if file.name != "README.md":
                self.ingest(file.read_text(), f"rag_materials/{file.name}")

    def search(self, query, filters: Filters, limit=4):
        limit = min(max(limit, 1), self.settings.max_results)
        with self.telemetry.span("retrieval.qdrant", result_limit=limit):
            conditions = [
                models.FieldCondition(key=k, match=models.MatchValue(value=v))
                for k, v in filters.model_dump().items()
                if v is not None
            ]
            with self.lock:
                hits = self.client.query_points(
                    self.collection,
                    query=self.embed([query])[0],
                    query_filter=models.Filter(must=conditions),
                    limit=16,
                    with_payload=True,
                ).points
            # Newest official version per doc_id is authoritative, even if an old version scored higher.
            all_meta = [m for m, _ in self.db.documents()]
            latest = {}
            for m in all_meta:
                if m["trust_level"] == "official":
                    latest[m["doc_id"]] = max(latest.get(m["doc_id"], ()), version_key(m["version"]))
            chosen = []
            for h in hits:
                p = h.payload
                if (
                    not filters.version
                    and p["trust_level"] == "official"
                    and version_key(p["version"]) < latest.get(p["doc_id"], ())
                ):
                    continue
                if h.score < self.settings.retrieval_threshold:
                    continue
                chosen.append(Citation(**p, score=round(float(h.score), 5)).model_dump())
                if len(chosen) >= limit:
                    break
            return chosen

    def close(self):
        self.client.close()
