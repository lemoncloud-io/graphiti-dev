from datetime import datetime
from typing import Literal, Optional

from graphiti_core.utils.datetime_utils import utc_now
from pydantic import BaseModel, Field


class Result(BaseModel):
    message: str
    success: bool


class Message(BaseModel):
    content: str = Field(..., description='The content of the message')
    uuid: str | None = Field(default=None, description='The uuid of the message (optional)')
    name: str = Field(
        default='', description='The name of the episodic node for the message (optional)'
    )
    role_type: Literal['user', 'assistant', 'system'] = Field(
        ..., description='The role type of the message (user, assistant or system)'
    )
    role: str | None = Field(
        description='The custom role of the message to be used alongside role_type (user name, bot name, etc.)',
    )
    timestamp: datetime = Field(default_factory=utc_now, description='The timestamp of the message')
    source_description: str = Field(
        default='', description='The description of the source of the message'
    )

class Text(BaseModel):
    content: str = Field(..., description='The content of the text')
    uuid: str | None = Field(default=None, description='The uuid of the text (optional)')
    name: str = Field(
        default='', description='The name of the episodic node for the text (optional)'
    )
    timestamp: datetime = Field(default_factory=utc_now, description='The timestamp of the text')
    source_description: str = Field(
        default='', description='The description of the source of the text'
    )

class Actor(BaseModel):
    """ACTOR: 행위 주체 및 책임자 (부서, 기관, 업체 등)"""
    actor_name: str = Field(..., description="기관명, 부서명 또는 담당 주체")
    description: str = Field(..., description="역할 및 책임에 대한 상세 설명")

class Author(BaseModel):
    """AUTHOR: 문서의 작성자 (개인 성함 및 직함 포함)"""
    author_name: str = Field(..., description="작성자 성함 및 직함")
    description: Optional[str] = Field(None, description="소속 부서 등 추가 정보")

class Object(BaseModel):
    """OBJECT: 공지사항, 문서명, 자산, 식단(메뉴) 등 관리 대상"""
    object_name: str = Field(..., description="대상 명칭 (예: '3월 소독 안내문', '제육볶음')")
    description: str = Field(..., description="상세 내용 및 증거 문구")

class Procedure(BaseModel):
    """PROCEDURE: 신청 방법, 업무 단계, 지침 등 행위의 절차"""
    procedure_name: str = Field(..., description="절차 명칭")
    description: str = Field(..., description="단계별 상세 가이드라인")

class Condition(BaseModel):
    """CONDITION: 법령, 규정, 자격 조건 등 행위의 근거"""
    condition_name: str = Field(..., description="규정 또는 조건 명칭")
    description: str = Field(..., description="제약 사유 및 법적 근거")

class Event(BaseModel):
    """EVENT: 점검, 사고, 행사 등 특정 시점에 발생하는 사건"""
    event_name: str = Field(..., description="사건 명칭")
    description: str = Field(..., description="사건의 상세 내용")

class Location(BaseModel):
    """LOCATION: 물리적 장소 또는 시스템 내 위치"""
    location_name: str = Field(..., description="구체적인 장소명")

class Datetime(BaseModel):
    """DATETIME: YYYY-MM-DD HH:mm:ss 형식의 정규화된 시점"""
    datetime_name: str = Field(..., description="YYYY-MM-DD HH:mm:ss")

class Year(BaseModel):
    """YEAR: 연도 노드 (시간 계층 최상위)"""
    year_name: str = Field(..., description="예: '2025'")

class Month(BaseModel):
    """MONTH: 월 노드"""
    month_name: str = Field(..., description="예: '3'")

class Day(BaseModel):
    """DAY: 일 노드"""
    day_name: str = Field(..., description="예: '15'")

class Week(BaseModel):
    """WEEK: 주차 노드 (예: '3월 2주차')"""
    week_name: str = Field(..., description="월 및 주차 정보")

class Concept(BaseModel):
    """CONCEPT: 전문 용어 또는 도메인 지식"""
    concept_name: str = Field(..., description="개념명")
    description: str = Field(..., description="개념의 정의")

class Image(BaseModel):
    """IMAGE: 첨부 이미지"""
    image_name: str = Field(..., description="이미지 식별자 또는 파일명")
    image_url: str = Field(..., description="이미지 링크 URL")

