import {useEffect, useRef, useState} from 'react'
import {api, errorText} from '../api/client'
import {Notice} from './UI'

type Suggestion = {
  suggested_scope: string | null
  matched_terms: string[]
  explanation: string
  needs_review: boolean
}
const names: Record<string, string> = {
  COMMUNITY: 'Öğrenci topluluğu', DEPARTMENT: 'Bölüm',
  FACULTY: 'Fakülte', UNIVERSITY: 'Üniversite',
}

export function ScopeAssistant({text, onChoose}: {text: string; onChoose: (scope: string) => void}) {
  const [result, setResult] = useState<Suggestion | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [chosen, setChosen] = useState(false)
  const revision = useRef(0)

  useEffect(() => {
    revision.current += 1
    setResult(null)
    setError('')
    setBusy(false)
    setChosen(false)
    return () => { revision.current += 1 }
  }, [text])

  async function suggest() {
    const request = ++revision.current
    setBusy(true)
    setError('')
    setChosen(false)
    try {
      const response = await api.post<Suggestion>('/engineering/scope-suggestion', {text: text.trim()})
      if (request === revision.current) setResult(response.data)
    } catch (e) {
      if (request === revision.current) setError(errorText(e))
    } finally {
      if (request === revision.current) setBusy(false)
    }
  }

  return <section className="scope-assistant" aria-label="Karar kapsamı yardımcısı">
    <strong>Doğru karar alanını seç</strong>
    <p>Başlık ve gerekçedeki ifadeleri kontrol et. Bu kural tabanlı yardımcı kurul yetkisi vermez; son seçim sana aittir.</p>
    <button type="button" className="button secondary" disabled={busy || text.trim().length < 5} onClick={suggest}>
      {busy ? 'İnceleniyor…' : 'Kapsam önerisini kontrol et'}
    </button>
    {error && <Notice>{error}</Notice>}
    {result && <div aria-live="polite" className="mt-4">
      <strong>{result.suggested_scope ? `Öneri: ${names[result.suggested_scope]}` : 'İnsan değerlendirmesi gerekli'}</strong>
      <p>{result.explanation}</p>
      {result.matched_terms.length > 0 && <p className="muted">Eşleşen ifadeler: {result.matched_terms.join(', ')}</p>}
      {result.suggested_scope && <button type="button" className="button secondary" onClick={() => {
        onChoose(result.suggested_scope!)
        setChosen(true)
      }}>Önerilen alanı seç</button>}
      {chosen && <p role="status">Önerilen alan seçildi. Aşağıdaki seçimden değiştirebilirsin.</p>}
    </div>}
  </section>
}
