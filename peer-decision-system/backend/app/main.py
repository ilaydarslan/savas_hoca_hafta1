import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import Base, engine
from app.routers.api import router
from app.routers.canvas import router as canvas_router
from app.routers.engineering import router as engineering_router
from app.core.migrations import migrate_authority

@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    migrate_authority(engine)
    yield

app = FastAPI(title='Akran Öğrenme ve Katılımcı Karar Alma Sistemi', version='1.0.0', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=os.getenv('CORS_ORIGINS','http://localhost:5173,http://127.0.0.1:5173').split(','), allow_credentials=True, allow_methods=['GET','POST','PUT','PATCH'], allow_headers=['Authorization','Content-Type'])
app.include_router(router)
app.include_router(canvas_router)
app.include_router(engineering_router)

@app.get('/health')
def health():
    return {'status': 'ok'}
