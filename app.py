"""Türkçe Streamlit Karar Destek Sistemi arayüzü."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data_loader import load_aluminum_market_data
from simulation_engine import (
    DEFAULT_SEED,
    delivery_sensitivity,
    generate_scenarios,
    optimize_order_quantity,
)


st.set_page_config(
    page_title="Alüminyum Tedarik DSS",
    page_icon=":material/analytics:",
    layout="wide",
)


@st.cache_data(ttl=3600, max_entries=20, show_spinner=False)
def cached_market_data() -> dict:
    return load_aluminum_market_data()


@st.cache_data(ttl=3600, max_entries=100, show_spinner=False)
def cached_scenarios(
    n_scenarios: int,
    mu_demand: float,
    sigma_demand: float,
    sigma_inflation: float,
    mean_lead_days: float,
    distribution: str,
) -> dict:
    return generate_scenarios(
        n_scenarios=n_scenarios,
        mu_demand=mu_demand,
        sigma_demand=sigma_demand,
        sigma_inflation=sigma_inflation,
        mean_lead_days=mean_lead_days,
        distribution=distribution,
        seed=DEFAULT_SEED,
    )


@st.cache_data(ttl=3600, max_entries=100, show_spinner=False)
def cached_sensitivity(
    quantity_values: np.ndarray,
    scenarios: dict,
    base_price: float,
    lead_means: np.ndarray,
    mean_inflation: float,
    sigma_inflation: float,
    holding_cost: float,
    fixed_order_cost: float,
    stockout_penalty: float,
) -> np.ndarray:
    return delivery_sensitivity(
        quantity_values,
        scenarios,
        base_price=base_price,
        mean_lead_days=lead_means,
        mean_inflation=mean_inflation,
        sigma_inflation=sigma_inflation,
        holding_cost=holding_cost,
        fixed_order_cost=fixed_order_cost,
        stockout_penalty=stockout_penalty,
    )


@st.cache_data(ttl=3600, max_entries=100, show_spinner=False)
def cached_optimization(
    quantity_values: np.ndarray,
    scenarios: dict,
    base_price: float,
    mean_demand: float,
    mean_inflation: float,
    sigma_inflation: float,
    holding_cost: float,
    fixed_order_cost: float,
    stockout_penalty: float,
) -> dict:
    return optimize_order_quantity(
        quantity_values,
        scenarios,
        base_price=base_price,
        mean_demand=mean_demand,
        mean_inflation=mean_inflation,
        sigma_inflation=sigma_inflation,
        holding_cost=holding_cost,
        fixed_order_cost=fixed_order_cost,
        stockout_penalty=stockout_penalty,
    )


market = cached_market_data()

st.title("Alüminyum Tedarik | Stokastik Karar Destek Sistemi")
st.caption("MAT 4902 · Belirsizlik altında sipariş miktarı ve kuyruk riski analizi")
if market["source"] == "Yahoo Finance (ALI=F)":
    st.success(market["message"])
else:
    st.warning(market["message"])

with st.sidebar:
    st.header("Senaryo Kontrolleri")
    with st.form("scenario_controls"):
        data_mode = st.selectbox(
            "Veri modu",
            ["Piyasa/Referans Verisi", "Özel Senaryo Girişi"],
            key="data_mode",
            help="Piyasa modunda varsayılan P₀ ve enflasyon özetleri ALI=F/yerel seri verisinden gelir; kaydırıcılarla değiştirilebilir.",
        )
        live_mode = data_mode == "Piyasa/Referans Verisi"
        default_price = float(np.clip(market["price"], 500, 5000)) if live_mode else 2500.0
        default_mu_i = float(np.clip(market["mean_return"], -0.2, 0.5)) if live_mode else 0.01
        default_sigma_i = float(np.clip(market["volatility"], 0.0, 0.5)) if live_mode else 0.04

        p0 = st.slider("Güncel birim fiyatı P₀ (USD/ton)", 500.0, 5000.0, default_price, 25.0, key="base_price")
        mu_d = st.slider("Aylık talep ortalaması μD (ton)", 50, 10000, 500, 50, key="mean_demand")
        sigma_d = st.slider("Talep standart sapması σD (ton)", 0, 3000, 100, 25, key="demand_sigma")
        mu_i = st.slider("Aylık enflasyon ortalaması μi", -0.20, 0.50, default_mu_i, 0.005, format="%.3f", key="mean_inflation")
        sigma_i = st.slider("Aylık enflasyon oynaklığı σi", 0.0, 0.50, default_sigma_i, 0.005, format="%.3f", key="inflation_sigma")
        fixed_cost = st.slider("Sabit sipariş maliyeti K (USD)", 0, 100000, 2500, 500, key="fixed_cost")
        holding_cost = st.slider("Birim elde tutma maliyeti h (USD/ton)", 1, 1000, 50, 5, key="holding_cost")
        mean_lead = st.slider("Ortalama teslimat süresi λL (gün)", 1, 90, 15, 1, key="mean_lead")
        stockout_penalty = st.slider("Birim stoksuzluk cezası cs (USD/ton)", 0, 5000, 500, 50, key="stockout_penalty")
        distribution = st.selectbox("Enflasyon dağılımı", ["Normal Dağılım", "Student-t Dağılımı"], key="inflation_distribution")
        n_scenarios = st.slider("Simülasyon sayısı N", 1000, 50000, 10000, 1000, key="scenario_count")
        st.form_submit_button("Analizi çalıştır", icon=":material/play_arrow:", width="stretch")

quantities = np.arange(50.0, 2000.0 + 25.0, 25.0)
scenarios = cached_scenarios(
    n_scenarios=int(n_scenarios),
    mu_demand=float(mu_d),
    sigma_demand=float(sigma_d),
    sigma_inflation=float(sigma_i),
    mean_lead_days=float(mean_lead),
    distribution=distribution,
)
result = cached_optimization(
    quantities,
    scenarios,
    base_price=float(p0),
    mean_demand=float(mu_d),
    mean_inflation=float(mu_i),
    sigma_inflation=float(sigma_i),
    holding_cost=float(holding_cost),
    fixed_order_cost=float(fixed_cost),
    stockout_penalty=float(stockout_penalty),
)

cost_gap = result["eoq_expected_cost"] - result["minimum_expected_cost"]
cost_gap_pct = 100.0 * cost_gap / result["eoq_expected_cost"] if result["eoq_expected_cost"] else 0.0

st.subheader("Yönetici Özeti")
kpi_columns = st.columns(5, border=True)
kpi_columns[0].metric("Optimum sipariş Q*", f"{result['q_star']:,.0f} ton")
kpi_columns[1].metric("Minimum beklenen maliyet", f"${result['minimum_expected_cost']:,.0f}")
kpi_columns[2].metric("VaR (%95)", f"${result['var_95']:,.0f}")
kpi_columns[3].metric("CVaR (%95)", f"${result['cvar_95']:,.0f}")
kpi_columns[4].metric(
    "EOQ'ya göre maliyet farkı",
    f"${cost_gap:,.0f}",
    delta=f"{cost_gap_pct:+.1f}% tasarruf",
    delta_color="normal",
)

left, right = st.columns((1.15, 1))
with left:
    cost_figure = go.Figure()
    cost_figure.add_trace(
        go.Scatter(x=quantities, y=result["expected_costs"], mode="lines", name="Beklenen toplam maliyet", line={"color": "#176B67", "width": 3})
    )
    cost_figure.add_trace(
        go.Scatter(
            x=[result["q_star"]], y=[result["minimum_expected_cost"]], mode="markers", name="Optimum Q*",
            marker={"color": "#C0392B", "size": 14, "symbol": "star"},
        )
    )
    cost_figure.add_vline(x=result["eoq"], line_dash="dash", line_color="#D28A24", annotation_text="Klasik EOQ")
    cost_figure.update_layout(
        title="Sipariş miktarına göre beklenen maliyet", xaxis_title="Sipariş miktarı Q (ton)",
        yaxis_title="Beklenen toplam maliyet (USD)", template="plotly_white", height=430,
        legend={"orientation": "h", "y": 1.12}, margin={"t": 75, "l": 20, "r": 20, "b": 20},
    )
    st.plotly_chart(cost_figure, width="stretch", alt="Sipariş miktarına göre beklenen toplam maliyet eğrisi")

with right:
    risk_figure = go.Figure()
    risk_figure.add_trace(go.Histogram(x=result["optimum_costs"], nbinsx=45, name="Senaryo maliyetleri", marker_color="#4E8C87", opacity=0.82))
    for value, label, color in [
        (result["minimum_expected_cost"], "Ortalama", "#176B67"),
        (result["var_95"], "VaR %95", "#D28A24"),
        (result["cvar_95"], "CVaR %95", "#C0392B"),
    ]:
        risk_figure.add_vline(x=value, line_dash="dash", line_color=color, annotation_text=label)
    risk_figure.update_layout(
        title="Q* noktasındaki toplam maliyet riski", xaxis_title="Toplam maliyet (USD)",
        yaxis_title="Senaryo sayısı", template="plotly_white", height=430,
        showlegend=False, margin={"t": 75, "l": 20, "r": 20, "b": 20},
    )
    st.plotly_chart(risk_figure, width="stretch", alt="Optimum sipariş miktarı için toplam maliyet dağılımı")

st.subheader("Stres Testi | Teslimat Gecikmesi")
stress_means = np.linspace(float(mean_lead), float(mean_lead) + max(15.0, float(mean_lead)), 9)
stress_costs = cached_sensitivity(
    quantities,
    scenarios,
    base_price=float(p0),
    lead_means=stress_means,
    mean_inflation=float(mu_i),
    sigma_inflation=float(sigma_i),
    holding_cost=float(holding_cost),
    fixed_order_cost=float(fixed_cost),
    stockout_penalty=float(stockout_penalty),
)
stress_figure = go.Figure()
for index, mean_value in enumerate(stress_means):
    best_index = int(np.argmin(stress_costs[index]))
    stress_figure.add_trace(
        go.Scatter(
            x=quantities, y=stress_costs[index], mode="lines",
            name=f"λL={mean_value:.0f} gün · Q*={quantities[best_index]:.0f} ton",
        )
    )
stress_figure.update_layout(
    title="Ortalama teslimat süresi arttıkça optimal sipariş miktarı",
    xaxis_title="Sipariş miktarı Q (ton)", yaxis_title="Beklenen toplam maliyet (USD)",
    template="plotly_white", height=430, legend={"orientation": "h", "y": -0.25},
    margin={"t": 65, "l": 20, "r": 20, "b": 110},
)
st.plotly_chart(stress_figure, width="stretch", alt="Teslimat gecikmesi stres seviyelerine göre maliyet eğrileri")
st.caption("Teslimat süreleri her stres düzeyinde Poisson dağılımından ortak uniform örneklerle üretilir (Common Random Numbers).")

stress_summary = pd.DataFrame(
    {
        "Ortalama teslimat (gün)": stress_means,
        "Optimal Q* (ton)": [quantities[int(np.argmin(row))] for row in stress_costs],
        "Beklenen maliyet (USD)": [float(np.min(row)) for row in stress_costs],
    }
)
with st.expander("Stres testi sonuç tablosu"):
    st.dataframe(stress_summary, hide_index=True, width="stretch", alt="Teslimat süresi stres seviyelerine göre optimal sipariş miktarı")

summary = pd.DataFrame(
    [
        {
            "Optimum sipariş Q* (ton)": result["q_star"],
            "Minimum beklenen maliyet (USD)": result["minimum_expected_cost"],
            "VaR %95 (USD)": result["var_95"],
            "CVaR %95 (USD)": result["cvar_95"],
            "Klasik EOQ (ton)": result["eoq"],
            "EOQ beklenen maliyet (USD)": result["eoq_expected_cost"],
            "EOQ'ya göre maliyet farkı (USD)": cost_gap,
            "EOQ'ya göre tasarruf (%)": cost_gap_pct,
            "Veri kaynağı": market["source"] if live_mode else "Özel senaryo",
            "Dağılım": distribution,
            "Senaryo sayısı": n_scenarios,
            "Rastgelelik tohumu": DEFAULT_SEED,
        }
    ]
)
parameters = pd.DataFrame(
    [{
        "Veri modu": data_mode,
        "P₀ (USD/ton)": p0,
        "μD (ton)": mu_d,
        "σD (ton)": sigma_d,
        "μi": mu_i,
        "σi": sigma_i,
        "K (USD)": fixed_cost,
        "h (USD/ton)": holding_cost,
        "λL (gün)": mean_lead,
        "cs (USD/ton)": stockout_penalty,
        "Dağılım": distribution,
        "N": n_scenarios,
        "Seed": DEFAULT_SEED,
    }]
)

st.subheader("Dışa Aktarım")
download_columns = st.columns(2)
download_columns[0].download_button(
    "Yönetici özeti CSV indir",
    data=summary.to_csv(index=False).encode("utf-8-sig"),
    file_name="aluminyum_dss_yonetici_ozeti.csv",
    mime="text/csv",
    width="stretch",
)
report_text = "ALÜMİNYUM TEDARİK DSS | YÖNETİCİ RAPORU\n\n"
report_text += f"Optimum sipariş miktarı: {result['q_star']:,.0f} ton\n"
report_text += f"Minimum beklenen toplam maliyet: {result['minimum_expected_cost']:,.2f} USD\n"
report_text += f"VaR (%95): {result['var_95']:,.2f} USD\nCVaR (%95): {result['cvar_95']:,.2f} USD\n"
report_text += f"Klasik EOQ: {result['eoq']:,.2f} ton\nEOQ beklenen maliyeti: {result['eoq_expected_cost']:,.2f} USD\n"
report_text += f"EOQ'ya göre maliyet farkı: {cost_gap:,.2f} USD ({cost_gap_pct:+.2f}%)\n\n"
report_text += "PARAMETRELER\n" + parameters.to_string(index=False) + "\n\n"
report_text += f"Veri durumu: {market['message'] if live_mode else 'Özel senaryo parametreleri kullanıldı.'}\n"
download_columns[1].download_button(
    "Özet raporu TXT indir",
    data=report_text.encode("utf-8"),
    file_name="aluminyum_dss_ozet_raporu.txt",
    mime="text/plain",
    width="stretch",
)

with st.expander("Model varsayımları ve yöntem"):
    st.markdown(
        "- Talep: Normal dağılım; teslimat süresi: Poisson dağılımı.\n"
        "- Enflasyon: Normal veya Student-t dağılımı.\n"
        "- Karar ölçütü: Beklenen toplam maliyetin minimizasyonu.\n"
        "- Risk ölçütleri: Senaryo dağılımından %95 VaR ve kuyruk ortalaması CVaR.\n"
        "- Karşılaştırılabilirlik: Tüm aday siparişlerde aynı senaryolar ve `seed=42` kullanılır."
    )
    st.latex(r"TC(Q) = P_0(1+i)D + h\frac{Q}{2} + K\frac{D}{Q} + c_s\max(0,L_D-Q)")
    st.latex(r"Q^*=\arg\min_Q\;E[TC(Q)]")
    st.caption("LD = D × (teslimat günü / 30). Enflasyon şoku -%95 sınırının altına düşürülmez.")

with st.expander("Senaryo parametreleri"):
    st.dataframe(parameters, hide_index=True, width="stretch", alt="Kullanılan model parametreleri")
    st.caption(f"Model: Normal talep, Poisson teslimat süresi, seed={DEFAULT_SEED}. Enflasyon şokları -%95'in altında sınırlandırılır.")