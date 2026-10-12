import json
from functools import lru_cache
from pathlib import Path


def encoded(value):
    # JSON lives in a script element: HTML-sensitive characters must be escaped.
    return (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )


@lru_cache(maxsize=1)
def viewer_bundle():
    import vl_convert

    return vl_convert.javascript_bundle(vl_version="6.4")


def chart_spec(report):
    import altair as alt

    timed = [
        a
        for a in report["actions"]
        if any(
            a.get(k) is not None
            for k in ("start", "observed_start", "end", "observed_end")
        )
    ]
    origin = min(
        (
            next(
                a[k]
                for k in ("start", "observed_start", "end", "observed_end")
                if a.get(k) is not None
            )
            for a in timed
        ),
        default=0,
    )
    data = []
    for a in timed:
        start = next(
            a[k]
            for k in ("start", "observed_start", "end", "observed_end")
            if a.get(k) is not None
        )
        end = a["end"] if a["start"] is not None else a["observed_end"]
        end = max(start, end) if end is not None else start
        data.append(
            {
                "id": a["id"],
                "name": a["name"][:140],
                "category": a["category"],
                "status": a["status"],
                "start": (start - origin) / 1000,
                "end": (end - origin) / 1000,
                "row": a["row"],
                "bottom": a["row"] + 0.78,
                "middle": a["row"] + 0.39,
                "start_utc": a["start_utc"]
                or a["observed_start_utc"]
                or a["end_utc"]
                or a["observed_end_utc"],
                "end_utc": a["end_utc"] or a["observed_end_utc"],
                "timing": a["timing"],
                "depth": a["depth"],
                "duration_ms": a["duration_ms"],
            }
        )
    extent = max((d["end"] for d in data), default=1) or 1
    categories = sorted({a["category"] for a in report["actions"]})
    chosen = alt.param(
        name="category",
        value="All",
        bind=alt.binding_select(options=["All", *categories], name="Category: "),
    )
    zoom = alt.selection_interval(name="time_window", encodings=["x"], bind="scales")
    scale_x = alt.Scale(domain=[0, extent], nice=False, zero=False)
    scale_y = alt.Scale(
        domain=[-1, max(report["rows"], 2)], reverse=True, nice=False, zero=False
    )
    base = alt.Chart(alt.Data(values=data)).transform_filter(
        "category === 'All' || datum.category === category"
    )
    tooltips = [
        alt.Tooltip("name:N", title="Action"),
        alt.Tooltip("status:N", title="Status"),
        alt.Tooltip("start_utc:N", title="Start / observation (UTC)"),
        alt.Tooltip("end_utc:N", title="End / output observation (UTC)"),
        alt.Tooltip("duration_ms:Q", title="Recorded duration (ms)"),
        alt.Tooltip("timing:N", title="Timing"),
    ]
    common = dict(
        x=alt.X(
            "start:Q",
            scale=scale_x,
            title="Elapsed seconds",
            axis=alt.Axis(orient="top", grid=True),
        ),
        color=alt.Color("category:N", scale=alt.Scale(scheme="tableau20"), legend=None),
        tooltip=tooltips,
    )
    bars = (
        base.transform_filter("datum.end > datum.start")
        .mark_rect(cornerRadius=2, clip=True)
        .encode(
            **common,
            x2="end:Q",
            y=alt.Y("row:Q", scale=scale_y, axis=None),
            y2="bottom:Q",
        )
    )
    points = (
        base.transform_filter("datum.end === datum.start")
        .mark_point(filled=True, shape="diamond", size=65, clip=True)
        .encode(**common, y=alt.Y("middle:Q", scale=scale_y, axis=None))
    )
    labels = (
        base.transform_filter("scale('x', datum.end) - scale('x', datum.start) > 90")
        .mark_text(
            align="left", baseline="middle", dx=4, limit=160, clip=True, color="#152338"
        )
        .encode(
            x=alt.X("start:Q", scale=scale_x),
            y=alt.Y("middle:Q", scale=scale_y, axis=None),
            text="name:N",
            tooltip=tooltips,
        )
    )
    chart = (
        alt.layer(bars, points, labels)
        .add_params(chosen, zoom)
        .properties(width=1050, height=max(130, report["rows"] * 26))
        .configure_view(stroke=None)
        .configure_axis(
            labelFont="sans-serif", titleFont="sans-serif", gridColor="#e8ecf2"
        )
    )
    return chart.to_dict(), origin


def render(report):
    spec, origin = chart_spec(report)
    payload = {**report, "origin_ms": origin}
    template = Path(__file__).with_name("viewer.html").read_text()
    # Substitute each token in one pass so record text cannot introduce a token.
    import re

    values = {
        "BUNDLE": viewer_bundle(),
        "APP": Path(__file__).with_name("viewer.js").read_text(),
        "REPORT": encoded(payload),
        "SPEC": encoded(spec),
    }
    return re.sub(r"@@(BUNDLE|REPORT|SPEC|APP)@@", lambda m: values[m[1]], template)
