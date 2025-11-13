import os
import re
import json
import httpx
import yaml
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, Body, Header
from fastapi.responses import JSONResponse

app = FastAPI(title="AST App Classifier", version="1.0")

USE_LLM = os.getenv("USE_LLM", "0") == "1"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b-instruct-q4_K_M")
API_TOKEN = os.getenv("API_TOKEN", "changeme")

RULES_PATH = os.getenv("RULES_PATH", "/rules_cache/generated/combined_rules.yaml")
def load_rules():
    try:
        with open(RULES_PATH,"r",encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception:
        pass
    with open("rules.yaml","r",encoding="utf-8") as f:
        return yaml.safe_load(f)

RULES = load_rules()

def norm_headers(headers_dict: Dict[str, str]) -> list[str]:
    items = []
    for k,v in (headers_dict or {}).items():
        items.append(f"{k.lower()}: {str(v).lower()}")
    return items

def match_rule(rule: Dict[str, Any], rec: Dict[str, Any]) -> int:
    score = 0
    uri = (rec.get("uri") or "").lower()
    headers = rec.get("headers",{}) or {}
    cookies = rec.get("cookies",{}) or {}
    ua = (rec.get("user_agent") or "").lower()

    uri_subs = [s.lower() for s in rule.get("uri_substr",[])]
    header_any = [s.lower() for s in rule.get("header_any",[])]
    cookie_any = [s.lower() for s in rule.get("cookie_any",[])]
    ua_any = [s.lower() for s in rule.get("ua_any",[])]

    if any(s in uri for s in uri_subs):
        score += 40

    h_lines = norm_headers(headers)
    for pat in header_any:
        try:
            r = re.compile(pat)
        except Exception:
            continue
        if any(r.search(h) for h in h_lines):
            score += 30
            break

    ck_names = [str(k).lower() for k in cookies.keys()]
    if any(any(p in c for p in cookie_any) for c in ck_names):
        score += 20

    if any(s in ua for s in ua_any):
        score += 10

    return score

def rules_classify(rec: Dict[str, Any]) -> List[Dict[str, Any]]:
    results = []
    for rule in RULES:
        base = int(rule.get("weight", 50) or 50)
        delta = match_rule(rule, rec)
        total = base + delta if delta > 0 else 0
        if total > 0:
            results.append({
                "id": rule.get("id",""),
                "label": rule.get("label","Unknown"),
                "score": total
            })
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:3]

async def llm_refine(rec: Dict[str, Any], labels: List[str]) -> Optional[str]:
    if not USE_LLM:
        return None
    prompt = f"""You are an application fingerprinting assistant.
Given HTTP telemetry (host, uri, headers, cookies, user-agent), pick ONE best category label.
Prefer one of these labels if appropriate: {labels}.
If none fit, reply "Unknown". Return ONLY the label text.
Telemetry:
{json.dumps(rec, indent=2)}
"""
    payload = {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(f"{OLLAMA_URL}/api/generate", json=payload)
            r.raise_for_status()
            data = r.json()
            text = (data.get("response") or "").strip()
            return text.splitlines()[0].strip()
    except Exception:
        return None

@app.get("/healthz")
async def healthz():
    return {"ok": True, "use_llm": USE_LLM}

@app.post("/classify")
async def classify(records: List[Dict[str, Any]] = Body(...), authorization: Optional[str] = Header(default=None)):
    if API_TOKEN and API_TOKEN != "changeme":
        if not authorization or not authorization.strip().lower().startswith("bearer "):
            return JSONResponse(status_code=401, content={"error":"missing bearer token"})
        token = authorization.split()[1]
        if token != API_TOKEN:
            return JSONResponse(status_code=403, content={"error":"invalid token"})

    out = []
    label_space = [r.get("label","Unknown") for r in RULES]

    for rec in records:
        top = rules_classify(rec)
        best = top[0]["label"] if top else "Unknown"
        llm_label = await llm_refine(rec, label_space)
        final_label = llm_label if llm_label and llm_label.lower() != "unknown" else best
        out.append({
            "input": rec,
            "top_matches": top,
            "label": final_label
        })
    return {"results": out}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8080, workers=1)
