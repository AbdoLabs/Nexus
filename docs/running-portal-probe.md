# Running the portal form probe

The first live inspection is deliberately manual. It opens the official portal
once, reads the initial form structure and visible text, and uploads a diagnostic
artifact. It does not enter identity data or submit a reservation.

## Steps

1. Open the [Portal Form Probe workflow](https://github.com/AbdoLabs/Nexus/actions/workflows/portal-probe.yml).
2. Choose **Run workflow**, keep branch `main`, and confirm **Run workflow**.
3. Wait for the run to finish.
4. Open the completed run and download the artifact named `nexus-portal-probe`.
5. Share the downloaded ZIP or the `portal_probe.json` report.

## Interpreting the report

- `appointment_portal_loaded`: the portal loaded; review the select controls
  and option labels in the report to implement the next step.
- `no_appointments_message`: the visible page showed an explicit no-appointments
  message. This is not inferred from a generic error.
- `manual_intervention_required`: the page displayed a CAPTCHA or access-control
  challenge. Nexus stops; it does not attempt to solve or bypass it.
- `unknown_or_loading`, `http_error`, or `navigation_error`: the portal
  response needs inspection before implementing any interaction.

The workflow is manual-only at this stage. Do not enable frequent polling until
we have confirmed the portal's actual form flow and a reasonable request rate.
