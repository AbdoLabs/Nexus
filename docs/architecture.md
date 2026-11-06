# Nexus architecture and current status

## Purpose

Nexus is a neutral project name. Its first use case is monitoring Spanish
fingerprint appointment availability in the Community of Madrid.

## Search strategy agreed for Nexus

- Search Madrid for the TIE fingerprint procedure.
- Do not select or submit an office at the search stage.
- If appointments are available, read the office choices from the next screen.
- If the portal then displays an office-selection screen with office choices,
  record the displayed offices as the positive availability signal.
- If it displays an explicit no-appointments message, record no availability.
- If it displays a CAPTCHA, access-denied page, loading error, or an unfamiliar
  response, report an unknown/manual-intervention state instead of claiming
  that no appointments exist.

Nexus should make one province-level query, not one query per municipality.
The office list is taken from the live response, not hard-coded.

## Current implementation

- Environment-based configuration and official portal URL.
- Telegram notification helper (credentials remain secret).
- A GET-only endpoint diagnostic that compares the official Police ICP+ URL with documented Sede aliases. The SSWEB Education route was excluded after it returned Education-only procedures.
- A manually triggered GitHub Actions diagnostic workflow.
- GitHub Actions CI and unit tests.

## Not implemented yet

- A supported cloud route to the official Police appointment application; the official link currently times out from GitHub-hosted runners.
- Positive/negative availability detection on the post-search page in a live
  portal run.
- Availability persistence and duplicate alert suppression.
- Telegram notification policy connected to detected availability.
- Dashboard and health status.
- Scheduled production monitoring.

The monitor must never report a successful availability check merely because
the portal loaded. Only the explicit post-search office chooser or explicit
no-appointments message are meaningful availability outcomes.
