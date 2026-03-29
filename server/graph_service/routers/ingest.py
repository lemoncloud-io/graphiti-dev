import asyncio
from contextlib import asynccontextmanager
from functools import partial

from fastapi import APIRouter, FastAPI, status
from graphiti_core.nodes import EpisodeType  # type: ignore
from graphiti_core.utils.datetime_utils import utc_now
from graphiti_core.utils.maintenance.graph_data_operations import clear_data  # type: ignore

from graph_service.dto import NormalizeNodeRequest, SaveEpisodeRequest, AddEntityNodeRequest, AddMessagesRequest, Message, Result, AddTextsRequest, Text, edge_type_maps, edge_type, entity_type
from graph_service.zep_graphiti import ZepGraphitiDep


class AsyncWorker:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.task = None

    async def worker(self):
        while True:
            try:
                print(f'Got a job: (size of remaining queue: {self.queue.qsize()})')
                job = await self.queue.get()
                await job()
            except asyncio.CancelledError:
                break

    async def start(self):
        self.task = asyncio.create_task(self.worker())

    async def stop(self):
        if self.task:
            self.task.cancel()
            await self.task
        while not self.queue.empty():
            self.queue.get_nowait()


async_worker = AsyncWorker()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await async_worker.start()
    yield
    await async_worker.stop()


router = APIRouter(lifespan=lifespan)


@router.post('/messages', status_code=status.HTTP_202_ACCEPTED)
async def add_messages(
    request: AddMessagesRequest,
    graphiti: ZepGraphitiDep,
):
    async def add_messages_task(m: Message):
        await graphiti.add_episode(
            uuid=m.uuid,
            group_id=request.group_id,
            name=m.name,
            episode_body=f'{m.role or ""}({m.role_type}): {m.content}',
            reference_time=m.timestamp,
            source=EpisodeType.message,
            source_description=m.source_description,
        )

    for m in request.messages:
        await async_worker.queue.put(partial(add_messages_task, m))

    return Result(message='Messages added to processing queue', success=True)


@router.post('/build-communities', status_code=status.HTTP_202_ACCEPTED)
async def build_communities(group_id: str, graphiti: ZepGraphitiDep):
    """
    특정 그룹의 노드들을 분석하여 커뮤니티(주제별 그룹)를 형성하고 요약합니다.
    """
    async def build_task():
        await graphiti.build_communities(group_ids=[group_id])

    await async_worker.queue.put(build_task)
    
    return Result(message='Community building started in background', success=True)


@router.post('/normalize-node', status_code=status.HTTP_200_OK)
async def normalize_node(request: NormalizeNodeRequest, graphiti: ZepGraphitiDep):
    normalized_node = await graphiti.normalize_node_v2(group_id=request.group_id, extracted_nodes=request.nodes)
    normalized= [ 
            {
                "name": node.name,
                "labels": node.labels,
                "summary": node.summary,
                "attribute": node.attributes,
                "nameEmbed": node.name_embedding
            } for node in normalized_node.nodes]

    return normalized



@router.post('/save-episode', status_code=status.HTTP_202_ACCEPTED)
async def save_episode(
    request: SaveEpisodeRequest,
    graphiti: ZepGraphitiDep,
):
    save_episode = await graphiti.add_episode_v2(
            group_id=request.group_id,
            name=request.name,
            episode_body=request.content, # specific strategy content
            source_description=request.name,
            reference_time=utc_now(),
            extract_nodes=request.nodes,
            extract_edges=request.edges,
            source=EpisodeType.text,
        )

    return save_episode


@router.post('/texts', status_code=status.HTTP_202_ACCEPTED)
async def add_texts(
    request: AddTextsRequest,
    graphiti: ZepGraphitiDep,
):

    async def add_texts_task(m: Text):
        await graphiti.add_episode(
            uuid=m.uuid,
            group_id=request.group_id,
            name=m.name,
            episode_body=m.content, # specific strategy content
            source_description=m.source_description,
            reference_time=m.timestamp,
            source=EpisodeType.text,
            entity_types=entity_type,
            edge_types=edge_type,
            edge_type_map=edge_type_maps,
            custom_extraction_instructions=request.prompt
        )

    for m in request.texts:
        await async_worker.queue.put(partial(add_texts_task, m))

    return Result(message='Texts added to processing queue', success=True)

@router.post('/entity-node', status_code=status.HTTP_201_CREATED)
async def add_entity_node(
    request: AddEntityNodeRequest,
    graphiti: ZepGraphitiDep,
):
    node = await graphiti.save_entity_node(
        uuid=request.uuid,
        group_id=request.group_id,
        name=request.name,
        summary=request.summary,
    )
    return node


@router.delete('/entity-edge/{uuid}', status_code=status.HTTP_200_OK)
async def delete_entity_edge(uuid: str, graphiti: ZepGraphitiDep):
    await graphiti.delete_entity_edge(uuid)
    return Result(message='Entity Edge deleted', success=True)


@router.delete('/group/{group_id}', status_code=status.HTTP_200_OK)
async def delete_group(group_id: str, graphiti: ZepGraphitiDep):
    await graphiti.delete_group(group_id)
    return Result(message='Group deleted', success=True)


@router.delete('/episode/{uuid}', status_code=status.HTTP_200_OK)
async def delete_episode(uuid: str, graphiti: ZepGraphitiDep):
    await graphiti.delete_episodic_node(uuid)
    return Result(message='Episode deleted', success=True)


@router.post('/clear', status_code=status.HTTP_200_OK)
async def clear(
    graphiti: ZepGraphitiDep,
):
    await clear_data(graphiti.driver)
    await graphiti.build_indices_and_constraints()
    return Result(message='Graph cleared', success=True)
