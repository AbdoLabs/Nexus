"""Read-only discovery of official ICP+ entry points.

Only HTTP GET requests are made. This probe records page titles, public form
controls and visible text, never hidden input values, cookies or session IDs.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from .route_probe import FormInspector, _parse_response, _safe_url, _safe_selects


CANDIDATES = [
    {
        "name": "Police-linked ICP+ index",
        "url": "https://icp.administracionelectronica.gob.es/icpplus/index.html",
    },
    {
        "name": "Police-linked ICP+ citar path",
        "url": "https://icp.administracionelectronica.gob.es/icpplus/citar?locale=es",
    },
    {
        "name": "Current cita previa host",
        "url": "https://citaprevia.administracionelectronica.gob.es/icpplus/citar",
    },
    {
        "name": "Sede ICP+ index path",
        "url": "https://sede.administracionespublicas.gob.es/icpplus/index.html",
    },
    {
        "name": "Sede ICP+ citar path",
        "url": "https://sede.administracionespublicas.gob.es/icpplus/citar?locale=es",
    },
    {
        "name": "Official ICP+ directory page",
        "url": "https://sede.administracionespublicas.gob.es/pagina/index/directorio/icpplus",
    },
]


def inspect_one(candidate: dict[str, str]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "name": candidate["name"],
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
        parser, title = _parse_response(response)
        result.update({
            "status_code": response.status_code,
            "final_url": _safe_url(response.url),
            "title": title,
            "forms": [
                {
                    "id": form.get("id", ""),
                    "name": form.get("name", ""),
                    "method": form.get("method", ""),
                    "action": _safe_url(form.get("action", "")),
                }
                for form in parser.forms
            ],
            "selects": _safe_selects(parser),
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
        "purpose": "Read-only public endpoint comparison; no form submitted.",
        "results": results,
    }
    Path("artifacts/official_endpoint_candidates.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps([
        {
            "name": item["name"],
            "status_code": item["status_code"],
            "final_url": item["final_url"],
            "title": item["title"],
            "selects": [
                {
                    "id": select["id"],
                    "name": select["name"],
                    "options": [option["label"] for option in select["options"][:20]],
                }
                for select in item["selects"]
            ],
            "error": item["error"],
        }
        for item in results
    ], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
