import { useEffect, useRef, useState } from 'react'
import { createChart, CrosshairMode } from 'lightweight-charts'
import styles from './ChartPanel.module.css'

const BINANCE_REST = 'https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval=5m&limit=500'
const BINANCE_WS = 'wss://fstream.binance.com/ws/btcusdt@kline_5m'

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

    const [timeframe, setTimeframe] = useState('5m')
    const [livePrice, setLivePrice] = useState(null)
    const [pctChange, setPctChange] = useState(null)
    const [ohlcv, setOhlcv] = useState({ o: '--', h: '--', l: '--', c: '--', v: '--' })
    const [lastUpdate, setLastUpdate] = useState('--')
    const prevPriceRef = useRef(null)

    const timeframes = [
        { id: '1m', label: '1분' },
        { id: '5m', label: '5분' },
        { id: '15m', label: '15분' },
        { id: '1h', label: '1시간' },
        { id: '4h', label: '4시간' },
        { id: '1d', label: '1일' },
    ]

    // ── 차트 생성 ─────────────────────────────────────
    useEffect(() => {
        if (!mainRef.current || !volRef.current) return

        const totalH = contRef.current.clientHeight
        const mainH = Math.floor(totalH * 0.75) // 비중 조절
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
            const mainH = Math.floor(totalH * 0.75)
            const volH = totalH - mainH
            chartRef.current.resize(mainRef.current.clientWidth, mainH)
            volChartRef.current.resize(volRef.current.clientWidth, volH)
        }
        window.addEventListener('resize', handler)
        return () => window.removeEventListener('resize', handler)
    }, [])

    // ── 데이터 로드 + WebSocket (타임프레임 변경 대응) ─────
    useEffect(() => {
        if (!candleSerRef.current) return

        const tfLabel = timeframes.find(t => t.id === timeframe)?.label || timeframe
        window.dispatchEvent(new CustomEvent('timeframe-change', { detail: { timeframe, label: tfLabel } }))

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
            const e20 = calcEMA(data, 20)
            const e50 = calcEMA(data, 50)
            ema20Ref.current?.setData(e20)
            ema50Ref.current?.setData(e50)
        }

        function connectWs() {
            if (wsRef.current) wsRef.current.close()
            const wsUrl = `wss://fstream.binance.com/ws/btcusdt@kline_${timeframe}`
            wsRef.current = new WebSocket(wsUrl)

            wsRef.current.onopen = () => {
                dispatchWsStatus(`LIVE · BTC/USDT (${timeframe}) 연결됨`, true)
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
                    if (candles.length > 0) {
                        const lastTime = candles[candles.length - 1].time
                        if (t < lastTime) return
                    }

                    const newCandle = { time: t, open, high, low, close }
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
                        if (candles.length > 1000) candles.shift()
                    }

                    updateEma()
                    updatePriceDisplay(close, open)
                    setOhlcv({ o: formatPrice(open), h: formatPrice(high), l: formatPrice(low), c: formatPrice(close), v: formatVol(vol) })
                    setLastUpdate(new Date().toTimeString().slice(0, 8))
                } catch (err) { }
            }

            wsRef.current.onclose = () => {
                dispatchWsStatus('연결 끊김 · 재연결 중...', false)
                timerRef.current = setTimeout(connectWs, 5000)
            }
        }

        // 초기 REST 데이터 로드
        const restUrl = `https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval=${timeframe}&limit=500`
        fetch(restUrl)
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
    }, [timeframe])

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

                {/* 타임프레임 선택기 */}
                <div className={styles.timeframeSelector}>
                    {timeframes.map(tf => (
                        <button
                            key={tf.id}
                            className={`${styles.tfButton} ${timeframe === tf.id ? styles.active : ''}`}
                            onClick={() => setTimeframe(tf.id)}
                        >
                            {tf.label}
                        </button>
                    ))}
                </div>
            </div>

            {/* 메인 차트 영역 */}
            <div className={styles.mainContent}>
                <div className={styles.chartContainer} ref={contRef}>
                    <div className={styles.mainChart} ref={mainRef} />
                    <div className={styles.volChart} ref={volRef} />
                </div>
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
