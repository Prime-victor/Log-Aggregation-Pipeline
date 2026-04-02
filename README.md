# Log-Aggregation-Pipeline

> A production-grade observability platform built with Django, Elasticsearch, React, and Python ML.
> Comparable in architecture to Datadog, Splunk, or a self-hosted ELK stack with intelligence.

---

## Document Index

| File | Phases Covered | Key Topics |
|------|---------------|------------|
| `PHASE_01_SETUP.md` | Phase 1 | Docker Compose, Django init, React scaffold, all config files |
| `PHASE_02_03_INGESTION_AND_BACKEND.md` | Phases 2–3 | Filebeat, Logstash pipeline, ES index templates, Django models, RBAC, URL routing |
| `PHASE_04_05_06_QUERY_RULES_ASYNC.md` | Phases 4–6 | Log search API, aggregations, rule engine, Celery tasks |
| `PHASE_07_08_09_10_ML_ALERTS_FRONTEND_PROD.md` | Phases 7–10 | Isolation Forest ML service, Slack/email alerts, React dashboard, Kubernetes |

---

## Architecture at a Glance

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          LOG SOURCES                                    │
│  Node.js App  │  Django App  │  Nginx  │  Any Service                  │
└───────────────┬─────────────┬──────────┬───────────────────────────────┘
                │             │          │
                ▼             ▼          ▼
         ┌─────────────────────────────────┐
         │         FILEBEAT                │  Ships logs from disk
         │    (sidecar / daemon)           │
         └────────────────┬────────────────┘
                          │
                          ▼
         ┌─────────────────────────────────┐
         │         LOGSTASH                │  Parse, enrich, route
         │    (JSON parse, GeoIP,          │
         │     normalize levels)           │
         └────────────────┬────────────────┘
                          │
               ┌──────────┴──────────┐
               │                     │
               ▼                     ▼
  ┌────────────────────┐   ┌──────────────────────┐
  │   ELASTICSEARCH    │   │     KAFKA (optional) │
  │  (log storage +    │   │  (high-volume buffer) │
  │   full-text search)│   └──────────────────────┘
  └────────┬───────────┘
           │
    ┌──────┴──────────────────────────────────────────┐
    │                DJANGO BACKEND                    │
    │  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
    │  │ Auth/RBAC│  │ Rule     │  │ Alert         │  │
    │  │ JWT      │  │ Engine   │  │ Dispatch      │  │
    │  └──────────┘  └──────────┘  └───────────────┘  │
    │  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
    │  │ Log      │  │ ES Query │  │ REST API      │  │
    │  │ Metadata │  │ Layer    │  │ (DRF)         │  │
    │  └──────────┘  └──────────┘  └───────────────┘  │
    └──────────────────────────┬──────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
    ┌─────────────┐  ┌──────────────┐  ┌────────────────┐
    │  POSTGRESQL │  │    REDIS     │  │  AI SERVICE    │
    │  users      │  │  Celery      │  │  (FastAPI +    │
    │  rules      │  │  broker      │  │  Isolation     │
    │  alerts     │  │  cache       │  │  Forest)       │
    │  anomalies  │  └──────────────┘  └────────────────┘
    └─────────────┘
                               │
                               ▼
         ┌─────────────────────────────────┐
         │      CELERY WORKERS             │
         │  - Rule evaluation (60s)        │
         │  - Alert notification delivery  │
         │  - Anomaly polling (5m)         │
         └─────────────────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
        ┌──────────┐    ┌──────────┐    ┌──────────────┐
        │  EMAIL   │    │  SLACK   │    │  WEBHOOK     │
        └──────────┘    └──────────┘    └──────────────┘

                               ▲
                               │  REST API
                               │
         ┌─────────────────────────────────┐
         │      REACT DASHBOARD            │
         │  Logs viewer │ Alerts │ Rules   │
         │  Analytics charts │ RBAC UI    │
         └─────────────────────────────────┘
```

---

## Data Flow Summary

### Log Ingestion Path
```
App writes JSON log → Filebeat reads file → Logstash parses + enriches
→ Elasticsearch indexes (logs-{service}-{date}) → Kibana / Django API reads
```

### Alert Trigger Path
```
Celery Beat (every 60s) → Rule Engine evaluates each active rule
→ Query ES for metric (error_rate, count, latency)
→ Compare to threshold → If breached: create Alert in PostgreSQL
→ Celery task: deliver via Email + Slack
```

### Anomaly Detection Path
```
Celery Beat (every 5m) → POST /detect to AI Service
→ Extract feature vectors from ES → Score with Isolation Forest
→ Return anomalies → Save to PostgreSQL Anomaly table
```

---

## Quick Start

```bash
# 1. Clone and configure
git clone <your-repo> log-intelligence-platform
cd log-intelligence-platform
cp backend/.env.example backend/.env
# Edit backend/.env with your values

# 2. Start infrastructure
cd infrastructure
docker compose up -d postgres elasticsearch redis zookeeper kafka logstash kibana

# 3. Wait for Elasticsearch (~60s)
docker compose exec elasticsearch curl -s http://localhost:9200/_cluster/health

# 4. Apply ES index template
curl -X PUT "http://localhost:9200/_index_template/logs-template" \
  -H "Content-Type: application/json" \
  -d @../services/search/elasticsearch/index-config/logs-template.json

# 5. Start application layer
docker compose up -d backend celery_worker celery_beat ai_service frontend

# 6. Initialize database
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser

# 7. Start generating sample logs
docker compose up -d sample-nodejs-app

# 8. Open dashboard
open http://localhost:3000
```

---

## Service Ports Reference

| Service         | Port   | URL                              |
|-----------------|--------|----------------------------------|
| React Frontend  | 3000   | http://localhost:3000            |
| Django Backend  | 8000   | http://localhost:8000            |
| AI Service      | 8001   | http://localhost:8001            |
| Elasticsearch   | 9200   | http://localhost:9200            |
| Kibana          | 5601   | http://localhost:5601            |
| Logstash API    | 9600   | http://localhost:9600            |
| Logstash Beats  | 5044   | (Filebeat input)                 |
| Logstash TCP    | 5000   | (Direct JSON input)              |
| Kafka           | 9092   | (Kafka broker)                   |
| Redis           | 6379   | (Internal)                       |
| PostgreSQL      | 5432   | (Internal)                       |

---

## Key Design Decisions (and Why)

**Why split PostgreSQL + Elasticsearch?**
PostgreSQL is your source of truth for transactional data (users, rules, alerts). Elasticsearch is optimized for log storage: inverted indices, time-series queries, aggregations, and horizontal scaling. Never put logs in Postgres — you'll hit performance walls immediately.

**Why Celery for rule evaluation?**
HTTP requests must return fast. Rule evaluation queries ES (slow, variable latency) and potentially sends emails. Running this inline would cause 30s+ API timeouts. Celery decouples this completely.

**Why Isolation Forest for anomaly detection?**
It's unsupervised (no labeled training data needed), handles high-dimensional feature spaces well, is computationally cheap to score in real-time, and has good interpretability. For production: consider adding a supervised layer once you have labeled incidents.

**Why a separate AI microservice?**
Separation of concerns: the ML service has its own dependency tree (scikit-learn, numpy), its own scaling profile (GPU possible), and its own release cycle. Django doesn't need to know about ML internals.

**Why UUID primary keys everywhere?**
Prevents sequential ID enumeration (security), works correctly in distributed systems, and survives database merges/migrations without ID collision.