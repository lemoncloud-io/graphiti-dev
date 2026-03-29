from datetime import datetime, timezone

from fastapi import APIRouter, status

from graph_service.dto import (
    GetMemoryRequest,
    GetMemoryResponse,
    Message,
    SearchQuery,
    SearchResults,
)
from graph_service.zep_graphiti import ZepGraphitiDep, get_fact_result_from_edge, get_node_result_from_entity
from graphiti_core.nodes import EntityNode
from graphiti_core.search.search_config import SearchConfig, NodeSearchConfig, CommunitySearchMethod, CommunitySearchConfig
from graphiti_core.search.search_filters import SearchFilters


import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from graphiti_core.embedder import EmbedderClient

from graphiti_core.nodes import EpisodeType, EpisodicNode, EntityNode, CommunityNode
from graphiti_core.edges import EntityEdge, EpisodicEdge, CommunityEdge, create_entity_edge_embeddings

from graphiti_core.search.search_config_recipes import (
    NODE_HYBRID_SEARCH_RRF,
    COMBINED_HYBRID_SEARCH_RRF,
    NODE_HYBRID_SEARCH_NODE_DISTANCE,
    EDGE_HYBRID_SEARCH_CROSS_ENCODER,
    NODE_HYBRID_SEARCH_EPISODE_MENTIONS,
    EDGE_HYBRID_SEARCH_RRF,  # 🔹 fact 전용
    COMMUNITY_HYBRID_SEARCH_RRF,
)
from graphiti_core.search.search_config import (
    EdgeSearchConfig,
    EdgeSearchMethod,
    EdgeReranker,
    NodeSearchMethod,
    NodeReranker,
)
from graphiti_core.search.search_filters import SearchFilters, DateFilter, ComparisonOperator
from graphiti_core.search.search_utils import node_bfs_search

router = APIRouter()


@router.post('/search', status_code=status.HTTP_200_OK)
async def search(query: SearchQuery, graphiti: ZepGraphitiDep):
    relevant_edges = await graphiti.search(
        group_ids=query.group_ids,
        query=query.query,
        num_results=query.max_facts,
    )
    facts = [get_fact_result_from_edge(edge) for edge in relevant_edges]
    return SearchResults(
        facts=facts, community='', nodes=None
    )


@router.get('/entity-edge/{uuid}', status_code=status.HTTP_200_OK)
async def get_entity_edge(uuid: str, graphiti: ZepGraphitiDep):
    entity_edge = await graphiti.get_entity_edge(uuid)
    return get_fact_result_from_edge(entity_edge)


@router.get('/episodes/{group_id}', status_code=status.HTTP_200_OK)
async def get_episodes(group_id: str, last_n: int, graphiti: ZepGraphitiDep):
    episodes = await graphiti.retrieve_episodes(
        group_ids=[group_id], last_n=last_n, reference_time=datetime.now(timezone.utc)
    )
    return episodes


@router.post('/get-memory', status_code=status.HTTP_200_OK)
async def get_memory(
    request: GetMemoryRequest,
    graphiti: ZepGraphitiDep,
):
    combined_query = compose_query_from_messages(request.messages)
    result = await graphiti.search(
        group_ids=[request.group_id],
        query=combined_query,
        num_results=request.max_facts,
    )
    facts = [get_fact_result_from_edge(edge) for edge in result]
    return GetMemoryResponse(facts=facts, nodes=None)


def compose_query_from_messages(messages: list[Message]):
    combined_query = ''
    for message in messages:
        combined_query += f'{message.role_type or ""}({message.role or ""}): {message.content}\n'
    return combined_query


