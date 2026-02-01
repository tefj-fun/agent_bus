#!/usr/bin/env python3
"""Seed initial templates into memory system."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.memory.chroma_store import ChromaDBStore
from src.config import settings


# Template definitions
SEED_TEMPLATES = [
    {
        "id": "template_web_app_saas",
        "pattern_type": "template",
        "success_score": 0.9,
        "metadata": {
            "category": "web_app",
            "tech_stack": "React, FastAPI, PostgreSQL",
            "complexity": "medium",
        },
        "content": """# SaaS Web Application Template

## Architecture
- **Frontend**: React 18 + TypeScript + TailwindCSS
- **Backend**: FastAPI (Python 3.10+)
- **Database**: PostgreSQL 15
- **Auth**: JWT-based authentication
- **Deployment**: Docker + Kubernetes

## Features
- User authentication and authorization
- Multi-tenant architecture
- RESTful API with OpenAPI docs
- WebSocket support for real-time updates
- Role-based access control (RBAC)
- Payment integration (Stripe)
- Email notifications
- Analytics dashboard

## Components
1. Landing page with hero section
2. User dashboard
3. Admin panel
4. Billing and subscription management
5. User settings and profile

## Best Practices
- Input validation on frontend and backend
- Error handling with proper HTTP status codes
- Database migrations with Alembic
- Unit and integration tests
- CI/CD pipeline with GitHub Actions
- Monitoring with Prometheus + Grafana
""",
    },
    {
        "id": "template_ml_pipeline",
        "pattern_type": "template",
        "success_score": 0.85,
        "metadata": {
            "category": "ml_pipeline",
            "tech_stack": "PyTorch, FastAPI, MLflow",
            "complexity": "high",
        },
        "content": """# Machine Learning Pipeline Template

## Architecture
- **Training**: PyTorch 2.0+ with distributed training
- **Serving**: FastAPI with model versioning
- **Experiment Tracking**: MLflow
- **Model Registry**: MLflow Model Registry
- **Monitoring**: Prometheus + Grafana
- **Data Storage**: S3-compatible object storage

## Pipeline Stages
1. Data ingestion and validation
2. Feature engineering
3. Model training with hyperparameter tuning
4. Model evaluation and validation
5. Model deployment
6. Inference serving
7. Performance monitoring

## Components
- Data pipeline (ETL)
- Feature store
- Training orchestration (Airflow/Prefect)
- Model serving API
- A/B testing framework
- Monitoring dashboard

## Best Practices
- Version control for data, models, and code
- Reproducible experiments
- Automated testing for models
- Gradual rollout with canary deployments
- Model performance monitoring
- Data drift detection
""",
    },
    {
        "id": "template_rest_api",
        "pattern_type": "template",
        "success_score": 0.95,
        "metadata": {
            "category": "api",
            "tech_stack": "FastAPI, PostgreSQL, Redis",
            "complexity": "low",
        },
        "content": """# REST API Template

## Architecture
- **Framework**: FastAPI (Python 3.10+)
- **Database**: PostgreSQL with asyncpg
- **Cache**: Redis
- **Documentation**: Auto-generated OpenAPI/Swagger
- **Validation**: Pydantic models

## Features
- CRUD operations for resources
- Pagination and filtering
- Rate limiting
- API key authentication
- Request/response logging
- Health check endpoints
- Metrics endpoint (Prometheus)

## Endpoints Structure
- GET /api/v1/{resource} - List resources
- GET /api/v1/{resource}/{id} - Get resource
- POST /api/v1/{resource} - Create resource
- PUT /api/v1/{resource}/{id} - Update resource
- DELETE /api/v1/{resource}/{id} - Delete resource
- GET /health - Health check
- GET /metrics - Prometheus metrics

## Best Practices
- Versioned API (v1, v2)
- Consistent error responses
- Input validation
- Database connection pooling
- Async/await for I/O operations
- Comprehensive logging
- Unit and integration tests
""",
    },
    {
        "id": "template_microservices",
        "pattern_type": "template",
        "success_score": 0.8,
        "metadata": {
            "category": "microservices",
            "tech_stack": "FastAPI, Kubernetes, RabbitMQ",
            "complexity": "high",
        },
        "content": """# Microservices Architecture Template

