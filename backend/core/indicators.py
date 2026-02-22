import numpy as np
import pandas as pd
import pandas_ta as ta

def calculate_vwap(df):
    """지수/세션별 VWAP 계산"""
    # 일간 VWAP (session-based)
    df = df.copy()
    df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
    df['date'] = df.index.date
    df['pv'] = df['typical_price'] * df['volume']
    
    # 그룹별 누적 합산으로 VWAP 도출
    groups = df.groupby('date', group_keys=False)
    return groups['pv'].cumsum() / groups['volume'].cumsum()

def calculate_volume_profile(df, bins=50, lookback=300):
    """매물대 분석 (AVP/Volume Profile)"""
    sliced_df = df.tail(lookback)
    if len(sliced_df) < 20:
        return {'poc': 0.0, 'vah': 0.0, 'val': 0.0, 'lookback': 0}
        
    price, volume = sliced_df['close'].values, sliced_df['volume'].values
    hist, bin_edges = np.histogram(price, bins=bins, weights=volume)
    
    max_idx = np.argmax(hist)
    poc = (bin_edges[max_idx] + bin_edges[max_idx + 1]) / 2
    
    total_vol = np.sum(hist)
    target_vol = total_vol * 0.7
    current_vol, l_idx, u_idx = hist[max_idx], max_idx, max_idx
    
    while current_vol < target_vol and (l_idx > 0 or u_idx < len(hist) - 1):
        v_l = hist[l_idx - 1] if l_idx > 0 else -1
        v_u = hist[u_idx + 1] if u_idx < len(hist) - 1 else -1
        if v_l > v_u:
            l_idx -= 1
            current_vol += hist[l_idx]
        else:
            u_idx += 1
            current_vol += hist[u_idx]
            
    return {
        'poc': float(poc),
        'vah': float(bin_edges[u_idx + 1]),
        'val': float(bin_edges[l_idx]),
        'lookback': len(sliced_df)
    }

def detect_divergences(df, window=10):
    """RSI 및 CVD 다이버전스 감지"""
    if len(df) < window * 2:
        return "없음", "없음"
    
    recent, prev = df.iloc[-window:], df.iloc[-(window*2):-window]
    
    # 1. CVD 다이버전스 (수급)
    cvd_div = "없음"
    if recent['high'].max() > prev['high'].max() and recent['cvd'].max() < prev['cvd'].max():
        cvd_div = "하락 다이버전스 (CVD Bearish Div)"
    elif recent['low'].min() < prev['low'].min() and recent['cvd'].min() > prev['cvd'].min():
        cvd_div = "상승 다이버전스 (CVD Bullish Div)"
        
    # 2. RSI 히든 다이버전스 (추세 강화)
    rsi_div = "없음"
    if 'rsi' in df.columns:
        if recent['low'].min() > prev['low'].min() and recent['rsi'].min() < prev['rsi'].min():
            rsi_div = "상승 히든 다이버전스 (Bullish Hidden)"
        elif recent['high'].max() < prev['high'].max() and recent['rsi'].max() > prev['rsi'].max():
            rsi_div = "하락 히든 다이버전스 (Bearish Hidden)"
            
    return cvd_div, rsi_div

def detect_smc_structure(df, lookback=200):
    """SMC(Smart Money Concept) 구조물 감지 (OB, FVG)"""
    df_recent = df.iloc[-lookback:].copy()
    if len(df_recent) < 20:
        return [], []
    
    # 보조 지표 필요 (ATR, Volume SMA)
    if 'atr' not in df_recent.columns:
        df_recent['atr'] = ta.atr(df_recent['high'], df_recent['low'], df_recent['close'], length=14)
    df_recent['vol_sma'] = df_recent['volume'].rolling(20).mean()
    
    unmit_fvgs, unmit_obs = [], []
    
    for i in range(2, len(df_recent) - 1):
        # 1. FVG (Fair Value Gap)
        c1_h, c1_l = df_recent['high'].iloc[i-2], df_recent['low'].iloc[i-2]
        c3_h, c3_l = df_recent['high'].iloc[i], df_recent['low'].iloc[i]
        gap = abs(c1_h - c3_l) if c1_h < c3_l else abs(c1_l - c3_h)
        atr_i = df_recent['atr'].iloc[i]
        
        if c1_h < c3_l and gap > atr_i * 0.5:
            unmit_fvgs.append({'type': 'BullFVG', 'top': c3_l, 'bottom': c1_h, 'idx': i})
        elif c1_l > c3_h and gap > atr_i * 0.5:
            unmit_fvgs.append({'type': 'BearFVG', 'top': c1_l, 'bottom': c3_h, 'idx': i})
            
        # 2. OB (Order Block) - 강한 캔들 기준
        body = abs(df_recent['close'].iloc[i] - df_recent['open'].iloc[i])
        if body > (atr_i * 1.8) and df_recent['volume'].iloc[i] > (df_recent['vol_sma'].iloc[i] * 1.5):
            if df_recent['close'].iloc[i] > df_recent['open'].iloc[i]: # 강세
                for j in range(i-1, max(0, i-5), -1):
                    if df_recent['close'].iloc[j] < df_recent['open'].iloc[j]:
                        unmit_obs.append({'type': 'BullOB', 'top': df_recent['high'].iloc[j], 'bottom': df_recent['low'].iloc[j], 'idx': j})
                        break
            else: # 약세
                for j in range(i-1, max(0, i-5), -1):
                    if df_recent['close'].iloc[j] > df_recent['open'].iloc[j]:
                        unmit_obs.append({'type': 'BearOB', 'top': df_recent['high'].iloc[j], 'bottom': df_recent['low'].iloc[j], 'idx': j})
                        break
                        
    # 미완화(Mitigation) 체크
    v_fvgs, v_obs = [], []
    for f in unmit_fvgs:
        sub = df_recent.iloc[f['idx']+1:]
        if f['type'] == 'BullFVG' and sub['low'].min() < f['bottom']: continue
        if f['type'] == 'BearFVG' and sub['high'].max() > f['top']: continue
        v_fvgs.append(f)
        
    for o in unmit_obs:
        sub = df_recent.iloc[o['idx']+1:]
        if o['type'] == 'BullOB' and sub['low'].min() < o['bottom']: continue
        if o['type'] == 'BearOB' and sub['high'].max() > o['top']: continue
        v_obs.append(o)
        
    return v_fvgs[-2:], v_obs[-2:]

def detect_liquidity_sweep(df, window=30):
    """리퀴디티 휩소(Sweep) 감지"""
    if len(df) < window + 5:
        return "없음"
    curr = df.iloc[-1]
    prev_high = df.iloc[-(window+1):-1]['high'].max()
    prev_low = df.iloc[-(window+1):-1]['low'].min()
    
    if curr['high'] > prev_high and curr['close'] < prev_high:
        return f"고점 휩소 (Bearish Sweep at {prev_high:.0f})"
    if curr['low'] < prev_low and curr['close'] > prev_low:
        return f"저점 휩소 (Bullish Sweep at {prev_low:.0f})"
    return "없음"
