import styles from './ReportPanel.module.css'

const Skeleton = () => (
    <div className={styles.skeleton}>
        {[80, 60, 90, 50, 70, 40, 85, 55].map((w, i) => <div key={i} className={styles.skeletonLine} style={{ width: `${w}%` }} />)}
    </div>
)

export function ReportPanel({ data, loading, error, onRefresh }) {
    const fmt = (v) => v?.toLocaleString('en-US', { maximumFractionDigits: 0 })
    return (
        <div className={styles.panel}>
            <div className={styles.panelHeader}>
                <div><div className={styles.panelTitle}>AI 분석 리포트</div>{data && <div className={styles.generatedAt}>시각: {data.generated_at}</div>}</div>
                <button className={styles.refreshBtn} onClick={onRefresh} disabled={loading}><span className={loading ? styles.spin : ''}>↻</span></button>
            </div>
            <div className={styles.priceBlock}>
                <div className={styles.priceLabel}>분석 기준가</div>
                {loading ? <div className={styles.priceSkeleton} /> : <div className={styles.priceValue}>${fmt(data?.price)}<span className={styles.priceUnit}>USDT</span></div>}
            </div>
            {data && (
                <div className={styles.metricsRow}>
                    {[['펀딩비', `${data.funding_rate.toFixed(4)}%`], ['미결제약정', `${(data.open_interest / 1000).toFixed(1)}K`]].map(([l, v]) => (
                        <div key={l} className={styles.metric}><span className={styles.metricLabel}>{l}</span><span className={styles.metricValue}>{v}</span></div>
                    ))}
                </div>
            )}
            <div className={styles.content}>
                {loading ? <Skeleton /> : error ? <div className={styles.errorBox}>⚠️ AI 분석 대기 중...</div> : data && <pre className={styles.reportText}>{data.strategy}</pre>}
            </div>
            <div className={styles.footer}>본 정보는 투자 권유가 아닙니다.</div>
        </div>
    )
}

