# api.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from budget_llm_project.main import build_engine

# Engine setup (sadece 1 kere çalışır, server açılırken)
engine, doc_list_data, index_data = build_engine()

app = FastAPI()

# CORS (preflight dahil)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_origin_regex=".*",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Query(BaseModel):
    message: str | None = None
    soru: str | None = None

@app.get("/")
def root():
    return {"message": "API ayakta"}


@app.post("/query")
def run_query(q: Query):
    try:
        user_msg = q.message or q.soru
        if not user_msg:
            return {"response": "Hata: 'message' veya 'soru' alanı gerekli.", "cevap": None}

        cevap = engine.smart_query(user_msg, doc_list_data, index_data)
        return {"response": cevap, "cevap": cevap}
    except Exception as e:
        return {"response": f"Hata oluştu: {str(e)}", "cevap": None}


@app.options("/query")
def options_query():
    return {"ok": True}

@app.get("/history")
def get_history(last: int = 20):
    return {"items": engine.get_history(last)}