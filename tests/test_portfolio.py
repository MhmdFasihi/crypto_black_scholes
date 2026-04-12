import pandas as pd

from crypto_bs.portfolio import (
    PortfolioAnalyzer,
    PortfolioPosition,
    build_portfolio_report,
    stress_test_portfolio,
)


def _sample_portfolio():
    return [
        {
            "label": "btc_call",
            "quantity": 8,
            "spot_price": 100000,
            "strike_price": 105000,
            "time_to_maturity": 30 / 365,
            "volatility": 0.68,
            "option_type": "call",
            "underlying": "BTC",
            "is_coin_based": True,
        },
        {
            "label": "btc_put_short",
            "quantity": -5,
            "spot_price": 100000,
            "strike_price": 95000,
            "time_to_maturity": 20 / 365,
            "volatility": 0.72,
            "option_type": "put",
            "underlying": "BTC",
            "is_coin_based": True,
        },
        {
            "label": "eth_call",
            "quantity": 15,
            "spot_price": 3500,
            "strike_price": 3600,
            "time_to_maturity": 45 / 365,
            "volatility": 0.80,
            "option_type": "call",
            "underlying": "ETH",
            "is_coin_based": True,
        },
    ]


def test_position_breakdown_returns_expected_columns():
    analyzer = PortfolioAnalyzer()

    breakdown = analyzer.position_breakdown(_sample_portfolio())

    assert len(breakdown) == 3
    assert {
        "label",
        "underlying",
        "position_value",
        "abs_position_value",
        "delta_usd",
        "gamma",
        "vega",
    } <= set(breakdown.columns)
    assert (breakdown["abs_position_value"] >= 0).all()


def test_stress_test_includes_base_scenario_and_down_spot_loss_for_long_call():
    analyzer = PortfolioAnalyzer()
    positions = [
        PortfolioPosition(
            quantity=10,
            spot_price=100000,
            strike_price=105000,
            time_to_maturity=30 / 365,
            volatility=0.65,
            option_type="call",
            underlying="BTC",
            is_coin_based=True,
            label="single_call",
        )
    ]

    stress = analyzer.stress_test(
        positions,
        spot_shocks=(0.0, -0.10),
        vol_shocks=(0.0,),
        days_forward=0,
    )

    base = stress.loc[(stress["spot_shock"] == 0.0) & (stress["vol_shock"] == 0.0)].iloc[0]
    down = stress.loc[(stress["spot_shock"] == -0.10) & (stress["vol_shock"] == 0.0)].iloc[0]
    assert abs(base["pnl"]) < 1e-9
    assert down["pnl"] < 0


def test_estimate_var_cvar_returns_non_negative_tail_metrics():
    analyzer = PortfolioAnalyzer()

    distribution = analyzer.estimate_var_cvar(
        _sample_portfolio(),
        confidence=0.95,
        n_scenarios=2000,
        random_seed=7,
    )

    assert distribution.value_at_risk >= 0
    assert distribution.conditional_value_at_risk >= distribution.value_at_risk
    assert distribution.scenario_count == 2000


def test_build_report_and_convenience_wrappers_return_expected_shapes():
    analyzer = PortfolioAnalyzer()

    report = analyzer.build_report(
        _sample_portfolio(),
        stress_spot_shocks=(-0.10, 0.0, 0.10),
        stress_vol_shocks=(0.0,),
        stress_days_forward=0,
        n_scenarios=1000,
        random_seed=11,
    )
    wrapped = build_portfolio_report(
        _sample_portfolio(),
        stress_spot_shocks=(-0.10, 0.0, 0.10),
        stress_vol_shocks=(0.0,),
        stress_days_forward=0,
        n_scenarios=1000,
        random_seed=11,
    )
    stress = stress_test_portfolio(
        _sample_portfolio(),
        spot_shocks=(-0.10, 0.0, 0.10),
        vol_shocks=(0.0,),
        days_forward=0,
    )

    assert report.portfolio_summary["positions_count"] == 3
    assert isinstance(report.positions, pd.DataFrame)
    assert isinstance(report.stress_tests, pd.DataFrame)
    assert report.concentration["largest_position_pct"] > 0
    assert len(wrapped["positions"]) == 3
    assert len(wrapped["stress_tests"]) == 3
    assert len(stress) == 3
