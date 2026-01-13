from datetime import datetime
from typing import Literal

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

class Person(BaseModel):
    """PEOPLE: 성함 및 직함 포함 (예: '홍길동 팀장')"""
    full_name: str = Field(..., description="Full name and title")

class Organization(BaseModel):
    """ORGANIZATIONS: 정식 기관/업체 명칭 (예: '단지1 로비')"""
    org_name: str = Field(..., description="Normalized legal name")

class Asset(BaseModel):
    """ASSETS: 공지사항, 게시물 등 주요 정보 객체 (가장 중심이 되는 노드)"""
    asset_name: str = Field(..., description="Title of the notice or post")
    web_url: str | None = Field(None, description="Related link URL")
    image_url: str | None = Field(None, description="Main image URL")

class Product(BaseModel):
    """PRODUCTS: 구체적인 제품 이름"""
    product_name: str = Field(..., description="Specific product name")

class Service(BaseModel):
    """SERVICES: 구체적인 서비스 명칭"""
    service_name: str = Field(..., description="Specific service name")

class Concept(BaseModel):
    """CONCEPTS: 도메인 전문 용어 또는 개념"""
    concept_label: str = Field(..., description="Domain-specific concept")

class Location(BaseModel):
    """LOCATIONS: 구체적인 장소 (예: '단지1 로비', '지하주차장')"""
    location_name: str = Field(..., description="Specific physical location")

class Datetime(BaseModel):
    """TEMPORAL ENTITIES: YYYY-MM-DD HH:mm:ss 형식의 정규화된 날짜 노드"""
    date_val: str = Field(..., description="Normalized ISO 8601 string")

class Category(BaseModel):
    """CATEGORY: 문서 분류"""
    category_name: str = Field(..., description="Name of the category")

class Image(BaseModel):
    """IMAGE: 첨부 이미지 정보"""
    url: str = Field(..., description="Direct image link")
    alt_text: str | None = Field(None, description="Description of the image")

class Web(BaseModel):
    """WEB: 외부 링크 정보"""
    url: str = Field(..., description="Direct web link")

# --- 엔티티 타입 등록 ---
entity_type = {
    "Person": Person,
    "Organization": Organization,
    "Asset": Asset,
    "Product": Product,
    "Service": Service,
    "Concept": Concept,
    "Location": Location,
    "Datetime": Datetime,
    "Category": Category,
    "Image": Image,
    "Web": Web,
}

# --- 엣지(Edge) 클래스 정의 ---
class MemberOf(BaseModel): fact: str = Field(default="MEMBER_OF")
class ManagedBy(BaseModel): fact: str = Field(default="MANAGED_BY")
class Published(BaseModel): fact: str = Field(default="PUBLISHED")
class ScheduledOn(BaseModel): fact: str = Field(default="SCHEDULED_ON")
class LocatedIn(BaseModel): fact: str = Field(default="LOCATED_IN")
class References(BaseModel): fact: str = Field(default="REFERENCES")
class Uses(BaseModel): fact: str = Field(default="USES")
class BelongsTo(BaseModel): fact: str = Field(default="BELONGS_TO")
class HasImage(BaseModel): fact: str = Field(default="HAS_IMAGE")
class HasLink(BaseModel): fact: str = Field(default="HAS_LINK")

edge_type = {
    "MEMBER_OF": MemberOf,
    "MANAGED_BY": ManagedBy,
    "PUBLISHED": Published,
    "SCHEDULED_ON": ScheduledOn,
    "LOCATED_IN": LocatedIn,
    "REFERENCES": References,
    "USES": Uses,
    "BELONGS_TO": BelongsTo,
    "HAS_IMAGE": HasImage,
    "HAS_LINK": HasLink
}

edge_type_maps = {
    ("Person", "Organization"): ["MEMBER_OF"],
    ("Organization", "Category"): ["MEMBER_OF"],
    
    # 관리 및 발행 관계
    ("Asset", "Organization"): ["MANAGED_BY"],
    ("Asset", "Person"): ["MANAGED_BY"],
    ("Organization", "Asset"): ["PUBLISHED"],
    ("Person", "Asset"): ["PUBLISHED"],
    
    # 시간 및 장소 (게시물 중심 연결)
    ("Asset", "Datetime"): ["SCHEDULED_ON"],
    ("Concept", "Datetime"): ["SCHEDULED_ON"],
    ("Asset", "Location"): ["LOCATED_IN"],
    ("Organization", "Location"): ["LOCATED_IN"],
    
    # 참조 및 분류
    ("Asset", "Asset"): ["REFERENCES"],
    ("Asset", "Web"): ["HAS_LINK", "REFERENCES"],
    ("Asset", "Category"): ["BELONGS_TO"],
    
    # 이미지 및 미디어 연결 (개선사항 반영)
    ("Asset", "Image"): ["HAS_IMAGE"],
    
    # 도메인 지식
    ("Organization", "Concept"): ["USES"],
    ("Person", "Concept"): ["USES"],
    ("Asset", "Concept"): ["USES"],
}
# class Doc(BaseModel):
#     uuid: str = Field(..., description='The uuid of the episode')
#     group_id: str = Field(..., description='The group id of the episode')
#     name: str = Field(..., description='The name of the episode')
#     episode_body: str = Field(..., description='The body of the episode')
#     reference_time: datetime = Field(default_factory=utc_now, description='The reference time of the episode')
#     source: str = Field(..., description='The source of the episode')
#     source_description: str = Field(...,)
    
