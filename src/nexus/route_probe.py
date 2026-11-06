"""Check reachability of official ICP+ entry points without submitting data."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

import requests


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.in_title = False
        self.title_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "title":
            self.in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        value = data.strip()
        if value:
            self.parts.append(value)
            if self.in_title:
                self.title_parts.append(value)


URLS = [
    {
        "name": "National Police ICP+ link",
        "url": "https://icp.administracionelectronica.gob.es/icpplus/index.html",
    },
    {
        "name": "Sede ICP+ path",
        "url": "https://sede.administracionespublicas.gob.es/icpplus/index.html",
    },
    {
        "name": "Sede ICP+ directory",
        "url": "https://sede.administracionespublicas.gob.es/pagina/index/directorio/icpplus",
    },
    {
        "name": "SSWEB ICP+ standard route",
        "url": "https://ssweb.seap.minhap.es/icpplus/citar?locale=es",
    },
    {
        "name": "SSWEB ICP+ nested route",
        "url": "https://ssweb.seap.minhap.es/icpplus/icpplus/citar?locale=es",
    },
]


def check(url_record: dict[str, str]) -> dict[str, object]:
    result: dict[str, object] = {
        "name": url_record["name"],
        "url": url_record["url"],
        "status_code": None,
        "final_url": None,
        "title": None,
        "markers": [],
        "body_excerpt": "",
        "error": None,
    }
    try:
        response = requests.get(
            url_record["url"],
            timeout=(8, 14),
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
        parser = TextExtractor()
        parser.feed(response.text[:1_500_000])
        body = re.sub(r"\s+", " ", " ".join(parser.parts))
        title = " ".join(parser.title_parts)
        result["title"] = title[:200]
        result["body_excerpt"] = body[:1800]
        lowered = body.casefold()
        markers = (
            "internet cita previa",
            "provincias disponibles",
            "seleccione la provincia",
            "toma de huella",
            "trámites cuerpo nacional de policía",
            "ámbitos disponibles",
            "tear",
            "tribunal económico-administrativo",
        )
        result["markers"] = [marker for marker in markers if marker in lowered]
    except requests.RequestException as exc:
        result["error"] = f"{type(exc).__name__}: {str(exc)[:400]}"
    return result


def main() -> int:
    report = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "Read-only URL reachability test; no form submitted.",
        "results": [check(item) for item in URLS],
    }
    Path("artifacts").mkdir(exist_ok=True)
    Path("artifacts/route_probe.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(
        [
            {
                "name": item["name"],
                "status_code": item["status_code"],
                "final_url": item["final_url"],
                "title": item["title"],
                "markers": item["markers"],
                "error": item["error"],
            }
            for item in report["results"]
        ],
        ensure_ascii=False,
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
