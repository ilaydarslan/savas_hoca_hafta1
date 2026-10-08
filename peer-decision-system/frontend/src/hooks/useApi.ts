import {useCallback, useEffect, useRef, useState} from 'react'
import {api, errorText} from '../api/client'

type RequestState<T> = {path: string; data: T | null; error: string; loading: boolean}

export function useApi<T>(path: string) {
  const [state, setState] = useState<RequestState<T>>({path, data: null, error: '', loading: true})
  const requestId = useRef(0)
  const refresh = useCallback(async () => {
    const request = ++requestId.current
    setState(previous => previous.path === path
      ? {...previous, loading: true, error: ''}
      : {path, data: null, error: '', loading: true})
    try {
      const response = await api.get<T>(path)
      if (request === requestId.current) setState({path, data: response.data, error: '', loading: false})
    } catch (error) {
      if (request === requestId.current) setState({path, data: null, error: errorText(error), loading: false})
    }
  }, [path])
  useEffect(() => {
    void refresh()
    return () => { requestId.current += 1 }
  }, [refresh])
  // Mask the old record immediately, before the new path's effect runs.
  const current = state.path === path
  return {data: current ? state.data : null, error: current ? state.error : '', loading: !current || state.loading, refresh}
}
