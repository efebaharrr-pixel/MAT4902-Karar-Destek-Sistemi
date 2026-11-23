"""Stokastik alüminyum envanter maliyeti ve kuyruk riski hesapları."""

from __future__ import annotations

from typing import Any

import numpy as np


DEFAULT_SEED = 42
STUDENT_T_DF = 5


def _poisson_from_uniforms(uniforms: np.ndarray, mean: float) -> np.ndarray:
    """Ortak uniform örneklerini Poisson ters-CDF dönüşümüyle sayımlara çevirir."""
    max_count = max(30, int(np.ceil(mean + 12.0 * np.sqrt(mean) + 10.0)))
    probabilities = np.empty(max_count + 1, dtype=float)
    probabilities[0] = np.exp(-mean)
    for count in range(1, max_count + 1):
        probabilities[count] = probabilities[count - 1] * mean / count
    cumulative = np.cumsum(probabilities)
    cumulative[-1] = 1.0
    return np.searchsorted(cumulative, uniforms, side="left").astype(float)


def generate_scenarios(
    n_scenarios: int,
    mu_demand: float,
    sigma_demand: float,
    sigma_inflation: float,
    mean_lead_days: float,
    distribution: str = "Normal Dağılım",
    seed: int = DEFAULT_SEED,
) -> dict[str, np.ndarray]:
    """CRN için tüm karar adaylarında tekrar kullanılacak senaryoları üretir."""
    if not isinstance(n_scenarios, (int, np.integer)) or n_scenarios < 1:
        raise ValueError("Senaryo sayısı en az 1 tam sayı olmalıdır.")
    if not all(np.isfinite(value) for value in (mu_demand, sigma_demand, sigma_inflation, mean_lead_days)):
        raise ValueError("Talep, oynaklık ve teslimat parametreleri sonlu sayılar olmalıdır.")
    if mu_demand < 0 or sigma_demand < 0 or sigma_inflation < 0 or mean_lead_days <= 0:
        raise ValueError("Talep, oynaklık ve teslimat parametreleri geçersiz.")

    rng = np.random.default_rng(seed)
    demand = np.maximum(0.0, rng.normal(mu_demand, sigma_demand, n_scenarios))
    if distribution == "Student-t Dağılımı":
        # df=5 için standart sapması 1 olan t şoku.
        inflation_shock = rng.standard_t(STUDENT_T_DF, n_scenarios) * np.sqrt(
            (STUDENT_T_DF - 2) / STUDENT_T_DF
        )
    elif distribution == "Normal Dağılım":
        inflation_shock = rng.standard_normal(n_scenarios)
    else:
        raise ValueError("Dağılım tipi Normal veya Student-t olmalıdır.")

    lead_uniform = rng.random(n_scenarios)
    lead_days = _poisson_from_uniforms(lead_uniform, mean_lead_days)
    return {
        "demand": demand,
        "inflation_shock": inflation_shock,
        "lead_uniform": lead_uniform,
        "lead_days": lead_days,
    }


