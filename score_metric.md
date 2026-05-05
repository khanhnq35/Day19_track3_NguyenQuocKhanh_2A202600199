# Score Metric — Lab Day 19 GraphRAG Self-Validation

## Mục đích

File này dùng để **tự đánh giá chất lượng** bài lab trước khi nộp. Chạy qua từng checklist item, ghi điểm, tính tổng.

---

## Thang điểm tổng quan

| Hạng mục | Điểm tối đa | Trọng số |
|----------|-------------|----------|
| A. Pipeline Completeness | 25 | 25% |
| B. Graph Quality | 25 | 25% |
| C. Query Engine | 20 | 20% |
| D. Evaluation & Comparison | 20 | 20% |
| E. Report & Documentation | 10 | 10% |
| **Tổng** | **100** | **100%** |

### Kết quả phân loại

| Mức | Điểm | Ý nghĩa |
|-----|-------|---------|
| ❌ FAIL | < 50 | Thiếu nhiều phần core, cần làm lại |
| ⚠️ PASS | 50–69 | Đủ nộp, còn nhiều thiếu sót |
| ✅ GOOD | 70–84 | Hoàn thành tốt, vài chỗ cần cải thiện |
| 🌟 EXCELLENT | 85–100 | Xuất sắc, đủ tiêu chuẩn production |

---

## A. Pipeline Completeness (25 điểm)

| # | Tiêu chí | Điểm | Đạt? | Ghi chú |
|---|----------|------|------|---------|
| A1 | Corpus tồn tại (`data/tech_company_corpus.txt`) với ≥15 đoạn văn | 3 | ☐ | |
| A2 | Entity Extraction chạy được, output triples hợp lệ | 5 | ☐ | |
| A3 | Deduplication logic hoạt động (không có node trùng) | 3 | ☐ | |
| A4 | Neo4j Docker chạy OK, kết nối Bolt thành công | 4 | ☐ | |
| A5 | Graph Construction: data được insert vào Neo4j thành công | 5 | ☐ | |
| A6 | Flat RAG baseline (ChromaDB) hoạt động | 3 | ☐ | |
| A7 | Có `requirements.txt` và `.env.example` | 2 | ☐ | |

**Subtotal A: ___ / 25**

### Validation Commands
```bash
# A1: Check corpus
wc -l data/tech_company_corpus.txt  # Expected: ≥50 lines

# A4: Check Neo4j
docker ps | grep neo4j  # Expected: container running

# A5: Check graph data
python -c "
from neo4j import GraphDatabase
d = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j','graphrag2024'))
with d.session() as s:
    nodes = s.run('MATCH (n) RETURN count(n) as c').single()['c']
    rels = s.run('MATCH ()-[r]->() RETURN count(r) as c').single()['c']
    print(f'Nodes: {nodes}, Relationships: {rels}')
    assert nodes >= 50, f'Too few nodes: {nodes}'
    assert rels >= 80, f'Too few relationships: {rels}'
    print('✅ Graph quality OK')
"
```

---

## B. Graph Quality (25 điểm)

| # | Tiêu chí | Điểm | Đạt? | Ghi chú |
|---|----------|------|------|---------|
| B1 | ≥50 nodes trong graph | 5 | ☐ | |
| B2 | ≥80 relationships trong graph | 5 | ☐ | |
| B3 | ≥4 loại Node labels (COMPANY, PERSON, PRODUCT, ...) | 3 | ☐ | |
| B4 | ≥5 loại Relationship types (FOUNDED_BY, CEO_OF, ...) | 3 | ☐ | |
| B5 | Không có orphan nodes (mọi node có ít nhất 1 relationship) | 3 | ☐ | |
| B6 | Có multi-hop paths tồn tại (path length ≥ 3) | 3 | ☐ | |
| B7 | Screenshot Neo4j graph visualization có trong `results/screenshots/` | 3 | ☐ | |

**Subtotal B: ___ / 25**

