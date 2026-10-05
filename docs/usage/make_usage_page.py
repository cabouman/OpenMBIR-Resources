"""Build docs/usage/index.html, the OpenMBIR usage page, from usage_data.json.

usage_data.json is a snapshot of three sources, gathered by hand on the date
recorded in it: the conda-forge download counts of svmbir (anaconda.org API),
the daily PyPI downloads of svmbir, mbirjax, and mbirtorch with mirrors
excluded (pypistats.org), and the GitHub star dates and repository counts
(GitHub API).  The page is static HTML with inline SVG charts and a small
script for the hover tooltips.

Run:  python3 make_usage_page.py
"""

import collections
import datetime as dt
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = json.load(open(os.path.join(HERE, 'usage_data.json')))

# Chart geometry (SVG user units; the SVG scales to the page width).
W, H = 760, 340
ML, MR, MT, MB = 64, 24, 20, 56

SERIES = {  # fixed categorical slots, one per package, never reassigned
    'svmbir': 1, 'mbirjax': 2, 'mbirtorch': 3, 'mbircone': 4, 'mbirhelical': 5,
}


def fmt(n):
    return f'{n:,}'


def month_name(iso):
    d = dt.date.fromisoformat(iso[:10])
    return d.strftime('%b %Y')


# ----------------------------------------------------------------------------
# Data preparation
# ----------------------------------------------------------------------------

def conda_by_version():
    """Return rows (version, first upload date, downloads, months current, per month)."""
    rows = {}
    for f in DATA['conda_files']:
        r = rows.setdefault(f['version'], {'date': f['upload_time'][:10], 'downloads': 0})
        r['downloads'] += f['ndownloads']
        r['date'] = min(r['date'], f['upload_time'][:10])
    order = sorted(rows, key=lambda v: rows[v]['date'])
    end = dt.date.fromisoformat(DATA['generated'])
    out = []
    for i, v in enumerate(order):
        start = dt.date.fromisoformat(rows[v]['date'])
        stop = dt.date.fromisoformat(rows[order[i + 1]]['date']) if i + 1 < len(order) else end
        months = max((stop - start).days / 30.44, 0.5)
        out.append(dict(version=v, date=rows[v]['date'], downloads=rows[v]['downloads'],
                        months=months, per_month=rows[v]['downloads'] / months))
    return out


def pypi_weekly():
    """Return (week start dates, {package: weekly totals}) over the common window."""
    daily = DATA['pypi_daily']
    all_dates = sorted(set(d for s in daily.values() for d in s))
    first = dt.date.fromisoformat(all_dates[0])
    last = dt.date.fromisoformat(all_dates[-1])
    # Whole weeks (Monday to Sunday) inside the window.
    start = first + dt.timedelta(days=(7 - first.weekday()) % 7)
    weeks = []
    w = start
    while w + dt.timedelta(days=6) <= last:
        weeks.append(w)
        w += dt.timedelta(days=7)
    totals = {}
    for pkg, series in daily.items():
        vals = []
        for w in weeks:
            days = [w + dt.timedelta(days=k) for k in range(7)]
            vals.append(sum(series.get(d.isoformat(), 0) for d in days))
        totals[pkg] = vals
    return weeks, totals


def stars_cumulative():
    """Return (dates, {repo: cumulative stars at each date}) as step data."""
    out = {}
    for repo, dates in DATA['github_stars'].items():
        pts = []
        for i, d in enumerate(dates):
            pts.append((dt.date.fromisoformat(d), i + 1))
        out[repo] = pts
    return out


# ----------------------------------------------------------------------------
# SVG helpers
# ----------------------------------------------------------------------------

def nice_ticks(vmax, n=5):
    """Return clean tick values whose top is the smallest clean multiple above vmax,
    using at most n intervals."""
    import math
    mag = 10 ** (len(str(int(vmax))) - 1)
    best = None
    for m in (0.1, 0.2, 0.25, 0.5, 1, 2, 2.5, 5, 10):
        step = m * mag
        k = math.ceil(vmax / step)
        if 1 <= k <= n and (best is None or step * k < best[0] * best[1]):
            best = (step, k)
    step, k = best
    return [step * i for i in range(k + 1)], step * k


