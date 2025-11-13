# Public Rules

Pulls public fingerprints and merges them:
- Wappalyzer: https://github.com/AliasIO/wappalyzer (branch: master)
- ProjectDiscovery Nuclei templates: https://github.com/projectdiscovery/nuclei-templates (branch: main)
- WhatWeb: https://github.com/urbanadventurer/WhatWeb (branch: master)

If `git clone` fails, the updater downloads from https://codeload.github.com/<owner>/<repo>/zip/refs/heads/<branch>
and extracts automatically.

The final merged file: `/rules_cache/generated/combined_rules.yaml`.

To bypass GitHub entirely and use the minimal local rules:
```bash
RULES_PATH=/app/rules.yaml ./run.sh
```
