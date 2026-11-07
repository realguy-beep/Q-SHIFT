# Reproduction and Local Runbook

The active pre-full-run freeze is `FREEZE_FINAL_V3.json`. Do not edit its hashed files. The full run remains unstarted and requires the user's explicit approval.

## Verify the prepared state

From the repository root in PowerShell:

```powershell
$repo = "C:\Users\LENOVO\Documents\Codex\2026-11-03\referenced-chatgpt-conversation-this-is-an"
$python = "C:\Users\LENOVO\AppData\Local\Programs\Python\Python312\python.exe"
$controller = Join-Path $repo "outputs\neural_decoder_diagnostic\autonomous_development\controller.py"
Set-Location $repo
& $python -c "import sys; sys.path.insert(0, 'outputs/neural_decoder_diagnostic/autonomous_development'); from controller import verify_freeze; print(verify_freeze()[0]['status'])"
& $python -m unittest discover -s outputs/neural_decoder_diagnostic/autonomous_development/tests -v
& $python outputs/neural_decoder_diagnostic/autonomous_development/verify_readiness.py
& $python $controller --status
```

The completed clean restart check is preserved in `DRY_RUN_RESUME_VERIFICATION_V4.json`; the full experiment does not need a new dry run. It records exact equality of the repeated sample arrays, selected model-state hash, and final paired predictions after a two-batch forced pause and resume.

## Launch after explicit approval only

Once the user explicitly authorizes the full run, this starts it in a hidden local process so it can continue without the Codex session. It uses the frozen Python environment and writes logs under the run directory:

```powershell
$repo = "C:\Users\LENOVO\Documents\Codex\2026-11-03\referenced-chatgpt-conversation-this-is-an"
$python = "C:\Users\LENOVO\AppData\Local\Programs\Python\Python312\python.exe"
$controller = Join-Path $repo "outputs\neural_decoder_diagnostic\autonomous_development\controller.py"
$runDir = Join-Path $repo "outputs\neural_decoder_diagnostic\autonomous_development\run"
New-Item -ItemType Directory -Force -Path $runDir | Out-Null
Start-Process -FilePath $python `
  -ArgumentList @($controller, "--full-run", "--confirm-full-autonomous") `
  -WorkingDirectory $repo `
  -RedirectStandardOutput (Join-Path $runDir "controller.stdout.log") `
  -RedirectStandardError (Join-Path $runDir "controller.stderr.log") `
  -WindowStyle Hidden -PassThru
```

The controller rejects `--full-run` without `--confirm-full-autonomous`, verifies the active freeze and dry-run proof, and refuses to overwrite an existing run. If it pauses or is interrupted, resume only after the original approval:

```powershell
Start-Process -FilePath $python `
  -ArgumentList @($controller, "--resume", "--confirm-full-autonomous") `
  -WorkingDirectory $repo `
  -RedirectStandardOutput (Join-Path $runDir "controller.stdout.log") `
  -RedirectStandardError (Join-Path $runDir "controller.stderr.log") `
  -WindowStyle Hidden -PassThru
```

## Safe stop and status

Create a stop request; the process saves at the next training-batch checkpoint or deterministic sampling boundary:

```powershell
& $python $controller --stop
```

Inspect progress and resource counters:

```powershell
& $python $controller --status
```

## Outputs after launch

- `run/data/root_XX.npz` and `final_root_XX.npz`: paired Stim detectors, observable labels, and frozen PyMatching predictions, with JSON seed/hash manifests. Final-evaluation arrays are generated after each job's selection is frozen.
- `run/checkpoints/`: alternating verified resumable checkpoints.
- `run/job_results/`, `run/selections/`, and `run/predictions/`: per-root model evidence.
- `run/progress.json`, `run/progress.jsonl`, `run/RUN_MANIFEST.json`: status, progress, and file integrity.
- `run/FINAL_MORNING_REPORT.md`: incremental report. It says `PAUSED`, `FAILED`, or `completed` based on actual execution; it must not be interpreted as confirmatory evidence.

No independent-test output is expected or permitted.
