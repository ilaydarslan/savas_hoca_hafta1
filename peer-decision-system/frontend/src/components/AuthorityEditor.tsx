import {useState} from 'react'
import type {User} from '../types'
import {api,errorText} from '../api/client'

const boards=[['DEPARTMENT','Bölüm Kurulu'],['FACULTY','Fakülte Kurulu'],['UNIVERSITY','Üniversite Yönetim Kurulu']] as const
export function AuthorityEditor({user,onSaved}:{user:User;onSaved:()=>Promise<void>}) {
  const [busy,setBusy]=useState(false)
  const [error,setError]=useState('')
  async function change(scope:string,checked:boolean){
    setBusy(true);setError('')
    const current=user.authority_scopes||[]
    try {
      await api.put(`/admin/users/${user.id}/authorities`,{scopes:checked?[...current,scope]:current.filter(s=>s!==scope)})
      await onSaved()
    } catch(e){setError(errorText(e))} finally{setBusy(false)}
  }
  return <div>{boards.map(([scope,label])=><label key={scope} style={{display:'flex',gap:8,alignItems:'center',fontSize:12,marginBottom:8}}><input type="checkbox" disabled={busy} checked={(user.authority_scopes||[]).includes(scope)} onChange={e=>change(scope,e.target.checked)}/>{label}</label>)}{error&&<span role="alert" style={{color:'#a13d39',whiteSpace:'normal'}}>{error}</span>}</div>
}
