from pprint import pprint

from worldmodel.engine import ResearchEngine


if __name__ == "__main__":
    report = ResearchEngine(seed=7).run_demo()
    pprint(report["experiment"])
    pprint(report["pre_regime"])
    pprint(report["post_regime"])
