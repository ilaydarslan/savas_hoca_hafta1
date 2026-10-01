from datetime import date
from typing import Literal
from pydantic import BaseModel, Field, EmailStr, ConfigDict, model_validator

class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
class Register(Input):
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    username: str = Field(min_length=3, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    birth_date: date | None = None
    address: str = Field(default='', max_length=500)
    team_id: int | None = None
    tag_ids: list[int] = Field(default_factory=list, max_length=20)
class Login(Input):
    email: EmailStr
    password: str
class TopicInput(Input):
    decision_scope: Literal['COMMUNITY','DEPARTMENT','FACULTY','UNIVERSITY'] = 'COMMUNITY'
    title: str = Field(min_length=5, max_length=200)
    description: str = Field(min_length=10, max_length=10000)
    category: str = Field(min_length=1, max_length=100)
    tag_ids: list[int] = Field(min_length=1, max_length=20)
    affected_team_id: int | None = None
    impact_level: Literal['NORMAL', 'HIGH'] = 'NORMAL'
class VoteInput(Input):
    target_type: Literal['TOPIC','SUBTOPIC','DELETION']
    target_id: int = Field(gt=0)
    choice: Literal['YES','NO','ABSTAIN']
class MessageInput(Input):
    message: str = Field(min_length=2, max_length=5000)
class ReasonInput(Input):
    reason: str = Field(min_length=5, max_length=2000)
class SubInput(Input):
    title: str = Field(min_length=5, max_length=200)
    description: str = Field(min_length=10, max_length=5000)
class ReviewInput(Input):
    opinion: str = Field(min_length=10, max_length=5000)
    recommendation: Literal['APPROVE','REJECT','REVISION_REQUIRED']
class RoleInput(Input):
    role: Literal['USER','EXPERT','ADMIN']
class AuthorityInput(Input):
    scopes: list[Literal['DEPARTMENT','FACULTY','UNIVERSITY']] = Field(max_length=3)
class ProfileInput(Input):
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    address: str = Field(max_length=500)
    birth_date: date | None = None
    team_id: int | None = None
    tag_ids: list[int] = Field(default_factory=list, max_length=20)
class Condition(Input):
    kind: Literal['HIGH_SUPPORT','MINORITY_SUPPORT','QUORUM','EXPERT_REVIEW','DESCRIPTION_LENGTH']
    value: float = Field(ge=0, le=10000)
    @model_validator(mode='after')
    def range_check(self):
        if self.kind in ('HIGH_SUPPORT','MINORITY_SUPPORT') and self.value > 1:
            raise ValueError('Destek oranı 0–1 aralığında olmalı.')
        return self
class RuleInput(Input):
    code: str = Field(pattern=r'^RULE-\d{3,6}$')
    name: str = Field(min_length=3, max_length=150)
    description: str = Field(min_length=5, max_length=2000)
    category: str = Field(min_length=1, max_length=100)
    condition: Condition
    severity: Literal['WARNING','BLOCKED']
