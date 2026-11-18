import pandas as pd


def run_backtest(df, cost=0.50):
    """Return a copy of df with a 'pnl' column: signal * spread minus cost per trade."""
    result = df.copy()
    traded = result["signal"] != 0
    result["pnl"] = result["signal"] * result["spread"] - cost * traded
    return result


def summarize(result):
    """Report total profit, number of trades, profit per trade, and win rate."""
    trades = result[result["signal"] != 0]
    num_trades = len(trades)
    total_profit = result["pnl"].sum()

    if num_trades > 0:
        profit_per_trade = total_profit / num_trades
        win_rate = (trades["pnl"] > 0).mean()
    else:
        profit_per_trade = 0.0
        win_rate = 0.0

    return {
        "total_profit": total_profit,
        "num_trades": num_trades,
        "profit_per_trade": profit_per_trade,
        "win_rate": win_rate,
    }


if __name__ == "__main__":
    example = pd.DataFrame({
        "signal": [1, 1, -1, -1, 0, 0],
        "spread": [10, -8, -35, 5, 12, -20],
    })

    result = run_backtest(example)
    stats = summarize(result)

    print(result)
    print(f"Total profit:     ${stats['total_profit']:.2f}")
    print(f"Number of trades: {stats['num_trades']}")
    print(f"Profit per trade: ${stats['profit_per_trade']:.2f}")
    print(f"Win rate:         {stats['win_rate']:.0%}")

    assert abs(stats["total_profit"] - 30.00) < 1e-9, "Expected total $30.00"
    assert stats["num_trades"] == 4, "Expected 4 trades"
    assert abs(stats["profit_per_trade"] - 7.50) < 1e-9, "Expected $7.50 per trade"
    assert abs(stats["win_rate"] - 0.50) < 1e-9, "Expected 50% win rate"
    print("All checks passed")
