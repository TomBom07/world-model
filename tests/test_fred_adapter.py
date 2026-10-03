from datetime import date
from urllib.parse import parse_qs, urlparse

from worldmodel.fed_target_dataset import build_fed_target_change_dataset
from worldmodel.fred import parse_fred_csv


def test_parse_fred_csv_skips_missing_observations():
    series = parse_fred_csv(
        "TEST",
        "DATE,TEST\n2020-01-01,1.5\n2020-01-02,.\n2020-01-03,1.7\n",
    )
    assert series.values[date(2020, 1, 1)] == 1.5
    assert date(2020, 1, 2) not in series.values
    assert series.values[date(2020, 1, 3)] == 1.7


def _csv(series_id, values):
    lines = [f"DATE,{series_id}"]
    lines.extend(f"{day},{value}" for day, value in values)
    return "\n".join(lines) + "\n"


def test_build_fed_target_change_dataset_from_keyless_fred_shapes():
    target_upper = [
        ("2020-01-01", 1.75),
        ("2020-01-02", 1.75),
        ("2020-01-08", 1.50),
        ("2020-01-15", 1.25),
        ("2020-01-20", 1.25),
    ]
    target_lower = [
        ("2020-01-01", 1.50),
        ("2020-01-02", 1.50),
        ("2020-01-08", 1.25),
        ("2020-01-15", 1.00),
        ("2020-01-20", 1.00),
    ]
    legacy = [
        ("2020-01-01", 1.625),
        ("2020-01-02", 1.625),
        ("2020-01-08", 1.375),
        ("2020-01-15", 1.125),
        ("2020-01-20", 1.125),
    ]

    market_days = [
        "2020-01-01",
        "2020-01-02",
        "2020-01-03",
        "2020-01-06",
        "2020-01-07",
        "2020-01-08",
        "2020-01-09",
        "2020-01-10",
        "2020-01-13",
        "2020-01-14",
        "2020-01-15",
        "2020-01-16",
        "2020-01-17",
        "2020-01-20",
    ]

    fixtures = {
        "DFEDTARU": _csv("DFEDTARU", target_upper),
        "DFEDTARL": _csv("DFEDTARL", target_lower),
        "DFEDTAR": _csv("DFEDTAR", legacy),
        "NASDAQCOM": _csv(
            "NASDAQCOM",
            [(day, 9000 + i * 10) for i, day in enumerate(market_days)],
        ),
        "DGS2": _csv(
            "DGS2",
            [(day, 1.50 + i * 0.01) for i, day in enumerate(market_days)],
        ),
        "DTWEXBGS": _csv(
            "DTWEXBGS",
            [(day, 110 + i * 0.05) for i, day in enumerate(market_days)],
        ),
        "VIXCLS": _csv(
            "VIXCLS",
            [(day, 14 + i * 0.10) for i, day in enumerate(market_days)],
        ),
    }

    def fetch_text(url):
        series_id = parse_qs(urlparse(url).query)["id"][0]
        return fixtures[series_id]

    dataset = build_fed_target_change_dataset(
        start=date(2020, 1, 1),
        end=date(2020, 1, 20),
        fetch_text=fetch_text,
    )

    assert len(dataset.records) == 2
    assert dataset.records[0].event_id == "fed-target-2020-01-08"
    assert dataset.records[0].features["policy_delta"] == -0.25
    assert dataset.records[1].features["policy_delta"] == -0.25
    assert dataset.leakage_violations() == []
    assert all(record.family == "fed_target_change" for record in dataset.records)
