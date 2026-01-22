# Graph RAG Experiment

## 1. 목적

기존 RAG의 한계를 개선하는 것을 목표로 Graphiti 기반의 Graph RAG 구조를 적용하여, Knowledge Graph가 검색 품질과 문맥 향상에 미치는 영향을 검증한다.

구체적으로 다음을 확인한다.

1. Graph RAG 적용에 따른 연관 문서 검색 정확도
2. 엔티티 관계 기반 탐색을 활용한 복합 질의 처리 성능
3. 필터링 적용한 검색으로 단지 및 날짜별 정확도

이 과정을 통해, Graph 기반 검색 구조가 기존 벡터 기반 RAG의 구조적 한계를 넘어 높은 연관성의 문서 검색이 가능하다는 것을 검토한다.

---

## 2. 배경

### 2.1 기존 응답 사례 분석

* 문서 간 관계나 시점 정보를 인식하지 못함
* 단순 벡터 유사도에 의존한 검색 → 부정확한 맥락 + 불필요한 정보 포함

| 질의 내용                | 검색 결과                                       | 실제 응답             | 기대 응답                   | 주요 문제점                                             |
| -------------------- | ------------------------------------------- | ----------------- | ----------------------- | -------------------------------------------------- |
| 이번 7월 가정식 메뉴 알려줘     | '2024년 7월'로 질문 재작성됨 → 2025년 7월 가정식 메뉴 문서 검색 | 2025년 메뉴 내용 출력    | 2025년 7월 가정식 메뉴         | **재작성 오류 + 검색 시점 인식 실패의 복합 오류**. 내부 과정의 **시점 불일치** |
| 라운지 시설 어떻게 이용할 수 있어? | ‘냉장/냉동고 정리안내’, ‘라운지 이용 설문조사’ 문서 검색          | 냉장고 정리 및 설문 관련 내용 | ‘라운지 시설은 예약제로 이용 가능하다.’ | 관련 문서가 없음에도 **유사도 스코어 기반으로 비관련 문서 선택**             |

### 2.2 문제 유형

| 유형        | 원인               | 영향               |
| --------- | ---------------- | ---------------- |
| 시점 인식 오류  | 날짜·기간 메타정보 반영 부족 | 잘못된 연도·기간의 응답 생성 |
| 비관련 문서 선택 | 유사도 점수 기반 검색     | 질문 의도와 무관한 응답 생성 |

---

## 3. 실험 환경

### 3.1 모델 설정

* 임베딩: `text-embedding-3-small`
* LLM: `gpt-5-mini`

  * Entity 추출 및 Edge 생성, 응답 생성

### 3.2 검색 및 랭킹 (Updated)

기존의 “Doc Entry Node → Graph 확장” 중심에서, **Fused Search + Graph(BFS) 확장** 중심으로 변경됨.

* **Text 검색 (BM25)**

* **Vector 검색 (Cosine Similarity)**

* **Graph 검색 (BFS, multi-hop)**

  * Vector 결과 상위 N개를 origin으로 잡고
  * `NodeSearchMethod.bfs`, `bfs_max_depth = N`로 확장

* **Fusion(RRF 스타일 가중 합산)**

  * text: `0.2`
  * vector: `0.4`
  * graph: `0.4`
  * 각 소스별 랭크에 대해 `1/(rank+1) * weight`로 점수 누적 후 최종 정렬

> 결과적으로, “의미 기반(벡터) + 정확 키워드(BM25) + 관계 기반(BFS)”를 한 번에 결합해 **비관련 문서의 비중을 낮추고 관련 문서의 비중을 높게**한다.

### 3.3 데이터 저장 (Episodes)

* Group: `site:{site_id}`
* 각 Episode는 Markdown 포맷으로 변환되 텍스트를 **episode_body로 저장**
* LLM이 원문으로부터 엔티티를 추출하여 Graph로 구조화

### 3.4 Entity / Edge 스키마 (Updated)

#### Entity Types

* **Who(주체/작성)**

  * `Actor`(부서/기관/업체 등 행위 주체)
  * `Author`(개인 작성자)
* **What(대상)**

  * `Object`(공지/문서/자산/식단/메뉴 등 핵심 대상)
* **How(절차)**

  * `Procedure`(신청/업무 단계/지침)
* **Why(근거/조건)**

  * `Condition`(규정/자격/법령)
* **Event(사건/행사)**

  * `Event`
* **Where(장소)**

  * `Location`
* **When(시간 계층)**

  * `Datetime`(정규화된 시점)
  * `Year`, `Month`, `Week`, `Day`(시간 계층 노드)
* **기타**

  * `Concept`(전문 용어/도메인 지식)
  * `Image`(첨부 이미지)
  * `Web`(외부 링크)
  * `Category`(게시판/분류)

#### Edge Types

* `EXECUTED_BY` : 작성자/실행 주체 연결 (Who)
* `SCHEDULED_ON` : 특정 시점 할당 (When)
* `PART_OF` : 시간 계층 구성 (Datetime–Day–Month–Year 등)
* `DEPENDS_ON` : 조건/근거 참조 (Why)
* `TRIGGERS` : 인과/유발 관계 (Event 중심)
* `LOCATED_IN` : 장소 연결 (Where)
* `HAS_DETAIL` : 이미지/링크/카테고리/컨셉 등 상세 연결 (Metadata)

#### Edge Type Mapping(규칙 기반 연결)

엔티티 조합별 허용 엣지를 제한하여 **잘못된 엣지 생성/확장을 방지**하고, multi-hop 추론을 안정화한다.

