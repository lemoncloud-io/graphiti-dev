import unittest
import sys
import os
import json
from datetime import datetime, timezone
from difflib import SequenceMatcher
from unittest.mock import Mock
from graphiti_core.nodes import EntityNode
from graphiti_core.normalize import EntityResolver

class EntityResolverTests(unittest.TestCase):
    '''
    test entity resolver

    ## runs
    $ python3.12 -m venv venv
    $ source venv/bin/activate
    $ pip3 install graphiti-core scikit-learn
    $ python3 -m unittest tests.test_normalize
    '''
    def setUp(self):
        self.resolver = EntityResolver()
        self.base_time = datetime.now()
        self.group_id = 'site:1000039'

    def create_node(self, extracted_node={}, uuid=None):

        node_args = {
            'uuid': uuid,
            'name': extracted_node['name'],
            'labels': extracted_node['labels'],
            'group_id': self.group_id,
            'created_at': datetime(2026, 1, 28, 5, 4, 39, 360956, tzinfo=timezone.utc),
            'name_embedding': None,
            'summary': '',
            'attributes': extracted_node['attribute'],
        }
        if uuid is None:
            del node_args['uuid']
            
        return EntityNode(**node_args)

    def test_compute_entity_similarity(self):
        '''Similarity calculation: Same name but different type (penalty applied)'''
        node1 = self.create_node({"name": "생활지원센터", "labels": ["AUTHOR"], "attribute": {"type": "AUTHOR", "context": "[공지사항 생활지원센터] [정기소독] 2월 정기소독 실시안내"}})
        node2 = self.create_node({"name": "생활지원센터", "labels": ["ACTOR"], "attribute": {"type": "ACTOR", "context": "[공지사항 생활지원센터] [정기소독] 2월 정기소독 실시안내"}})
        
        # Name match -> base_score = 0.9
        # Type mismatch penalty -> base_score *= 0.3  (0.27)
        ctx_sim = SequenceMatcher(None, node1.attributes['context'].lower(), node2.attributes['context'].lower()).ratio()
        expected_sim = 0.7 * (0.9 * 0.3) + 0.3 * ctx_sim
        sim1 = self.resolver.compute_entity_similarity(node1, node2)
        self.assertEqual(sim1, 0.489)
        self.assertAlmostEqual(sim1, expected_sim, places=2)
        self.assertLess(sim1, 0.75, "Type mismatch should prevent merging")

        # Similarity calculation: Slightly different names (Fuzzy match)
        node3 = self.create_node({"name": "정기소독", "labels": ["EVENT"], "attribute": {"type": "EVENT", "context": "[정기소독] 2월 정기소독 실시안내"}})
        node4 = self.create_node({"name": "정기소독 실시", "labels": ["EVENT"], "attribute": {"type": "EVENT", "context": "[정기소독] 2월 정기소독 실시안내"}})
        
        name_sim = SequenceMatcher(None, node3.name.lower(), node4.name.lower()).ratio()
        ctx_sim2 = SequenceMatcher(None, node3.attributes['context'].lower(), node4.attributes['context'].lower()).ratio()
        expected_sim2 = 0.7 * name_sim + 0.3 * ctx_sim2

        sim2 = self.resolver.compute_entity_similarity(node3, node4)
        self.assertEqual(sim2, 0.8090909090909091)
        self.assertAlmostEqual(sim2, expected_sim2, places=2)        


    def test_normalize_nodes(self):
        '''Test normalization of extracted nodes using DBSCAN clustering.'''

        # 1. Prepare test data
        extracted_data = {
            "nodes": [
                {"name": "공지사항", "labels": ["CATEGORY"], "attribute": {"type": "CATEGORY", "context": "[공지사항 생활지원센터] [정기소독] 2월 정기소독 실시안내"}},
                {"name": "생활지원센터", "labels": ["AUTHOR"], "attribute": {"type": "AUTHOR", "context": "[공지사항 생활지원센터] [정기소독] 2월 정기소독 실시안내"}},
                {"name": "생활지원센터", "labels": ["ACTOR"], "attribute": {"type": "ACTOR", "context": "[공지사항 생활지원센터] [정기소독] 2월 정기소독 실시안내"}},
                {"name": "정기소독", "labels": ["EVENT"], "attribute": {"type": "EVENT", "context": "[정기소독] 2월 정기소독 실시안내"}},
                {"name": "정기소독 실시", "labels": ["EVENT"], "attribute": {"type": "EVENT", "context": "[정기소독] 2월 정기소독 실시안내"}},
                {"name": "2", "labels": ["MONTH"], "attribute": {"type": "MONTH", "context": "2월 정기소독 실시안내"}},
                {"name": "정기소독 실시안내", "labels": ["OBJECT"], "attribute": {"type": "OBJECT", "context": "[정기소독] 2월 정기소독 실시안내"}},
                {"name": "notice", "labels": ["CATEGORY"], "attribute": {"type": "CATEGORY", "context": "카테고리 notice"}},
                {"name": "2025-02-19 16:21:22", "labels": ["DATETIME"], "attribute": {"type": "DATETIME", "context": "작성일 2025-02-19 16:21:22"}},
                {"name": "2025", "labels": ["YEAR"], "attribute": {"type": "YEAR", "context": "작성일 2025-02-19 16:21:22"}},
                {"name": "2", "labels": ["MONTH"], "attribute": {"type": "MONTH", "context": "작성일 2025-02-19 16:21:22"}},
                {"name": "19", "labels": ["DAY"], "attribute": {"type": "DAY", "context": "작성일 2025-02-19 16:21:22"}},
                {"name": "이미지1 (https://image.teset)", "labels": ["IMAGE"], "attribute": {"type": "IMAGE", "context": "첨부 이미지 - [이미지1](https://image.test)"}},
                {"name": "/post/11/board/22", "labels": ["WEB"], "attribute": {"type": "WEB", "context": "링크 /post/11/board/22"}},
            ]
        }

        # Verify default threshold
        self.assertEqual(self.resolver.similarity_threshold, 0.75)


        # Sanity check: create_node helper
        test_uuid = '5e9f662a-7a65-4580-b9b8-9384a0c731d6'
        node1 = self.create_node({"name": "생활지원센터", "labels": ["AUTHOR"], "attribute": {"type": "AUTHOR", "context": "[공지사항 생활지원센터] [정기소독] 2월 정기소독 실시안내"}}, uuid=test_uuid)
        self.assertEqual(node1, EntityNode(
                uuid=test_uuid,
                name='생활지원센터',
                labels=["AUTHOR"],
                group_id=self.group_id,
                created_at=datetime(2026, 1, 28, 5, 4, 39, 360956, tzinfo=timezone.utc),
                name_embedding=None,
                summary='',
                attributes={"type": "AUTHOR", "context": "[공지사항 생활지원센터] [정기소독] 2월 정기소독 실시안내"},
            ))

        # 2. Create initial nodes from sample data
        initial_nodes = [
            self.create_node(n) for n in extracted_data['nodes']
        ]
        
        # 3. Run normalization
        # "정기소독" and "정기소독 실시" should merge because their similarity (0.809) > threshold (0.75)
        normalized_nodes = self.resolver.normalize_extracted_nodes(initial_nodes, 0.75)
        
        # 4. Verify results
        # Expected count: 14 initial nodes. "정기소독" and "정기소독 실시" merge -> 13 nodes.
        self.assertEqual(len(normalized_nodes), 13)

        # Verify '정기소독' (EVENT) was merged (occurrence_count should be 2)
        event_node = next((n for n in normalized_nodes if n.name == "정기소독"))
        self.assertIsNotNone(event_node)
        self.assertEqual(event_node.attributes.get('occurrence_count'), 2)

        # Verify '생활지원센터' (AUTHOR) was NOT merged with '생활지원센터' (ACTOR) due to type mismatch
        author_nodes = [n for n in normalized_nodes if n.name == '생활지원센터']
        self.assertEqual(len(author_nodes), 2)
        self.assertEqual(author_nodes[0].attributes.get('occurrence_count'), 1)
        self.assertEqual(author_nodes[1].attributes.get('occurrence_count'), 1)


if __name__ == '__main__':
    unittest.main()