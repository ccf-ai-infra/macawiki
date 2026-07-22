---
{
  "id": "doc-pytorch-operator-reference",
  "title": "PyTorch stable operator reference for evaluation baselines",
  "type": "source-doc",
  "status": "reviewed",
  "summary": "PyTorch stable API pages provide the reference semantics for add, softmax, LayerNorm, and matmul used by Macawiki's future cross-backend evaluation.",
  "languages": ["en"],
  "tags": ["documentation", "operator-evaluation", "correctness", "benchmark"],
  "hardware": ["unspecified"],
  "mxmaca_versions": ["unspecified"],
  "components": ["pytorch", "mctilelang", "mxmaca-cpp"],
  "sources": [],
  "related": ["evaluation-compare-operator-backends"],
  "verified_at": "2026-07-22",
  "url": "https://docs.pytorch.org/docs/stable/torch.html",
  "source_category": "official-doc",
  "retrieved_at": "2026-07-22",
  "license_status": "source-terms",
  "aliases": ["PyTorch operators", "torch.add", "torch.softmax", "torch.matmul"]
}
---

# Source summary

The PyTorch stable documentation defines the public reference operators used in the evaluation fixture:

- [`torch.add`](https://docs.pytorch.org/docs/stable/generated/torch.add.html)
- [`torch.softmax`](https://docs.pytorch.org/docs/stable/generated/torch.softmax.html)
- [`torch.nn.LayerNorm`](https://docs.pytorch.org/docs/stable/generated/torch.nn.LayerNorm.html)
- [`torch.matmul`](https://docs.pytorch.org/docs/stable/generated/torch.matmul.html)

This source record preserves links and the intended semantic role. It does not claim that PyTorch behavior, device APIs, or performance transfer unchanged to MXMACA.