def evaluate_order_quantities(
    quantities: np.ndarray,
    scenarios: dict[str, np.ndarray],
    base_price: float,
    mean_inflation: float,
    sigma_inflation: float,
    holding_cost: float,
    fixed_order_cost: float,
    stockout_penalty: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Senaryo x sipariş miktarı maliyet matrisini broadcasting ile hesaplar."""
    quantities = np.asarray(quantities, dtype=float).reshape(-1)
    if quantities.size == 0 or np.any(~np.isfinite(quantities)) or np.any(quantities <= 0):
        raise ValueError("Sipariş miktarları pozitif ve sonlu olmalıdır.")
    if not all(np.isfinite(value) for value in (base_price, mean_inflation, sigma_inflation, holding_cost, fixed_order_cost, stockout_penalty)):
        raise ValueError("Maliyet ve enflasyon parametreleri sonlu sayılar olmalıdır.")
    if base_price <= 0 or holding_cost <= 0 or fixed_order_cost < 0 or stockout_penalty < 0 or sigma_inflation < 0:
        raise ValueError("Maliyet ve oynaklık parametreleri geçersiz.")

    required_keys = ("demand", "lead_days", "inflation_shock")
    if any(key not in scenarios for key in required_keys):
        raise ValueError("Senaryo verisinde talep, enflasyon veya teslimat alanı eksik.")
    demand = np.asarray(scenarios["demand"], dtype=float).reshape(-1)
    lead_days = np.asarray(scenarios["lead_days"], dtype=float).reshape(-1)
    inflation_shock = np.asarray(scenarios["inflation_shock"], dtype=float).reshape(-1)
    if demand.size == 0 or demand.size != lead_days.size or demand.size != inflation_shock.size:
        raise ValueError("Senaryo dizilerinin uzunlukları ve boyutları eşleşmelidir.")
    if np.any(~np.isfinite(demand)) or np.any(demand < 0):
        raise ValueError("Talep senaryoları negatif veya sonsuz olamaz.")
    if np.any(~np.isfinite(lead_days)) or np.any(lead_days < 0):
        raise ValueError("Teslimat senaryoları negatif veya sonsuz olamaz.")
    if np.any(~np.isfinite(inflation_shock)):
        raise ValueError("Enflasyon senaryoları sonsuz veya tanımsız olamaz.")

    demand = demand[:, None]
    lead_days = lead_days[:, None]
    inflation = np.maximum(
        -0.95,
        mean_inflation + sigma_inflation * inflation_shock,
    )[:, None]
    q = quantities[None, :]

    purchase_cost = base_price * (1.0 + inflation) * demand
    holding = holding_cost * q / 2.0
    ordering = fixed_order_cost * demand / q
    lead_demand = demand * (lead_days / 30.0)
    shortage = np.maximum(0.0, lead_demand - q)
    total_cost = purchase_cost + holding + ordering + stockout_penalty * shortage
    return total_cost.mean(axis=0), total_cost


def optimize_order_quantity(
    quantities: np.ndarray,
    scenarios: dict[str, np.ndarray],
    base_price: float,
    mean_demand: float,
    mean_inflation: float,
    sigma_inflation: float,
    holding_cost: float,
    fixed_order_cost: float,
    stockout_penalty: float,
) -> dict[str, Any]:
    """Beklenen maliyet minimizasyonu, EOQ karşılaştırması ve VaR/CVaR."""
    expected_costs, cost_matrix = evaluate_order_quantities(
        quantities,
        scenarios,
        base_price,
        mean_inflation,
        sigma_inflation,
        holding_cost,
        fixed_order_cost,
        stockout_penalty,
    )
    optimum_index = int(np.argmin(expected_costs))
    q_star = float(np.asarray(quantities, dtype=float)[optimum_index])
    optimum_costs = cost_matrix[:, optimum_index]

    eoq = float(np.sqrt(2.0 * fixed_order_cost * max(mean_demand, 0.0) / holding_cost))
    _, eoq_cost_matrix = evaluate_order_quantities(
        np.array([max(eoq, np.finfo(float).eps)]),
        scenarios,
        base_price,
        mean_inflation,
        sigma_inflation,
        holding_cost,
        fixed_order_cost,
        stockout_penalty,
    )
    eoq_expected_cost = float(eoq_cost_matrix[:, 0].mean())

    var_95 = float(np.quantile(optimum_costs, 0.95))
    tail_count = max(1, int(np.ceil(0.05 * optimum_costs.size)))
    worst_costs = np.partition(optimum_costs, optimum_costs.size - tail_count)[-tail_count:]
    cvar_95 = float(worst_costs.mean())
    return {
        "q_star": q_star,
        "minimum_expected_cost": float(expected_costs[optimum_index]),
        "expected_costs": expected_costs,
        "cost_matrix": cost_matrix,
        "optimum_costs": optimum_costs,
        "eoq": eoq,
        "eoq_expected_cost": eoq_expected_cost,
        "var_95": var_95,
        "cvar_95": cvar_95,
    }


def delivery_sensitivity(
    quantities: np.ndarray,
    scenarios: dict[str, np.ndarray],
    base_price: float,
    mean_lead_days: np.ndarray,
    mean_inflation: float,
    sigma_inflation: float,
    holding_cost: float,
    fixed_order_cost: float,
    stockout_penalty: float,
) -> np.ndarray:
    """Ortak uniform örnekleriyle Poisson teslimat gecikmesi maliyet eğrilerini verir."""
    quantities = np.asarray(quantities, dtype=float).reshape(-1)
    mean_lead_days = np.asarray(mean_lead_days, dtype=float).reshape(-1)
    if quantities.size == 0 or np.any(~np.isfinite(quantities)) or np.any(quantities <= 0):
        raise ValueError("Sipariş miktarları pozitif ve sonlu olmalıdır.")
    if mean_lead_days.size == 0 or np.any(~np.isfinite(mean_lead_days)) or np.any(mean_lead_days <= 0):
        raise ValueError("Ortalama teslimat süreleri pozitif ve sonlu olmalıdır.")
    if not all(np.isfinite(value) for value in (base_price, mean_inflation, sigma_inflation, holding_cost, fixed_order_cost, stockout_penalty)):
        raise ValueError("Maliyet ve enflasyon parametreleri sonlu sayılar olmalıdır.")
    if base_price <= 0 or sigma_inflation < 0 or holding_cost <= 0 or fixed_order_cost < 0 or stockout_penalty < 0:
        raise ValueError("Maliyet ve oynaklık parametreleri geçersiz.")

    required_keys = ("demand", "lead_uniform", "inflation_shock")
    if any(key not in scenarios for key in required_keys):
        raise ValueError("Stres senaryolarında talep, ortak uniform veya enflasyon alanı eksik.")
    demand = np.asarray(scenarios["demand"], dtype=float).reshape(-1)
    lead_uniform = np.asarray(scenarios["lead_uniform"], dtype=float).reshape(-1)
    inflation_shock = np.asarray(scenarios["inflation_shock"], dtype=float).reshape(-1)
    if demand.size == 0 or demand.size != lead_uniform.size or demand.size != inflation_shock.size:
        raise ValueError("Stres senaryo dizilerinin uzunlukları eşleşmelidir.")
    if np.any(~np.isfinite(demand)) or np.any(demand < 0):
        raise ValueError("Talep senaryoları negatif veya sonsuz olamaz.")
    if np.any(~np.isfinite(lead_uniform)) or np.any((lead_uniform < 0) | (lead_uniform > 1)):
        raise ValueError("Ortak uniform senaryoları [0, 1] aralığında olmalıdır.")
    if np.any(~np.isfinite(inflation_shock)):
        raise ValueError("Enflasyon senaryoları sonsuz veya tanımsız olamaz.")
    q = quantities[None, :]
    inflation = np.maximum(-0.95, mean_inflation + sigma_inflation * scenarios["inflation_shock"])
    purchase_cost = float(np.mean(base_price * (1.0 + inflation) * demand))
    holding = holding_cost * q / 2.0
    ordering = fixed_order_cost * demand.mean() / q
    expected_costs = np.empty((mean_lead_days.size, quantities.size), dtype=float)
    for index, lead_mean in enumerate(mean_lead_days):
        lead_days = _poisson_from_uniforms(scenarios["lead_uniform"], float(lead_mean))
        lead_demand = demand[:, None] * lead_days[:, None] / 30.0
        shortage = np.maximum(0.0, lead_demand - q)
        expected_costs[index] = (
            purchase_cost + holding + ordering + stockout_penalty * shortage.mean(axis=0)
        )
    return expected_costs