"""Alüminyum piyasa verisini yükler ve canlı veri yoksa referans seri sağlar."""

from __future__ import annotations

from typing import Any

import pandas as pd


# Canlı kaynağa erişilemediğinde kullanılacak, yaklaşık aylık USD/ton referansları.
# Bu gömülü seri sunum amaçlıdır; resmi LME/TÜİK verisi olarak yorumlanmamalıdır.
_REFERENCE_PRICES = [
    2980, 3150, 3250, 3220, 2870, 2500, 2380, 2260, 2240, 2180, 2190, 2340,
    2470, 2400, 2280, 2220, 2260, 2320, 2200, 2160, 2180, 2210, 2180, 2220,
    2240, 2310, 2380, 2460, 2530, 2610, 2540, 2580, 2510, 2460, 2490, 2550,
]


def _summarize_history(prices: pd.Series, source: str, message: str) -> dict[str, Any]:
    clean_prices = prices.astype(float).dropna()
    returns = clean_prices.pct_change().dropna()
    if clean_prices.empty or returns.empty:
        raise ValueError("Piyasa serisi özetlenemedi.")

    history = pd.DataFrame(
        {"Tarih": clean_prices.index, "Fiyat (USD/ton)": clean_prices.values}
    )
    return {
        "price": float(clean_prices.iloc[-1]),
        "mean_return": float(returns.mean()),
        "volatility": float(returns.std(ddof=1)) if len(returns) > 1 else 0.0,
        "source": source,
        "message": message,
        "history": history,
    }


def _fallback_data(reason: str) -> dict[str, Any]:
    dates = pd.date_range(
        end=pd.Timestamp.today().normalize(),
        periods=len(_REFERENCE_PRICES),
        freq=pd.offsets.MonthEnd(),
    )
    prices = pd.Series(_REFERENCE_PRICES, index=dates, name="Close")
    return _summarize_history(
        prices,
        "Yerel referans veri seti",
        f"Canlı piyasa verisi alınamadı ({reason}). Yaklaşık tarihsel referans seri kullanılıyor; değerleri resmi fiyat olarak değerlendirmeyin.",
    )


def load_aluminum_market_data(period: str = "5y") -> dict[str, Any]:
    """Yahoo Finance ALI=F aylık serisini yükler, hata halinde referans seri döndürür."""
    try:
        import yfinance as yf

        history = yf.Ticker("ALI=F").history(
            period=period,
            interval="1mo",
            auto_adjust=True,
        )
        if history.empty or "Close" not in history:
            raise ValueError("Sembol için kullanılabilir kapanış verisi bulunamadı.")

        prices = history["Close"].dropna()
        if len(prices) < 3 or (prices <= 0).any():
            raise ValueError("Canlı fiyat serisi yetersiz veya geçersiz.")
        return _summarize_history(prices, "Yahoo Finance (ALI=F)", "Canlı ALI=F verisi kullanılıyor.")
    except Exception as exc:  # Ağ, sağlayıcı ve sembol hatalarında uygulama çalışmaya devam eder.
        return _fallback_data(f"{type(exc).__name__}: {exc}")