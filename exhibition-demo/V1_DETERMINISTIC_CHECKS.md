# Exhibition Demo V1 — deterministic checks

## Environment and commands

- Windows 11 environment, Python 3.12.10, Node.js 24.19.0.
- Reused the already installed demo virtual-environment interpreter from the
  pre-existing checkout. No packages were installed or upgraded.
- Frontend syntax:
  `node -e "const fs=require('fs'); const h=fs.readFileSync('index.html','utf8'); const a=h.indexOf('<script>')+8,b=h.lastIndexOf('</script>'); new Function(h.slice(a,b)); console.log('PASS frontend syntax')"`
- Deterministic API/decoder checks:
  `python -m pytest -q tests/test_deterministic_exhibition.py`

## Results

- Frontend JavaScript syntax: **PASS**.
- Deterministic tests: **4 passed**, with one existing Starlette/httpx
  deprecation warning.
- The fixed fixture uses one detector-bearing mechanism in the decomposed,
  approximate DEM at burst setting 0.008. It reported support `[0]`, mechanism
  observable parity `0`, PyMatching prediction `0`, and agreement for that
  fixture. The endpoint was called repeatedly and returned identical data.
- A deterministic spy-decoder test verifies that fixed, adaptive, and
  privileged arms receive identical detector rows, input arrays are unchanged,
  and paired error counts are computed as expected.

## Scope of verification

No detector sampler, random-number generator, live `/api/run` request, or
research experiment was run while preparing this branch. The deterministic
fixture constructs a Stim circuit and approximate DEM, then decodes a fixed
mechanism syndrome. The historical full test record in `TEST_RESULTS.md`
describes earlier live demo runs; it is preserved and is not a result of this
work.

The complete legacy pytest suite was not run because it deliberately samples
Stim shots. The COM preference and LED preview were validated by code review,
not by connecting hardware. No screenshot was captured in this pass.
