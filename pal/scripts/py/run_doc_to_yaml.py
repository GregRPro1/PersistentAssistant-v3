#!/usr/bin/env python3
import sys, json
from pathlib import Path
from pal.pipelines.doc_to_yaml import doc_to_yaml

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: run_doc_to_yaml.py <doc.txt> [provider]", file=sys.stderr); sys.exit(2)
    doc = Path(sys.argv[1])
    provider = sys.argv[2] if len(sys.argv) > 2 else "openai"
    out = doc_to_yaml(doc, provider=provider)
    print(json.dumps(out, indent=2, ensure_ascii=False))
