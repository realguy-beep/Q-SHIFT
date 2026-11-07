# Localhost middleware repair

## Root cause

`is_loopback()` had been split by an earlier edit: the IP parsing `try/except` sat after `attach_execution_identity()`'s unconditional `return`. As a result, actual socket addresses such as `127.0.0.1` and `::1` fell through and returned `None`, which the middleware treated as false. TestClient's special `testclient` address was the only accepted path. The original middleware raised `HTTPException` inside the HTTP middleware and did not log request diagnostics.

The rejection was not caused by the `Host` or forwarded headers. The peer IP is now parsed directly; forwarded headers are never consulted for authorization. The old server did not log request metadata, so the precise host/header tuple from the user's failed requests cannot be recovered. The new rejection log records the peer, request hostname, Host, X-Forwarded-For/Proto/Host (each capped and safely repr-formatted), and path.

## Security behavior

- HTTP and WebSocket requests are checked against the socket peer. IPv4, IPv6, and IPv4-mapped loopback are accepted; non-loopback and invalid values are rejected.
- HTTP rejection returns a normal JSON 403 response. WebSocket rejection closes with policy code 1008 before accepting.
- Uvicorn listens on separate `127.0.0.1` and `::1` sockets only.
- Uvicorn proxy-header handling is disabled, and its trusted-forwarder list is empty. Forwarded headers cannot grant or revoke access.

## Verification

- Real Uvicorn test with ephemeral port: GET `/` = 200, GET `/api/health` = 200, safe checkpoint-control request = 200 over both IPv4 and IPv6 loopback.
- In-process WebSocket test over IPv6 receives its snapshot; remote WebSocket closes with 1008.
- Remote HTTP with `X-Forwarded-For: 127.0.0.1` returns JSON 403. A real loopback peer with a spoofed remote X-Forwarded-For remains allowed based on its peer IP.
- Full dashboard suite: 21 tests pass. JavaScript syntax and Python compilation checks pass.
- Existing GPU telemetry tests remain green; `/api/health` reports CUDA from `torch.cuda.is_available()`.

## Restart

From the repository root, stop the old dashboard process and run:

```powershell
python dashboard/run_local.py
```

Then open `http://127.0.0.1:8765` or `http://[::1]:8765`.
