"""Dependency-free, offline HTML forecast visualization; no wagering features."""
from __future__ import annotations

from html import escape
from pathlib import Path

from .model import Forecast


def render_forecast_report(
    prediction: Forecast, *, dataset_id: str, dataset_sha256: str,
    source_name: str, synthetic: bool,
) -> str:
    """Render only local, checksum-verified research inputs into escaped HTML."""
    esc = lambda value: escape(str(value), quote=True)
    low80, high80 = prediction.central_interval(0.8)
    low90, high90 = prediction.central_interval(0.9)
    modal = prediction.modal_bucket()
    rows = []
    for bucket in prediction.buckets():
        probability = bucket.probability * 100
        if probability < 0.01:
            continue
        label = str(bucket.low) if bucket.low == bucket.high else f"{bucket.low}–{bucket.high}"
        rows.append(
            '<tr><th scope="row">' + esc(label) + '</th><td>' +
            f'{probability:.2f}%' + '</td><td><div class="track"><span style="width:' +
            f'{probability:.4f}%' + '"></span></div></td></tr>'
        )
    dataset_label = 'ENGINEERED SYNTHETIC DATA' if synthetic else 'USER-DECLARED RESEARCH DATA'
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>SportProb · {esc(prediction.player_id)} · {esc(prediction.stat)}</title>
<style>
:root{{color-scheme:dark;font-family:system-ui,-apple-system,Segoe UI,sans-serif}}
body{{background:#08121c;color:#edf4fa;margin:0;line-height:1.5}}
main{{max-width:920px;margin:auto;padding:32px 20px 70px}}
header{{border-bottom:1px solid #344455;padding-bottom:24px;margin-bottom:25px}}
.eyebrow{{color:#8dc7d2;letter-spacing:.13em;font-size:.75rem;font-weight:700}}
h1{{font-size:clamp(1.7rem,4vw,2.6rem);letter-spacing:-.045em;margin:10px 0}}
h2{{font-size:1.1rem;margin:0 0 18px}}
p,.subtle{{color:#b0becc}}
.flag{{background:#172b3a;border:1px solid #35616d;border-radius:9px;padding:12px 14px;color:#d5eaf0;margin:18px 0}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:22px}}
.card,section{{background:#111e2b;border:1px solid #304153;border-radius:12px;padding:18px}}
.card span{{display:block;color:#b0becc;font-size:.85rem}}
.card strong{{display:block;font-size:1.65rem;margin:6px 0}}
section{{margin:16px 0}}
table{{width:100%;border-collapse:collapse;text-align:left}}
td,th{{padding:9px;border-bottom:1px solid #2b3b49;font-size:.94rem}}
th{{font-weight:600}}
.track{{height:12px;background:#203343;border-radius:999px;overflow:hidden}}
.track span{{display:block;height:100%;background:#64cbd4;border-radius:999px}}
.small{{font-size:.81rem;overflow-wrap:anywhere}}
footer{{color:#94a7b8;font-size:.85rem;margin-top:30px}}
</style></head><body><main>
<header><div class="eyebrow">SPORTPROB / OFFLINE PERFORMANCE RESEARCH</div>
<h1>{esc(prediction.player_id)} · {esc(prediction.stat.title())}</h1>
<p>Forecast as of {esc(prediction.as_of.isoformat())} — only prior played games enter the model.</p>
<div class="flag">{dataset_label} · RESEARCH ONLY · UNCALIBRATED MODEL · NOT A PREDICTION GUARANTEE</div></header>
<div class="grid">
<div class="card"><span>Estimated mean count</span><strong>{prediction.expected_stat:.2f}</strong></div>
<div class="card"><span>80% central model interval</span><strong>{low80}–{high80}</strong></div>
<div class="card"><span>90% central model interval</span><strong>{low90}–{high90}</strong></div>
<div class="card"><span>Most probable {modal.high-modal.low+1}-count bucket</span><strong>{modal.low}–{modal.high}</strong><span>{modal.probability*100:.1f}% model mass</span></div>
</div>
<section><h2>Full count-distribution buckets</h2>
<p>Non-overlapping groups; bar lengths show model probability, not certainty. Omitted groups each have less than 0.01% mass.</p>
<table><thead><tr><th scope="col">Observed count range</th><th scope="col">Model mass</th><th scope="col">Distribution</th></tr></thead><tbody>
{''.join(rows)}
</tbody></table></section>
<section><h2>Method and source trace</h2>
<p>Played historical games: {prediction.training_games} · Projected minutes: {prediction.projected_minutes:.2f} · Predictive variance: {prediction.variance:.2f}.</p>
<p>The statistical model is a provisional Gamma–Poisson / Negative Binomial research baseline. Game-to-game dispersion has not been calibrated against authentic NBA history, so interval coverage and probability accuracy are unverified.</p>
<p class="small">Dataset: {esc(dataset_id)} · Source: {esc(source_name)}<br>SHA-256 verified against locally supplied manifest: <code>{esc(dataset_sha256)}</code></p>
<p class="small">Source rights are user-declared and not independently established. Forecast does not incorporate opponents, injury, schedule or pace. No sportsbook links, odds, staking or automated actions.</p></section>
<footer>Generated entirely offline. No external scripts, fonts, network requests or telemetry.</footer>
</main></body></html>"""


def save_forecast_report(html: str, destination: str | Path, *, overwrite: bool = False) -> Path:
    """Write only to an explicit local path, without replacing files by default."""
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w" if overwrite else "x", encoding="utf-8") as output:
        output.write(html)
    return path.resolve()
