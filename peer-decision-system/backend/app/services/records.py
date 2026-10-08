from fastapi import HTTPException

def require(db, model, id):
    obj = db.get(model, id)
    if obj is None:
        raise HTTPException(404, 'Kayıt bulunamadı.')
    return obj
