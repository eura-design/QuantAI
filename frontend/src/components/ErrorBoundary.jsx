import React from 'react';

class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false };
    }

    static getDerivedStateFromError(error) {
        return { hasError: true };
    }

    componentDidCatch(error, errorInfo) {
        console.error("Component Error:", error, errorInfo);
    }

    render() {
        if (this.state.hasError) {
            return (
                <div style={{ padding: '20px', color: '#ef5350', background: '#2d1b1b', borderRadius: '8px', border: '1px solid #ef5350' }}>
                    <h3>⚠️ 오류 발생</h3>
                    <p style={{ fontSize: '0.8rem' }}>이 컴포넌트를 불러오는 중 문제가 발생했습니다.</p>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;
