import { useLanguage } from '../contexts/LanguageContext'
import styles from './ReportPanel.module.css'

export function ReportPanel({ data, loading, error, onRefresh }) {
    const { t } = useLanguage()

    if (loading) return (
        <div className={styles.panel}>
            <div className={styles.panelHeader}>
                <div className={styles.panelTitle}>{t('report.title')}</div>
            </div>
            <div className={styles.content}>
                <div className={styles.skeleton}>
                    <div className={styles.skeletonLine} />
                    <div className={styles.skeletonLine} />
                    <div className={styles.skeletonLine} />
                    <p style={{ marginTop: '20px', textAlign: 'center', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                        {t('report.loading')}
                    </p>
                </div>
            </div>
        </div>
    )

    if (error) return (
        <div className={styles.panel}>
            <div className={styles.errorBox}>
                <div className={styles.errorIcon}>⚠️</div>
                <p>{t('common.error')}</p>
                <p>{t('common.error')}</p>
            </div>
        </div>
    )

    return (
        <div className={styles.panel}>
            <div className={styles.panelHeader}>
                <div>
                    <div className={styles.panelTitle}>{t('report.title')}</div>
                    <div className={styles.generatedAt}>{t('report.generatedAt')}: {data?.generated_at || '--'}</div>
                </div>
            </div>

            <div className={styles.metricsRow}>
                <div className={styles.metric}>
                    <div className={styles.metricLabel}>{t('report.metrics.volatility')}</div>
                    <div className={styles.metricValue}>HIGH</div>
                </div>
                <div className={styles.metric}>
                    <div className={styles.metricLabel}>{t('report.metrics.strength')}</div>
                    <div className={styles.metricValue}>STRONG</div>
                </div>
                <div className={styles.metric}>
                    <div className={styles.metricLabel}>{t('report.metrics.sentiment')}</div>
                    <div className={styles.metricValue}>BULLISH</div>
                </div>
            </div>

            <div className={styles.content}>
                <div className={styles.reportText}>
                    {data?.strategy ? (
                        data.strategy.split('\n').map((line, i) => (
                            <p key={i} style={{ marginBottom: '12px' }}>{line}</p>
                        ))
                    ) : (
                        <p className={styles.empty}>{t('common.loading')}</p>
                    )}
                </div>
            </div>

            <div className={styles.footer}>
                Powered by QuantAI Intelligence Model
            </div>
        </div >
    )
}
