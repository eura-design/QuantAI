import ccxt
import pandas as pd
from datetime import datetime

class MarketDataFetcher:
    def __init__(self, symbol='BTC/USDT'):
        self.symbol = symbol
        self.exchange = ccxt.binance({'options': {'defaultType': 'future'}})

    def fetch_ohlcv(self, tf, limit=500):
        """실시간 OHLCV 및 Taker Volume 수집"""
        try:
            params = {'symbol': self.symbol.replace('/', ''), 'interval': tf, 'limit': limit}
            ohlcv = self.exchange.fapiPublicGetKlines(params)
            cols = [
                'timestamp', 'open', 'high', 'low', 'close', 'volume', 
                'close_time', 'q_vol', 'trades', 'taker_buy_vol', 'taker_buy_quote_vol', 'ignore'
            ]
            df = pd.DataFrame(ohlcv, columns=cols)
            
            # 수치 데이터 변환
            cols_numeric = ['open', 'high', 'low', 'close', 'volume', 'taker_buy_vol']
            for c in cols_numeric:
                df[c] = pd.to_numeric(df[c], errors='coerce')
                
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)
            
            # CVD 계산을 위한 기본 필드
            df['taker_sell_vol'] = df['volume'] - df['taker_buy_vol']
            df['delta'] = df['taker_buy_vol'] - df['taker_sell_vol']
            
            return df
        except Exception as e:
            print(f"[Error] OHLCV 수집 실패 ({tf}): {e}")
            return pd.DataFrame()

    def fetch_market_context(self):
        """실시간 미결제약정(OI) 및 펀딩비 수집"""
        try:
            funding = self.exchange.fetch_funding_rate(self.symbol)
            fr = funding['fundingRate'] * 100 if funding else 0.0
            oi_res = self.exchange.fapiPublicGetOpenInterest({'symbol': self.symbol.replace('/', '')})
            oi = float(oi_res['openInterest']) if oi_res else 0.0
            return round(fr, 4), oi
        except Exception as e:
            print(f"[Error] Market Context 수집 실패: {e}")
            return 0.0, 0.0
