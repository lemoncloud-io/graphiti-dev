from datetime import datetime, timezone

from pydantic import BaseModel, Field

from graph_service.dto.common import Message

from typing import Any, Dict, List, Optional, Tuple


class SearchQuery(BaseModel):
    group_ids: list[str] | None = Field(
        None, description='The group ids for the memories to search'
    )
    query: str
    max_facts: int = Field(default=10, description='The maximum number of facts to retrieve')
    max_nodes: int = Field(default=10, description='The maximum number of nodes to retrieve')


class FactResult(BaseModel):
    uuid: str
    name: str
    fact: str
    valid_at: datetime | None
    invalid_at: datetime | None
    created_at: datetime
    expired_at: datetime | None

    class Config:
        json_encoders = {datetime: lambda v: v.astimezone(timezone.utc).isoformat()}

class NodeResult(BaseModel):
    uuid: str
    name: str
    labels: list[str]
    summary: str
    attributes: dict[str, Any] = Field(default={})
    created_at: datetime

class SearchResults(BaseModel):
    facts: Optional[list[FactResult]]
    nodes: Optional[list[NodeResult]]  
    community: str


class GetMemoryRequest(BaseModel):
    group_id: str = Field(..., description='The group id of the memory to get')
    max_facts: int = Field(default=10, description='The maximum number of facts to retrieve')
    center_node_uuid: str | None = Field(
        ..., description='The uuid of the node to center the retrieval on'
    )
    messages: list[Message] = Field(
        ..., description='The messages to build the retrieval query from '
    )


class GetMemoryResponse(BaseModel):
    facts: list[FactResult] = Field(..., description='The facts that were retrieved from the graph')
    nodes: Optional[list[NodeResult]] = Field(..., description='The nodes that were retrieved from the graph')
