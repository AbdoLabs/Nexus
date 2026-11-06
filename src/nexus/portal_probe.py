"""Read-only discovery of the official appointment portal form.

This probe does not submit personal data, reserve/cancel appointments, solve
CAPTCHAs, or attempt to evade access controls. It records only form structure
and visible page text needed to implement a stable adapter.
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from .config import settings, validate_settings

logger = logging.getLogger(__name__)

CHALLENGE_PATTERNS = (
    "captcha",
    "verify you are human",
    "access denied",
    "too many requests",
    "unusual traffic",
    "actividad inusual",
    "demasiadas solicitudes",
    "verifique que es humano",
)

NO_APPOINTMENT_PATTERNS = (
    "no hay citas disponibles en este momento",
    "no existen citas disponibles",
    "en este momento no hay citas",
)


def classify_visible_text(text: str) -> str:
    """Classify visible portal state without interpreting ambiguous errors as availability."""
    normalized = re.sub(r"\s+", " ", text or "").casefold()
    if any(pattern in normalized for pattern in CHALLENGE_PATTERNS):
        return "manual_intervention_required"
    if any(pattern in normalized for pattern in NO_APPOINTMENT_PATTERNS):
        return "no_appointments_message"
    if "internet cita previa" in normalized or "cita previa" in normalized:
        return "appointment_portal_loaded"
    return "unknown_or_loading"


def _frame_snapshot(frame: Any, index: int) -> dict[str, Any]:
    """Return visible metadata for selects, options, headings and safe form shape."""
    data = frame.evaluate(
        """(frameIndex) => {
          const labelFor = (el) => {
            if (el.labels && el.labels.length) {
              return Array.from(el.labels).map(x => x.innerText.trim()).join(" ");
            }
            if (el.id) {
              const label = document.querySelector('label[for="' + CSS.escape(el.id) + '"]');
              if (label) return label.innerText.trim();
            }
            return el.getAttribute('aria-label') || el.getAttribute('title') || '';
          };
          const visible = (el) => {
            const s = window.getComputedStyle(el);
            const r = el.getBoundingClientRect();
            return s.display !== 'none' && s.visibility !== 'hidden' &&
                   r.width > 0 && r.height > 0;
          };
          return {
            frame_index: frameIndex,
            title: document.title || '',
            url: location.href,
            headings: Array.from(document.querySelectorAll('h1,h2,h3'))
              .filter(visible).map(x => x.innerText.trim()).filter(Boolean).slice(0, 30),
            selects: Array.from(document.querySelectorAll('select')).map((el, i) => ({
              index: i,
              id: el.id || '',
              name: el.name || '',
              label: labelFor(el),
              visible: visible(el),
              disabled: !!el.disabled,
              options: Array.from(el.options).map(o => ({
                value: o.value,
                label: o.label || o.textContent.trim(),
                disabled: !!o.disabled
              })).slice(0, 150)
            })),
            buttons: Array.from(document.querySelectorAll('button,input[type=button],input[type=submit]'))
              .filter(visible).map(el => ({
                text: (el.innerText || el.value || el.getAttribute('aria-label') || '').trim(),
                disabled: !!el.disabled
              })).slice(0, 40),
            iframe_count: document.querySelectorAll('iframe').length,
            input_count: document.querySelectorAll('input').length,
            body_text: (document.body && document.body.innerText || '').slice(0, 6000)
          };
        }""",
        index,
    )
    return data


def build_report() -> dict[str, Any]:
    """Open the official portal once and produce a read-only form inventory."""
    validate_settings()
    report: dict[str, Any] = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "configured_url": settings.portal_url,
        "final_url": None,
        "http_status": None,
        "page_title": None,
        "state": "not_started",
        "frames": [],
        "error": None,
        "safety": {
            "read_only": True,
            "personal_data_submitted": False,
            "appointment_reserved_or_cancelled": False,
            "captcha_or_access_controls_bypassed": False,
        },
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            locale="es-ES",
            timezone_id=settings.timezone,
            viewport={"width": 1440, "height": 1000},
        )
        page = context.new_page()
        try:
            response = page.goto(
                settings.portal_url,
                wait_until="commit",
                timeout=30000,
            )
            report["http_status"] = response.status if response else None
            try:
                page.wait_for_load_state("domcontentloaded", timeout=10000)
            except PlaywrightTimeoutError:
                logger.info("Portal did not become network-idle; continuing with DOM snapshot.")
            page.wait_for_timeout(2000)

            report["final_url"] = page.url
            report["page_title"] = page.title()
            frames = page.frames
            for index, frame in enumerate(frames):
                try:
                    report["frames"].append(_frame_snapshot(frame, index))
                except Exception as exc:  # inaccessible or detached frame
                    report["frames"].append({
                        "frame_index": index,
                        "url": frame.url,
                        "snapshot_error": type(exc).__name__,
                    })

            visible_text = " ".join(
                str(frame.get("body_text", "")) for frame in report["frames"]
            )
            report["state"] = classify_visible_text(visible_text)
            if report["http_status"] and report["http_status"] >= 400:
                report["state"] = "http_error"
            os.makedirs("artifacts", exist_ok=True)
            page.screenshot(path="artifacts/portal_probe.png", full_page=True)
        except Exception as exc:
            report["state"] = "navigation_error"
            report["error"] = f"{type(exc).__name__}: {str(exc)[:500]}"
            try:
                report["final_url"] = page.url
            except Exception:
                pass
        finally:
            context.close()
            browser.close()

    return report


def main() -> int:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    report = build_report()
    os.makedirs("artifacts", exist_ok=True)
    output = Path(os.getenv("PORTAL_PROBE_OUTPUT", "artifacts/portal_probe.json"))
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "state": report["state"],
        "http_status": report["http_status"],
        "final_url": report["final_url"],
        "frames": len(report["frames"]),
        "select_count": sum(
            len(frame.get("selects", []))
            for frame in report["frames"]
        ),
        "report": str(output),
    }, ensure_ascii=False, indent=2))
    return 0 if report["state"] != "navigation_error" else 1


if __name__ == "__main__":
    raise SystemExit(main())
