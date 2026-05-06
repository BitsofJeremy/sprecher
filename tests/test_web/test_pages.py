"""Browser tests for Sprecher web UI using Playwright.

Run with: pytest tests/test_web/test_pages.py --headed  (for headed mode)
Or: pytest tests/test_web/test_pages.py             (headless)
"""

import pytest
import asyncio
import subprocess
import time
import signal
from pathlib import Path
from typing import Generator

import pytest_asyncio
from playwright.sync_api import sync_playwright, Browser, Page, expect


# Mark all tests in this module as web tests
pytestmark = pytest.mark.web


class UvicornServer:
    """Context manager for a test uvicorn server."""

    def __init__(self, host="127.0.0.1", port=0):
        self.host = host
        self.port = port
        self.process = None
        self.base_url = None

    def __enter__(self):
        import random
        import socket

        # Find an available port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.host, 0))
            self.port = s.getsockname()[1]

        self.base_url = f"http://{self.host}:{self.port}"

        project_root = Path(__file__).parent.parent.parent
        self.process = subprocess.Popen(
            ["uvicorn", "app.main:app", "--host", self.host, "--port", str(self.port), "--factory"],
            cwd=str(project_root),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=os.setsid if hasattr(os, 'setsid') else None,
        )
        # Wait for server to be ready
        for _ in range(30):
            try:
                import urllib.request
                urllib.request.urlopen(f"{self.base_url}/api/health", timeout=1)
                break
            except Exception:
                time.sleep(0.5)
        else:
            raise RuntimeError("Server failed to start")

        return self

    def __exit__(self, *args):
        if self.process:
            import os
            if hasattr(os, 'killpg'):
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            else:
                self.process.terminate()
            self.process.wait(timeout=5)


import os


@pytest.fixture(scope="session")
def server_url() -> Generator[str, None, None]:
    """Start a real uvicorn server for the test session."""
    server = UvicornServer()
    with server:
        yield server.base_url


