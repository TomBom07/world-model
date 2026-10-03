# Historical event data schema

Phase 2 evaluates event reactions under a strict information-timing contract.

## Core rule

For an event at time `event_at`, every model feature must have:

```text
feature_available_at <= event_at
```

If even one feature became available after the event cutoff, the dataset is rejected before fitting.

## CSV layout

Every file contains:

```text
event_id
family
event_at
x_<feature>
x_<feature>__available_at
y_<outcome>
```

Example feature `surprise`:

```text
x_surprise
x_surprise__available_at
```

Example outcome `growth_equity`:

```text
y_growth_equity
```

Timestamps should be ISO-8601 and preferably include a timezone:

```text
2026-09-15T12:30:00+00:00
```

Naive timestamps are interpreted as UTC.

## Intended event families

The first real datasets should be event-defined rather than generic daily bars:

- earnings releases
- inflation releases
- central-bank decisions
- liquidity / funding shocks
- large volatility events

This makes the target a **reaction fingerprint** rather than a vague next-price prediction.

## Suggested Phase-2 feature set

The exact schema must be frozen before evaluation, but likely categories include:

- event surprise / standardized surprise
- pre-event implied volatility
- positioning proxy
- liquidity / funding state
- rates state
- risk sentiment
- valuation / expectation state where appropriate

Every field needs a defensible historical availability timestamp.

## Suggested outcomes

Use synchronized cross-asset reaction windows, for example:

- growth equity return
- two-year yield change
- USD return
- volatility change

The outcome window should also be frozen in the experiment spec before evaluation.

## Audit artifacts

A sealed run stores hashes for:

- experiment specification
- dataset schema
- exact dataset payload
- every event's pre-event feature payload
- every model forecast

A result is considered valid only when all forecast seals verify and the leakage audit returns zero violations.

## Important boundary

Hashing and chronology reduce accidental or silent look-ahead. They do not prove the economic model is correct, and they do not turn a historical backtest into live evidence.
