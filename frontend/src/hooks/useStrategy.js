import { useState, useEffect, useCallback } from 'react'
import { API } from '../config'

export function useStrategy() {
    const [state, setState] = useState({ data: null, loading: true, error: null })
    const fetchStrategy = useCallback(async () => {
        setState(s => ({ ...s, loading: true, error: null }))
        try {
            const res = await fetch(API.STRATEGY)
            if (!res.ok) throw new Error(`${res.status}`)
            setState({ data: await res.json(), loading: false, error: null })
        } catch (e) { setState(s => ({ ...s, loading: false, error: e.message })) }
    }, [])
    useEffect(() => { fetchStrategy() }, [fetchStrategy])
    return { ...state, refetch: fetchStrategy }
}
