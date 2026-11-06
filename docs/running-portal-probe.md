# Portal form probe

The diagnostic reaches the public ICP+ form and submits the Madrid province
selection only. It keeps hidden form fields and cookies in memory for the single
HTTP session; it does not save them in the report or repository.

It does not submit a person's identity information, select a police office,
select a time slot, reserve, or cancel an appointment.

## Run

1. Open the [Portal Form Probe workflow](https://github.com/AbdoLabs/Nexus/actions/workflows/portal-probe.yml).
2. Choose **Run workflow** on branch `main`.
3. Download the `nexus-http-inspection` artifact from the completed run.

## What to inspect

The report includes the initial form's public metadata, hidden-field names (never values), and snippets from the public JavaScript submit handler. It also records the response to the Madrid-only transition. A session-expired response is a form-flow diagnostic, not a no-appointments result.

The next implementation step is to reproduce the ordinary Aceptar button behavior, identify the exact TIE fingerprint procedure option, and then inspect the post-procedure screen for office choices or an explicit no-appointments message.

No office is selected by this diagnostic.
