"""FastAPI server for the equity-research War Room app."""

import json

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from agents import STAGES, run_stage

app = FastAPI(title="Equity Research War Room")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def index():
    return FileResponse("static/index.html")


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


@app.get("/api/run")
def run(company: str = Query(..., min_length=1)):
    def event_stream():
        case_file = ""
        try:
            for stage in STAGES:
                yield _sse({"type": "stage_start", "stage": stage.id, "title": stage.title})
                full_text = ""
                for ev in run_stage(stage, company, case_file):
                    if ev["type"] == "delta":
                        full_text += ev["text"]
                        yield _sse({"type": "delta", "stage": stage.id, "text": ev["text"]})
                    elif ev["type"] == "search":
                        yield _sse({"type": "search", "stage": stage.id})
                case_file += f"## {stage.title}\n\n{full_text}\n\n"
                yield _sse({"type": "stage_end", "stage": stage.id})
            yield _sse({"type": "done"})
        except Exception as exc:  # surface errors to the UI instead of a silent drop
            yield _sse({"type": "error", "message": str(exc)})

    return StreamingResponse(event_stream(), media_type="text/event-stream")
