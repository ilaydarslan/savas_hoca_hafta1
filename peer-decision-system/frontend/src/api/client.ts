import axios from 'axios'
export const api = axios.create({baseURL:import.meta.env.VITE_API_URL || '/api/v1'})
api.interceptors.request.use(config => { const token=sessionStorage.getItem('token'); if(token) config.headers.Authorization=`Bearer ${token}`; return config })
api.interceptors.response.use(r=>r, e=>{if(e.response?.status===401 && !e.config?.url?.includes('/auth/login')){sessionStorage.removeItem('token'); window.dispatchEvent(new Event('session-expired'))}return Promise.reject(e)})
export function errorText(error:unknown):string {if(axios.isAxiosError(error)){const d=error.response?.data?.detail; return typeof d==='string'?d:Array.isArray(d)?d.map(x=>`${x.loc?.slice(1).join('.')}: ${x.msg}`).join(' · '):(error.response?'Sunucu isteği tamamlayamadı. Lütfen yeniden dene.':'Sunucuya bağlanılamadı. Uygulamayi Ac.cmd dosyasını çalıştırıp sayfayı yenile.')} return 'İşlem tamamlanamadı.'}
