# a2a-artifact-audit

**Audit A2A artifact streaming for silent data loss. Dumb math, honest numbers, zero dependencies.**

[![Tests](https://img.shields.io/badge/tests-16%20passed-brightgreen)]() [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)]()

Fourth in the a2a family: [a2a-tax](https://github.com/ZidoCode/a2a-tax) (polling), [a2a-stream-tax](https://github.com/ZidoCode/a2a-stream-tax) (streaming), [a2a-reconnect-tax](https://github.com/ZidoCode/a2a-reconnect-tax) (reconnects), and now the artifacts themselves.

A2A artifacts stream in chunks — `artifact-update` events with `append=true`, a `last_chunk` flag, and artifactIds the client is trusted to track. The hard cases are **open in the spec**:

- Can an artifact be replaced after `last_chunk=true`? ([a2aproject/A2A#1231](https://github.com/a2aproject/A2A/issues/1231) — open)
- `append` to an unknown artifactId is **silently dropped** ([a2a-python#1038](https://github.com/a2aproject/a2a-python/issues/1038))
- No content integrity at all — hash/signature is just a proposal ([A2A#1140](https://github.com/a2aproject/A2A/issues/1140))

So chunks get lost, duplicated, and written after close — invisibly. a2a-artifact-audit replays a recorded stream and reports every violation.

## Install

```bash
pip install a2a-artifact-audit   # or: copy the three .py files
```

## Usage

```bash
$ a2a-artifact-audit report stream.jsonl
a2a-artifact-audit report — 4 artifact(s), 8 finding(s)

  report                 5 chunks       46 tok  closed
  ghost                  1 chunks       10 tok  OPEN (no last_chunk)

  [CRITICAL] event 5: write to 'report' after last_chunk (artifact already closed)
  [WARNING ] event 3: duplicate part delivered to 'report' (~9 tokens re-sent)
  [WARNING ] artifact 'ghost' never closed — missing last_chunk (1 chunk(s) held open)
  [INFO    ] event 1: first chunk of 'report' has append=true — should be a fresh write

  verdict: 1 CRITICAL — chunks silently lost or written after close.
$ echo $?
2
```

## What it catches

| Finding | Severity | The bug class |
|---|---|---|
| Write after `last_chunk` | **CRITICAL** | artifact already closed — content corruption ([A2A#1231](https://github.com/a2aproject/A2A/issues/1231)) |
| Duplicate part delivered | WARNING | same part appended twice — wasted tokens, doubled content |
| Artifact never closed | WARNING | missing `last_chunk` — client waits forever |
| First chunk has `append=true` | INFO | protocol hygiene — servers drop appends to unknown ids ([a2a-python#1038](https://github.com/a2aproject/a2a-python/issues/1038)) |
| Wholesale replacement | INFO | earlier chunks discarded — intentional? |

CI mode: `audit` exits non-zero on any CRITICAL. `--json`-free, plain text, one finding per line.

## Stream format

One JSON event per line (same as [a2a-stream-tax](https://github.com/ZidoCode/a2a-stream-tax)):

```
{"jsonrpc":"2.0","id":1,"result":{"kind":"artifact-update","taskId":"t1","append":true,"last_chunk":false,"artifact":{"artifactId":"report","parts":[...]}}}
```

Capture: record your client's `message/stream` session to JSONL, then audit it.

## Honest numbers

Deterministic replay — same stream, same findings, byte for byte. Token counts are `chars/4` estimates used only for the "re-sent" size annotations. MIT license.