# TODO - 세가지 검색 각각 실행 후 결과를 종합해야함.
@router.post('/search-fused', status_code=status.HTTP_200_OK)
async def search_fused(query: SearchQuery, graphiti: ZepGraphitiDep):
    # --- [1. 검색 함수 정의부] ---
    async def get_text_matches():
        config = SearchConfig(
            node_config=NodeSearchConfig(search_methods=[NodeSearchMethod.bm25], reranker=NodeReranker.rrf),
            limit=query.max_nodes
        )
        res = await graphiti._search(query=query.query, config=config, group_ids=query.group_ids)
        return res.nodes or []

    async def get_vector_matches():
        config = SearchConfig(
            node_config=NodeSearchConfig(
                search_methods=[NodeSearchMethod.cosine_similarity], 
                reranker=NodeReranker.rrf,
                sim_min_score=0.6
            ),
            limit=query.max_nodes
        )
        res = await graphiti._search(query=query.query, config=config, group_ids=query.group_ids)
        return res.nodes or []

    async def get_community_matches():
        config = SearchConfig(
            community_config=CommunitySearchConfig(
                search_methods=[CommunitySearchMethod.cosine_similarity],
            ),
            limit=query.max_nodes
        )
        res = await graphiti._search(query=query.query, config=COMMUNITY_HYBRID_SEARCH_RRF, group_ids=query.group_ids)
        return res.communities or []

    async def get_graph_matches(seed_nodes):
        """복합 관계를 찾기 위한 BFS 탐색"""
        if not seed_nodes: return []
        seed_uuids = [n.uuid for n in seed_nodes[:9]]
        config = SearchConfig(
            node_config=NodeSearchConfig(search_methods=[NodeSearchMethod.bfs], bfs_max_depth=2),
            limit=query.max_nodes
        )
        res = await graphiti._search(
            query=query.query, 
            config=config, 
            group_ids=query.group_ids, 
            bfs_origin_node_uuids=seed_uuids
        )
        return res.nodes or []

    # --- [2. 실행 로직] ---
    # 먼저 텍스트, 벡터, 커뮤니티를 병렬로 가져옵니다.
    text_nodes, vector_nodes, community_results = await asyncio.gather(
        get_text_matches(),
        get_vector_matches(),
        get_community_matches()
    )
    
    # [복구된 부분] 벡터 결과를 기반으로 연관 노드들을 추가로 긁어옵니다.
    graph_nodes = await get_graph_matches(vector_nodes)
    
    # --- [3. Fusion 및 정렬] ---
    all_nodes: Dict[str, Dict[str, Any]] = {}
    weights = {'text': 0.2, 'vector': 0.4, 'graph': 0.4}

    def process_matches(nodes, source_key):
        weight = weights[source_key]
        for i, node in enumerate(nodes):
            rank_score = (1.0 / (i + 1)) * weight 
            if node.uuid not in all_nodes:
                all_nodes[node.uuid] = {'node': node, 'total_score': 0.0, 'sources': []}
            all_nodes[node.uuid]['total_score'] += rank_score
            all_nodes[node.uuid]['sources'].append(source_key)

    process_matches(text_nodes, 'text')
    process_matches(vector_nodes, 'vector')
    process_matches(graph_nodes, 'graph')

    ranked_results = sorted(all_nodes.values(), key=lambda x: x['total_score'], reverse=True)
    final_nodes = [get_node_result_from_entity(item['node']) for item in ranked_results[:query.max_nodes]]
    
    # --- [4. 결과 반환] ---
    community_facts = [f"[테마 요약: {c.name}] {c.summary}" for c in community_results]

    debug_data = {
        "query": query.query,
        "counts": {
            "text": len(text_nodes),
            "vector": len(vector_nodes),
            "graph": len(graph_nodes)
        },
        "final_ranking": [
            {"name": n.name, "score": item['total_score'], "sources": item['sources']} 
            for item, n in zip(ranked_results, [item['node'] for item in ranked_results])
        ]
    }

    with open('search-fused-debug.json', 'w', encoding='utf-8') as f:
        json.dump(debug_data, f, ensure_ascii=False, indent=4)

    with open('search-fused.json', 'w', encoding='utf-8') as f:
        json.dump({"community_facts": community_facts, "all_nodes": str(all_nodes), "reranked_results": str(ranked_results),"final_nodes": str(final_nodes)}, f, ensure_ascii=False, indent=4)


    return SearchResults(nodes=final_nodes, community=str(community_facts), facts=None)

@router.post('/search-node', status_code=status.HTTP_200_OK)
async def search_node(query: SearchQuery, graphiti: ZepGraphitiDep):
    search_config= SearchConfig(
        node_config=NodeSearchConfig(
            search_methods=[NodeSearchMethod.bm25, NodeSearchMethod.cosine_similarity],
            reranker=NodeReranker.rrf,
            mmr_lambda=1,
            bfs_max_depth=1,
            sim_min_score=0.6,
        ),
        limit=24,
    )

    search_filter = SearchFilters(node_labels=["Doc"])
    search_config.limit = query.max_nodes
    relevant_nodes = await graphiti._search(
        query=query.query,
        config=search_config,
        group_ids=query.group_ids,
        search_filter=search_filter
    )

    nodes = [get_node_result_from_entity(node) for node in relevant_nodes.nodes]

    return SearchResults(
        nodes=nodes, facts=None, community=''
    )