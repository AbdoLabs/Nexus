# Nexus architecture and current status

## Purpose

Nexus is a neutral project name. Its first use case is monitoring Spanish
fingerprint appointment availability in the Community of Madrid.

## Search strategy agreed for Nexus

- Search Madrid for the TIE fingerprint procedure.
- Do not preselect a specific police station/office.
- Continue the broad search using the portal's general/all-offices choice
  only where the portal requires that wildcard.
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
- A read-only Playwright probe that inventories visible form controls and text.
- A manually triggered GitHub Actions diagnostic workflow.
- GitHub Actions CI and unit tests.

## Not implemented yet

- Complete interaction with the Madrid + TIE fingerprint search form.
- Positive/negative availability detection on the post-search page in a live
  portal run.
- Availability persistence and duplicate alert suppression.
- Telegram notification policy connected to detected availability.
- Dashboard and health status.
- Scheduled production monitoring.

The monitor must never report a successful availability check merely because
the portal loaded. Only the explicit post-search office chooser or explicit
no-appointments message are meaningful availability outcomes.
