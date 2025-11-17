# AST App Fingerprint (v5)

Rules-based classifier for HTTP telemetry with optional LLM refinement.

## Quick Start
```bash
unzip ast-app-fingerprint-v5.zip
cd ast-app-fingerprint

# Start rules-updater + classifier (no LLM)
./run.sh

# Test with sample
./run.sh test
```

## Optional LLM
```bash
# Start with Ollama profile (pulls ~small model)
./run.sh llm
# Or connect to an existing Ollama:
export OLLAMA_URL=http://host.docker.internal:11434
USE_LLM=1 ./run.sh
```

## Env knobs
- `SOURCES_WAPPALYZER`, `SOURCES_NUCLEI`, `SOURCES_WHATWEB` — repo or codeload zip URLs
- `MAX_RULES` - cap merged rules (default 5000)
- `RULES_PATH` - force a specific rules file (e.g., `/app/rules.yaml` fallback)
- `OLLAMA_HOST_PORT` - change host port if 11434 is in use
