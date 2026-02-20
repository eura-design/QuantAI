import { useEffect, useRef } from 'react'
import { createChart } from 'lightweight-charts'

const COLORS = {
    bg: '#0d1117',
    grid: '#131c2e',
    text: '#64748b',
    border: '#1e2d45',
    up: '#26a69a',
    down: '#ef5350',
}

export function MiniChart({ interval, title }) {
    const chartContainerRef = useRef(null)
    const chartRef = useRef(null)

    useEffect(() => {
        if (!chartContainerRef.current) return

        const chart = createChart(chartContainerRef.current, {
            width: chartContainerRef.current.clientWidth,
            height: chartContainerRef.current.clientHeight,
            layout: {
                background: { color: COLORS.bg },
                textColor: COLORS.text,
                fontSize: 10
            },
            grid: {
                vertLines: { visible: false },
                horzLines: { color: COLORS.grid }
            },
            rightPriceScale: {
                borderColor: COLORS.border,
                scaleMargins: { top: 0.1, bottom: 0.1 }
            },
            timeScale: {
                borderColor: COLORS.border,
                timeVisible: true,
                secondsVisible: false
            },
            handleScroll: false,
            handleScale: false,
        })

        const series = chart.addCandlestickSeries({
            upColor: COLORS.up, downColor: COLORS.down,
            borderUpColor: COLORS.up, borderDownColor: COLORS.down,
            wickUpColor: COLORS.up, wickDownColor: COLORS.down,
        })

        chartRef.current = chart

        const fetchHistory = async () => {
            try {
                const res = await fetch(`https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=${interval}&limit=100`)
                const raw = await res.json()
                const data = raw.map(k => ({
                    time: Math.floor(k[0] / 1000),
                    open: parseFloat(k[1]),
                    high: parseFloat(k[2]),
                    low: parseFloat(k[3]),
                    close: parseFloat(k[4])
                }))
                series.setData(data)
                chart.timeScale().fitContent()
            } catch (e) {
                console.error('MiniChart fetch error:', e)
            }
        }

        fetchHistory()
        const timer = setInterval(fetchHistory, 60000)

        const resizeHandler = () => {
            if (chartRef.current && chartContainerRef.current) {
                chartRef.current.resize(chartContainerRef.current.clientWidth, chartContainerRef.current.clientHeight)
            }
        }
        window.addEventListener('resize', resizeHandler)

        return () => {
            window.removeEventListener('resize', resizeHandler)
            clearInterval(timer)
            chart.remove()
        }
    }, [interval])

    return (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', border: '1px solid #1e2d45', borderRadius: '8px', overflow: 'hidden', minWidth: '0' }}>
            <div style={{ padding: '4px 8px', fontSize: '11px', fontWeight: 'bold', color: '#94a3b8', background: '#131c2e', borderBottom: '1px solid #1e2d45' }}>
                {title}
            </div>
            <div ref={chartContainerRef} style={{ flex: 1, minHeight: '0' }} />
        </div>
    )
}
