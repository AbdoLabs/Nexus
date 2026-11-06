# Official ICP+ endpoint diagnostic

This workflow compares documented entry points using HTTP GET only. It does
not submit a form, select a province, choose an office, or make a booking.

## Run

1. Open the [Portal Form Probe workflow](https://github.com/AbdoLabs/Nexus/actions/workflows/portal-probe.yml).
2. Choose **Run workflow** on branch `main`.
3. Download the `nexus-http-inspection` artifact.

## Current findings

- The National Police links applicants to
  `https://icp.administracionelectronica.gob.es/icpplus/index.html`.
- GitHub-hosted runners currently time out when connecting to that hostname.
- The alternate SSWEB endpoint served Education procedures for Madrid, not
  Police fingerprint appointments, and is therefore not used by Nexus.
- Other Sede aliases returned a general landing page, HTTP 403 or HTTP 503
  from the GitHub runner.

Until a cloud runner can reach the correct Police application, Nexus must not
claim that it checked appointment availability. The next useful diagnostic is
to open the official link in a normal browser, select Madrid, and inspect the
procedure screen without entering identity details or choosing a time.
