from app.config import ROOT, Settings
from app.service import Service

if __name__ == "__main__":
    s = Service(Settings())
    try:
        s.rag.ingest_corpus(ROOT / "rag_materials")
        print(f"Indexed {len(s.db.documents())} document versions.")
    finally:
        s.close()