def svg_open(title_id, desc):
    return (f'<svg viewBox="0 0 {W} {H}" role="img" aria-labelledby="{title_id}" '
            f'class="chart"><title id="{title_id}">{desc}</title>')


def axis_y(ticks, top, plot_h, label_fmt=fmt):
    parts = []
    for t in ticks:
        y = MT + plot_h - t / top * plot_h
        parts.append(f'<line class="grid" x1="{ML}" x2="{W - MR}" y1="{y:.1f}" y2="{y:.1f}"/>')
        parts.append(f'<text class="tick" x="{ML - 8}" y="{y + 4:.1f}" text-anchor="end">{label_fmt(int(t))}</text>')
    return ''.join(parts)


def legend(names):
    items = []
    for i, n in enumerate(names):
        items.append(f'<span class="key"><i class="swatch s{SERIES[n]}"></i>{n}</span>')
    return '<div class="legend" aria-label="Legend">' + ''.join(items) + '</div>'


# ----------------------------------------------------------------------------
# Charts
# ----------------------------------------------------------------------------

def chart_conda(rows):
    plot_w, plot_h = W - ML - MR, H - MT - MB
    vmax = max(r['downloads'] for r in rows)
    ticks, top = nice_ticks(vmax)
    n = len(rows)
    band = plot_w / n
    bar_w = min(24, band * 0.6)
    s = [svg_open('t-conda', 'Downloads of each svmbir version from conda-forge')]
    s.append(axis_y(ticks, top, plot_h))
    s.append(f'<line class="axis" x1="{ML}" x2="{W - MR}" y1="{MT + plot_h}" y2="{MT + plot_h}"/>')
    best = max(rows, key=lambda r: r['downloads'])
    for i, r in enumerate(rows):
        x = ML + band * (i + 0.5) - bar_w / 2
        h = r['downloads'] / top * plot_h
        y = MT + plot_h - h
        tip = (f"svmbir {r['version']}|{fmt(r['downloads'])} downloads|released {month_name(r['date'])}|"
               f"about {fmt(int(round(r['per_month'], -2)))} a month while current")
        s.append(f'<g class="col" tabindex="0" data-tip="{tip}">'
                 f'<rect class="hit" x="{x - band * 0.2:.1f}" y="{MT}" width="{bar_w + band * 0.4:.1f}" height="{plot_h}"/>'
                 f'<path class="bar s{SERIES["svmbir"]}" d="M{x:.1f},{MT + plot_h} v{-(h - 4):.1f} a4,4 0 0 1 4,-4 h{bar_w - 8:.1f} a4,4 0 0 1 4,4 v{h - 4:.1f} z"/>'
                 f'</g>')
        if r is best:
            s.append(f'<text class="label" x="{x + bar_w / 2:.1f}" y="{y - 8:.1f}" text-anchor="middle">{fmt(r["downloads"])}</text>')
        s.append(f'<text class="tick" x="{ML + band * (i + 0.5):.1f}" y="{MT + plot_h + 18}" text-anchor="middle">{r["version"]}</text>')
        s.append(f'<text class="tick muted" x="{ML + band * (i + 0.5):.1f}" y="{MT + plot_h + 34}" text-anchor="middle">{month_name(r["date"])}</text>')
    s.append('</svg>')
    return ''.join(s)


