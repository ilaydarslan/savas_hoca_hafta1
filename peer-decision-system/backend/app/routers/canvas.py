"""Persist the project's problem definition separately from voting decisions."""
from fastapi import APIRouter, Depends
from pydantic import Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import admin, current_user
from app.core.transactions import commit, write_lock
from app.models import ProjectCanvas, now
from app.schemas import Input
from app.services.ledger import append_ledger

router = APIRouter(prefix='/api/v1/engineering', tags=['engineering'])


class CanvasFields(Input):
    business_goal: str = Field(min_length=10, max_length=3000)
    decision: str = Field(min_length=10, max_length=3000)
    task: str = Field(min_length=10, max_length=3000)
    data: str = Field(min_length=10, max_length=3000)
    metrics: str = Field(min_length=10, max_length=3000)
    baseline: str = Field(min_length=10, max_length=3000)
    constraints: str = Field(min_length=10, max_length=3000)
    risks: str = Field(min_length=10, max_length=3000)


class CanvasInput(Input):
    fields: CanvasFields


DEFAULT_FIELDS = {
    'business_goal': 'Üniversite topluluğunda önerileri gerekçeleriyle tartışmak, ilgili karar organına yönlendirmek ve karar geçmişini izlenebilir tutmak. Yanlış kapsama yönlendirilen önerilerin oranını azaltmak; gerçek kullanım başlangıç değeri henüz ölçülmedi.',
    'decision': 'Katılımcı karar kapsamını seçer; yardımcı öneriyi kabul edebilir veya değiştirebilir. Toplulukta ilgili kişiler, kurumsal konularda ilgili kurul üyeleri eşit oyla karar verir. Uzman yalnızca görüş sunar.',
    'task': 'Yardımcı görev: öneri metninden COMMUNITY, DEPARTMENT, FACULTY veya UNIVERSITY kapsamını önermek. Belirsiz metinlerde REVIEW ile insana bırakmak. Kabul/ret ve oy yetkisi açık kurallardır; ML kullanılmaz. Mevcut yöntem eğitilmiş model değil, Türkçe anahtar kelime kuralıdır.',
    'data': 'Ölçüm ekranı sürümlenmiş, elle yazılmış sentetik kapsam örneklerini kullanır. Gerçek öğrenci verisi veya bağımsız saha test seti değildir. Gerçek değerlendirme için izinli öneriler, iki değerlendiriciyle etiketleme ve ayrı sabit test kümesi gerekir.',
    'metrics': 'Önerilen hedefler: yardımcı kapsam önerisinde makro F1 ≥ 0,80 ve kapsam başına duyarlılık ≥ 0,70; yerel yöntem süresi p95 < 200 ms. Koruyucu ölçüt: hiçbir öneri kurul yetkisini otomatik değiştirmez. Ürün metriği: insanın düzelttiği kapsam oranı; iş metriği: yanlış kurula yönlendirme oranı. Sentetik deney saha başarısını kanıtlamaz.',
    'baseline': 'Sabit COMMUNITY tahmini ile Türkçe anahtar kelime stratejisi aynı sürümlü örnekler üzerinde karşılaştırılır. Ölçüm ekranında doğruluk, makro F1, sınıf dağılımı, karışıklık matrisi, insan incelemesine bırakma ve hata örnekleri hesaplanır. Henüz gerçek ML/LLM karşılaştırması yoktur.',
    'constraints': 'Yerel bilgisayarda React + FastAPI + SQLite; tek backend worker. Harici model çağrısı ve ücretli API yok. Kişisel veriler dış servise gönderilmez. Kurul eşlemeleri eğitim amaçlıdır; gerçek mevzuat veya kurum onayı değildir.',
    'risks': 'Ön-otopsi: anahtar kelime belirsizliği yanlış kapsam önerebilir → insan onayı; sentetik veride yüksek puan yanıltabilir → bağımsız gerçek test kümesi; rol ile kurul yetkisi karışabilir → ortak yetki kontrolü; azınlık desteği kaybolabilir → değişmez oy anı takım bilgisi ve regresyon testleri. Gerçek yayına alma kararı saha ölçümleri olmadan verilmez.',
}


def serialize(canvas):
    return {
        'id': 1,
        'fields': canvas.fields if canvas else DEFAULT_FIELDS,
        'updated_at': canvas.updated_at if canvas else None,
        'updated_by': canvas.updated_by if canvas else None,
    }


@router.get('/canvas')
def read_canvas(user=Depends(current_user), db: Session = Depends(get_db)):
    return serialize(db.get(ProjectCanvas, 1))


@router.put('/canvas')
def save_canvas(data: CanvasInput, user=Depends(admin), db: Session = Depends(get_db)):
    with write_lock:
        canvas = db.get(ProjectCanvas, 1)
        if canvas is None:
            canvas = ProjectCanvas(id=1)
            db.add(canvas)
        canvas.fields = data.fields.model_dump()
        canvas.updated_at = now()
        canvas.updated_by = user.id
        append_ledger(db, 'PROJECT_CANVAS_UPDATED', 'PROJECT_CANVAS', 1,
                      {'actor': user.id, 'fields': canvas.fields})
        commit(db)
        return serialize(canvas)
