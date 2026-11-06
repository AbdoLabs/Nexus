# Nexus architecture and current status

## Purpose

Nexus is a neutral project name. Its first use case is monitoring Spanish
fingerprint appointment availability in the Community of Madrid.

## Search strategy agreed for Nexus

- Search Madrid for the TIE fingerprint procedure.
- The initial form/screen may show an office selector containing **all offices**.
  This is only the initial input screen and is never evidence that appointments
  are available.
- Preserve the province-level search: do not narrow the search to a specific
  office when the portal allows the search to proceed without one.
- After submitting the initial search, distinguish the next screen carefully:
  - If the portal displays a **second office-selection screen containing only
    offices with available appointments**, record those offices and report
    availability. This filtered post-search screen is the positive signal.
  - If the portal displays the explicit message
    "En este momento no hay citas disponibles", report no availability.
  - If it displays a CAPTCHA, access-denied page, loading error, or unfamiliar
    response, report an unknown/manual-intervention state.
- Never classify the initial all-offices selector as availability.
- Never infer availability merely because the portal loaded or because any
  generic office selector exists.

Nexus should make one province-level query, not one query per municipality.
For the positive result, capture office names from the **filtered second
selector**, not from the initial all-offices list. Do not hard-code office names.

## Evidence from the first local inspection

The local inspection at 2026-11-06 18:40 Europe/Madrid reached
`/icpplustiem/acCitarB` and displayed the explicit no-appointments message.
That report did not include visible select elements. It confirms the negative
message path, but does not yet document the filtered positive office selector.

## Current implementation

- Environment-based configuration and official portal URL.
- Telegram notification helper (credentials remain secret).
- A GET-only endpoint diagnostic that compares the official Police ICP+ URL with documented Sede aliases. The SSWEB Education route was excluded after it returned Education-only procedures.
- A manually triggered GitHub Actions diagnostic workflow.
- GitHub Actions CI and unit tests.

## Not implemented yet

- A supported cloud route to the official Police appointment application; the official link currently times out from GitHub-hosted runners.
- Browser automation of the initial search and detection of the filtered second office selector.
- Positive availability detection confirmed with a captured real example of the second selector.
- Availability persistence and duplicate alert suppression.
- Telegram notification policy connected to detected availability.
- Dashboard and health status.
- Scheduled production monitoring.

The monitor must treat the portal as a state machine. The initial all-offices
selector is a search input, not an availability result. Only the filtered
post-search office selector or the explicit no-appointments message are
meaningful availability outcomes.
