from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from app.core.security import current_user
from app.services.scope_analysis import KeywordScopeStrategy
from app.services.evaluation import evaluate

router = APIRouter(prefix='/api/v1/engineering', dependencies=[Depends(current_user)])


class ScopeSuggestionInput(BaseModel):
    text: str = Field(min_length=5, max_length=10000)


@router.post('/scope-suggestion')
def scope_suggestion(data: ScopeSuggestionInput):
    return KeywordScopeStrategy().suggest(data.text)


@router.get('/evaluation')
def evaluation():
    return evaluate()