### Validation Commands
```bash
python -c "
from neo4j import GraphDatabase
d = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j','graphrag2024'))
with d.session() as s:
    # B1-B2
    nodes = s.run('MATCH (n) RETURN count(n) as c').single()['c']
    rels = s.run('MATCH ()-[r]->() RETURN count(r) as c').single()['c']
    print(f'B1: Nodes = {nodes} (need ≥50)')
    print(f'B2: Rels = {rels} (need ≥80)')

    # B3
    labels = s.run('MATCH (n) RETURN DISTINCT labels(n) as l').data()
    unique_labels = set()
    for row in labels:
        for l in row['l']:
            unique_labels.add(l)
    print(f'B3: Label types = {len(unique_labels)}: {unique_labels} (need ≥4)')

    # B4
    rel_types = s.run('MATCH ()-[r]->() RETURN DISTINCT type(r) as t').data()
    print(f'B4: Rel types = {len(rel_types)}: {[r[\"t\"] for r in rel_types]} (need ≥5)')

    # B5
    orphans = s.run('MATCH (n) WHERE NOT (n)--() RETURN count(n) as c').single()['c']
    print(f'B5: Orphan nodes = {orphans} (need 0)')

    # B6
    long_paths = s.run('MATCH p = (a)-[*3..4]->(b) RETURN count(p) as c LIMIT 1').single()['c']
    print(f'B6: Paths ≥3 hops exist = {long_paths > 0}')
"
```

---

## C. Query Engine (20 điểm)

| # | Tiêu chí | Điểm | Đạt? | Ghi chú |
|---|----------|------|------|---------|
| C1 | Entity extraction từ câu hỏi hoạt động | 4 | ☐ | |
| C2 | 2-hop Cypher traversal trả về kết quả | 4 | ☐ | |
| C3 | Textualization: graph results → readable context | 3 | ☐ | |
| C4 | LLM answer generation từ graph context | 4 | ☐ | |
| C5 | End-to-end: question → answer pipeline chạy được | 5 | ☐ | |

**Subtotal C: ___ / 20**

### Validation Commands
```bash
# Test end-to-end query
python -c "
from src.graphrag_pipeline import query
answer = query('Ai là CEO của OpenAI?')
print(f'Answer: {answer}')
assert len(answer) > 10, 'Answer too short'
print('✅ Query engine OK')
"
```

---

## D. Evaluation & Comparison (20 điểm)

| # | Tiêu chí | Điểm | Đạt? | Ghi chú |
|---|----------|------|------|---------|
| D1 | 20 câu benchmark tồn tại với ground truth | 4 | ☐ | |
| D2 | Flat RAG chạy được trên 20 câu | 3 | ☐ | |
| D3 | GraphRAG chạy được trên 20 câu | 3 | ☐ | |
| D4 | Bảng so sánh đầy đủ (`results/comparison_table.md`) | 3 | ☐ | |
| D5 | GraphRAG accuracy > Flat RAG accuracy (đặc biệt multi-hop) | 3 | ☐ | |
| D6 | Ghi nhận hallucination cases (Flat RAG sai, GraphRAG đúng) | 2 | ☐ | |
| D7 | Cost analysis: token usage + time (`results/cost_analysis.md`) | 2 | ☐ | |

**Subtotal D: ___ / 20**

### Validation Commands
```bash
# Check benchmark file
python -c "
import json
with open('benchmark/questions.json') as f:
    qs = json.load(f)
print(f'D1: {len(qs)} questions (need 20)')
for q in qs:
    assert 'question' in q, 'Missing question field'
    assert 'ground_truth' in q, 'Missing ground_truth field'
    assert 'type' in q, 'Missing type field (single_hop/multi_hop/complex)'
print('✅ Benchmark format OK')
"

# Check comparison table exists
ls -la results/comparison_table.md
ls -la results/cost_analysis.md
```

---

## E. Report & Documentation (10 điểm)

| # | Tiêu chí | Điểm | Đạt? | Ghi chú |
|---|----------|------|------|---------|
| E1 | `README.md` có phần nghiên cứu lý thuyết (3 câu hỏi) | 2 | ☐ | |
| E2 | `README.md` mô tả pipeline architecture | 2 | ☐ | |
| E3 | `README.md` có kết quả benchmark summary | 2 | ☐ | |
| E4 | `README.md` có nhận xét/phân tích sự khác biệt GraphRAG vs Flat RAG | 2 | ☐ | |
| E5 | Code có docstrings (Google Style) và type hints | 2 | ☐ | |

**Subtotal E: ___ / 10**

---

## Bảng tổng kết

| Hạng mục | Điểm đạt | Điểm tối đa |
|----------|----------|-------------|
| A. Pipeline Completeness | ___ | 25 |
| B. Graph Quality | ___ | 25 |
| C. Query Engine | ___ | 20 |
| D. Evaluation & Comparison | ___ | 20 |
| E. Report & Documentation | ___ | 10 |
| **TỔNG** | **___** | **100** |

### Kết quả: ___ → ❌/⚠️/✅/🌟

---

## Quick Validation Script

Chạy script dưới đây để tự động check tất cả tiêu chí có thể kiểm tra bằng code:

