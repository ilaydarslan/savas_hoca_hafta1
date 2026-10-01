import {createContext,useContext,useEffect,useState,type ReactNode} from 'react'
import {api} from '../api/client'
import type {User} from '../types'
const AuthContext=createContext<{user:User|null;loading:boolean;setUser:(u:User|null)=>void;logout:()=>void;refresh:()=>Promise<void>}>({user:null,loading:true,setUser:()=>{},logout:()=>{},refresh:async()=>{}})
export function AuthProvider({children}:{children:ReactNode}){const [user,setUser]=useState<User|null>(null);const [loading,setLoading]=useState(true)
  const refresh=async()=>{if(sessionStorage.getItem('token')){const {data}=await api.get('/auth/me');setUser(data)}}
  const logout=()=>{sessionStorage.removeItem('token');setUser(null)}
  useEffect(()=>{refresh().catch(logout).finally(()=>setLoading(false));window.addEventListener('session-expired',logout);return()=>window.removeEventListener('session-expired',logout)},[])
  return <AuthContext.Provider value={{user,loading,setUser,logout,refresh}}>{children}</AuthContext.Provider>}
export const useAuth=()=>useContext(AuthContext)