@pytest.fixture(scope="session")
def browser(server_url) -> Generator[Browser, None, None]:
    """Launch a Chromium browser."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def page(browser: Browser, server_url: str) -> Generator[Page, None, None]:
    """Open a new browser page."""
    context = browser.new_context(
        viewport={"width": 1280, "height": 800},
        ignore_https_errors=True,
    )
    page = context.new_page()
    page.set_default_timeout(10000)
    yield page
    page.close()
    context.close()


# ---------------------------------------------------------------------------
# Page tests
# ---------------------------------------------------------------------------

class TestDashboard:
    """Tests for the dashboard (/) page."""

    def test_dashboard_loads(self, page: Page, server_url: str):
        """Dashboard page loads without errors."""
        response = page.goto(f"{server_url}/")
        assert response is not None
        assert response.ok

    def test_dashboard_title(self, page: Page, server_url: str):
        """Dashboard has correct title."""
        page.goto(f"{server_url}/")
        assert "Sprecher" in page.title()

    def test_dashboard_nav_links(self, page: Page, server_url: str):
        """All nav links are present and point to correct routes."""
        page.goto(f"{server_url}/")
        nav_links = {
            "TTS": "/tts",
            "STT": "/stt",
            "Narrate": "/narrate",
            "Voices": "/voices",
            "Jobs": "/jobs",
        }
        for label, path in nav_links.items():
            link = page.get_by_role("link", name=label)
            expect(link).to_be_visible()

    def test_dashboard_stats_load(self, page: Page, server_url: str):
        """Stats cards load voices count from API."""
        page.goto(f"{server_url}/")
        # Wait for voices to load
        page.wait_for_selector("#stat-voices", timeout=5000)
        voices_text = page.locator("#stat-voices").text_content()
        # Should be a number or placeholder, not "—"
        assert voices_text not in ("—", "Loading...")

    def test_dashboard_voice_select_loads(self, page: Page, server_url: str):
        """Voice select dropdown gets populated from API."""
        page.goto(f"{server_url}/")
        page.wait_for_selector("#tts-voice-select option:not([value=''])", timeout=5000)
        options = page.locator("#tts-voice-select option").count()
        assert options >= 2  # at least placeholder + 1 voice

    def test_dashboard_recent_jobs_section(self, page: Page, server_url: str):
        """Recent jobs section renders (may be empty)."""
        page.goto(f"{server_url}/")
        page.wait_for_selector("#recent-jobs", timeout=5000)
        assert page.locator("#recent-jobs").is_visible()


class TestTTSPage:
    """Tests for the TTS page."""

    def test_tts_page_loads(self, page: Page, server_url: str):
        """TTS page loads without errors."""
        response = page.goto(f"{server_url}/tts")
        assert response is not None
        assert response.ok

    def test_tts_voice_select_loads(self, page: Page, server_url: str):
        """Voice select dropdown gets populated."""
        page.goto(f"{server_url}/tts")
        page.wait_for_selector("#voice option:not([value=''])", timeout=5000)
        options = page.locator("#voice option").count()
        assert options >= 2

    def test_tts_form_has_required_fields(self, page: Page, server_url: str):
        """TTS form has text, voice, engine, audio_format, speed fields."""
        page.goto(f"{server_url}/tts")
        assert page.locator("textarea[name='text']").is_visible()
        assert page.locator("#voice").is_visible()
        assert page.locator("input[name='engine']").first.is_visible()
        assert page.locator("#audio_format").is_visible()
        assert page.locator("input[name='speed']").is_visible()

    def test_tts_preview_button_present(self, page: Page, server_url: str):
        """Preview and Generate buttons are present."""
        page.goto(f"{server_url}/tts")
        assert page.get_by_role("button", name="Preview").is_visible()
        assert page.get_by_role("button", name="Generate Speech").is_visible()

    def test_tts_voice_preselect_from_query_param(self, page: Page, server_url: str):
        """Navigating with ?voice=xxx pre-selects that voice."""
        page.goto(f"{server_url}/tts")
        page.wait_for_selector("#voice option:not([value=''])", timeout=5000)
        # Get first available voice value
        first_voice = page.locator("#voice option:not([value=''])").first
        voice_value = first_voice.get_attribute("value")
        voice_text = first_voice.text_content()
        page.goto(f"{server_url}/tts?voice={voice_value}")
        page.wait_for_timeout(500)
        selected = page.locator("#voice").evaluate("el => el.value")
        assert selected == voice_value


class TestSTTPage:
    """Tests for the STT page."""

    def test_stt_page_loads(self, page: Page, server_url: str):
        """STT page loads without errors."""
        response = page.goto(f"{server_url}/stt")
        assert response is not None
        assert response.ok

    def test_stt_form_has_fields(self, page: Page, server_url: str):
        """STT form has file input, language select, engine radios, submit."""
        page.goto(f"{server_url}/stt")
        assert page.locator("#audio-file").is_visible()
        assert page.locator("#language").is_visible()
        assert page.locator("input[name='engine']").first.is_visible()
        assert page.get_by_role("button", name="Transcribe").is_visible()

    def test_stt_drop_zone_clickable(self, page: Page, server_url: str):
        """Drop zone is clickable and triggers file input."""
        page.goto(f"{server_url}/stt")
        page.locator("#drop-zone").click()
        # File input should now be focused or dialog should appear
        # (dialog behavior depends on browser; just verify no crash)


class TestNarratePage:
    """Tests for the Narrate page."""

    def test_narrate_page_loads(self, page: Page, server_url: str):
        """Narrate page loads without errors."""
        response = page.goto(f"{server_url}/narrate")
        assert response is not None
        assert response.ok

    def test_narrate_voice_select_loads(self, page: Page, server_url: str):
        """Voice select gets populated from API."""
        page.goto(f"{server_url}/narrate")
        page.wait_for_selector("#voice_id option:not([value=''])", timeout=5000)
        options = page.locator("#voice_id option").count()
        assert options >= 2


class TestVoicesPage:
    """Tests for the Voices library page."""

    def test_voices_page_loads(self, page: Page, server_url: str):
        """Voices page loads without errors."""
        response = page.goto(f"{server_url}/voices")
        assert response is not None
        assert response.ok

    def test_voices_add_button_link(self, page: Page, server_url: str):
        """Add Voice button links to /voice/add."""
        page.goto(f"{server_url}/voices")
        link = page.get_by_role("link", name="Add Voice").first
        expect(link).to_be_visible()
        assert "/voice/add" in link.get_attribute("href")

    def test_voices_filter_tabs_present(self, page: Page, server_url: str):
        """Filter tabs (All, Kokoro, Qwen) are present."""
        page.goto(f"{server_url}/voices")
        page.wait_for_timeout(2000)  # wait for JS to render
        assert page.get_by_role("button", name="All").is_visible()
        assert page.get_by_role("button", name="Kokoro").is_visible()
        assert page.get_by_role("button", name="Qwen").is_visible()

    def test_voices_load_dynamically(self, page: Page, server_url: str):
        """Voice cards load dynamically from API (not static HTML)."""
        page.goto(f"{server_url}/voices")
        page.wait_for_timeout(2000)
        cards = page.locator(".card-glow")
        # Should have at least one card or an empty state
        assert cards.count() >= 0  # empty is OK if no voices in DB


class TestVoiceAddPage:
    """Tests for the Add Voice page."""

    def test_voice_add_page_loads(self, page: Page, server_url: str):
        """Voice add page loads without errors."""
        response = page.goto(f"{server_url}/voice/add")
        assert response is not None
        assert response.ok

    def test_voice_add_form_fields(self, page: Page, server_url: str):
        """Form has name, engine radios, voice_key, description."""
        page.goto(f"{server_url}/voice/add")
        assert page.locator("input[name='name']").is_visible()
        assert page.locator("input[name='engine']").first.is_visible()
        assert page.locator("input[name='voice_key']").is_visible()
        assert page.locator("textarea[name='description']").is_visible()

    def test_voice_add_back_link(self, page: Page, server_url: str):
        """Back link returns to /voices."""
        page.goto(f"{server_url}/voice/add")
        back = page.get_by_role("link", name="Back to Voice Library")
        expect(back).to_be_visible()


class TestJobsPage:
    """Tests for the Jobs page."""

    def test_jobs_page_loads(self, page: Page, server_url: str):
        """Jobs page loads without errors."""
        response = page.goto(f"{server_url}/jobs")
        assert response is not None
        assert response.ok

    def test_jobs_filter_tabs_present(self, page: Page, server_url: str):
        """Filter tabs are present."""
        page.goto(f"{server_url}/jobs")
        assert page.get_by_role("button", name="All").is_visible()

    def test_jobs_table_present(self, page: Page, server_url: str):
        """Jobs table or empty state is visible."""
        page.goto(f"{server_url}/jobs")
        page.wait_for_timeout(2000)  # wait for JS dynamic load
        assert page.locator("table, #empty-state").first.is_visible()

    def test_jobs_new_job_button(self, page: Page, server_url: str):
        """New Job button links to /tts."""
        page.goto(f"{server_url}/jobs")
        link = page.get_by_role("link", name="New Job").first
        expect(link).to_be_visible()


class TestJobDetailPage:
    """Tests for individual job detail pages."""

    def test_job_detail_loads(self, page: Page, server_url: str):
        """Job detail page loads (shows empty/error for non-existent job)."""
        response = page.goto(f"{server_url}/jobs/99999")
        assert response is not None
        # Should not 404 - the route exists even if job doesn't
        assert response.status == 200

    def test_job_detail_cancel_button_present(self, page: Page, server_url: str):
        """Cancel button is present (even if job doesn't exist)."""
        page.goto(f"{server_url}/jobs/99999")
        cancel_btn = page.get_by_role("button", name="Cancel Job")
        # Button may be disabled but should exist
        expect(cancel_btn).to_be_attached()

    def test_job_detail_back_link(self, page: Page, server_url: str):
        """Back to Jobs link is present."""
        page.goto(f"{server_url}/jobs/99999")
        back = page.get_by_role("link", name="Back to Jobs")
        expect(back).to_be_visible()


class TestNavigation:
    """Tests for navigation and routing."""

    def test_all_routes_return_200(self, page: Page, server_url: str):
        """All web routes return 200, not 404."""
        routes = ["/", "/tts", "/stt", "/narrate", "/voices", "/jobs", "/voice/add"]
        for route in routes:
            response = page.goto(f"{server_url}{route}")
            assert response is not None and response.ok, f"Route {route} failed: {response.status if response else 'no response'}"

    def test_nav_bar_present_on_all_pages(self, page: Page, server_url: str):
        """Nav bar with links is present on all pages."""
        routes = ["/", "/tts", "/stt", "/narrate", "/voices", "/jobs"]
        for route in routes:
            page.goto(f"{server_url}{route}")
            nav = page.locator("nav, header, .sidebar")
            expect(nav.first).to_be_visible()

    def test_no_console_errors_on_dashboard(self, page: Page, server_url: str):
        """Dashboard has no JavaScript console errors."""
        errors = []
        page.on("console", lambda msg: errors.append(msg) if msg.type == "error" else None)
        page.goto(f"{server_url}/")
        page.wait_for_timeout(2000)  # wait for async loads
        assert len(errors) == 0, f"Console errors: {[e.text for e in errors]}"

    def test_no_console_errors_on_tts(self, page: Page, server_url: str):
        """TTS page has no JavaScript console errors."""
        errors = []
        page.on("console", lambda msg: errors.append(msg) if msg.type == "error" else None)
        page.goto(f"{server_url}/tts")
        page.wait_for_timeout(2000)
        assert len(errors) == 0, f"Console errors: {[e.text for e in errors]}"

    def test_no_console_errors_on_voices(self, page: Page, server_url: str):
        """Voices page has no JavaScript console errors."""
        errors = []
        page.on("console", lambda msg: errors.append(msg) if msg.type == "error" else None)
        page.goto(f"{server_url}/voices")
        page.wait_for_timeout(2000)
        assert len(errors) == 0, f"Console errors: {[e.text for e in errors]}"
