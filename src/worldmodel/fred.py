from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import csv
from io import StringIO
from typing import Callable
from urllib.parse import urlencode
from urllib.request import urlopen


FetchText = Callable[[str], str]


@dataclass(frozen=True)
class FredSeries:
    series_id: str
    values: dict[date, float]

    @property
    def dates(self) -> tuple[date, ...]:
        return tuple(sorted(self.values))

    def value(self, day: date) -> float | None:
        return self.values.get(day)

    def on_or_before(self, day: date) -> tuple[date, float] | None:
        candidates = [d for d in self.values if d <= day]
        if not candidates:
            return None
        chosen = max(candidates)
        return chosen, self.values[chosen]

    def before(self, day: date) -> tuple[date, float] | None:
        candidates = [d for d in self.values if d < day]
        if not candidates:
            return None
        chosen = max(candidates)
        return chosen, self.values[chosen]

    def after_or_on(self, day: date) -> tuple[date, float] | None:
        candidates = [d for d in self.values if d >= day]
        if not candidates:
            return None
        chosen = min(candidates)
        return chosen, self.values[chosen]

    def changes(self) -> list[tuple[date, float, float]]:
        rows: list[tuple[date, float, float]] = []
        previous: float | None = None
        for day in self.dates:
            value = self.values[day]
            if previous is not None and value != previous:
                rows.append((day, previous, value))
            previous = value
        return rows


def fred_csv_url(
    series_id: str,
    *,
    start: date | None = None,
    end: date | None = None,
) -> str:
    params = {"id": series_id}
    if start is not None:
        params["cosd"] = start.isoformat()
    if end is not None:
        params["coed"] = end.isoformat()
    return "https://fred.stlouisfed.org/graph/fredgraph.csv?" + urlencode(params)


def _default_fetch_text(url: str) -> str:
    with urlopen(url, timeout=30) as response:
        return response.read().decode("utf-8")


def parse_fred_csv(series_id: str, text: str) -> FredSeries:
    reader = csv.DictReader(StringIO(text))
    fieldnames = reader.fieldnames or []
    if len(fieldnames) < 2:
        raise ValueError(f"Unexpected FRED CSV shape for {series_id}")

    date_field = fieldnames[0]
    value_field = (
        series_id
        if series_id in fieldnames
        else next((name for name in fieldnames[1:] if name), fieldnames[1])
    )

    values: dict[date, float] = {}
    for row in reader:
        raw_date = str(row.get(date_field, "")).strip()
        raw_value = str(row.get(value_field, "")).strip()
        if not raw_date or raw_value in {"", ".", "NA", "nan"}:
            continue
        try:
            day = datetime.fromisoformat(raw_date).date()
            value = float(raw_value)
        except ValueError:
            continue
        values[day] = value

    if not values:
        raise ValueError(f"No usable observations returned for FRED series {series_id}")
    return FredSeries(series_id=series_id, values=values)


def download_fred_series(
    series_id: str,
    *,
    start: date | None = None,
    end: date | None = None,
    fetch_text: FetchText | None = None,
) -> FredSeries:
    fetch = fetch_text or _default_fetch_text
    url = fred_csv_url(series_id, start=start, end=end)
    return parse_fred_csv(series_id, fetch(url))
