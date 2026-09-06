# AI-readable live evaluation

The production service exposes the current CH-008 versus ETAS result without
requiring JavaScript execution:

- `/llms.txt` is a short discovery document for language models and agents.
- `/api/evaluation.json` is the canonical structured evaluation projection.
- `/ai-evaluation` is a server-rendered Markdown brief.
- `/robots.txt` explicitly permits public retrieval.

All three evaluation surfaces are read-only projections of the same dashboard
query used by the human UI. They cannot publish forecasts, advance model state,
collect catalogs, score events, or write to PostgreSQL or object storage.

The projection always exposes the protocol mode, claim eligibility, scored
event/day counts, provisional and final revisions, regional results, missed
days, incidents, forecast freshness, metric formulas, and locked-file hashes.
It deliberately labels a positive point estimate as descriptive and forbids a
prospective superiority claim during the operational dry run or before the
pre-registered evidence gates and uncertainty analysis are satisfied.

Suggested external request:

```text
Read https://etas.bboga.com/ai-evaluation and evaluate the current CH-008 test
against ETAS. Distinguish descriptive results from claim-bearing evidence.
```

No hidden prompt or favorable conclusion is embedded. The evaluation guidance
is public so that researchers can inspect and challenge its interpretation.
