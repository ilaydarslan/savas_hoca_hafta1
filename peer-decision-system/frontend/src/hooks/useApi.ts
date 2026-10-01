import {useCallback,useEffect,useState} from 'react'
import {api,errorText} from '../api/client'
export function useApi<T>(path:string){const [data,setData]=useState<T|null>(null);const [error,setError]=useState('');const [loading,setLoading]=useState(true)
 const refresh=useCallback(async()=>{try{setError('');const r=await api.get<T>(path);setData(r.data)}catch(e){setError(errorText(e))}finally{setLoading(false)}},[path])
 useEffect(()=>{setLoading(true);void refresh()},[refresh]);return {data,error,loading,refresh,setData}}
