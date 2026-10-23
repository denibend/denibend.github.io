"""Plotly figures for Study 01. Each function takes finished results and only draws them."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Reference data-viz palette (categorical slots in fixed order; light mode).
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
SURFACE = "#fcfcfb"
FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'

FACTOR_LABELS = {"market": "European market", "eurusd": "EUR/USD", "china": "China (Hang Seng)"}


def _style(fig: go.Figure, height: int = 420) -> go.Figure:
    """Shared chrome: system sans, hairline solid grid, recessive axes, legend on top."""
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=16, t=40, b=8),
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font=dict(family=FONT, size=13, color=INK_2),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title_text=""),
        hoverlabel=dict(bgcolor="white", bordercolor=GRID, font=dict(family=FONT, color=INK)),
    )
    axis = dict(
        gridcolor=GRID, gridwidth=1, linecolor=AXIS, zerolinecolor=AXIS, tickfont_color=MUTED
    )
    fig.update_xaxes(**axis)
    fig.update_yaxes(**axis)
    return fig


def performance_index(log_returns: pd.DataFrame, colors: dict[str, str]) -> go.Figure:
    """Total return indexed to 100 at the start, log scale so equal % moves look equal."""
    index = 100 * np.exp(log_returns.cumsum())
    start = log_returns.index[0] - pd.Timedelta(weeks=1)
    index = pd.concat([pd.DataFrame(100.0, index=[start], columns=index.columns), index])
    fig = go.Figure()
    for name in index.columns:
        fig.add_scatter(
            x=index.index,
            y=index[name],
            name=name,
            line=dict(width=2, color=colors[name]),
            hovertemplate="%{y:.0f}",
        )
    fig.update_yaxes(
        type="log",
        title_text="Index, start = 100 (log scale)",
        tickvals=[25, 50, 100, 200, 400, 800],
    )
    fig.update_layout(hovermode="x unified")
    return _style(fig)


def highlight_performance(log_returns: pd.DataFrame, colors: dict[str, str]) -> go.Figure:
    """Indexed performance with one stock in colour and the rest in gray; a menu picks the focus."""
    fig = performance_index(log_returns, colors)
    names = list(log_returns.columns)

    def styles(focus: str) -> dict:
        return {
            "line.color": [colors[n] if n == focus else GRID for n in names],
            "line.width": [2.5 if n == focus else 1.5 for n in names],
        }

    initial = styles(names[0])
    for i, trace in enumerate(fig.data):
        trace.line.color = initial["line.color"][i]
        trace.line.width = initial["line.width"][i]
    # The menu replaces the legend. Gray lines stay thin and light so the focus line reads on top
    # even when it is drawn underneath them.
    fig.update_traces(showlegend=False)
    buttons = [dict(label=n, method="restyle", args=[styles(n)]) for n in names]
    fig.update_layout(
        hovermode="closest",
        updatemenus=[
            dict(
                buttons=buttons,
                x=0,
                xanchor="left",
                y=1.14,
                yanchor="top",
                bgcolor="white",
                bordercolor=GRID,
                font=dict(color=INK),
            )
        ],
    )
    fig.update_traces(hovertemplate="<b>%{y:.0f}</b><br>%{fullData.name}<extra></extra>")
    return fig


def factor_betas(table: pd.DataFrame) -> go.Figure:
    """Dot + 95% CI per stock for each factor; filled dot = significant at 5%."""
    factors = list(FACTOR_LABELS)
    fig = make_subplots(
        rows=1,
        cols=3,
        shared_yaxes=True,
        horizontal_spacing=0.04,
        subplot_titles=[FACTOR_LABELS[f] for f in factors],
    )
    order = table.sort_values("beta_market").index
    in_legend = set()  # legend entry for each marker style, shown once on its first non-empty trace
    for col, f in enumerate(factors, start=1):
        beta = table.loc[order, f"beta_{f}"]
        se = (beta / table.loc[order, f"t_{f}"]).abs()
        significant = table.loc[order, f"p_{f}"] < 0.05
        for sig, symbol, label in [
            (True, "circle", "Significant (p < 0.05)"),
            (False, "circle-open", "Not significant"),
        ]:
            mask = significant == sig
            show = bool(mask.any()) and label not in in_legend
            in_legend |= {label} if show else set()
            fig.add_scatter(
                x=beta[mask],
                y=list(order[mask]),
                error_x=dict(
                    type="data", array=1.96 * se[mask], color=AXIS, thickness=1.5, width=0
                ),
                mode="markers",
                marker=dict(
                    size=10, symbol=symbol, color=SERIES[0], line=dict(width=2, color=SERIES[0])
                ),
                name=label,
                legendgroup=label,
                showlegend=show,
                customdata=np.c_[table.loc[order[mask], f"t_{f}"]],
                hovertemplate="<b>%{x:.2f}</b> (t %{customdata[0]:.1f})<br>%{y}<extra></extra>",
                row=1,
                col=col,
            )
        fig.add_vline(x=0, line=dict(color=AXIS, width=1), row=1, col=col)
    fig.update_annotations(font=dict(size=13, color=INK))
    fig = _style(fig, height=400)
    fig.update_layout(margin=dict(t=80), legend=dict(y=1.2))
    return fig


def rolling_betas_chart(rolling: dict[str, pd.DataFrame]) -> go.Figure:
    """104-week rolling betas; a dropdown picks the stock, three lines show the factors."""
    fig = go.Figure()
    stocks = list(rolling)
    for i, stock in enumerate(stocks):
        for j, (f, label) in enumerate(FACTOR_LABELS.items()):
            fig.add_scatter(
                x=rolling[stock].index,
                y=rolling[stock][f],
                name=label,
                line=dict(width=2, color=SERIES[j]),
                visible=(i == 0),
                hovertemplate="%{y:.2f}",
            )
    buttons = [
        dict(
            label=s,
            method="update",
            args=[{"visible": [k // 3 == i for k in range(3 * len(stocks))]}],
        )
        for i, s in enumerate(stocks)
    ]
    fig.add_hline(y=0, line=dict(color=AXIS, width=1))
    fig.update_layout(
        hovermode="x unified",
        updatemenus=[
            dict(
                buttons=buttons,
                x=1,
                xanchor="right",
                y=1.18,
                yanchor="top",
                bgcolor="white",
                bordercolor=GRID,
                font=dict(color=INK),
            )
        ],
    )
    fig.update_yaxes(title_text="Beta (2-year rolling window)")
    return _style(fig)


def divergence_bars(gap: pd.DataFrame) -> go.Figure:
    """Post-2023 gap vs factor model, split into sector-wide and brand-specific parts."""
    g = (gap * 100).sort_values("total", ascending=False)
    fig = go.Figure()
    for col, label, color in [
        ("sector", "Shared with luxury peers", SERIES[0]),
        ("brand", "Brand-specific", SERIES[1]),
    ]:
        fig.add_bar(
            y=g.index,
            x=g[col],
            name=label,
            orientation="h",
            marker_color=color,
            hovertemplate="<b>%{x:.0f}</b> log pts<br>" + label + "<extra>%{y}</extra>",
        )
    fig.add_scatter(
        y=g.index,
        x=g["total"],
        mode="markers",
        name="Total gap",
        marker=dict(symbol="line-ns", size=18, line=dict(width=3, color=INK)),
        hovertemplate="<b>%{x:.0f}</b> log pts<br>Total gap<extra>%{y}</extra>",
    )
    fig.add_vline(x=0, line=dict(color=AXIS, width=1))
    fig.update_layout(barmode="relative", bargap=0.45)
    fig.update_xaxes(
        title_text="Cumulative log points since Jan 2023 (negative = below factor-implied)"
    )
    return _style(fig, height=400)


def event_dots(events: pd.DataFrame) -> go.Figure:
    """Day-0 abnormal return per announcement with 95% interval, coloured by category."""
    e = events.sort_values("event_day")
    labels = (e["brand"] + " · " + e["person"] + " (" + e["event_day"].str[:7] + ")").str.replace(
        "->", "→"
    )
    fig = go.Figure()
    for i, (cat, label) in enumerate(
        [("creative", "Creative director"), ("management", "CEO / management")]
    ):
        m = e["category"] == cat
        fig.add_scatter(
            x=e.loc[m, "car0"] * 100,
            y=labels[m],
            mode="markers",
            name=label,
            error_x=dict(
                type="data",
                array=1.96 * e.loc[m, "sigma"] * 100,
                color=AXIS,
                thickness=1.5,
                width=0,
            ),
            marker=dict(size=10, color=SERIES[i], line=dict(width=2, color=SURFACE)),
            customdata=np.c_[e.loc[m, "t0"], e.loc[m, "confounders"].fillna("")],
            hovertemplate="<b>%{x:.1f}%</b> (t %{customdata[0]:.1f})<br>%{y}<br>%{customdata[1]}<extra></extra>",
        )
    fig.add_vline(x=0, line=dict(color=AXIS, width=1))
    fig.update_yaxes(
        autorange="reversed",
        tickfont=dict(size=11),
        categoryorder="array",
        categoryarray=list(labels),
    )
    fig.update_xaxes(title_text="Abnormal return on announcement day, % (bar = 95% interval)")
    return _style(fig, height=640)


def event_paths_chart(paths: dict[str, pd.Series], default: int = 0) -> go.Figure:
    """Cumulative abnormal return from 10 days before to 20 days after; dropdown picks the event."""
    fig = go.Figure()
    names = list(paths)
    for i, name in enumerate(names):
        fig.add_scatter(
            x=paths[name].index,
            y=paths[name] * 100,
            name=name,
            showlegend=False,
            line=dict(width=2, color=SERIES[0]),
            visible=(i == default),
            hovertemplate="Day %{x}: <b>%{y:.1f}%</b><extra></extra>",
        )
    buttons = [
        dict(label=n, method="update", args=[{"visible": [k == i for k in range(len(names))]}])
        for i, n in enumerate(names)
    ]
    fig.add_vline(x=0, line=dict(color=MUTED, width=1))
    fig.add_hline(y=0, line=dict(color=AXIS, width=1))
    fig.update_layout(
        updatemenus=[
            dict(
                buttons=buttons,
                active=default,
                x=0,
                xanchor="left",
                y=1.18,
                yanchor="top",
                bgcolor="white",
                bordercolor=GRID,
                font=dict(color=INK),
            )
        ],
    )
    fig.update_xaxes(title_text="Trading days relative to announcement")
    fig.update_yaxes(title_text="Cumulative abnormal return, %")
    return _style(fig, height=380)
