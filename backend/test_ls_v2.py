import ccxt
exchange = ccxt.binance({'options': {'defaultType': 'future'}})
try:
    # Unified API
    res = exchange.fetch_long_short_ratio('BTC/USDT', '5m', 1)
    print(f"Unified result: {res}")
except Exception as e:
    print(f"Unified Error: {e}")

try:
    # fapiData API
    symbol = 'BTCUSDT'
    params = {'symbol': symbol, 'period': '5m', 'limit': 1}
    res = exchange.fapiDataGetGlobalLongShortAccountRatio(params)
    print(f"fapiData result: {res}")
except Exception as e:
    print(f"fapiData Error: {e}")
