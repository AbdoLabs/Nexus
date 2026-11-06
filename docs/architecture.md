# Nexus architecture and current status

## Purpose

Nexus is a neutral project name. Its first use case is monitoring Spanish
fingerprint appointment availability in the Community of Madrid.

## Search strategy agreed for Nexus

- Search Madrid for the TIE fingerprint procedure.
- The initial form/screen may show an office selector containing all offices.
  This is a search-input screen, not a search result, and must not by itself
  trigger an availability alert.
- Preserve the province-level search: do not narrow the search to a specific
  office when the portal allows the search to proceed without one.
- After submitting the initial search, compare the resulting page with the
  known no-availability page captured on 2026-11-06.
  - If the result page displays the explicit message
    "En este momento no hay citas disponibles", report NO_APPOINTMENTS.
  - If a different, successfully loaded result screen appears after the search
    submission, report APPOINTMENTS_AVAILABLE. The user explicitly prefers
    this broad difference-based rule; identifying the second office selector
    or parsing individual office names is not required for the first detector.
  - If the request fails, the page does not finish loading, access is denied,
    or a CAPTCHA / anti-automation challenge appears, report
    UNKNOWN_MANUAL_CHECK. These are not valid appointment result screens.
- Do not compare the initial input form to the no-availability page. The
  comparison applies only after the province-level search has been submitted.

Nexus should make one province-level query, not one query per municipality.
The broad positive rule should be implemented only for a successfully loaded
post-search result page. Preserve a screenshot and a redacted page summary
for each positive result so the rule can be audited and refined.

## Evidence from the first local inspection

The local inspection at 2026-11-06 18:40 Europe/Madrid reached
`/icpplustiem/acCitarB` and displayed the explicit no-appointments message.
That report did not include visible select elements. It is the baseline
no-availability page for the first comparison-based detector.

## Current implementation

- Environment-based configuration and official portal URL.
- Telegram notification helper (credentials remain secret).
- A GET-only endpoint diagnostic that compares the official Police ICP+ URL with documented Sede aliases. The SSWEB Education route was excluded after it returned Education-only procedures.
- A manually triggered GitHub Actions diagnostic workflow.
- GitHub Actions CI and unit tests.

## Not implemented yet

- A supported cloud route to the official Police appointment application; the official link currently times out from GitHub-hosted runners.
- Browser automation of the province-level search and post-submit page comparison.
- Positive availability detection confirmed by a live second-result example.
- Availability persistence and duplicate alert suppression.
- Telegram notification policy connected to detected availability.
- Dashboard and health status.
- Scheduled production monitoring.

The monitor must never treat the initial all-offices input screen as an
availability result. The first detector compares only the successfully loaded
post-search result page with the known no-availability baseline. Exact
no-availability message means NO_APPOINTMENTS; a different successful
post-search result screen means APPOINTMENTS_AVAILABLE; technical failures
and challenges mean UNKNOWN_MANUAL_CHECK.
