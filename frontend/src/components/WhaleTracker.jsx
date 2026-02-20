import React from 'react'

/**
 * WhaleTracker - 안전 진단 모드
 * 모든 기능을 끄고 화면이 나오는지부터 확인합니다.
 */
export function WhaleTracker() {
    try {
        const style = {
            padding: '20px',
            background: '#0d1117',
            color: '#94a3b8',
            fontSize: '12px',
            textAlign: 'center',
            borderTop: '1px solid #1e2d45',
            height: '100px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
        };

        return (
            <div style={style}>
                🐋 고래 추적 시스템 작동 테스트 중...
                <br />
                (이 문구가 보인다면 컴포넌트 로딩은 성공입니다!)
            </div>
        );
    } catch (e) {
        return <div style={{ color: 'red' }}>Error in Render</div>;
    }
}

export default WhaleTracker;
