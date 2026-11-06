# Nexus architecture and current status

## Purpose

Nexus is a neutral project name. Its first planned use case is monitoring
Spanish fingerprint appointment availability in the Community of Madrid.

## Current implementation

- Environment-based configuration, including the official portal URL.
- Telegram notification helper (credentials are optional and must remain secret).
- A read-only Playwright portal probe that inventories visible select controls,
  their option labels and values, page headings, frames, and visible status text.
- Manual GitHub Actions workflow to run the portal probe and upload a short-lived
  diagnostic artifact.
- GitHub Actions CI for Python compilation and unit tests.

## Official appointment procedure

The Policía Nacional identifies the relevant TIE procedure as:

`POLICIA - TOMA DE HUELLA (EXPEDICIÓN DE TARJETA), RENOVACIÓN DE TARJETA DE
LARGA DURACIÓN y DUPLICADO`.

The exact option label and available offices must be verified against the live
portal before implementing the availability query.

## Probe safety and limits

The portal probe is read-only. It does not submit identity information, reserve
or cancel appointments, solve CAPTCHAs, or bypass rate limits/access controls.
If a CAPTCHA or access-denied page appears, the report marks it for manual
intervention.

The probe records only the page structure and visible text needed to identify
the current form flow. It does not collect field values, cookies, browser
storage, or personal data.

## Not implemented yet

- Selecting Madrid and the fingerprint procedure in the live portal.
- Enumerating every office shown by the portal and checking availability.
- Availability persistence and duplicate detection.
- Telegram alert policy.
- Dashboard and health status.
- Scheduled production monitoring.

The monitor must not report a successful appointment check until the official
portal adapter has completed a real query and its response has been validated.
GitHub scheduled workflows are best-effort, not a precise timer.