## Services
1. **API Gateway**: Request routing and authentication
2. **User Service**: User management and authentication
3. **Product Service**: Product catalog
4. **Order Service**: Order processing
5. **Payment Service**: Payment processing
6. **Notification Service**: Email/SMS notifications

## Inter-Service Communication
- **Synchronous**: REST/gRPC
- **Asynchronous**: RabbitMQ/Kafka message queues

## Infrastructure
- **Orchestration**: Kubernetes
- **Service Mesh**: Istio
- **API Gateway**: Kong/Traefik
- **Service Discovery**: Kubernetes DNS
- **Config Management**: ConfigMaps/Secrets
- **Monitoring**: Prometheus + Grafana
- **Logging**: ELK Stack
- **Tracing**: Jaeger

## Patterns
- Circuit breaker for fault tolerance
- Saga pattern for distributed transactions
- Event sourcing for audit trails
- CQRS for read/write separation

## Best Practices
- Each service has its own database
- Containerization with Docker
- Declarative deployments with Helm
- Health checks and readiness probes
- Horizontal pod autoscaling
- Centralized logging and monitoring
""",
    },
    {
        "id": "template_mobile_backend",
        "pattern_type": "template",
        "success_score": 0.88,
        "metadata": {
            "category": "mobile_backend",
            "tech_stack": "FastAPI, PostgreSQL, Firebase",
            "complexity": "medium",
        },
        "content": """# Mobile App Backend Template

## Architecture
- **API**: FastAPI with REST and GraphQL support
- **Database**: PostgreSQL
- **File Storage**: S3-compatible storage
- **Push Notifications**: Firebase Cloud Messaging
- **Analytics**: Firebase Analytics
- **Crash Reporting**: Sentry

## Features
- User authentication (email, social login)
- Profile management
- File upload/download
- Push notifications
- In-app purchases (iOS/Android)
- Offline sync support
- Real-time chat (WebSocket)
- Location-based services

## API Design
- RESTful endpoints for CRUD operations
- GraphQL for complex queries
- WebSocket for real-time features
- Pagination for list endpoints
- Image optimization and CDN

## Mobile-Specific Considerations
- Token-based authentication with refresh tokens
- API versioning for app version compatibility
- Graceful degradation for older app versions
- Rate limiting per device
- Device management and tracking
- App version enforcement

## Best Practices
- Minimal payload sizes
- Efficient pagination
- Background job processing
- Comprehensive error codes
- API documentation for mobile team
- Load testing for high concurrency
""",
    },
]


async def seed_templates():
    """Seed initial templates into ChromaDB."""
    print("Initializing ChromaDB store...")
    store = ChromaDBStore(
        collection_name="agent_bus_patterns",
        persist_directory=settings.chroma_persist_directory,
        auto_embed=True,
    )

    print(f"Seeding {len(SEED_TEMPLATES)} templates...\n")
    
    for i, template in enumerate(SEED_TEMPLATES, 1):
        # Prepare metadata
        metadata = template.get("metadata", {})
        metadata.update({
            "pattern_type": template["pattern_type"],
            "success_score": str(template["success_score"]),
            "usage_count": "0",
            "is_seed": "true",
        })

        # Store template
        doc_id = template["id"]
        await store.upsert_document(doc_id, template["content"], metadata)
        
        print(f"[{i}/{len(SEED_TEMPLATES)}] Seeded template: {doc_id}")
        print(f"    Category: {metadata.get('category', 'N/A')}")
        print(f"    Success Score: {template['success_score']}")
        print()

    # Verify
    health = await store.health()
    print(f"✓ Seeding complete!")
    print(f"  Total patterns in store: {health.get('count', 0)}")
    print(f"  Backend: {health.get('backend')}")
    print(f"  Mode: {health.get('mode')}")


if __name__ == "__main__":
    asyncio.run(seed_templates())
