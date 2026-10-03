from __future__ import annotations

import argparse
import json


def main() -> None:
    parser = argparse.ArgumentParser(prog="worldmodel", description="WorldModel RMC research lab")
    sub = parser.add_subparsers(dest="command")

    demo = sub.add_parser("demo", help="run the V0 symbolic mechanism-recovery experiment")
    demo.add_argument("--seed", type=int, default=7)
    demo.add_argument("--observations", type=int, default=360)
    demo.add_argument("--target", default="growth_equity")

    strategic = sub.add_parser(
        "strategic",
        help="run the V1 strategic hidden-world identification experiment",
    )
    strategic.add_argument("--seed", type=int, default=7)
    strategic.add_argument("--observations", type=int, default=260)

    sealed = sub.add_parser(
        "sealed",
        help="run the V2 sealed historical replay protocol demo",
    )
    sealed.add_argument("--seed", type=int, default=7)
    sealed.add_argument("--observations", type=int, default=120)

    fred = sub.add_parser(
        "fred-fed",
        help="download FRED series and build a real Fed target-change event CSV",
    )
    fred.add_argument("--output", required=True)
    fred.add_argument("--start", default="1994-01-01")
    fred.add_argument("--end", default=None)

    fred_eval = sub.add_parser(
        "fred-evaluate",
        help="run a sealed evaluation on a previously downloaded Fed event CSV",
    )
    fred_eval.add_argument("--input", required=True)
    fred_eval.add_argument("--training-end", required=True)
    fred_eval.add_argument("--evaluation-start", required=True)
    fred_eval.add_argument("--evaluation-end", required=True)
    fred_eval.add_argument("--seed", type=int, default=7)
    fred_eval.add_argument("--report", default=None)

    serve = sub.add_parser("serve", help="launch the local research dashboard")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--reload", action="store_true")

    args = parser.parse_args()
    if args.command == "serve":
        import uvicorn

        uvicorn.run("worldmodel.api:app", host=args.host, port=args.port, reload=args.reload)
        return

    if args.command == "strategic":
        from .strategic_engine import StrategicResearchEngine

        result = StrategicResearchEngine(seed=args.seed).run_demo(n=args.observations)
    elif args.command == "sealed":
        from .historical_engine import HistoricalResearchEngine

        result = HistoricalResearchEngine(seed=args.seed).run_demo(n=args.observations)
    elif args.command == "fred-fed":
        from datetime import date

        from .fed_target_dataset import build_fed_target_change_dataset

        dataset = build_fed_target_change_dataset(
            start=date.fromisoformat(args.start),
            end=date.fromisoformat(args.end) if args.end else None,
        )
        dataset.to_csv(args.output)
        result = {
            "output": args.output,
            "events": len(dataset.records),
            "first_event": dataset.records[0].event_at,
            "last_event": dataset.records[-1].event_at,
            "feature_names": dataset.feature_names,
            "outcome_names": dataset.outcome_names,
            "leakage_violations": len(dataset.leakage_violations()),
        }
    elif args.command == "fred-evaluate":
        from pathlib import Path

        from .event_data import EventDataset, parse_timestamp
        from .fed_target_dataset import FEATURES, OUTCOMES
        from .historical_runner import SealedHistoricalRunner
        from .sealing import ExperimentSpec

        dataset = EventDataset.from_csv(
            args.input,
            feature_names=FEATURES,
            outcome_names=OUTCOMES,
        )
        spec = ExperimentSpec(
            name="fed-target-effective-date-v1",
            training_end=parse_timestamp(args.training_end),
            evaluation_start=parse_timestamp(args.evaluation_start),
            evaluation_end=parse_timestamp(args.evaluation_end),
            event_families=("fed_target_change",),
            feature_names=dataset.feature_names,
            outcome_names=dataset.outcome_names,
            model_config={
                "freeze_at_training_end": True,
                "event_definition": "Fed target effective-date change",
                "timing_resolution": "daily-close bootstrap",
            },
        )
        report = SealedHistoricalRunner(
            dataset,
            spec,
            seed=args.seed,
            code_ref="worldmodel-0.3.0-fred-bootstrap",
        ).run()
        if args.report:
            Path(args.report).write_text(
                json.dumps(report, indent=2, default=str),
                encoding="utf-8",
            )
            result = {
                "report": args.report,
                "manifest_seal": report["manifest"]["seal"],
                "training_events": report["audit"]["training_events"],
                "evaluation_events": report["audit"]["evaluation_events"],
                "metrics": report["metrics"],
            }
        else:
            result = report
    else:
        from .engine import ResearchEngine

        result = ResearchEngine(seed=getattr(args, "seed", 7)).run_demo(
            n=getattr(args, "observations", 360),
            target=getattr(args, "target", "growth_equity"),
        )
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