def line_chart(title_id, desc, xs, series, x_labels, y_fmt=fmt, step=False):
    """xs: list of dates (shared); series: {name: [values]} aligned to xs (None = no data)."""
    plot_w, plot_h = W - ML - MR, H - MT - MB
    vmax = max(v for vals in series.values() for v in vals if v is not None)
    ticks, top = nice_ticks(vmax)
    x0, x1 = xs[0].toordinal(), xs[-1].toordinal()

    def X(d):
        return ML + (d.toordinal() - x0) / max(x1 - x0, 1) * plot_w

    def Y(v):
        return MT + plot_h - v / top * plot_h

    s = [svg_open(title_id, desc)]
    s.append(axis_y(ticks, top, plot_h, y_fmt))
    s.append(f'<line class="axis" x1="{ML}" x2="{W - MR}" y1="{MT + plot_h}" y2="{MT + plot_h}"/>')
    for d, text in x_labels:
        s.append(f'<text class="tick" x="{X(d):.1f}" y="{MT + plot_h + 18}" text-anchor="middle">{text}</text>')
    points_json = []
    for name, vals in series.items():
        pts = [(X(d), Y(v)) for d, v in zip(xs, vals) if v is not None]
        if not pts:
            continue
        if step:
            path = f'M{pts[0][0]:.1f},{pts[0][1]:.1f}' + ''.join(
                f'H{x:.1f}V{y:.1f}' for x, y in pts[1:]) + f'H{X(xs[-1]):.1f}'
        else:
            path = 'M' + 'L'.join(f'{x:.1f},{y:.1f}' for x, y in pts)
        s.append(f'<path class="line s{SERIES[name]}" d="{path}"/>')
        ex, ey = pts[-1] if not step else (X(xs[-1]), pts[-1][1])
        s.append(f'<circle class="dot s{SERIES[name]}" cx="{ex:.1f}" cy="{ey:.1f}" r="4"/>')
        s.append(f'<text class="label" x="{ex + 8:.1f}" y="{ey + 4:.1f}">{name}</text>')
    # Crosshair data: one row per x with every series value.
    rows = []
    for i, d in enumerate(xs):
        rows.append({'x': round(X(d), 1), 'label': d.strftime('%b %d, %Y'),
                     'values': {n: (vals[i] if vals[i] is not None else None) for n, vals in series.items()}})
    s.append(f'<line class="crosshair" x1="0" x2="0" y1="{MT}" y2="{MT + plot_h}" visibility="hidden"/>')
    s.append(f'<rect class="hit-all" x="{ML}" y="{MT}" width="{plot_w}" height="{plot_h}" '
             f"data-rows='{json.dumps(rows)}'/>")
    s.append('</svg>')
    return ''.join(s)


# ----------------------------------------------------------------------------
# Page
# ----------------------------------------------------------------------------

def build():
    conda_rows = conda_by_version()
    conda_total = sum(r['downloads'] for r in conda_rows)
    current = conda_rows[-1]
    by_platform = collections.Counter()
    for f in DATA['conda_files']:
        by_platform[f['subdir']] += f['ndownloads']

    weeks, weekly = pypi_weekly()
    last30 = {}
    for pkg, series in DATA['pypi_daily'].items():
        dates = sorted(series)[-30:]
        last30[pkg] = sum(series[d] for d in dates)
    six_months = {pkg: sum(v.values()) for pkg, v in DATA['pypi_daily'].items()}

    star_pts = stars_cumulative()
    # A shared monthly grid for the step chart.
    first_star = min(p[0][0] for p in star_pts.values())
    end = dt.date.fromisoformat(DATA['generated'])
    grid = []
    d = dt.date(first_star.year, first_star.month, 1)
    while d <= end:
        grid.append(d)
        d = dt.date(d.year + (d.month // 12), d.month % 12 + 1, 1)
    grid.append(end)
    star_series = {}
    for repo, pts in star_pts.items():
        vals = []
        for g in grid:
            n = sum(1 for p in pts if p[0] <= g)
            vals.append(n if n > 0 else None)
        star_series[repo] = vals
    star_labels = [(dt.date(y, 1, 1), str(y)) for y in range(first_star.year + 1, end.year + 1)]

    week_labels = [(w, w.strftime('%b')) for w in weeks if w.day <= 7]

    pypi_names = ['svmbir', 'mbirjax', 'mbirtorch']
    pypi_series = {}
    for n in pypi_names:
        vals = weekly[n]
        # mbirtorch has no data before its first release; hide the zeros before it.
        first_nonzero = next((i for i, v in enumerate(vals) if v > 0), None)
        pypi_series[n] = [v if first_nonzero is not None and i >= first_nonzero else None
                          for i, v in enumerate(vals)]

    gh = DATA['github']
    gh_rows = ''.join(
        f'<tr><td><a href="https://github.com/cabouman/{r}">{r}</a></td><td>{gh[r]["stars"]}</td>'
        f'<td>{gh[r]["forks"]}</td><td>{gh[r]["created"]}</td></tr>'
        for r in ('svmbir', 'mbirjax', 'mbirtorch', 'mbircone', 'mbirhelical', 'xcal'))

    generated = dt.date.fromisoformat(DATA['generated']).strftime('%B %d, %Y')

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>OpenMBIR Usage</title>
<meta name="description" content="How many people download and use the OpenMBIR software packages: svmbir, mbirjax, and mbirtorch.">
<style>
:root {{
  color-scheme: light;
  --surface: #fcfcfb; --surface-2: #f1f1ee; --grid: #e4e4df;
  --text: #0b0b0b; --text-2: #52514e; --muted: #7d7c78;
  --s1: #2a78d6; --s2: #eb6834; --s3: #1baf7a; --s4: #eda100; --s5: #e87ba4;
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    color-scheme: dark;
    --surface: #1a1a19; --surface-2: #232322; --grid: #343431;
    --text: #ffffff; --text-2: #c3c2b7; --muted: #8f8e88;
    --s1: #3987e5; --s2: #d95926; --s3: #199e70; --s4: #c98500; --s5: #d55181;
  }}
}}
:root[data-theme="dark"] {{
  color-scheme: dark;
  --surface: #1a1a19; --surface-2: #232322; --grid: #343431;
  --text: #ffffff; --text-2: #c3c2b7; --muted: #8f8e88;
  --s1: #3987e5; --s2: #d95926; --s3: #199e70; --s4: #c98500; --s5: #d55181;
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--surface); color: var(--text);
  font: 16px/1.5 -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; }}
