"""Read-only discovery of official ICP+ entry points.

Only HTTP GET requests are made. This probe records public page titles,
form metadata, select option labels and visible text. It never submits forms,
reads hidden field values, or stores cookies/session identifiers.
"""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import requests


class ReadOnlyPageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.forms: list[dict[str, str]] = []
        self.selects: list[dict[str, Any]] = []
        self.buttons: list[dict[str, str]] = []
        self.text_parts: list[str] = []
        self._form: dict[str, str] | None = None
        self._select: dict[str, Any] | None = None
        self._option: dict[str, Any] | None = None
        self._button: dict[str, str] | None = None
        self._skip_text = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {key: value or "" for key, value in attrs}
        if tag in {"script", "style"}:
            self._skip_text = True
        if tag == "form":
            self._form = {
                "id": a.get("id", ""),
                "name": a.get("name", ""),
                "method": a.get("method", "get").upper(),
                "action": a.get("action", ""),
            }
            self.forms.append(self._form)
        elif tag == "select":
            self._select = {
                "id": a.get("id", ""),
                "name": a.get("name", ""),
                "aria_label": a.get("aria-label", ""),
                "disabled": "disabled" in a,
                "options": [],
            }
            self.selects.append(self._select)
        elif tag == "option" and self._select is not None:
            self._option = {
                "value": a.get("value", ""),
                "label": "",
                "disabled": "disabled" in a,
            }
            self._select["options"].append(self._option)
        elif tag == "input" and a.get("type", "").lower() in {"submit", "button"}:
            self.buttons.append({
                "type": a.get("type", ""),
                "name": a.get("name", ""),
                "label": a.get("value", ""),
            })
        elif tag == "button":
            self._button = {
                "type": a.get("type", "submit"),
                "name": a.get("name", ""),
                "label": "",
            }

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"}:
            self._skip_text = False
        if tag == "option":
            self._option = None
        elif tag == "select":
            self._select = None
        elif tag == "button":
            if self._button is not None:
                self.buttons.append(self._button)
            self._button = None
        elif tag == "form":
            self._form = None

    def handle_data(self, data: str) -> None:
        value = data.strip()
        if not value:
            return
        if not self._skip_text:
            self.text_parts.append(value)
        if self._option is not None:
            self._option["label"] = (
                self._option["label"] + " " + value
            ).strip()
        if self._button is not None:
            self._button["label"] = (
                self._button["label"] + " " + value
            ).strip()


def safe_url(url: str) -> str:
    return re.sub(r";jsessionid=[^?]+", "", url or "")


CANDIDATES = [
    {
        "name": "Police-linked ICP+ index",
        "url": "https://icp.administracionelectronica.gob.es/icpplus/index.html",
        "official_role": "National Police direct link",
    },
    {
        "name": "Police-linked ICP+ citar path",
        "url": "https://icp.administracionelectronica.gob.es/icpplus/citar?locale=es",
        "official_role": "Same Police hostname, alternate application path",
    },
    {
        "name": "Current cita previa host",
        "url": "https://citaprevia.administracionelectronica.gob.es/icpplus/citar",
        "official_role": "Alternate central appointment hostname",
    },
    {
        "name": "Sede ICP+ index path",
        "url": "https://sede.administracionespublicas.gob.es/icpplus/index.html",
        "official_role": "Historic Sede alias",
    },
    {
        "name": "Sede ICP+ citar path",
        "url": "https://sede.administracionespublicas.gob.es/icpplus/citar?locale=es",
        "official_role": "Historic Sede alias",
    },
    {
        "name": "Official ICP+ directory page",
        "url": "https://sede.administracionespublicas.gob.es/pagina/index/directorio/icpplus",
        "official_role": "Official procedure information page",
    },
]


def inspect_one(candidate: dict[str, str]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "name": candidate["name"],
        "official_role": candidate["official_role"],
        "requested_url": candidate["url"],
        "status_code": None,
        "final_url": None,
        "title": None,
        "forms": [],
        "selects": [],
        "buttons": [],
        "visible_text_excerpt": "",
        "error": None,
    }
    try:
        response = requests.get(
            candidate["url"],
            timeout=(6, 9),
            allow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "es-ES,es;q=0.9,en;q=0.6",
            },
        )
        parser = ReadOnlyPageParser()
        parser.feed(response.text[:1_500_000])
        title_match = re.search(
            r"<title[^>]*>(.*?)</title>", response.text, re.I | re.S
        )
        result.update({
            "status_code": response.status_code,
            "final_url": safe_url(response.url),
            "title": (
                re.sub(r"\s+", " ", title_match.group(1)).strip()
                if title_match else ""
            ),
            "forms": [
                {
                    **form,
                    "action": safe_url(form.get("action", "")),
                }
                for form in parser.forms
            ],
            "selects": parser.selects,
            "buttons": parser.buttons,
            "visible_text_excerpt": " ".join(parser.text_parts)[:1600],
        })
    except requests.RequestException as exc:
        result["error"] = f"{type(exc).__name__}: {str(exc)[:300]}"
    return result


def main() -> int:
    Path("artifacts").mkdir(exist_ok=True)
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(inspect_one, item) for item in CANDIDATES]
        for future in as_completed(futures):
            results.append(future.result())
    order = {item["name"]: index for index, item in enumerate(CANDIDATES)}
    results.sort(key=lambda item: order[item["name"]])
    report = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "GET-only endpoint comparison; no form submitted.",
        "results": results,
    }
    Path("artifacts/official_endpoint_candidates.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    summary = [
        {
            "name": item["name"],
            "status_code": item["status_code"],
            "final_url": item["final_url"],
            "title": item["title"],
            "selects": [
                {
                    "id": select["id"],
                    "name": select["name"],
                    "options": [
                        option["label"] for option in select["options"][:20]
                    ],
                }
                for select in item["selects"]
            ],
            "error": item["error"],
        }
        for item in results
    ]
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
