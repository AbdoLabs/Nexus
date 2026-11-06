"""Read-only ICP+ form inspection with a province-only transition.

The script fetches the public appointment form, keeps its session cookies and
hidden form fields in memory, and submits only the Madrid province selection.
It does not submit identity data, select an office, choose an appointment slot,
or create/cancel a reservation. Session identifiers and hidden field values
are deliberately excluded from all saved reports.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests


PORTAL_URL = "https://ssweb.seap.minhap.es/icpplus/citar?locale=es"


class FormInspector(HTMLParser):
    """Extract safe form metadata while keeping hidden values private in memory."""

    def __init__(self) -> None:
        super().__init__()
        self.forms: list[dict[str, Any]] = []
        self.selects: list[dict[str, Any]] = []
        self.inputs: list[dict[str, str]] = []
        self.buttons: list[dict[str, str]] = []
        self.scripts: list[str] = []
        self.hidden_fields_by_form: dict[str, list[tuple[str, str]]] = {}
        self.text_parts: list[str] = []
        self._current_form: dict[str, Any] | None = None
        self._current_select: dict[str, Any] | None = None
        self._current_option: dict[str, Any] | None = None
        self._current_button: dict[str, str] | None = None
        self._skip_text = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key: (value or "") for key, value in attrs}

        if tag in {"script", "style"}:
            self._skip_text = True

        if tag == "form":
            self._current_form = {
                "id": attributes.get("id", ""),
                "name": attributes.get("name", ""),
                "method": attributes.get("method", "get").upper(),
                "action": attributes.get("action", ""),
            }
            self.forms.append(self._current_form)
        elif tag == "select":
            self._current_select = {
                "id": attributes.get("id", ""),
                "name": attributes.get("name", ""),
                "class": attributes.get("class", ""),
                "aria_label": attributes.get("aria-label", ""),
                "disabled": "disabled" in attributes,
                "options": [],
            }
            self.selects.append(self._current_select)
        elif tag == "option" and self._current_select is not None:
            self._current_option = {
                "value": attributes.get("value", ""),
                "label": "",
                "disabled": "disabled" in attributes,
            }
            self._current_select["options"].append(self._current_option)
        elif tag == "input":
            input_type = attributes.get("type", "text").lower()
            input_name = attributes.get("name", "")
            if input_type == "hidden" and input_name and self._current_form:
                form_name = self._current_form.get("name", "")
                self.hidden_fields_by_form.setdefault(form_name, []).append(
                    (input_name, attributes.get("value", ""))
                )
            self.inputs.append({
                "id": attributes.get("id", ""),
                "name": input_name,
                "type": input_type,
                "placeholder": attributes.get("placeholder", ""),
            })
            if input_type in {"submit", "button"}:
                self.buttons.append({
                    "type": input_type,
                    "name": input_name,
                    "label": attributes.get("value", ""),
                })
        elif tag == "button":
            self._current_button = {
                "type": attributes.get("type", "submit"),
                "name": attributes.get("name", ""),
                "label": "",
            }
        elif tag == "script" and attributes.get("src"):
            self.scripts.append(attributes["src"])

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"}:
            self._skip_text = False
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
        if not self._skip_text:
            self.text_parts.append(value)
        if self._current_option is not None:
            self._current_option["label"] = (
                self._current_option["label"] + " " + value
            ).strip()
        if self._current_button is not None:
            self._current_button["label"] = (
                self._current_button["label"] + " " + value
            ).strip()


def _safe_url(url: str) -> str:
    """Remove path-based session identifiers before a URL enters the report."""
    return re.sub(r";jsessionid=[^?]+", "", url or "")


def _parse_response(response: requests.Response) -> tuple[FormInspector, str]:
    parser = FormInspector()
    parser.feed(response.text[:2_000_000])
    title_match = re.search(r"<title[^>]*>(.*?)</title>", response.text, re.I | re.S)
    title = re.sub(r"\s+", " ", title_match.group(1)).strip() if title_match else ""
    return parser, title


def _safe_selects(parser: FormInspector) -> list[dict[str, Any]]:
    """Return only public option labels/values and control metadata."""
    return [
        {
            "id": item["id"],
            "name": item["name"],
            "class": item["class"],
            "aria_label": item["aria_label"],
            "disabled": item["disabled"],
            "options": item["options"],
        }
        for item in parser.selects
    ]


def inspect_portal() -> dict[str, Any]:
    report: dict[str, Any] = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "portal_url": PORTAL_URL,
        "initial_http_status": None,
        "initial_final_url": None,
        "initial_page_title": None,
        "initial_selects": [],
        "initial_buttons": [],
        "initial_forms": [],
        "javascript_probe": [],
        "province_step": {
            "madrid_found": False,
            "madrid_value": None,
            "form_found": False,
            "submitted": False,
            "http_status": None,
            "final_url": None,
            "page_title": None,
            "selects": [],
            "buttons": [],
            "visible_text_excerpt": "",
            "error": None,
        },
        "privacy": {
            "province_selection_submitted": False,
            "personal_data_submitted": False,
            "office_selected": False,
            "appointment_slot_selected": False,
            "appointment_reserved_or_cancelled": False,
            "hidden_values_saved": False,
            "cookies_or_session_tokens_saved": False,
        },
        "error": None,
    }

    session = requests.Session()
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.6",
    }

    try:
        first = session.get(
            PORTAL_URL,
            headers=headers,
            timeout=(8, 20),
            allow_redirects=True,
        )
        report["initial_http_status"] = first.status_code
        report["initial_final_url"] = _safe_url(first.url)
        parser, title = _parse_response(first)
        report["initial_page_title"] = title
        report["initial_selects"] = _safe_selects(parser)
        report["initial_buttons"] = parser.buttons
        report["initial_forms"] = [
            {
                "id": item.get("id", ""),
                "name": item.get("name", ""),
                "method": item.get("method", ""),
                "action": _safe_url(urljoin(first.url, item.get("action", ""))),
                "hidden_field_count": len(
                    parser.hidden_fields_by_form.get(
                        item.get("name") or item.get("id"), []
                    )
                ),
                "hidden_field_names": [
                    name for name, _ in parser.hidden_fields_by_form.get(
                        item.get("name") or item.get("id"), []
                    )
                ],
            }
            for item in parser.forms
        ]

        # Fetch the public page script with the same HTTP session. Its raw URL
        # may contain a session path parameter; never include that in reports.
        for script_src in parser.scripts:
            if "portada_pt.min.js" not in script_src:
                continue
            script_url = urljoin(first.url, script_src)
            try:
                js_response = session.get(
                    script_url,
                    headers=headers,
                    timeout=(8, 35),
                    stream=True,
                )
                chunks = []
                total = 0
                for chunk in js_response.iter_content(chunk_size=16384):
                    if not chunk:
                        continue
                    chunks.append(chunk)
                    total += len(chunk)
                    if total >= 1_500_000:
                        break
                js = b"".join(chunks).decode(
                    js_response.encoding or "utf-8", errors="replace"
                )
                snippets = []
                for term in (
                    "btnAceptar", "portadaForm", "provincia", "subtramite",
                    "alert_captcha", "method", "acInfo",
                ):
                    matches = list(re.finditer(re.escape(term), js, re.I))[:4]
                    for match in matches:
                        snippets.append({
                            "term": term,
                            "context": js[max(0, match.start()-350):match.end()+650],
                        })
                report["javascript_probe"].append({
                    "script": _safe_url(script_url),
                    "status_code": js_response.status_code,
                    "bytes_read": total,
                    "snippets": snippets,
                    "error": None,
                })
            except requests.RequestException as exc:
                report["javascript_probe"].append({
                    "script": _safe_url(script_url),
                    "error": f"{type(exc).__name__}: {str(exc)[:250]}",
                })
            break

        province_control = next(
            (item for item in parser.selects if item["name"] == "provincia"),
            None,
        )
        madrid = None
        if province_control:
            madrid = next(
                (
                    option for option in province_control["options"]
                    if option["label"].strip().casefold() == "madrid"
                    and not option["disabled"]
                ),
                None,
            )

        form = next(
            (
                item for item in parser.forms
                if item["name"] == "portadaForm"
                or item["id"] == "portadaForm"
            ),
            None,
        )
        report["province_step"]["madrid_found"] = madrid is not None
        report["province_step"]["madrid_value"] = madrid["value"] if madrid else None
        report["province_step"]["form_found"] = form is not None

        if not first.ok:
            report["province_step"]["error"] = (
                f"Initial page returned HTTP {first.status_code}."
            )
        elif not madrid:
            report["province_step"]["error"] = (
                "Madrid was not found in the province selector."
            )
        elif not form:
            report["province_step"]["error"] = (
                "The initial appointment form was not found."
            )
        else:
            form_name = form.get("name") or form.get("id")
            hidden_fields = list(
                parser.hidden_fields_by_form.get(form_name, [])
            )
            # This transition sends Madrid only. Hidden anti-CSRF/session fields
            # stay inside this request and are never copied into the report.
            payload = hidden_fields + [("provincia", madrid["value"])]
            action = urljoin(first.url, form.get("action") or first.url)
            next_response = session.post(
                action,
                data=payload,
                headers={**headers, "Referer": first.url},
                timeout=(8, 25),
                allow_redirects=True,
            )
            next_parser, next_title = _parse_response(next_response)
            report["province_step"].update({
                "submitted": True,
                "http_status": next_response.status_code,
                "final_url": _safe_url(next_response.url),
                "page_title": next_title,
                "selects": _safe_selects(next_parser),
                "buttons": next_parser.buttons,
                "visible_text_excerpt": " ".join(next_parser.text_parts)[:2500],
            })
            report["privacy"]["province_selection_submitted"] = True

    except requests.RequestException as exc:
        report["error"] = f"{type(exc).__name__}: {str(exc)[:400]}"

    return report


def main() -> int:
    report = inspect_portal()
    Path("artifacts").mkdir(exist_ok=True)
    Path("artifacts/portal_http_inspection.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