main {{ max-width: 860px; margin: 0 auto; padding: 32px 16px 64px; }}
h1 {{ font-size: 1.8rem; margin: 0 0 4px; }}
h2 {{ font-size: 1.25rem; margin: 40px 0 8px; }}
p {{ margin: 8px 0; color: var(--text-2); }}
p.lead {{ color: var(--text); font-size: 1.05rem; }}
a {{ color: var(--s1); }}
.tiles {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin: 20px 0; }}
.tile {{ background: var(--surface-2); border-radius: 8px; padding: 14px 16px; }}
.tile .n {{ font-size: 1.7rem; font-weight: 600; line-height: 1.2; }}
.tile .l {{ color: var(--text-2); font-size: 0.9rem; }}
figure {{ margin: 12px 0 0; position: relative; }}
figcaption {{ color: var(--text-2); font-size: 0.9rem; margin: 4px 0 0; }}
.chart {{ width: 100%; height: auto; display: block; overflow: visible; }}
.grid {{ stroke: var(--grid); stroke-width: 1; }}
.axis {{ stroke: var(--grid); stroke-width: 1; }}
.tick {{ fill: var(--text-2); font-size: 12px; }}
.tick.muted {{ fill: var(--muted); font-size: 11px; }}
.label {{ fill: var(--text); font-size: 12px; font-weight: 600; }}
.bar {{ stroke: none; }}
.bar.s1 {{ fill: var(--s1); }}
.line {{ fill: none; stroke-width: 2; stroke-linejoin: round; stroke-linecap: round; }}
.dot {{ stroke: var(--surface); stroke-width: 2; }}
.line.s1, .dot.s1 {{ stroke: var(--s1); }} .dot.s1 {{ fill: var(--s1); }}
.line.s2, .dot.s2 {{ stroke: var(--s2); }} .dot.s2 {{ fill: var(--s2); }}
.line.s3, .dot.s3 {{ stroke: var(--s3); }} .dot.s3 {{ fill: var(--s3); }}
.line.s4, .dot.s4 {{ stroke: var(--s4); }} .dot.s4 {{ fill: var(--s4); }}
.line.s5, .dot.s5 {{ stroke: var(--s5); }} .dot.s5 {{ fill: var(--s5); }}
.hit, .hit-all {{ fill: transparent; }}
.col:hover .bar, .col:focus .bar {{ filter: brightness(1.15); }}
.col:focus {{ outline: none; }}
.crosshair {{ stroke: var(--text-2); stroke-width: 1; }}
.legend {{ display: flex; flex-wrap: wrap; gap: 6px 18px; font-size: 0.9rem; color: var(--text-2); margin: 6px 0 0; }}
.swatch {{ display: inline-block; width: 14px; height: 3px; vertical-align: middle; margin-right: 6px; border-radius: 2px; }}
.swatch.s1 {{ background: var(--s1); }} .swatch.s2 {{ background: var(--s2); }} .swatch.s3 {{ background: var(--s3); }}
.swatch.s4 {{ background: var(--s4); }} .swatch.s5 {{ background: var(--s5); }}
.tip {{ position: absolute; pointer-events: none; background: var(--surface-2); color: var(--text);
  border: 1px solid var(--grid); border-radius: 6px; padding: 8px 10px; font-size: 0.85rem; line-height: 1.35;
  box-shadow: 0 2px 8px rgba(0,0,0,.12); display: none; max-width: 260px; z-index: 2; }}