class Web(BaseModel):
    """WEB: 외부 링크"""
    web_name: str = Field(..., description="링크 제목")
    web_url: str = Field(..., description="웹 사이트 URL")


class Category(BaseModel):
    """CATEGORY: 카테고리 또는 게시판 분류"""
    category_name: str = Field(..., description="분류 명칭 (예: '공지사항')")


# --- 엣지(Edge) 클래스 정의 ---
class ExecutedBy(BaseModel): 
    fact: str = Field(default="EXECUTED_BY", description="작성자나 실행 주체 연결")

class ScheduledOn(BaseModel): 
    fact: str = Field(default="SCHEDULED_ON", description="특정 시점 또는 작성 일시 할당")

class PartOf(BaseModel): 
    fact: str = Field(default="PART_OF", description="시간 계층(Day-Month-Year) 구조 형성")

class DependsOn(BaseModel): 
    fact: str = Field(default="DEPENDS_ON", description="선행 요건 및 법적 근거 참조")

class Triggers(BaseModel): 
    fact: str = Field(default="TRIGGERS", description="인과관계(A가 B를 유발함) 연결")

class LocatedIn(BaseModel): 
    fact: str = Field(default="LOCATED_IN", description="물리적/디지털 장소 연결")

class HasDetail(BaseModel): 
    fact: str = Field(default="HAS_DETAIL", description="이미지, 링크, 메타데이터 연결")


# Entity type
entity_type = {
    "Actor": Actor, "Author": Author, "Object": Object,
    "Procedure": Procedure, "Condition": Condition, "Event": Event,
    "Location": Location, "Datetime": Datetime, "Year": Year,
    "Month": Month, "Day": Day, "Week": Week, "Concept": Concept,
    "Image": Image, "Web": Web, "Category": Category
}

# Edge type
edge_type = {
    "EXECUTED_BY": ExecutedBy,
    "SCHEDULED_ON": ScheduledOn,
    "PART_OF": PartOf,
    "DEPENDS_ON": DependsOn,
    "TRIGGERS": Triggers,
    "LOCATED_IN": LocatedIn,
    "HAS_DETAIL": HasDetail
}

# Edge type map
edge_type_maps = {
    # 1. 주체 및 작성 (Who)
    ("Object", "Author"): ["EXECUTED_BY"],
    ("Event", "Author"): ["EXECUTED_BY"],
    ("Procedure", "Author"): ["EXECUTED_BY"],
    ("Object", "Actor"): ["EXECUTED_BY"],
    
    # 2. 시간 계층 (When - PART_OF)
    ("Datetime", "Day"): ["PART_OF"],
    ("Day", "Week"): ["PART_OF"],
    ("Day", "Month"): ["PART_OF"],
    ("Week", "Month"): ["PART_OF"],
    ("Month", "Year"): ["PART_OF"],
    
    # 3. 일정 할당 (When - SCHEDULE_ON)
    ("Object", "Datetime"): ["SCHEDULED_ON"],
    ("Event", "Datetime"): ["SCHEDULED_ON"],
    ("Procedure", "Datetime"): ["SCHEDULED_ON"],
    
    # 4. 인과 관계 및 근거 (Why/How)
    ("Object", "Condition"): ["DEPENDS_ON"],
    ("Procedure", "Condition"): ["DEPENDS_ON"],
    ("Condition", "Actor"): ["DEPENDS_ON"], 
    ("Event", "Procedure"): ["TRIGGERS"],
    ("Event", "Event"): ["TRIGGERS"],
    
    # 5. 장소 (Where)
    ("Actor", "Location"): ["LOCATED_IN"],
    ("Object", "Location"): ["LOCATED_IN"],
    ("Event", "Location"): ["LOCATED_IN"],
    
    # 6. 상세 정보 및 미디어 (Metadata)
    ("Object", "Image"): ["HAS_DETAIL"],
    ("Object", "Web"): ["HAS_DETAIL"],
    ("Object", "Concept"): ["HAS_DETAIL"],
    ("Object", "Category"): ["HAS_DETAIL"],
    ("Event", "Category"): ["HAS_DETAIL"],
}
