# Q-SHIFT hybrid residual sprint v1 — launch and recovery

## Frozen state

- Production freeze: `FREEZE.json`, SHA-256 `1dbd4e1c58f180b78fb071521d853ef1c408259dd848d8491ba8c066c27d8b8e`.
- Preflight: PASS, bound to that freeze; 384 diagnostic shots were preserved and re-used, not regenerated.
- Production partitions generated: 0. Current runner status: `not_started`.
- Independent-test access: 0.
- Planned production sampling: 1,665,000 unique shots; hard limits remain 3 hours wall time, 2.5 GPU hours, 3 million production shots.

## Run from the user's own PowerShell terminal

The managed Codex execution context did not retain a detached `Start-Process` worker, so the experiment is not running. Run this in a normal PowerShell window. It runs in the foreground and requires no input. Keep the PowerShell window open; it will continue independently of Codex.

```powershell
Set-Location -LiteralPath 'C:\Users\LENOVO\Documents\Codex\2026-11-03\referenced-chatgpt-conversation-this-is-an'
& 'C:\Users\LENOVO\AppData\Local\Programs\Python\Python312\python.exe' 'C:\Users\LENOVO\Documents\Codex\2026-11-03\referenced-chatgpt-conversation-this-is-an\outputs\neural_decoder_diagnostic\hybrid_residual_sprint_v1\run_sprint.py' --run
```

## Check, safely stop, and resume

Open another PowerShell window and run the matching command below.

```powershell
# Status
& 'C:\Users\LENOVO\AppData\Local\Programs\Python\Python312\python.exe' 'C:\Users\LENOVO\Documents\Codex\2026-11-03\referenced-chatgpt-conversation-this-is-an\outputs\neural_decoder_diagnostic\hybrid_residual_sprint_v1\run_sprint.py' --status

# Request a checkpointed safe stop
& 'C:\Users\LENOVO\AppData\Local\Programs\Python\Python312\python.exe' 'C:\Users\LENOVO\Documents\Codex\2026-11-03\referenced-chatgpt-conversation-this-is-an\outputs\neural_decoder_diagnostic\hybrid_residual_sprint_v1\run_sprint.py' --stop

# After status reports paused/failed and the old process has exited, resume
& 'C:\Users\LENOVO\AppData\Local\Programs\Python\Python312\python.exe' 'C:\Users\LENOVO\Documents\Codex\2026-11-03\referenced-chatgpt-conversation-this-is-an\outputs\neural_decoder_diagnostic\hybrid_residual_sprint_v1\run_sprint.py' --resume
```

The safe-stop marker is checked at saved optimizer-batch boundaries. Do not launch `--resume` while the original process is still active. Checkpoints and progress are under `outputs/neural_decoder_diagnostic/hybrid_residual_sprint_v1/run/`.

## Launch attempt record

Two hidden `Start-Process` attempts returned PIDs 27916 and 25344, but neither had a live process, run lock, `PROGRESS.json`, error record, or log output by verification. A read-only hidden `--status` probe worked. No production sample was generated. The managed execution environment gave no OS traceback or explicit denial, so the evidence establishes that the worker did not persist but does not distinguish an immediate interpreter exit from process cleanup by the managed context. No alternative execution mechanism was attempted after that observation.
