# Initial architecture

## Purpose

Nexus is the neutral project name. The first planned use case is monitoring
Spanish fingerprint appointment availability in the Community of Madrid.

## Current implementation

- Environment-based configuration.
- Telegram notification helper.
- A minimal monitor entry point.
- GitHub Actions CI for compilation and unit tests.

## Not implemented yet

- Appointment portal navigation and form submission.
- Municipality/office discovery and result extraction.
- Availability persistence and duplicate detection.
- Telegram alert policy.
- Dashboard and health status.
- Scheduled production monitoring.

The monitor must not report an appointment check as successful until the
official portal adapter has completed a real query and its response has been
validated. GitHub scheduled workflows are best-effort, not a precise timer.
