# Troubleshooting

## GitHub auth / prompts
- The updater falls back to codeload ZIP automatically.
- You can also set the source directly to a codeload URL, e.g.:
  ```bash
  export SOURCES_WAPPALYZER="https://codeload.github.com/AliasIO/wappalyzer/zip/refs/heads/master"
  ```

## YAML ScannerError
- Fixed in v5 by quoting labels with ":" in `rules.yaml`.

## Ollama port in use
```
export OLLAMA_HOST_PORT=11435
./run.sh llm
```

## Force baseline rules
```
RULES_PATH=/app/rules.yaml ./run.sh
```
