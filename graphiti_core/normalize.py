import numpy as np
from sklearn.cluster import DBSCAN

class EntityResolver:
    """Production entity resolution with context-aware disambiguation"""
    
    def __init__(self):
        self.entity_cache = {}
        self.canonical_map = {}
    
    def compute_entity_similarity(self, entity1, entity2):
        """Compute similarity considering both text and semantic context"""
        
        # Exact match gets high score
        if entity1['surface_form'].lower() == entity2['surface_form'].lower():
            base_score = 0.9
        else:
            # Fuzzy match on surface form
            from difflib import SequenceMatcher
            base_score = SequenceMatcher(
                None, 
                entity1['surface_form'].lower(), 
                entity2['surface_form'].lower()
            ).ratio()
        
        # Type mismatch penalty
        if entity1['type'] != entity2['type']:
            base_score *= 0.3
        
        # Context similarity boost
        if 'features' in entity1 and 'features' in entity2:
            shared_features = set(entity1['features'].keys()) & set(entity2['features'].keys())
            if shared_features:
                # Features match increases confidence
                feature_match_score = sum(
                    1 for k in shared_features 
                    if entity1['features'][k] == entity2['features'][k]
                ) / len(shared_features)
                base_score = 0.7 * base_score + 0.3 * feature_match_score
        
        return base_score
    def resolve_entities(self, all_entities, similarity_threshold=0.75):
        """Cluster entities into canonical forms using DBSCAN"""
        
        n = len(all_entities)
        if n == 0:
            return {}
        
        # Build similarity matrix
        similarity_matrix = np.zeros((n, n))
        for i in range(n):
            for j in range(i+1, n):
                sim = self.compute_entity_similarity(all_entities[i], all_entities[j])
                similarity_matrix[i,j] = sim
                similarity_matrix[j,i] = sim
        
        # Convert similarity to distance for DBSCAN
        distance_matrix = 1 - similarity_matrix
        
        # Cluster entities
        clustering = DBSCAN(
            eps=1-similarity_threshold, 
            min_samples=1, 
            metric='precomputed'
        ).fit(distance_matrix)
        
        # Create canonical entities
        canonical_entities = {}
        for cluster_id in set(clustering.labels_):
            cluster_members = [
                all_entities[i] for i, label in enumerate(clustering.labels_) 
                if label == cluster_id
            ]
            
            # Most common surface form becomes canonical
            surface_forms = [e['surface_form'] for e in cluster_members]
            canonical_form = max(set(surface_forms), key=surface_forms.count)
            
            canonical_entities[canonical_form] = {
                'canonical_name': canonical_form,
                'type': cluster_members[0]['type'],
                'variant_forms': list(set(surface_forms)),
                'occurrences': len(cluster_members),
                'contexts': [e['context'] for e in cluster_members[:5]]  # Sample contexts
            }
            
            # Map all variants to canonical form
            for variant in surface_forms:
                self.canonical_map[variant] = canonical_form
        
        return canonical_entities
    
    def get_canonical_form(self, surface_form):
        """Get canonical entity name for any surface form"""
        return self.canonical_map.get(surface_form, surface_form)