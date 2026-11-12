"""FastAPI integration kept separate from the existing batch-run endpoints."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, Literal

import stim
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .engine import InteractiveDemoEngine, InvalidTransition
from .serial_protocol import SerialCommandProcessor


class InjectRequest(BaseModel):
    data_index: int = Field(default=4, ge=0, le=8, strict=True)
    pauli: Literal["X", "Y", "Z"] = "X"


def create_interactive_integration(
    circuit_factory: Callable[[float], stim.Circuit],
    decoder_factory: Callable[[float], object],
) -> tuple[APIRouter, InteractiveDemoEngine, SerialCommandProcessor]:
    """Build the isolated routes, deterministic engine, and serial protocol."""
    root = Path(__file__).resolve().parent
    page_path = (root / "index.html").resolve()
    if not page_path.is_relative_to(root.resolve()) or not page_path.is_file():
        raise RuntimeError("Interactive demo page escaped its exhibition-only package")

    engine = InteractiveDemoEngine(circuit_factory, decoder_factory)
    serial_processor = SerialCommandProcessor(
        engine,
        default_data_index=4,
        default_pauli="X",
        clock=time.monotonic,
    )
    router = APIRouter()

    def add_transport(result: dict, request: Request) -> dict:
        bridge = getattr(request.app.state, "interactive_serial_bridge", None)
        if bridge is None:
            result["transport"] = "desktop_mock_no_esp32_connected"
        else:
            result["transport"] = "usb_serial_connected" if bridge.connected else "usb_serial_disconnected"
        return result

    @router.get("/interactive")
    def interactive_page() -> FileResponse:
        return FileResponse(page_path, media_type="text/html")

    @router.get("/api/interactive/state")
    def interactive_state(request: Request) -> dict:
        return add_transport(engine.snapshot(), request)

    @router.post("/api/interactive/inject")
    def interactive_inject(request: InjectRequest, http_request: Request) -> dict:
        try:
            result = engine.inject_and_prepare_syndrome(request.data_index, request.pauli)
            return add_transport(result, http_request)
        except InvalidTransition as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.post("/api/interactive/decode")
    def interactive_decode(request: Request) -> dict:
        try:
            result = engine.decode()
            return add_transport(result, request)
        except InvalidTransition as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @router.post("/api/interactive/reset")
    def interactive_reset(request: Request) -> dict:
        result = engine.reset()
        return add_transport(result, request)

    return router, engine, serial_processor
