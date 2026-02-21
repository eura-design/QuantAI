import ccxt
exchange = ccxt.binance({'options': {'defaultType': 'future'}})
methods = [m for m in dir(exchange) if 'LongShort' in m]
print(f"Methods: {methods}")

try:
    symbol = 'BTCUSDT'
    params = {'symbol': symbol, 'period': '5m', 'limit': 1}
    # Try common variations
    if hasattr(exchange, 'fapiPublicGetGlobalLongShortAccountRatio'):
        print("Using fapiPublicGetGlobalLongShortAccountRatio")
        res = exchange.fapiPublicGetGlobalLongShortAccountRatio(params)
        print(res)
    elif hasattr(exchange, 'fapi_public_get_global_long_short_account_ratio'):
        print("Using fapi_public_get_global_long_short_account_ratio")
        res = exchange.fapi_public_get_global_long_short_account_ratio(params)
        print(res)
except Exception as e:
    print(f"Error: {e}")
