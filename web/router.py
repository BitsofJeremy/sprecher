# /// script
# dependencies = [
#   "fastapi>=0.115.0",
#   "uvicorn[standard]>=0.34.0",
#   "jinja2>=3.1.4",
#   "aiosqlite>=0.20.0",
#   "python-multipart>=0.0.20",
# ]
# requires-python = ">=3.10"
# ///

"""
Sprecher - Unified TTS/STT Service

Theme: "Build for bots" — AI agents use REST API, humans use beautiful web UI.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

web_router = APIRouter(prefix="", tags=["web"])
templates = Jinja2Templates(directory="web/templates")


@web_router.get("/")
async def dashboard_page(request: Request) -> HTMLResponse:
    """Home dashboard with stats and quick actions."""
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"page_title": "Sprecher - Unified Voice Synthesis"},
    )


@web_router.get("/tts")
async def tts_page(request: Request) -> HTMLResponse:
    """Quick TTS generation page."""
    return templates.TemplateResponse(
        request=request,
        name="tts.html",
        context={"page_title": "Text-to-Speech - Sprecher"},
    )


@web_router.get("/stt")
async def stt_page(request: Request) -> HTMLResponse:
    """Speech-to-text transcription page."""
    return templates.TemplateResponse(
        request=request,
        name="stt.html",
        context={"page_title": "Speech-to-Text - Sprecher"},
    )


@web_router.get("/voices")
async def voices_page(request: Request) -> HTMLResponse:
    """Voice library page."""
    return templates.TemplateResponse(
        request=request,
        name="voices.html",
        context={"page_title": "Voice Library - Sprecher"},
    )


@web_router.get("/jobs")
async def jobs_page(request: Request) -> HTMLResponse:
    """Job list page."""
    return templates.TemplateResponse(
        request=request,
        name="jobs.html",
        context={"page_title": "Jobs - Sprecher"},
    )


@web_router.get("/jobs/{job_id}")
async def job_detail_page(request: Request, job_id: str) -> HTMLResponse:
    """Job detail page with progress tracking."""
    return templates.TemplateResponse(
        request=request,
        name="job_detail.html",
        context={"page_title": f"Job {job_id} - Sprecher", "job_id": job_id},
    )


@web_router.get("/narrate")
async def narrate_page(request: Request) -> HTMLResponse:
    """Document narration page."""
    return templates.TemplateResponse(
        request=request,
        name="narrate.html",
        context={"page_title": "Document Narration - Sprecher"},
    )


@web_router.get("/voice/add")
async def voice_add_page(request: Request) -> HTMLResponse:
    """Add new voice page."""
    return templates.TemplateResponse(
        request=request,
        name="voice_add.html",
        context={"page_title": "Add Voice - Sprecher"},
    )


@web_router.post("/voice/add")
async def voice_add_submit(request: Request) -> HTMLResponse:
    """Handle voice add form submission via HTMX."""
    from fastapi.responses import RedirectResponse
    import httpx
    
    form_data = await request.form()
    
    # POST to API endpoint
    async with httpx.AsyncClient() as client:
        try:
            api_response = await client.post(
                f"{request.base_url}api/voices",
                data=form_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if api_response.status_code in (200, 201):
                return RedirectResponse(url="/voices", status_code=303)
        except Exception:
            pass
    
    return templates.TemplateResponse(
        request=request,
        name="voice_add.html",
        context={
            "page_title": "Add Voice - Sprecher",
            "error": "Failed to create voice. Please try again.",
        },
    )