# Prospective Daily Newsletter

The newsletter is an observational layer separate from forecast generation and
scoring. A newsletter failure cannot delay, modify, or invalidate a forecast.

## Subscription contract

- The public form accepts an email address and locale (`tr` or `en`).
- A subscription remains `pending` until its confirmation link is opened.
- Only `active` subscribers appear in the public count and delivery queue.
- Addresses are normalized to lowercase and never returned by a public API.
- Every report contains an individual unsubscribe link and RFC 8058
  `List-Unsubscribe` headers.
- Unsubscribing takes effect in PostgreSQL immediately.

## Coolify environment

```text
RESEND_API_KEY=re_...
NEWSLETTER_PUBLIC_BASE_URL=https://your-public-dashboard-domain.example
NEWSLETTER_FROM=CH-008 Prospective Test <hello@bboga.com>
```

`bboga.com` must be verified in Resend before `hello@bboga.com` can deliver to
public recipients. Store the API key only as a Coolify secret; do not commit it.

## Scheduled task

Create a second Coolify Scheduled Task. Do not replace or modify the forecast
pipeline task.

```text
Schedule: 0 3 * * *
Command:  python scripts/send_daily_newsletter.py
```

Coolify schedules are interpreted in UTC in this deployment. `03:00 UTC` is
`06:00` Turkey time. The report reads the dashboard after the `00:05 UTC`
forecast pipeline has completed.

## Delivery safety

`prospective.newsletter_deliveries` has one row per subscriber and report date.
The Resend request also uses `ch008-daily-<date>-<subscriber-id>` as its
idempotency key. Re-running a task therefore skips successful deliveries and
allows failed deliveries up to three persisted attempts without duplicating a
successful message.

The report contains pipeline health, forecast publication coverage, incident
count, cumulative provisional IGPE, relative factor, and the latest completed
target-day regional scores. It is labeled as research output, not an earthquake
warning.

To inspect rendering without contacting Resend:

```bash
python scripts/send_daily_newsletter.py --dry-run
```

The dry run creates no Resend delivery and does not consume an attempt.
