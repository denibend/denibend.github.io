"""Plotly figures for Study 02. Each function takes finished results and only draws them."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go

# Shared chart chrome and palette from Study 01, so the portfolio reads as one system.
from studies.luxury_drivers.charts import AXIS, GRID, INK, MUTED, SERIES, SURFACE
from studies.luxury_drivers.charts import _style as style

DRIVER_LABELS = {
    "income": "Income",
    "equity": "Equity wealth (mostly top 10%)",
    "housing": "Housing wealth (middle class)",
}


def driver_effects(effects: pd.DataFrame) -> go.Figure:
    """Grouped horizontal bars: typical-quarter effect of each driver on each spending category."""
    fig = go.Figure()
    order = list(effects["category"].drop_duplicates())[::-1]
    for i, (key, label) in enumerate(DRIVER_LABELS.items()):
        d = effects[effects["driver"] == key].set_index("category").reindex(order)
        fig.add_bar(
            y=d.index,
            x=d["effect"],
            name=label,
            orientation="h",
            marker_color=SERIES[i],
            customdata=np.c_[d["elasticity"], d["t"]],
            hovertemplate="<b>%{x:.2f}%</b> of spending<br>elasticity %{customdata[0]:.2f} "
            "(t %{customdata[1]:.1f})<extra>%{y}</extra>",
        )
    fig.add_vline(x=0, line=dict(color=AXIS, width=1))
    fig.update_layout(barmode="group", bargap=0.3, bargroupgap=0.08)
    fig.update_xaxes(
        title_text="Spending response over a year to a typical one-quarter move (% of spending)"
    )
    return style(fig, height=520)


def holdings(shares: pd.DataFrame) -> go.Figure:
    """Stacked bars: share of US household equities and real estate held by each wealth group."""
    fig = go.Figure()
    for i, group in enumerate(shares.columns):
        fig.add_bar(
            y=shares.index,
            x=shares[group],
            name=group,
            orientation="h",
            marker=dict(color=SERIES[i], line=dict(color=SURFACE, width=2)),
            hovertemplate="<b>%{x:.0f}%</b> held by " + group + "<extra>%{y}</extra>",
        )
    fig.update_layout(barmode="stack", bargap=0.45, legend=dict(traceorder="normal"))
    fig.update_xaxes(title_text="Share of all US household holdings (%)", range=[0, 100])
    return style(fig, height=260)


def confidence_by_sample(results: pd.DataFrame) -> go.Figure:
    """Dot + 95% interval: effect of a 1-point confidence rise on the top-minus-aspirational spread."""
    fig = go.Figure()
    fig.add_scatter(
        x=results["coef"] * 100,
        y=results["sample"],
        mode="markers",
        error_x=dict(
            type="data", array=1.96 * results["se"] * 100, color=AXIS, thickness=1.5, width=0
        ),
        marker=dict(size=11, color=SERIES[0], line=dict(width=2, color=SURFACE)),
        customdata=np.c_[results["t"], results["n"]],
        hovertemplate="<b>%{x:.2f}%</b> per point (t %{customdata[0]:.1f}, n %{customdata[1]})<extra>%{y}</extra>",
        showlegend=False,
    )
    fig.add_vline(x=0, line=dict(color=AXIS, width=1))
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(
        title_text="Top-tier minus aspirational monthly return per +1 point of EU confidence (%)"
    )
    return style(fig, height=280)


def category_deviation(dev: pd.DataFrame) -> go.Figure:
    """Lines per category: real volume vs its 2010-19 trend (%), a menu switches goods / experiences."""
    fig = go.Figure()
    groups = {"Luxury-type goods": [], "Experiences": []}
    for i, (cat, (label, group)) in enumerate(dev.attrs["labels"].items()):
        groups[group].append(i)
        fig.add_scatter(
            x=dev.index,
            y=dev[cat],
            name=label,
            mode="lines+markers",
            line=dict(width=2, color=SERIES[i]),  # 8 categories, 8 slots, fixed order
            marker=dict(size=7),
            visible=True,
            hovertemplate="%{y:+.1f}%<extra>" + label + "</extra>",
        )
    n = len(fig.data)
    buttons = [dict(label="All categories", method="update", args=[{"visible": [True] * n}])]
    for g, idx in groups.items():
        buttons.append(
            dict(label=g, method="update", args=[{"visible": [k in idx for k in range(n)]}])
        )
    fig.add_hline(y=0, line=dict(color=AXIS, width=1))
    fig.update_layout(
        hovermode="x unified",
        updatemenus=[
            dict(
                buttons=buttons,
                x=0,
                xanchor="left",
                y=1.32,
                yanchor="top",
                bgcolor="white",
                bordercolor=GRID,
                font=dict(color=INK),
            )
        ],
    )
    fig.update_yaxes(title_text="Real volume vs 2010–19 trend (%)")
    fig.update_xaxes(dtick=1)
    # Menu sits above the legend so it cannot hide a legend entry.
    fig = style(fig, height=480)
    fig.update_layout(margin=dict(t=110), legend=dict(y=1.04))
    return fig


def share_vs_trend(d: pd.DataFrame) -> go.Figure:
    """Experiences share of US spending: actual vs extrapolated 2010-19 trend."""
    fig = go.Figure()
    fig.add_scatter(
        x=d.index,
        y=d["trend"],
        name="2010–19 trend, extrapolated",
        line=dict(width=2, color=MUTED, dash="dot"),
        hovertemplate="%{y:.2f}%",
    )
    fig.add_scatter(
        x=d.index,
        y=d["actual"],
        name="Actual",
        line=dict(width=2, color=SERIES[0]),
        hovertemplate="%{y:.2f}%",
    )
    fig.update_layout(hovermode="x unified")
    fig.update_yaxes(title_text="Experiences, % of US consumer spending")
    return style(fig, height=360)


def eu_shift(dev: pd.DataFrame) -> go.Figure:
    """Grouped bars by country: semi-durables vs services, real volume vs 2011-19 trend."""
    fig = go.Figure()
    for i, col in enumerate(["Semi-durable goods", "Services"]):
        fig.add_bar(
            x=dev.index,
            y=dev[col],
            name=col,
            marker_color=SERIES[i],
            hovertemplate="<b>%{y:+.1f}%</b><extra>" + col + " · %{x}</extra>",
        )
    fig.add_hline(y=0, line=dict(color=AXIS, width=1))
    fig.update_layout(barmode="group", bargap=0.35)
    fig.update_yaxes(title_text="Real volume vs 2011–19 trend, latest year (%)")
    return style(fig, height=360)


def hk_per_visitor(annual: pd.Series) -> go.Figure:
    """Bars: HK jewellery & watch sales per mainland visitor (HK$), excluding border-closure years."""
    fig = go.Figure()
    fig.add_bar(
        x=annual.index,
        y=annual.values,
        marker_color=SERIES[0],
        showlegend=False,
        hovertemplate="<b>HK$%{y:,.0f}</b><extra>%{x}</extra>",
    )
    fig.update_layout(bargap=0.35)
    fig.update_yaxes(title_text="HK$ per mainland visitor")
    fig.update_xaxes(dtick=1)
    return style(fig, height=360)


def hk_actual_vs_model(d: pd.DataFrame) -> go.Figure:
    """Lines: actual yoy growth of HK jewellery sales vs the 2005-19 model's prediction."""
    fig = go.Figure()
    fig.add_scatter(
        x=d.index,
        y=d["predicted"] * 100,
        name="Predicted by 2005–19 model",
        line=dict(width=2, color=MUTED, dash="dot"),
        hovertemplate="%{y:+.1f}%",
    )
    fig.add_scatter(
        x=d.index,
        y=d["actual"] * 100,
        name="Actual",
        line=dict(width=2, color=SERIES[0]),
        hovertemplate="%{y:+.1f}%",
    )
    fig.add_hline(y=0, line=dict(color=AXIS, width=1))
    fig.update_layout(hovermode="x unified")
    fig.update_yaxes(title_text="Year-on-year growth (%)")
    return style(fig, height=360)


