# Billo Case Medic (helper)

![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)
![tag:hackathon](https://img.shields.io/badge/hackathon-5F43F1)

Wakes on a signed Sentry alert, joins the case trace, and applies a safe recovery action: retry a transient failure, request human review when confidence is low, or pause settlement when payment safety is uncertain. It records the outcome with a hashed case ID and tells the patient in plain language without exposing health or payment data to Sentry.