```bash
# Từ root project directory
python -c "
import os, json

score = 0
max_score = 0

# === A: Pipeline Completeness ===
print('=== A: Pipeline Completeness ===')

# A1
max_score += 3
if os.path.exists('data/tech_company_corpus.txt'):
    with open('data/tech_company_corpus.txt') as f:
        lines = len(f.readlines())
    if lines >= 50:
        score += 3
        print(f'  A1: ✅ Corpus exists ({lines} lines)')
    else:
        score += 1
        print(f'  A1: ⚠️ Corpus exists but short ({lines} lines)')
else:
    print('  A1: ❌ Corpus missing')

# A4
max_score += 4
import subprocess
result = subprocess.run(['docker', 'ps', '--filter', 'name=neo4j'], capture_output=True, text=True)
if 'neo4j' in result.stdout:
    score += 4
    print('  A4: ✅ Neo4j container running')
else:
    print('  A4: ❌ Neo4j container not running')

# A7
max_score += 2
if os.path.exists('requirements.txt'):
    score += 1
    print('  A7a: ✅ requirements.txt exists')
else:
    print('  A7a: ❌ requirements.txt missing')
if os.path.exists('.env') or os.path.exists('.env.example'):
    score += 1
    print('  A7b: ✅ .env exists')
else:
    print('  A7b: ❌ .env missing')

# === B: Graph Quality ===
print('\n=== B: Graph Quality ===')
try:
    from neo4j import GraphDatabase
    d = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j','graphrag2024'))
    with d.session() as s:
        nodes = s.run('MATCH (n) RETURN count(n) as c').single()['c']
        rels = s.run('MATCH ()-[r]->() RETURN count(r) as c').single()['c']

        max_score += 5
        if nodes >= 50: score += 5; print(f'  B1: ✅ Nodes = {nodes}')
        elif nodes >= 30: score += 3; print(f'  B1: ⚠️ Nodes = {nodes} (need ≥50)')
        else: print(f'  B1: ❌ Nodes = {nodes}')

        max_score += 5
        if rels >= 80: score += 5; print(f'  B2: ✅ Rels = {rels}')
        elif rels >= 50: score += 3; print(f'  B2: ⚠️ Rels = {rels} (need ≥80)')
        else: print(f'  B2: ❌ Rels = {rels}')

        orphans = s.run('MATCH (n) WHERE NOT (n)--() RETURN count(n) as c').single()['c']
        max_score += 3
        if orphans == 0: score += 3; print(f'  B5: ✅ No orphan nodes')
        else: print(f'  B5: ❌ Orphan nodes = {orphans}')
    d.close()
except Exception as e:
    print(f'  B: ❌ Neo4j connection failed: {e}')
    max_score += 13

# === D: Benchmark ===
print('\n=== D: Evaluation ===')
max_score += 4
if os.path.exists('benchmark/questions.json'):
    with open('benchmark/questions.json') as f:
        qs = json.load(f)
    if len(qs) >= 20:
        score += 4
        print(f'  D1: ✅ {len(qs)} benchmark questions')
    else:
        score += 2
        print(f'  D1: ⚠️ Only {len(qs)} questions (need 20)')
else:
    print('  D1: ❌ benchmark/questions.json missing')

max_score += 3
if os.path.exists('results/comparison_table.md'):
    score += 3
    print('  D4: ✅ Comparison table exists')
else:
    print('  D4: ❌ Comparison table missing')

max_score += 2
if os.path.exists('results/cost_analysis.md'):
    score += 2
    print('  D7: ✅ Cost analysis exists')
else:
    print('  D7: ❌ Cost analysis missing')

# === E: Documentation ===
print('\n=== E: Documentation ===')
max_score += 2
if os.path.exists('README.md'):
    score += 2
    print('  E1: ✅ README.md exists')
else:
    print('  E1: ❌ README.md missing')

# === SUMMARY ===
print(f'\n{'='*40}')
print(f'Automated Score: {score} / {max_score} (checked items only)')
pct = score / max_score * 100 if max_score > 0 else 0
if pct >= 85: grade = '🌟 EXCELLENT'
elif pct >= 70: grade = '✅ GOOD'
elif pct >= 50: grade = '⚠️ PASS'
else: grade = '❌ FAIL'
print(f'Grade (partial): {grade} ({pct:.0f}%)')
print(f'Note: Manual checks still needed for remaining {100 - max_score} points')
"
```

---

> [!TIP]
> Chạy validation script này **trước khi nộp bài** để đảm bảo không thiếu sót phần nào. Các tiêu chí không kiểm tra tự động được (C1-C5, D5-D6, E2-E5) cần review thủ công.
