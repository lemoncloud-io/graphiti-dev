from pydantic import BaseModel, Field
from typing import Any, List
from graph_service.dto.common import Message, Text

class AddMessagesRequest(BaseModel):
    group_id: str = Field(..., description='The group id of the messages to add')
    messages: list[Message] = Field(..., description='The messages to add')


class AddEntityNodeRequest(BaseModel):
    uuid: str = Field(..., description='The uuid of the node to add')
    group_id: str = Field(..., description='The group id of the node to add')
    name: str = Field(..., description='The name of the node to add')
    summary: str = Field(default='', description='The summary of the node to add')


class AddTextsRequest(BaseModel):
    group_id: str = Field(..., description='The group id of the texts to add')
    texts: List[Text] = Field(..., description='The texts to add')
    prompt: str = Field(default='', description='The custom extraction prompt for the text')

# Node -> Graphiti. 
class NormalizeNodeRequest(BaseModel):
    group_id: str = Field(..., description='The group id of the texts to add')
    nodes: List[dict[str, Any]] = Field(..., description='The nodes of extracted by LLM')

# Node -> Graphiti. 
class SaveEpisodeRequest(BaseModel):
    group_id: str = Field(..., description='The group id of the texts to add')
    name: str = Field(..., description='The title of the episode to add')
    content: str = Field(..., description='The content of the episode to add')
    nodes: List[dict[str, Any]] = Field(..., description='The nodes of extracted by LLM')  
    edges: List[dict[str, Any]] = Field(..., description='The edges of extracted by LLM')  