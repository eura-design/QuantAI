import { useState, useEffect, useCallback } from 'react'
import { API } from '../config'

export function useStrategy(lang = 'ko') {
    const [state, setState] = useState({ data: null, loading: true, error: null })
    const fetchStrategy = useCallback(async () => {
        setState(s => ({ ...s, loading: true, error: null }))
        try {
            const res = await fetch(`${API.STRATEGY}?lang=${lang}`)
            if (!res.ok) throw new Error(`${res.status}`)
            setState({ data: await res.json(), loading: false, error: null })
        } catch (e) { setState(s => ({ ...s, loading: false, error: e.message })) }
    }, [lang])
    useEffect(() => {
        fetchStrategy();
        const interval = setInterval(fetchStrategy, 60000); // 1분마다 폴링
        return () => clearInterval(interval);
    }, [fetchStrategy]);
    return { ...state, refetch: fetchStrategy }
}
