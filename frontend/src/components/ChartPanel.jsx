import { useEffect, useRef, useState } from 'react'
import { createChart, CrosshairMode } from 'lightweight-charts'
import styles from './ChartPanel.module.css'

const BINANCE_REST = 'https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=5m&limit=500'
const BINANCE_WS = 'wss://stream.binance.com:9443/ws/btcusdt@kline_5m'

const COLORS = {
    bg: '#0d1117',
    grid: '#131c2e',
    text: '#64748b',
    border: '#1e2d45',
    up: '#26a69a',
    down: '#ef5350',
    ema20: '#f59e0b',
    ema50: '#a78bfa',
}

function calcEMA(data, period) {
    const k = 2 / (period + 1)
    const result = []
    let ema = null

    for (let i = 0; i < data.length; i++) {
        const c = data[i].close
        if (ema === null) {
            if (i + 1 >= period) {
                let sum = 0
                for (let j = i - period + 1; j <= i; j++) sum += data[j].close
                ema = sum / period
                result.push({ time: data[i].time, value: ema })
            }
        } else {
            ema = c * k + ema * (1 - k)
            result.push({ time: data[i].time, value: ema })
        }
    }
    return result
}

function formatPrice(v) {
    return v
        ? Number(v).toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 })
        : '--'
}

function formatVol(v) {
    if (!v) return '--'
    if (v >= 1000) return (v / 1000).toFixed(1) + 'K'
    return Number(v).toFixed(2)
}

function toSec(ms) {
    return Math.floor(ms / 1000)
}

