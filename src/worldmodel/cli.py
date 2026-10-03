from __future__ import annotations

import argparse
import json


def main() -> None:
    parser = argparse.ArgumentParser(prog="worldmodel", description="WorldModel RMC research lab")
    sub = parser.add_subparsers(dest="command")

    demo = sub.add_parser("demo", help="run the synthetic mechanism-recovery experiment")
    demo.add_argument("--seed", type=int, default=7)
    demo.add_argument("--observations", type=int, default=360)
    demo.add_argument("--target", default="growth_equity")

    serve = sub.add_parser("serve", help="launch the local research dashboard")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--reload", action="store_true")

    args = parser.parse_args()
    if args.command == "serve":
        import uvicorn

        uvicorn.run("worldmodel.api:app", host=args.host, port=args.port, reload=args.reload)
        return

    from .engine import ResearchEngine

    result = ResearchEngine(seed=getattr(args, "seed", 7)).run_demo(
        n=getattr(args, "observations", 360),
        target=getattr(args, "target", "growth_equity"),
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
