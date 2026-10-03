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
    else:
        from .engine import ResearchEngine

        result = ResearchEngine(seed=getattr(args, "seed", 7)).run_demo(
            n=getattr(args, "observations", 360),
            target=getattr(args, "target", "growth_equity"),
        )
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
