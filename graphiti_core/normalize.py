from typing import Any
import numpy as np
from sklearn.cluster import DBSCAN
import json
from collections import Counter

from graphiti_core.nodes import EntityNode
from graphiti_core.utils.datetime_utils import utc_now
from difflib import SequenceMatcher #* 문자열 유사도 계산
from sklearn.cluster import DBSCAN

class EntityResolver:
    """Production entity resolution with context-aware disambiguation"""
    
    def __init__(self):
        self.similarity_threshold = 0.75
    
    def compute_entity_similarity(self, entity1: EntityNode, entity2: EntityNode):
        """Compute similarity considering both text and semantic context"""
        
        # Exact match gets high score
        if entity1.name.lower() == entity2.name.lower():
            base_score = 0.9
        else:
            # Fuzzy match on surface form
            base_score = SequenceMatcher(
                None, 
                entity1.name.lower(), 
                entity2.name.lower()
            ).ratio()

        feat1 = entity1.attributes
        feat2 = entity2.attributes

        # Type mismatch penalty
        if feat1.get('type') != feat2.get('type'):
            base_score *= 0.3

        
        # Context similarity boost 
        # - 같은 텍스트여도 type에 따라 동일성 판단 보정.
        ctx1 = feat1.get('context', '').lower()
        ctx2 = feat2.get('context', '').lower()
        

        if ctx1 and ctx2:
            if ctx1 == ctx2:
                # 추출된 문장이 완정 동일
                feature_match_score = 1.0
            else:
                # 문장이 조금 다른 경우
                feature_match_score = SequenceMatcher(None, ctx1, ctx2).ratio()
            base_score = 0.7 * base_score + 0.3 * feature_match_score
        return base_score


    def normalize_extracted_nodes(self, extracted_nodes: list[EntityNode], similarity_threshold: float = 0.75):
        self.similariy_threshold = similarity_threshold or self.similarity_threshold

        """Normalize extracted nodes"""

        if not extracted_nodes:
            return []

        n = len(extracted_nodes)
        
        # 1. 유사도 행렬 구성 (자기 자신은 1.0)
        similarity_matrix = np.eye(n)
        for i in range(n):
            for j in range(i + 1, n):
                sim = self.compute_entity_similarity(extracted_nodes[i], extracted_nodes[j])
                similarity_matrix[i, j] = sim
                similarity_matrix[j, i] = sim

        # 2. DBSCAN 클러스터링
        distance_matrix = 1 - similarity_matrix
        clustering = DBSCAN(
            eps=1 - similarity_threshold,
            min_samples=1,
            metric='precomputed'
        ).fit(distance_matrix)

        normalized_nodes: list[EntityNode] = []
        node_to_group_map = {} # {원본_index: 최종_병합_노드}

        # 3. 클러스터별 병합 수행
        for cluster_id in set(clustering.labels_):

            # 해당 클러스터에 속한 원본 인덱스들 추출
            member_indices = [i for i, label in enumerate(clustering.labels_) if label == cluster_id]
            cluster_members = [extracted_nodes[i] for i in member_indices]

            # A. 대표 이름 결정 (빈도수가 가장 높은 이름)
            names = [node.name for node in cluster_members]
            canonical_name = Counter(names).most_common(1)[0][0]

            # B. 타입(Labels) 합치기 (Set으로 중복 제거)
            all_labels = set()
            for node in cluster_members:
                all_labels.update(node.labels)
            
            # C. 속성 및 특징 누적 (Persistence)
            merged_attributes = {}
            all_features = []
            for node in cluster_members:
                # 기존 extraction_features 수집
                features = node.attributes
                if isinstance(features, list):
                    all_features.extend(features)
                else:
                    all_features.append(features)
            
            unique_features = []
            seen_json = set()

            for feature in all_features:
                feature_dict = feature.model_dump() if hasattr(feature, 'model_dump') else feature

                feature_json = json.dumps(feature_dict, sort_keys=True, default=str)

                if feature_json not in seen_json:
                    seen_json.add(feature_json)
                    unique_features.append(feature_dict)

            merged_attributes["extraction_features"] = json.dumps(unique_features, ensure_ascii=False)

            merged_attributes["occurrence_count"] = len(cluster_members)


            # D. 새로운 EntityNode 생성 (병합본)
            new_node = EntityNode(
                name=canonical_name,
                group_id=cluster_members[0].group_id,
                labels=list(all_labels),
                summary='',
                created_at=utc_now(),
                attributes=merged_attributes
            )
            normalized_nodes.append(new_node)

            # 핵심: 이 클러스터에 속했던 모든 원본 인덱스가 이 new_node를 바라보게 함
            for idx in member_indices:
                node_to_group_map[idx] = new_node

        return normalized_nodes, node_to_group_map
        