예시:

* (`Object` → `Author`) = `EXECUTED_BY`
* (`Object` → `Datetime`) = `SCHEDULED_ON`
* (`Datetime` → `Day`) = `PART_OF`
* (`Object` → `Image/Web/Concept/Category`) = `HAS_DETAIL`
* (`Object/Procedure` → `Condition`) = `DEPENDS_ON`

### 3.5 선택 이유 (Updated)

| 항목                                           | 설명                                                             |
| -------------------------------------------- | -------------------------------------------------------------- |
| **Episode Body 원본 유지**                       | Node/Edge는 요약/속성 중심이므로, 최종 답변 근거는 원본(episode_body)이 가장 신뢰도가 높음 |
| **도메인 엔티티 확장(Object/Procedure/Condition 등)** | “누가/무엇을/어떻게/왜/언제/어디서” 질의에 구조적으로 대응                             |
| **시간 계층(Year/Month/Week/Day) + Datetime**    | “이번 7월”, “올해”, “3월 2주차” 같은 기간 질의를 계층적으로 필터/확장 가능               |
| **HAS_DETAIL로 메타 통합**                        | 이미지/링크/카테고리/컨셉을 하나의 패턴으로 연결해 확장/근거 제시에 유리                      |
| **Fused Search(BM25+Vector+BFS)**            | 유사도만으로 비관련 문서가 섞이는 문제를 완화하고, 관계 기반으로 재확장하여 맥락 일관성 강화           |
| **Community 요약 제공**                          | “테마/군집” 단위의 상위 요약을 함께 제공해 탐색성과 설명력 개선                          |

---

## 4. 데이터 저장 (Episodes)

### 4.1 전체 구조 (Updated Concept)

```
Group (site:{site_id})
└─ Episodic (episode_body = 원문)
   └─ Extracted Entities
      ├─ Object / Procedure / Condition / Event ...
      ├─ Author / Actor
      ├─ Datetime ─ PART_OF ─ Day ─ PART_OF ─ Month ─ PART_OF ─ Year
      ├─ Location
      └─ Image / Web / Concept / Category
```

### 4.2 Entity / Edge 예시 (Updated)

| Entity     | 의미        | 예시(Name)                     |
| ---------- | --------- | ---------------------------- |
| `Object`   | 공지/문서/대상  | Object:관리비 납부마감안내            |
| `Author`   | 작성자(개인)   | Author:홍길동(생활지원센터)           |
| `Actor`    | 주체(부서/기관) | Actor:생활지원센터                 |
| `Datetime` | 시점        | Datetime:2025-03-31 00:00:00 |
| `Month`    | 월         | Month:3                      |
| `Year`     | 연도        | Year:2025                    |
| `Category` | 분류        | Category:공지사항                |
| `Web`      | 링크        | Web:/post/1000001/...        |
| `Image`    | 이미지       | Image:PT1000001:1000020      |

| Edge                                                 | 의미          |
| ---------------------------------------------------- | ----------- |
| `Object -[:EXECUTED_BY]-> Author/Actor`              | 작성자/주체 연결   |
| `Object -[:SCHEDULED_ON]-> Datetime`                 | 문서 시점 연결    |
| `Datetime -[:PART_OF]-> Day/Month/Year`              | 시간 계층 구성    |
| `Object -[:HAS_DETAIL]-> Image/Web/Category/Concept` | 상세/메타 연결    |
| `Object/Procedure -[:DEPENDS_ON]-> Condition`        | 규정/조건 근거    |
| `Event -[:TRIGGERS]-> Procedure/Event`               | 사건 기반 유발 관계 |
| `Object/Event -[:LOCATED_IN]-> Location`             | 장소 연결       |

---

## 5. 검색 Flow (Updated)

### 5.1 전체 흐름

```
질문
 → BM25(Text) Node 검색
 → Vector(Cosine) Node 검색 (min_score=0.6)
 → Vector seed 기반 BFS(Graph) 확장 (depth=2)
 → Fusion(가중 RRF)
 → 상위 N개 노드 반환
 → (선택) episode_body 원문 로딩 후 LLM 응답 생성
```

### 5.2 Fused Search 세부 (search-fused)

* 입력: `query`, `group_ids`, `max_nodes`
* 병렬:

  * Text nodes(BM25)
  * Vector nodes(Cosine)
* Graph 확장:

  * Vector nodes 상위 N개 uuid를 seed로 BFS 탐색(depth=2)
* Fusion:

  * text 0.2 / vector 0.4 / graph 0.4
  * 각 소스별 랭킹 점수 누적 후 최종 정렬
* 출력:

  * `nodes`: 최종 상위 N개
  * `facts`: 현재 미사용(None)

---

## 6. 검증 포인트 (Updated)

* 관련 노드(문서/대상) 검색 정확도 (BM25 vs Vector vs Fusion 비교)
* 복합 질의(규정/절차/시점/주체)에서 BFS 확장 효과
* 기간 질의(올해/이번 달/몇 주차)에서 시간 계층(PART_OF) 활용 가능성
* 카테고리/링크/이미지 등 메타 근거(HAS_DETAIL) 연결 품질

---

## 7. 결과

공지·게시판 검색에서는 단순 문서 유사도 기반 검색보다 **(1) 도메인 엔티티 구조화(Object/Procedure/Condition 등), (2) 시간 계층 모델링(Year/Month/Week/Day + Datetime), (3) BM25+Vector+BFS를 결합한 Fused Search**가 더 정확하고 일관된 응답을 제공한다.
