# GraphRAG Flow

## [Step 1: Document - 데이터 수집]

1. **Loader**
    * **Goal**: 원본 데이터(공지사항, 게시글 등)를 시스템으로 로드.
    * **Process**:
        * site: 지웰홈스왕십리(1000024)
        * board: 공지사항(1000039), FAQ(1000038), 입주안내(1000087) etc.
        * site의 board를 가져와서 Document/Image로 저장.

2. **Vision (이미지 처리)**
    * **Goal**: 이미지 내 텍스트를 추출하여 검색 및 답변에 활용.
    * **Input**: Image URL
    * **Process**:
        * **Prompt**:
            * 검색 / 답변 생성에 사용 가능한 구조화된 텍스트를 추출.
            * raw text: 이미지의 모든 텍스트 추출
    * **Output**: OCR 또는 Vision Model을 사용하여 추출한 이미지의 모든 텍스트(Raw Text)
    * 텍스트를 Image에 업데이트 (원본 보존)

## [Step 2: Transform - 데이터 변환]

1. **Build Document Content**
    * **Strategy**: `MD2` (Markdown Conversion).
    * **Process**: `Document` 및 `Image` 데이터를 그래프 구축에 적합한 Markdown 형식의 텍스트로 변환.

## [Step 3: Graph Storage - 지식 그래프 구축]

1. **Extract Nodes (Phase 1)**
    * **Goal**: 5W1H(육하원칙)에 따라 엔티티를 추출하고 분류.
    * **Prompt Rules**:
        * **Language**: 한국어(Korean) 필수.
        * **Entity Types (14 types)**:
            * **Who**: `ACTOR` (행위자), `AUTHOR` (작성자)
            * **What**: `OBJECT` (대상), `EVENT` (사건), `IMAGE` (이미지), `WEB` (웹사이트), `CATEGORY` (카테고리)
            * **How**: `PROCEDURE` (절차)
            * **Why**: `CONDITION` (조건)
            * **Where**: `LOCATION` (위치)
            * **When**: `DATETIME` (날짜/시간), `YEAR`, `MONTH`, `DAY`
    * **Attributes**:
        * `type`: 엔티티 유형.
        * `context`: 엔티티가 포함된 문맥.
    * **Output**: Entity Nodes

2. **Normalize Nodes**
    * **Goal**: Entity Nodes의 정규화.
    * **Rules**:
        * **Surfcae match** (텍스트 표면 일치 및 유사도 검사)
            * name과 context가 얼마나 일치하는지 점수화
            * 이름 유사도: SequenceMatcher를 활용해 게산 (70% 비중)
            * 타입 검증: name이 비슷해도 Labels(타입)가 다르면 노드 분리.
            * 맥락 보정(Context Boost): 추출된 원문 문장이 일치하면, name이 조금 달라도 동일 엔티티일 확률이 높다고 판단하여 점수를 높임. (30% 비중)
        * **DBSCAN** (Density-Based Spatial Clustering Of Applications With Noise)
            * 계산된 유사도 score로 Entity들을 그룹화.
            * 거리 변환:  1 - 유사도 score
            * 자동 군집화: 임계값(0.75) 이내에 밀집된 노드들을 하나의 클러스터로 군집화
            * 대표성 추출 (Canonicalization): 묶인 그룹 내에서 가장 많이 등장한 이름을 대표 이름으로 정하고, 속성(attributes)과 특징(features)을 중복 없이 통합
    * **Output**: Entity Nodes

3. **Extract Edges (Phase 2)**
    * **Goal**: 엔티티 간 인과관계 및 시간적 계층 구조 설정 (BFS 최적화).
    * **Prompt Rules**:
        * **Language**: 한국어(Korean) 필수.
        * **Hub Node Strategy**:
            * **Temporal Hub**: 주요 노드(OBJECT, EVENT) -> DATETIME 연결.
            * **Hierarchy**: DATETIME -> DAY -> MONTH -> YEAR 연결.
        * **Edge Types**:
            * `EXECUTED_BY`: (Procedure/Event/Object) -> (Actor/Author)
            * `SCHEDULED_ON`: (Any) -> (Datetime)
            * `PART_OF`: (Datetime/Day/Month) -> (Day/Month/Year)
            * `DEPENDS_ON`: (Object/Procedure) -> (Condition/Datetime)
            * `TRIGGERS`: (Event) -> (Procedure/Event)
            * `LOCATED_IN`: (Any) -> (Location)
            * `HAS_DETAIL`: (Object) -> (Image/Web/Category)
    * **Output**: Entity Edges

4. **Summarize Nodes (Phase 3)**
    * **Goal**: 검색 품질(BM25) 향상을 위한 노드 요약 및 키워드 추출.
    * **Process**:
    * **Prompt Rules**:
        * **Language**: 한국어(Korean) 필수.
        * LLM을 활용하여 Vision 텍스트를 포함하여 중요 키워드 추출.
        * LLM을 활용하여 노드 관련 내용을 요약.
    * **Output**: Attributes와 Summary가 포함된 최종 Entity Nodes

5. **Add Episode (저장)**
    * **Goal**: 그래프 데이터와 원본 데이터를 통합 저장.
    * **Structure**:
        * **Group ID**: `site-{siteId}-{strategy}`
        * **Episode Body**: 원본 텍스트(Markdown) 및 Vision 추출 텍스트 보존 (답변 생성의 근거).
        * **Graph**: 추출된 Node 및 Edge 저장.

## [Step 4: Graph RAG - 검색 및 답변 생성]

1. **Query Rewrite**
    * **Goal**: 질문 재작성
    * **Prompt Rules**:
        * 질문을 검색 및 답변에 용이한 완전한 문장으로 작성.
    * **Output**: 재작성된 질문 텍스트

2. **Graph Retrieve (Fused Search)**
    * **Strategy**: Text(BM25) + Vector + Graph(BFS) 결합.
    * **Flow**:
        1. **BM25 Search (Text)**: 키워드 기반 노드 검색 (Weight: 0.2).
        2. **Vector Search (Embedding)**: 의미 기반 노드 검색 (Weight: 0.4).
        3. **BFS Expansion (Graph)**: Vector 검색 상위 노드를 Seed로 하여 연결된 노드(날짜, 상세 정보 등) 확장 (Weight: 0.4).
        4. **Fusion**: RRF(Reciprocal Rank Fusion) 방식으로 최종 순위 결정 및 상위 N개 노드 도출.

3. **Prompt Construction**
    * **Components**:
        * **System Prompt**: 페르소나 및 답변 규칙
        * **User Prompt**:
            * quesiton: Original Query (사용자 질문).
            * nodes: Retrieved Nodes (그래프 맥락).
            * documents: Episode Body (원본 문서 및 Vision 텍스트).

4. **Generate Response**
    * **Process**: LLM이 구성된 프롬프트를 바탕으로 사용자 질문에 대한 최종 답변 생성.
    * **Output**: 생성된 최종 답변

---

## 요약

1. **저장 (Indexing)**
   * `Document` -> `Loader`/`Vision` -> `Transform(MD2)` -> `Graph Extraction` -> `Storage (Graph + Episode)`
2. **검색 (Retrieval)**
   * `Query` -> `Rewrite` -> `Fused Search (BM25 + Vector + BFS)` -> `Context Construction`
3. **생성 (Generation)**
   * `Context` + `Query` -> `LLM` -> `Answer`