.tip b {{ font-weight: 600; }}
.tip .row {{ display: flex; gap: 8px; align-items: center; }}
.tip .row i {{ display: inline-block; width: 12px; height: 3px; border-radius: 2px; }}
table {{ border-collapse: collapse; margin: 8px 0; width: 100%; max-width: 520px; font-size: 0.95rem; }}
th, td {{ text-align: left; padding: 6px 10px; border-bottom: 1px solid var(--grid); }}
th {{ color: var(--text-2); font-weight: 600; }}
td:nth-child(n+2), th:nth-child(n+2) {{ text-align: right; }}
.note {{ font-size: 0.9rem; }}
footer {{ margin-top: 48px; color: var(--muted); font-size: 0.85rem; }}
</style>
</head>
<body>
<main>
<h1>OpenMBIR usage</h1>
<p class="lead">How many people download and use the <a href="https://github.com/cabouman/OpenMBIR-Resources">OpenMBIR</a>
software packages for model-based iterative reconstruction: <a href="https://github.com/cabouman/svmbir">svmbir</a>,
<a href="https://github.com/cabouman/mbirjax">mbirjax</a>, and <a href="https://github.com/cabouman/mbirtorch">mbirtorch</a>.
Counts gathered on {generated}.</p>

<div class="tiles">
  <div class="tile"><div class="n">{fmt(conda_total)}</div><div class="l">svmbir downloads from conda-forge since 2022</div></div>
  <div class="tile"><div class="n">{fmt(int(round(current['per_month'], -2)))}</div><div class="l">a month for the current svmbir version</div></div>
  <div class="tile"><div class="n">{fmt(last30['svmbir'] + last30['mbirjax'] + last30['mbirtorch'])}</div><div class="l">PyPI installs of the three packages in the last 30 days</div></div>
</div>

<h2>svmbir on conda-forge</h2>
<p>conda-forge is svmbir's main channel. Each column is one released version and the number of times its
conda-forge package has been downloaded. Downloads of a version keep accumulating after the next one is
released, so the newest version is still growing.</p>
<figure>
{chart_conda(conda_rows)}
<figcaption>Downloads of each svmbir version from conda-forge, by release date. Source: anaconda.org.</figcaption>
</figure>
<p class="note">Of these downloads, {fmt(by_platform.get('linux-64', 0))} were the Linux package and
{fmt(by_platform.get('osx-64', 0))} the Intel Mac package. No Apple Silicon package existed before
version 0.5.0. conda-forge counts every download, including mirrors and automated systems, so the number of
people is smaller than the number of downloads.</p>

<h2>PyPI downloads</h2>
<p>Weekly downloads from PyPI with mirrors excluded, which is closer to real installs. mbirtorch was first
released in August 2026. In the last six months: svmbir {fmt(six_months['svmbir'])}, mbirjax {fmt(six_months['mbirjax'])},
mbirtorch {fmt(six_months['mbirtorch'])}.</p>
<figure>
{line_chart('t-pypi', 'Weekly PyPI downloads of svmbir, mbirjax, and mbirtorch', weeks, pypi_series, week_labels)}
<figcaption>Weekly PyPI downloads, mirrors excluded, whole weeks only. Source: pypistats.org.</figcaption>
</figure>
{legend(pypi_names)}

<h2>GitHub stars</h2>
<p>Stars are readers who bookmarked a repository. The counts are small, as they are for most scientific
software, but they show when each package found its audience.</p>
<figure>
{line_chart('t-stars', 'Cumulative GitHub stars of the OpenMBIR repositories over time', grid, star_series, star_labels, step=True)}
<figcaption>Cumulative GitHub stars by month. Source: GitHub.</figcaption>
</figure>
{legend(['svmbir', 'mbirjax', 'mbircone', 'mbirhelical'])}

