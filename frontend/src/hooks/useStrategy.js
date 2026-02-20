import { useState, useEffect, useCallback } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001/api/strategy'

export function useStrategy() {
    const [data, setData] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    const fetchStrategy = useCallback(async () => {
        setLoading(true)
        setError(null)
        try {
            const res = await fetch(API_URL)
            if (!res.ok) throw new Error(`서버 오류: ${res.status}`)
            const json = await res.json()
            setData(json)
        } catch (e) {
            setError(e.message)
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => {
        fetchStrategy()
    }, [fetchStrategy])

    return { data, loading, error, refetch: fetchStrategy }
}