export function ChartPanel() {
    const mainRef = useRef(null)
    const volRef = useRef(null)
    const contRef = useRef(null)

    const chartRef = useRef(null)
    const volChartRef = useRef(null)
    const candleSerRef = useRef(null)
    const ema20Ref = useRef(null)
    const ema50Ref = useRef(null)
    const volSerRef = useRef(null)

    const candlesRef = useRef([])
    const wsRef = useRef(null)
    const timerRef = useRef(null)

    const [livePrice, setLivePrice] = useState(null)
    const [pctChange, setPctChange] = useState(null)
    const [ohlcv, setOhlcv] = useState({ o: '--', h: '--', l: '--', c: '--', v: '--' })
    const [lastUpdate, setLastUpdate] = useState('--')
    const prevPriceRef = useRef(null)

    // ── 차트 생성 ─────────────────────────────────────
    useEffect(() => {
        if (!mainRef.current || !volRef.current) return

        const totalH = contRef.current.clientHeight
        const mainH = Math.floor(totalH * 0.68)
        const volH = totalH - mainH

        // 메인 캔들 차트
        const mainChart = createChart(mainRef.current, {
            width: mainRef.current.clientWidth,
            height: mainH,
            layout: { background: { color: COLORS.bg }, textColor: COLORS.text, fontSize: 11 },
            grid: { vertLines: { color: COLORS.grid }, horzLines: { color: COLORS.grid } },
            crosshair: {
                mode: CrosshairMode.Normal,
                vertLine: { color: '#334155', width: 1, style: 1 },
                horzLine: { color: '#334155', width: 1, style: 1 },
            },
            rightPriceScale: { borderColor: COLORS.border, scaleMargins: { top: 0.08, bottom: 0.05 } },
            timeScale: { borderColor: COLORS.border, timeVisible: true, secondsVisible: false, rightOffset: 5 },
        })

        const candleSer = mainChart.addCandlestickSeries({
            upColor: COLORS.up, downColor: COLORS.down,
            borderUpColor: COLORS.up, borderDownColor: COLORS.down,
            wickUpColor: COLORS.up, wickDownColor: COLORS.down,
        })

        const ema20 = mainChart.addLineSeries({
            color: COLORS.ema20, lineWidth: 1,
            priceLineVisible: false, lastValueVisible: true, title: 'EMA20',
        })

        const ema50 = mainChart.addLineSeries({
            color: COLORS.ema50, lineWidth: 1,
            priceLineVisible: false, lastValueVisible: true, title: 'EMA50',
        })

        // 볼륨 차트
        const volChart = createChart(volRef.current, {
            width: volRef.current.clientWidth,
            height: volH,
            layout: { background: { color: COLORS.bg }, textColor: COLORS.text, fontSize: 10 },
            grid: { vertLines: { color: COLORS.grid }, horzLines: { color: COLORS.grid } },
            rightPriceScale: { borderColor: COLORS.border, scaleMargins: { top: 0.05, bottom: 0 } },
            timeScale: { borderColor: COLORS.border, timeVisible: true, visible: false },
            crosshair: {
                mode: CrosshairMode.Normal,
                vertLine: { color: '#334155', width: 1, style: 1, labelVisible: false },
                horzLine: { visible: false },
            },
        })

        const volSer = volChart.addHistogramSeries({
            priceFormat: { type: 'volume' },
        })

        // 시간축 동기화
        mainChart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
            if (range) volChart.timeScale().setVisibleLogicalRange(range)
        })
        volChart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
            if (range) mainChart.timeScale().setVisibleLogicalRange(range)
        })

        // 크로스헤어: OHLCV 업데이트
        mainChart.subscribeCrosshairMove((param) => {
            if (!param?.time) return
            volChart.setCrosshairPosition(0, param.time, volSer)
            const d = param.seriesData?.get(candleSer)
            const vd = param.seriesData?.get(volSer)
            if (d) {
                setOhlcv({
                    o: formatPrice(d.open),
                    h: formatPrice(d.high),
                    l: formatPrice(d.low),
                    c: formatPrice(d.close),
                    v: vd ? formatVol(vd.value) : '--',
                })
            }
        })

        chartRef.current = mainChart
        volChartRef.current = volChart
        candleSerRef.current = candleSer
        ema20Ref.current = ema20
        ema50Ref.current = ema50
        volSerRef.current = volSer

        return () => {
            mainChart.remove()
            volChart.remove()
        }
    }, [])

    // ── 리사이즈 ──────────────────────────────────────
    useEffect(() => {
        const handler = () => {
            if (!chartRef.current || !volChartRef.current || !contRef.current) return
            const totalH = contRef.current.clientHeight
            const mainH = Math.floor(totalH * 0.68)
            const volH = totalH - mainH
            chartRef.current.resize(mainRef.current.clientWidth, mainH)
            volChartRef.current.resize(volRef.current.clientWidth, volH)
        }
        window.addEventListener('resize', handler)
        return () => window.removeEventListener('resize', handler)
    }, [])

    // ── 데이터 로드 + WebSocket ───────────────────────
    useEffect(() => {
        if (!candleSerRef.current) return

        function dispatchWsStatus(text, live) {
            window.dispatchEvent(new CustomEvent('ws-status-change', { detail: { text, live } }))
        }

        function updatePriceDisplay(close, open) {
            setLivePrice(close)
            const dayOpen = candlesRef.current.length > 0 ? candlesRef.current[0].open : open
            const pct = ((close - dayOpen) / dayOpen) * 100
            setPctChange(pct)
            prevPriceRef.current = close
        }

        function updateEma() {
            const data = candlesRef.current
            if (data.length === 0) return

            // 전체 다시 계산 (과거 데이터 변경 가능성 대비)
            const e20 = calcEMA(data, 20)
            const e50 = calcEMA(data, 50)

            // 데이터가 많으면 setData로 전체 덮어쓰기 (가장 확실함)
            // 깜빡임 방지를 위해 마지막 1개만 update할 수도 있지만,
            // EMA는 과거 데이터 영향으로 값이 변할 수 있어 setData가 안전
            ema20Ref.current?.setData(e20)
            ema50Ref.current?.setData(e50)
        }

        function connectWs() {
            if (wsRef.current) wsRef.current.close()
            wsRef.current = new WebSocket(BINANCE_WS)

            wsRef.current.onopen = () => {
                dispatchWsStatus('LIVE · 실시간 연결됨', true)
                if (timerRef.current) { clearTimeout(timerRef.current); timerRef.current = null }
            }

            wsRef.current.onmessage = (event) => {
                try {
                    const msg = JSON.parse(event.data)
                    const k = msg.k
                    const t = toSec(k.t)
                    const open = parseFloat(k.o)
                    const high = parseFloat(k.h)
                    const low = parseFloat(k.l)
                    const close = parseFloat(k.c)
                    const vol = parseFloat(k.v)

                    const candles = candlesRef.current
                    // 안전장치: 캔들 데이터가 없거나, 새 데이터가 과거 데이터면 무시
                    if (candles.length > 0) {
                        const lastTime = candles[candles.length - 1].time
                        if (t < lastTime) return
                    }

                    const newCandle = { time: t, open, high, low, close }

                    // 현재 봉 업데이트 vs 새 봉 추가
                    if (candles.length > 0 && candles[candles.length - 1].time === t) {
                        candles[candles.length - 1] = newCandle
                        candleSerRef.current?.update(newCandle)
                        volSerRef.current?.update({
                            time: t, value: vol,
                            color: close >= open ? 'rgba(38,166,154,0.5)' : 'rgba(239,83,80,0.5)',
                        })
                    } else {
                        candles.push(newCandle)
                        candleSerRef.current?.update(newCandle)
                        volSerRef.current?.update({
                            time: t, value: vol,
                            color: close >= open ? 'rgba(38,166,154,0.5)' : 'rgba(239,83,80,0.5)',
                        })
                        if (candles.length > 600) candles.shift()
                    }

                    updateEma()
                    updatePriceDisplay(close, open)
                    setOhlcv({ o: formatPrice(open), h: formatPrice(high), l: formatPrice(low), c: formatPrice(close), v: formatVol(vol) })
                    setLastUpdate(new Date().toTimeString().slice(0, 8))
                } catch (err) {
                    // ignored
                }
            }

            wsRef.current.onerror = () => { }

            wsRef.current.onclose = () => {
                dispatchWsStatus('연결 끊김 · 재연결 중...', false)
                timerRef.current = setTimeout(connectWs, 5000)
            }
        }

        // 초기 REST 데이터 로드
        fetch(BINANCE_REST)
            .then(r => r.json())
            .then(raw => {
                const candles = []
                const volData = []
                for (const k of raw) {
                    const t = toSec(parseInt(k[0]))
                    const c = { time: t, open: +k[1], high: +k[2], low: +k[3], close: +k[4] }
                    candles.push(c)
                    volData.push({
                        time: t, value: +k[5],
                        color: c.close >= c.open ? 'rgba(38,166,154,0.5)' : 'rgba(239,83,80,0.5)',
                    })
                }
                candlesRef.current = candles
                candleSerRef.current?.setData(candles)
                volSerRef.current?.setData(volData)

                const e20 = calcEMA(candles, 20)
                const e50 = calcEMA(candles, 50)
                ema20Ref.current?.setData(e20)
                ema50Ref.current?.setData(e50)

                chartRef.current?.timeScale().fitContent()

                if (candles.length > 0) {
                    const last = candles[candles.length - 1]
                    updatePriceDisplay(last.close, last.open)
                    setOhlcv({ o: formatPrice(last.open), h: formatPrice(last.high), l: formatPrice(last.low), c: formatPrice(last.close), v: formatVol(volData[volData.length - 1].value) })
                }

                setTimeout(connectWs, 300)
            })
            .catch(() => {
                dispatchWsStatus('데이터 로드 실패', false)
            })

        return () => {
            wsRef.current?.close()
            if (timerRef.current) clearTimeout(timerRef.current)
        }
    }, [])

    const isUp = livePrice !== null && prevPriceRef.current !== null
        ? livePrice >= prevPriceRef.current
        : true

    return (
        <div className={styles.panel}>
            {/* 가격 상단 바 */}
            <div className={styles.topBar}>
                <div className={styles.priceBlock}>
                    <span
                        className={styles.livePrice}
                        style={{ color: isUp ? COLORS.up : COLORS.down }}
                    >
                        ${livePrice !== null ? livePrice.toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) : '--'}
                    </span>
                    {pctChange !== null && (
                        <span
                            className={styles.pctChange}
                            style={{ color: pctChange >= 0 ? COLORS.up : COLORS.down }}
                        >
                            {pctChange >= 0 ? '+' : ''}{pctChange.toFixed(2)}%
                        </span>
                    )}
                </div>
            </div>

            {/* 차트 영역 */}
            <div className={styles.chartContainer} ref={contRef}>
                <div className={styles.mainChart} ref={mainRef} />
                <div className={styles.volChart} ref={volRef} />
            </div>

            {/* OHLCV 하단 바 */}
            <div className={styles.infoBar}>
                <div className={styles.ohlcv}>
                    <span><label>O</label><span className={styles.ohlcO}>{ohlcv.o}</span></span>
                    <span><label>H</label><span className={styles.ohlcH}>{ohlcv.h}</span></span>
                    <span><label>L</label><span className={styles.ohlcL}>{ohlcv.l}</span></span>
                    <span><label>C</label><span className={styles.ohlcC}>{ohlcv.c}</span></span>
                    <span><label>Vol</label><span>{ohlcv.v}</span></span>
                </div>
                <span className={styles.updateTime}>{lastUpdate}</span>
            </div>
        </div>
    )
}
