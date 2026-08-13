"""
revalue.py — refresca los datos de dinero de la app con precios ACTUALES.

Corre en GitHub Actions (repo público malabar1312/strata) cada ~30 min, gratis y
sin el PC de Mario. Revaloriza las posiciones ya conocidas (shares fijas; solo
cambian cuando Mario opera y reimporta) con el último precio de yfinance, y
reescribe data/wallet.json + los totales de data/today.json y
data/portfolio-real-watch.json para que TODA la app muestre lo mismo y fresco.

Autosuficiente: solo necesita yfinance. No inventa nada (si un precio falla, deja
el valor anterior de esa posición).
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import yfinance as yf

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
USD_TICKERS = {"WQDA.AS"}  # fondos USD que cotizan en USD en yfinance


def _eurusd() -> float:
    try:
        h = yf.Ticker("EURUSD=X").history(period="5d")
        return float(h["Close"].iloc[-1]) if len(h) else 1.0
    except Exception:  # noqa: BLE001
        return 1.0


def _price_eur(sym: str, fx: float) -> float | None:
    try:
        h = yf.Ticker(sym).history(period="5d")
        if not len(h):
            return None
        p = float(h["Close"].iloc[-1])
        return p / fx if (sym in USD_TICKERS and fx > 0) else p
    except Exception:  # noqa: BLE001
        return None


def _patch_total(path: Path, total: float, invested: float, cash: float) -> None:
    """Alinea el total en otras vistas (Hoy, Vigilancia) para que no discrepen."""
    if not path.exists():
        return
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return
    for key in ("total_value_eur",):
        if key in d:
            d[key] = total
    pf = d.get("portfolio")
    if isinstance(pf, dict):
        if "total" in pf:
            pf["total"] = total
        if "invested_value" in pf:
            pf["invested_value"] = round(invested, 2)
        if "cash" in pf:
            pf["cash"] = cash
    path.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    wf = DATA / "wallet.json"
    w = json.loads(wf.read_text(encoding="utf-8"))
    fx = _eurusd()
    invested, cost = 0.0, 0.0
    for h in w["holdings"]:
        p = _price_eur(h["sym"], fx)
        if p is not None and h.get("shares"):
            h["value"] = round(h["shares"] * p, 2)
        c = h.get("cost", 0) or 0
        cost += c
        h["pnl"] = round((h["value"] - c) / c * 100, 1) if c else 0.0
        invested += h["value"]
    for h in w["holdings"]:
        h["weight"] = round(h["value"] / invested * 100, 1) if invested else 0.0
    cash = w.get("cash", 0) or 0
    total = round(invested + cash, 2)
    w["total"] = total
    w["invested"] = round(invested, 2)
    w["pnl_eur"] = round(invested - cost, 2)
    w["pnl_pct"] = round((invested - cost) / cost * 100, 1) if cost else 0.0
    now = dt.datetime.now(dt.timezone.utc)
    w["asof"] = now.strftime("%Y-%m-%d %H:%M UTC")
    # curva: actualiza el punto de hoy o añade uno nuevo (siempre ascendente)
    ev = w.get("evolution") or []
    today0 = int(now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
    pt = {"time": int(now.timestamp()), "value": total}
    if ev and ev[-1]["time"] >= today0:
        ev[-1] = pt
    else:
        ev.append(pt)
        if len(ev) > 400:
            ev = ev[-400:]
    w["evolution"] = ev
    wf.write_text(json.dumps(w, ensure_ascii=False, indent=1), encoding="utf-8")
    _patch_total(DATA / "today.json", total, invested, cash)
    _patch_total(DATA / "portfolio-real-watch.json", total, invested, cash)
    print(f"[refresh] patrimonio {total} EUR @ {w['asof']}  (fx {fx:.4f})")


if __name__ == "__main__":
    main()
