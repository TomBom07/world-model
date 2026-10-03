# Real-data bootstrap: Fed target effective-date changes

This is WorldModel's first real public-data ingestion path.

It is intentionally narrow and conservative.

## Source series

The builder downloads these FRED series without an API key:

- `DFEDTAR` — legacy Federal Funds Target Rate
- `DFEDTARU` — Federal Funds Target Range, upper limit
- `DFEDTARL` — Federal Funds Target Range, lower limit
- `NASDAQCOM` — Nasdaq Composite daily close
- `DGS2` — 2-year Treasury constant-maturity yield
- `DTWEXBGS` — nominal broad U.S. dollar index
- `VIXCLS` — VIX daily close

The code downloads data at runtime; the repository does not redistribute those series.

## What counts as an event?

An event is a date where the merged Fed target midpoint changes.

Before the range regime, the legacy target is used. During the range regime:

```text
midpoint = (upper + lower) / 2
```

This is an **effective-date** event, not a claim that the date/time exactly equals the FOMC announcement timestamp.

## Features

Features are intentionally simple and auditable:

- target midpoint change
- new target midpoint
- five-session Nasdaq momentum before the event
- previous common-close VIX
- previous common-close 2-year Treasury yield
- five-session broad-dollar momentum before the event

Market-state features use only closes strictly before the target-change date.

## Outcomes

The reaction fingerprint runs from the final common market close before the effective date to the first common close on/after it:

- Nasdaq log return
- 2-year yield change
- broad-dollar log return
- VIX change

## Why this is not yet an FOMC alpha study

There are important timing limitations:

1. FRED target series describe the rate effective as of a date; that is not a precise intraday announcement timestamp.
2. Daily closes are too coarse to isolate an announcement reaction cleanly.
3. Current FRED observations can reflect later revisions for some economic series.
4. This dataset contains target **changes**, not every unchanged FOMC decision.
5. There is no analyst-consensus surprise measure.

So this adapter should be treated as a real-data plumbing and sealed-evaluation bootstrap.

A serious announcement study should later replace the event timestamp with official statement timestamps, use point-in-time/vintage data where relevant, and use intraday market observations.

## Commands

Download/build the dataset:

```bash
worldmodel fred-fed \
  --output data/fed-target-events.csv \
  --start 1994-01-01 \
  --end 2025-12-31
```

Then **choose the cutoff before looking at holdout performance**:

```bash
worldmodel fred-evaluate \
  --input data/fed-target-events.csv \
  --training-end 2019-12-31T23:59:59+00:00 \
  --evaluation-start 2020-01-01T00:00:00+00:00 \
  --evaluation-end 2025-12-31T23:59:59+00:00 \
  --report reports/fed-sealed.json
```

The report contains the manifest seal, exact dataset hash, event-level forecast seals, audit results and baseline metrics.
