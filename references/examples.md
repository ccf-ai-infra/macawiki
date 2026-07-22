# Query examples

## Find a diagnostic method

```bash
python3 scripts/query.py "利用率 诊断" --type wiki-pattern --compact
```

## Filter by environment

```bash
python3 scripts/query.py --hardware c500 --version unspecified --component mcprofiler
```

## Trace an answer to evidence

```bash
python3 scripts/get_page.py pattern-establish-performance-baseline --follow-sources
```

## Search exact text or symbols

```bash
python3 scripts/grep_wiki.py "roofline|kWarpSize"
```