def regional_mix(shares: pd.DataFrame, years: list[int]) -> go.Figure:
    """Stacked bars of regional shares per company; a menu picks the year."""
    buckets = {
        "asia": "Asia (incl. Japan)",
        "europe": "Europe / EMEA",
        "americas": "Americas",
        "other": "Other",
    }
    fig = go.Figure()
    companies = list(shares.xs(years[-1], level="fiscal_year").sort_values("asia").index)
    for yi, year in enumerate(years):
        s = shares.xs(year, level="fiscal_year").reindex(companies)
        for bi, (b, label) in enumerate(buckets.items()):
            fig.add_bar(
                y=companies,
                x=s[b],
                name=label,
                orientation="h",
                legendgroup=label,
                showlegend=(yi == len(years) - 1),
                visible=(yi == len(years) - 1),
                marker=dict(color=SERIES[bi], line=dict(color=SURFACE, width=2)),
                hovertemplate="<b>%{x:.0f}%</b> " + label + f" ({year})<extra>%{{y}}</extra>",
            )
    nb = len(buckets)
    buttons = [
        dict(
            label=str(y),
            method="update",
            args=[
                {
                    "visible": [k // nb == i for k in range(nb * len(years))],
                    "showlegend": [k // nb == i for k in range(nb * len(years))],
                }
            ],
        )
        for i, y in enumerate(years)
    ]
    fig.update_layout(
        barmode="stack",
        bargap=0.35,
        updatemenus=[
            dict(
                buttons=buttons,
                active=len(years) - 1,
                x=1,
                xanchor="right",
                y=1.2,
                yanchor="top",
                bgcolor="white",
                bordercolor=GRID,
                font=dict(color=INK),
            )
        ],
    )
    fig.update_xaxes(title_text="Share of revenue (%)", range=[0, 100])
    return style(fig, height=420)


# Moncler and Prada sit almost on the same point (Asia share ~43%, gap ~+4): label one below.
LABEL_POSITION = {"Moncler": "bottom center"}


def asia_vs_gap(d: pd.DataFrame) -> go.Figure:
    """Scatter: 2022 Asia share vs post-2023 brand-specific gap, labelled by company (n = 8)."""
    fig = go.Figure()
    fig.add_scatter(
        x=d["asia_2022"],
        y=d["brand_gap"],
        mode="markers+text",
        text=d.index,
        textposition=[LABEL_POSITION.get(c, "top center") for c in d.index],
        textfont=dict(size=11, color=INK),
        marker=dict(size=12, color=SERIES[0], line=dict(width=2, color=SURFACE)),
        hovertemplate="<b>%{text}</b><br>Asia share 2022: %{x:.0f}%<br>Brand-specific gap: %{y:.0f} pts<extra></extra>",
        showlegend=False,
    )
    fig.add_hline(y=0, line=dict(color=AXIS, width=1))
    fig.update_xaxes(title_text="Asia (incl. Japan) share of revenue, 2022 (%)")
    fig.update_yaxes(title_text="Brand-specific gap since 2023 (log points, Study 01)")
    return style(fig, height=440)
