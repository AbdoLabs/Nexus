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
        self.hidden_fields: list[tuple[str, str]] = []
        self.buttons: list[dict[str, str]] =
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
            if a.get("type", "").lower() == "hidden" and a.get("name"):
                self.hidden_fields.append((a.get("name", ""), a.get("value", "")))
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


def _parse_response(response: requests.Response) -> tuple[FormInspector, str]:
    parser = FormInspector()
    parser.feed(response.text[:2_000_000])
    title = re.search(r"<title[^>]*>(.*?)</title>", response.text, re.I | re.S)
    page_title = re.sub(r"\\s+", " ", title.group(1)).strip() if title else ""
    return parser, page_title


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
        session = requests.Session()
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.6",
        }
        response = session.get(
            PORTAL_URL,
            timeout=(8, 20),
            allow_redirects=True,
            headers=headers,
        )
        result["status_code"] = response.status_code
        result["final_url"] = response.url
        parser, page_title = _parse_response(response)
        result["title"] = page_title
        # Preserve session-only hidden fields in memory to submit the same
        # province form as a normal user; none of these values are logged.
        province_select = next(
            (s for s in parser.selects if s["name"] == "provincia"), None
        )
        madrid_option = None
        if province_select:
            madrid_option = next(
                (o for o in province_select["options"]
                 if o["label"].strip().casefold() == "madrid"),
                None,
            )
        form = next(
            (item for item in parser.forms if item["name"] == "portadaForm"),
            parser.forms[0] if parser.forms else None,
        )
        result["province_step"] = {
            "madrid_found": bool(madrid_option),
            "madrid_value": madrid_option["value"] if madrid_option else None,
            "form_found": bool(form),
            "submitted": False,
            "stage": "not_submitted",
        }
        if response.ok and madrid_option and form:
            action = urljoin(response.url, form.get("action") or response.url)
            fields = list(parser.hidden_fields)
            fields.append(("provincia", madrid_option["value"]))
            # This is only the province-selection step; no identity data,
            # office, appointment slot, or reservation details are sent.
            next_response = session.post(
                action,
                data=fields,
                headers={**headers, "Referer": response.url},
                timeout=(8, 25),
                allow_redirects=True,
            )
            next_parser, next_title = _parse_response(next_response)
            result["province_step"].update({
                "submitted": True,
                "http_status": next_response.status_code,
                "final_url": re.sub(
                    r";jsessionid=[^?]+", "", next_response.url
                ),
                "page_title": next_title,
                "stage": "province_post_response",
                "selects": next_parser.selects,
                "forms": [
                    {**item, "action": re.sub(
                        r";jsessionid=[^?]+", "", item.get("action", "")
                    )}
                    for item in next_parser.forms
                ],
                "buttons": next_parser.buttons,
                "message_excerpt": re.sub(
                    r"\\s+", " ", next_response.text
                )[:2500],
            })
        result["forms"] = [
            {**item, "action": re.sub(
                r";jsessionid=[^?]+", "", item.get("action", "")
            )}
            for item in parser.forms
        ]
        result["selects"] = parser.selects
        result["inputs"] = parser.inputs
        result["buttons"] = parser.buttons
        # Sanitize per-session JSESSIONID values before writing diagnostics.
        for form in parser.forms:
            form["action"] = re.sub(r";jsessionid=[^?]+", "", form["action"])
        result["external_scripts"] = [
            re.sub(r";jsessionid=[^?]+", "", urljoin(response.url, src))
            for src in parser.scripts[:30]
        ]
        # Inspect only the public scripts that wire the initial form controls.
        for script_url in result["external_scripts"]:
            if not any(name in script_url for name in ("portada_pt.min.js", "icp-7.37.min.js")):
                continue
            try:
                js_response = requests.get(script_url, timeout=(5, 12))
                js = js_response.text[:2_000_000]
                snippets = []
                for term in ("btnAceptar", "portadaForm", "provincia", "subtramite", "acInfo"):
                    match = re.search(re.escape(term), js, re.IGNORECASE)
                    if match:
                        snippets.append({
                            "term": term,
                            "context": js[max(0, match.start()-250):match.end()+500],
                        })
                result["script_inspection"].append({
                    "script": script_url,
                    "status_code": js_response.status_code,
                    "length": len(js),
                    "snippets": snippets,
                })
            except requests.RequestException as exc:
                result["script_inspection"].append({
                    "script": script_url,
                    "error": f"{type(exc).__name__}: {str(exc)[:300]}",
                })
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
        "province_step": {
            "madrid_found": report.get("province_step", {}).get("madrid_found"),
            "submitted": report.get("province_step", {}).get("submitted"),
            "stage": report.get("province_step", {}).get("stage"),
            "http_status": report.get("province_step", {}).get("http_status"),
            "page_title": report.get("province_step", {}).get("page_title"),
            "selects": report.get("province_step", {}).get("selects", []),
            "buttons": report.get("province_step", {}).get("buttons", []),
            "message_excerpt": report.get("province_step", {}).get("message_excerpt", ""),
        },
        "script_inspection": report["script_inspection"],
        "error": report["error"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
