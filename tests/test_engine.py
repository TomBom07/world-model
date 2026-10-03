from worldmodel.engine import ResearchEngine


def test_demo_returns_research_report():
    report = ResearchEngine(seed=11).run_demo(n=220)
    assert report["experiment"]["true_switch_index"] > 0
    assert report["post_regime"]["top_models"]
    assert len(report["tomography"]) == 3
    assert report["sample_efficiency"]
    assert "Synthetic" in report["disclaimer"]
