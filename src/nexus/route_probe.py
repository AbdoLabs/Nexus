"""Inspect ICP+ form structure through read-only HTTP requests.

This module avoids browser automation and never submits the form. It records
field names, labels and non-personal select options only; input values,
cookies, authorization tokens and hidden field values are deliberately omitted.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import requests
from urllib.parse import urljoin


class FormInspector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.forms: list[dict[str, Any]] = []
        self.selects: list[dict[str, Any]] = []
        self.inputs: list[dict[str, str]] = []
        self.buttons: list[dict[str, str]] = []
        self.scripts: list[str] = []
        self._current_form: dict[str, Any] | None = None
        self._current_select: dict[str, Any] | None = None
        self._current_option: dict[str, str] | None = None
        self._current_button: dict[str, str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: (v or "") for k, v in attrs}
        if tag == "form":
            self._current_form = {
                "id": a.get("id", ""),
                "name": a.get("name", ""),
                "method": a.get("method", "get").upper(),
                "action": a.get("action", ""),
            }
            self.forms.append(self._current_form)
        elif tag == "select":
            self._current_select = {
                "id": a.get("id", ""),
                "name": a.get("name", ""),
                "class": a.get("class", ""),
                "aria_label": a.get("aria-label", ""),
                "disabled": "disabled" in a,
                "options": [],
            }
            self.selects.append(self._current_select)
        elif tag == "option" and self._current_select is not None:
            self._current_option = {
                "value": a.get("value", ""),
                "label": "",
                "disabled": "disabled" in a,
            }
            self._current_select["options"].append(self._current_option)
        elif tag == "input":
            self.inputs.append({
                "id": a.get("id", ""),
                "name": a.get("name", ""),
                "type": a.get("type", "text"),
                "placeholder": a.get("placeholder", ""),
            })
            if a.get("type", "").lower() in {"submit", "button"}:
                self.buttons.append({
                    "type": a.get("type", ""),
                    "name": a.get("name", ""),
                    "label": a.get("value", ""),
                })
        elif tag == "button":
            self._current_button = {
                "type": a.get("type", "submit"),
                "name": a.get("name", ""),
                "label": "",
            }
        elif tag == "script" and a.get("src"):
            self.scripts.append(a["src"])

    def handle_endtag(self, tag: str) -> None:
        if tag == "option":
            self._current_option = None
        elif tag == "select":
            self._current_select = None
        elif tag == "button":
            if self._current_button is not None:
                self.buttons.append(self._current_button)
            self._current_button = None
        elif tag == "form":
            self._current_form = None

    def handle_data(self, data: str) -> None:
        value = data.strip()
        if not value:
            return
        if self._current_option is not None:
            self._current_option["label"] = (
                self._current_option["label"] + " " + value
            ).strip()
        if self._current_button is not None:
            self._current_button["label"] = (
                self._current_button["label"] + " " + value
            ).strip()


PORTAL_URL = "https://ssweb.seap.minhap.es/icpplus/citar?locale=es"


def inspect_portal() -> dict[str, Any]:
    result: dict[str, Any] = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "url": PORTAL_URL,
        "status_code": None,
        "final_url": None,
        "title": None,
        "forms": [],
        "selects": [],
        "inputs": [],
        "buttons": [],
        "external_scripts": [],
        "script_inspection": [],
        "markers": [],
        "error": None,
        "privacy": {
            "form_not_submitted": True,
            "input_values_omitted": True,
            "cookies_and_tokens_omitted": True,
        },
    }
    try:
        response = requests.get(
            PORTAL_URL,
            timeout=(8, 20),
            allow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "es-ES,es;q=0.9,en;q=0.6",
            },
        )
        result["status_code"] = response.status_code
        result["final_url"] = response.url
        parser = FormInspector()
        parser.feed(response.text[:2_000_000])
        result["forms"] = parser.forms
        result["selects"] = parser.selects
        result["inputs"] = parser.inputs
        result["buttons"] = parser.buttons
        result["external_scripts"] = [
            urljoin(response.url, src) for src in parser.scripts[:30]
        ]
        text = re.sub(r"\s+", " ", " ".join(
            part for part in response.text.split("<") if part
        ))
        markers = (
            "INTERNET CITA PREVIA",
            "PROVINCIAS DISPONIBLES",
            "TRÁMITES CUERPO NACIONAL DE POLICÍA",
            "TOMA DE HUELLA",
            "CUALQUIER OFICINA",
        )
        lowered = response.text.casefold()
        result["markers"] = [m for m in markers if m.casefold() in lowered]
        title = re.search(r"<title[^>]*>(.*?)</title>", response.text, re.I | re.S)
        result["title"] = re.sub(r"\s+", " ", title.group(1)).strip() if title else None
    except requests.RequestException as exc:
        result["error"] = f"{type(exc).__name__}: {str(exc)[:400]}"
    return result


def main() -> int:
    report = inspect_portal()
    Path("artifacts").mkdir(exist_ok=True)
    Path("artifacts/portal_http_inspection.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({
        "status_code": report["status_code"],
        "final_url": report["final_url"],
        "title": report["title"],
        "markers": report["markers"],
        "selects": [
            {
                "id": s["id"],
                "name": s["name"],
                "aria_label": s["aria_label"],
                "option_count": len(s["options"]),
                "options_preview": s["options"][:35],
            }
            for s in report["selects"]
        ],
        "buttons": report["buttons"],
        "script_inspection": report["script_inspection"],
        "error": report["error"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
