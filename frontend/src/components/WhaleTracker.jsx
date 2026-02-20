import { useState, useEffect } from 'react'

export function WhaleTracker() {
    // 가장 원시적인 형태의 렌더링으로 테스트
    return (
        <div style={{
            padding: '20px',
            background: '#0d1117',
            color: '#94a3b8',
            fontSize: '13px',
            textAlign: 'center',
            borderTop: '1px solid #1e2d45',
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            minHeight: '150px'
        }}>
            <p style={{ margin: '0 0 10px 0', fontSize: '18px' }}>🐋</p>
            <p style={{ margin: 0 }}>고래 추적 시스템 준비 중...</p>
            <p style={{ marginTop: '10px', fontSize: '11px', color: '#475569' }}>
                (이 화면이 보인다면 로딩 성공입니다)
            </p>
        </div>
    );
}