<table>
<thead><tr><th>Repository</th><th>Stars</th><th>Forks</th><th>Created</th></tr></thead>
<tbody>{gh_rows}</tbody>
</table>

<h2>Sources</h2>
<p class="note">conda-forge counts: the anaconda.org API, all files of the svmbir package, totals since the first
conda-forge release in 2022. PyPI counts: pypistats.org, daily downloads with mirrors excluded, the most recent
six months. GitHub: the repositories' star dates and counts. The data snapshot and the script that draws this page
are in the <a href="https://github.com/cabouman/OpenMBIR-Resources/tree/main/docs/usage">OpenMBIR-Resources</a>
repository.</p>

<footer>OpenMBIR usage page, generated {generated}.</footer>
</main>
<div class="tip" id="tip" role="status"></div>
<script>
(function () {{
  var tip = document.getElementById('tip');
  var colors = {{s1: 'var(--s1)', s2: 'var(--s2)', s3: 'var(--s3)', s4: 'var(--s4)', s5: 'var(--s5)'}};
  var slots = {json.dumps({k: 's' + str(v) for k, v in SERIES.items()})};
  function show(x, y, lines) {{
    while (tip.firstChild) tip.removeChild(tip.firstChild);
    lines.forEach(function (ln) {{
      var row = document.createElement('div'); row.className = 'row';
      if (ln.series) {{ var i = document.createElement('i'); i.style.background = colors[slots[ln.series]]; row.appendChild(i); }}
      var t = document.createElement(ln.strong ? 'b' : 'span'); t.textContent = ln.text; row.appendChild(t);
      tip.appendChild(row);
    }});
    tip.style.display = 'block';
    var w = tip.offsetWidth, h = tip.offsetHeight;
    var left = x + 14, top = y + 14;
    if (left + w > window.innerWidth - 8) left = x - w - 14;
    if (top + h > window.innerHeight - 8) top = y - h - 14;
    tip.style.left = (left + window.scrollX) + 'px'; tip.style.top = (top + window.scrollY) + 'px';
  }}
  function hide() {{ tip.style.display = 'none'; }}
  document.querySelectorAll('.col').forEach(function (g) {{
    var parts = g.getAttribute('data-tip').split('|');
    var lines = parts.map(function (p, i) {{ return {{text: p, strong: i === 1}}; }});
    g.addEventListener('pointermove', function (e) {{ show(e.clientX, e.clientY, lines); }});
    g.addEventListener('focus', function () {{ var r = g.getBoundingClientRect(); show(r.left + r.width / 2, r.top, lines); }});
    g.addEventListener('pointerleave', hide); g.addEventListener('blur', hide);
  }});
  document.querySelectorAll('.hit-all').forEach(function (rect) {{
    var svg = rect.ownerSVGElement, rows = JSON.parse(rect.getAttribute('data-rows'));
    var cross = svg.querySelector('.crosshair');
    rect.addEventListener('pointermove', function (e) {{
      var pt = svg.createSVGPoint(); pt.x = e.clientX; pt.y = e.clientY;
      var p = pt.matrixTransform(svg.getScreenCTM().inverse());
      var best = rows[0], d = Infinity;
      rows.forEach(function (r) {{ var dd = Math.abs(r.x - p.x); if (dd < d) {{ d = dd; best = r; }} }});
      cross.setAttribute('x1', best.x); cross.setAttribute('x2', best.x); cross.setAttribute('visibility', 'visible');
      var lines = [{{text: best.label}}];
      Object.keys(best.values).forEach(function (k) {{
        if (best.values[k] !== null) lines.push({{text: best.values[k].toLocaleString() + '  ' + k, series: k, strong: true}});
      }});
      show(e.clientX, e.clientY, lines);
    }});
    rect.addEventListener('pointerleave', function () {{ cross.setAttribute('visibility', 'hidden'); hide(); }});
  }});
}})();
</script>
</body>
</html>
'''
    with open(os.path.join(HERE, 'index.html'), 'w') as f:
        f.write(html)
    print('wrote index.html:', len(html), 'bytes')


if __name__ == '__main__':
    build()
