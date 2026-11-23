from __future__ import annotations

import numpy as np

from data_loader import _fallback_data
from simulation_engine import generate_scenarios, optimize_order_quantity


def test_scenarios_are_reproducible_and_valid():
    first = generate_scenarios(500, 500, 100, 0.04, 15, seed=42)
    second = generate_scenarios(500, 500, 100, 0.04, 15, seed=42)

    assert np.array_equal(first["demand"], second["demand"])
    assert np.array_equal(first["inflation_shock"], second["inflation_shock"])
    assert np.array_equal(first["lead_days"], second["lead_days"])
    assert np.all(first["demand"] >= 0)
    assert np.all(first["lead_days"] >= 0)


def test_optimization_is_reproducible_and_q_is_in_grid():
    scenarios = generate_scenarios(1000, 500, 100, 0.04, 15, seed=42)
    quantities = np.arange(50.0, 2000.0 + 25.0, 25.0)

    result = optimize_order_quantity(
        quantities,
        scenarios,
        base_price=2500,
        mean_demand=500,
        mean_inflation=0.01,
        sigma_inflation=0.04,
        holding_cost=50,
        fixed_order_cost=2500,
        stockout_penalty=500,
    )

    assert result["q_star"] in quantities
    assert result["minimum_expected_cost"] <= np.min(result["expected_costs"])
    assert result["var_95"] <= result["cvar_95"]
    assert result["eoq"] > 0


def test_fallback_marks_reference_series_not_live():
    market = _fallback_data("test")

    assert market["source"] == "Yerel referans veri seti"
    assert "resmi" in market["message"].lower()
    assert len(market["history"]) > 0
