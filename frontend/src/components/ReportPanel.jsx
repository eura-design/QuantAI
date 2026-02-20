import styles from './ReportPanel.module.css'

function Skeleton() {
    return (
        <div className={styles.skeleton}>
            {[80, 60, 90, 50, 70, 40, 85, 55].map((w, i) => (
                <div key={i} className={styles.skeletonLine} style={{ width: `${w}%` }} />
            ))}
        </div>
    )
}

export function ReportPanel({ data, loading, error, onRefresh }) {
    return (
        <div className={styles.panel}>
            {/* 헤더 */}
            <div className={styles.panelHeader}>
                <div>
                    <div className={styles.panelTitle}>AI 분석 리포트</div>
                    {data && (
                        <div className={styles.generatedAt}>생성 시각: {data.generated_at}</div>
                    )}
                </div>
                <button
                    className={styles.refreshBtn}
                    onClick={onRefresh}
                    disabled={loading}
                    title="AI 재분석"
                >
                    <span className={loading ? styles.spin : ''}>↻</span>
                </button>
            </div>

            {/* 가격 블록 */}
            <div className={styles.priceBlock}>
                <div className={styles.priceLabel}>분석 기준가</div>
                {loading ? (
                    <div className={styles.priceSkeleton} />
                ) : (
                    <div className={styles.priceValue}>
                        ${data ? data.price.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 }) : '--'}
                        <span className={styles.priceUnit}>USDT</span>
                    </div>
                )}
            </div>

            {/* 시장 지표 */}
            {data && (
                <div className={styles.metricsRow}>
                    <div className={styles.metric}>
                        <span className={styles.metricLabel}>펀딩비</span>
                        <span
                            className={styles.metricValue}
                            style={{ color: data.funding_rate > 0.02 ? '#ef5350' : data.funding_rate < -0.02 ? '#26a69a' : '#94a3b8' }}
                        >
                            {data.funding_rate.toFixed(4)}%
                        </span>
                    </div>
                    <div className={styles.metric}>
                        <span className={styles.metricLabel}>미결제약정</span>
                        <span className={styles.metricValue}>
                            {(data.open_interest / 1000).toFixed(1)}K
                        </span>
                    </div>
                </div>
            )}

            {/* 리포트 본문 */}
            <div className={styles.content}>
                {loading && <Skeleton />}

                {/* 에러 발생 시: 지저분한 텍스트 숨기고 깔끔한 안내 메시지 표시 */}
                {!loading && error && (
                    <div className={styles.errorBox}>
                        <div className={styles.errorIcon}>⚡</div>
                        <div style={{ fontWeight: 600, marginBottom: '4px' }}>AI 분석 대기 중...</div>
                        <div style={{ fontSize: '0.75rem', opacity: 0.7, marginBottom: '16px' }}>
                            시스템이 자동으로 재시도 중입니다.
                        </div>
                    </div>
                )}

                {!loading && !error && data && (
                    <pre className={styles.reportText}>{data.strategy}</pre>
                )}
            </div>

            {/* 푸터 */}
            <div className={styles.footer}>
                본 정보는 투자를 권유하지 않으며, 모든 투자 판단과 결과에 대한 책임은 본인에게 있습니다.
            </div>
        </div>
    )
}

