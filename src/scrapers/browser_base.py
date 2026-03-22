"""Base class for scrapers that use browser-use CLI for JS-rendered pages."""

from __future__ import annotations

import json
import logging
import subprocess
import time

logger = logging.getLogger(__name__)

BROWSER_USE = "browser-use"


class BrowserUseMixin:
    """Mixin providing browser-use CLI integration for scrapers."""

    browser_headed: bool = False
    browser_profile: str | None = None

    def _cmd(self, *args: str, timeout: int = 30) -> subprocess.CompletedProcess:
        """Run a browser-use CLI command."""
        cmd = [BROWSER_USE]
        if self.browser_headed:
            cmd.append("--headed")
        if self.browser_profile:
            cmd.extend(["--profile", self.browser_profile])
        cmd.extend(args)

        logger.debug(f"browser-use: {' '.join(cmd)}")
        return subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )

    def browser_open(self, url: str) -> bool:
        """Navigate to a URL. Returns True on success."""
        result = self._cmd("open", url, timeout=30)
        if result.returncode != 0:
            logger.error(f"browser-use open failed: {result.stderr}")
            return False
        time.sleep(1)  # let page settle
        return True

    def browser_get_html(self, selector: str | None = None) -> str:
        """Get page HTML, optionally for a specific selector."""
        args = ["get", "html"]
        if selector:
            args.extend(["--selector", selector])
        result = self._cmd(*args, timeout=15)
        return result.stdout

    def browser_eval(self, js: str) -> str:
        """Execute JavaScript and return the result."""
        result = self._cmd("eval", js, timeout=15)
        return result.stdout

    def browser_click(self, index: int) -> bool:
        """Click an element by its state index."""
        result = self._cmd("click", str(index), timeout=10)
        return result.returncode == 0

    def browser_scroll_down(self, amount: int = 500) -> None:
        """Scroll down by pixel amount."""
        self._cmd("scroll", "down", "--amount", str(amount), timeout=5)

    def browser_state(self) -> str:
        """Get current page state with clickable element indices."""
        result = self._cmd("state", timeout=10)
        return result.stdout

    def browser_wait_selector(self, selector: str, timeout_ms: int = 10000) -> bool:
        """Wait for a CSS selector to appear."""
        result = self._cmd(
            "wait", "selector", selector,
            "--timeout", str(timeout_ms),
            timeout=timeout_ms // 1000 + 5,
        )
        return result.returncode == 0

    def browser_close(self) -> None:
        """Close the browser session."""
        self._cmd("close", timeout=10)
