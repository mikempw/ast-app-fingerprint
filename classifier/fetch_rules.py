\
import os, subprocess, json, re, shutil, glob, yaml, sys, pathlib, zipfile, io, urllib.request

WAPP_URL = os.getenv("SOURCES_WAPPALYZER", "https://github.com/AliasIO/wappalyzer.git")
NUC_URL = os.getenv("SOURCES_NUCLEI", "https://github.com/projectdiscovery/nuclei-templates.git")
WW_URL = os.getenv("SOURCES_WHATWEB", "https://github.com/urbanadventurer/WhatWeb.git")
MAX_RULES = int(os.getenv("MAX_RULES","5000"))

ROOT = pathlib.Path("/rules_cache")
SRC = ROOT / "sources"
GEN = ROOT / "generated"
SRC.mkdir(parents=True, exist_ok=True)
GEN.mkdir(parents=True, exist_ok=True)

def run(cmd, cwd=None):
    print("+", " ".join(cmd), file=sys.stderr)
    subprocess.run(cmd, cwd=cwd, check=True)

def default_branch_for(owner_repo: str) -> str:
    m = owner_repo.lower()
    if m in ["aliasio/wappalyzer"]:
        return "main"
    if m in ["urbanadventurer/whatweb"]:
        return "master"
    if m in ["projectdiscovery/nuclei-templates"]:
        return "main"
    return "main"

def to_codeload_zip(url: str) -> str:
    if "codeload.github.com" in url:
        return url
    m = re.match(r"https://github.com/([^/]+)/([^/.]+)(?:\.git)?", url)
    if not m:
        raise ValueError(f"Cannot parse GitHub URL: {url}")
    owner, repo = m.group(1), m.group(2)
    branch = default_branch_for(f"{owner}/{repo}")
    return f"https://codeload.github.com/{owner}/{repo}/zip/refs/heads/{branch}"

def download_and_extract(zip_url: str, dest: pathlib.Path):
    print(f"Downloading ZIP from {zip_url}", file=sys.stderr)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.parent / (dest.name + "_dl")
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(zip_url) as resp:
        data = resp.read()
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        z.extractall(tmp)
    entries = [p for p in tmp.iterdir() if p.is_dir()]  # pick first folder
    if entries:
        if dest.exists():
            shutil.rmtree(dest, ignore_errors=True)
        entries[0].rename(dest)
    shutil.rmtree(tmp, ignore_errors=True)

def ensure_repo(url, dest: pathlib.Path):
    if "codeload.github.com" in url:
        download_and_extract(url, dest)
        return
    if dest.exists():
        try:
            run(["git","-C", str(dest), "pull","--ff-only"])
            return
        except Exception as e:
            print(f"git pull failed: {e}", file=sys.stderr)
            shutil.rmtree(dest, ignore_errors=True)
    try:
        run(["git","clone","--depth","1", url, str(dest)])
        return
    except Exception as e:
        print(f"git clone failed: {e}", file=sys.stderr)
        zip_url = to_codeload_zip(url)
        download_and_extract(zip_url, dest)

def safe_get(d, *keys, default=None):
    cur = d
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur

def build_rules_from_wappalyzer(repo):
    merged = []
    tech_dirs = []
    for p in [repo, *repo.glob("*")]:
        t = p / "src" / "technologies"
        if t.exists():
            tech_dirs.append(t)
    for tech_dir in tech_dirs:
        for f in sorted(tech_dir.glob("*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            for app_name, spec in data.items():
                rule = {
                    "id": re.sub(r"[^a-z0-9]+","-", (app_name or "").lower()),
                    "label": f"Tech: {app_name}",
                    "weight": 70,
                    "uri_substr": [],
                    "header_any": [],
                    "cookie_any": [],
                    "ua_any": []
                }
                headers = safe_get(spec, "headers", default={}) or {}
                for k,v in headers.items():
                    try:
                        rule["header_any"].append(f"{str(k).lower()}:.*{str(v).lower()}")
                    except Exception:
                        pass
                cookies = safe_get(spec, "cookies", default={}) or {}
                for k,_ in cookies.items():
                    rule["cookie_any"].append(str(k).lower())
                urls = safe_get(spec, "url", default=[]) or []
                if isinstance(urls, str):
                    urls = [urls]
                for u in urls:
                    if isinstance(u, str):
                        rule["uri_substr"].append(u.lower()[:120])
                merged.append(rule)
                if len(merged) >= MAX_RULES:
                    return merged
    return merged

def build_rules_from_nuclei(repo):
    merged = []
    tech_dirs = list(repo.rglob("technologies"))
    count = 0
    for tech_dir in tech_dirs:
        for ypath in tech_dir.rglob("*.yaml"):
            try:
                y = ypath.read_text("utf-8", errors="ignore")
                paths = re.findall(r'path:\s*-\s*"([^"]{1,80})"', y)
                merged.append({
                    "id": "nuclei-"+os.path.basename(str(ypass)).replace(".yaml",""),
                    "label": "Nuclei: "+os.path.basename(str(ypass)),
                    "weight": 60,
                    "uri_substr": [p.lower() for p in paths[:3]],
                    "header_any": [],
                    "cookie_any": [],
                    "ua_any": []
                })
                count += 1
                if count >= MAX_RULES:
                    return merged
            except Exception:
                continue
    return merged

def build_rules_from_whatweb(repo):
    merged = []
    plug_dirs = list(repo.rglob("plugins"))
    count = 0
    for plug_dir in plug_dirs:
        for p in sorted(plug_dir.glob("*.rb")):
            name = p.stem
            merged.append({
                "id": f"whatweb-{name}",
                "label": f"WhatWeb: {name}",
                "weight": 40,
                "uri_substr": [],
                "header_any": [],
                "cookie_any": [],
                "ua_any": []
            })
            count += 1
            if count >= MAX_RULES:
                return merged
    return merged

def main():
    rules = []
    try:
        wdir = SRC / "wappalyzer"
        ensure_repo(WAPP_URL, wdir)
        rules += build_rules_from_wappalyzer(wdir)
    except Exception as e:
        print("wappalyzer failed:", e, file=sys.stderr)
    try:
        ndir = SRC / "nuclei-templates"
        ensure_repo(NUC_URL, ndir)
        rules += build_rules_from_nuclei(ndir)
    except Exception as e:
        print("nuclei failed:", e, file=sys.stderr)
    try:
        wwdir = SRC / "whatweb"
        ensure_repo(WW_URL, wwdir)
        rules += build_rules_from_whatweb(wwdir)
    except Exception as e:
        print("whatweb failed:", e, file=sys.stderr)

    seen = set(); deduped = []
    for r in rules:
        rid = r.get("id") or ""
        if rid in seen: continue
        seen.add(rid)
        deduped.append(r)

    out_file = GEN / "combined_rules.yaml"
    if not deduped:
        deduped = [{"id":"baseline","label":"Baseline (no external rules)","weight":1,"uri_substr":[],"header_any":[],"cookie_any":[],"ua_any":[]}]

    with open(out_file, "w", encoding="utf-8") as f:
        yaml.safe_dump(deduped, f, sort_keys=False)
    print(f"Wrote {out_file} with {len(deduped)} rules")

if __name__ == "__main__":
    main()
