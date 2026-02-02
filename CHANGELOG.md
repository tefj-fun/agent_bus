# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Release automation workflow with Docker image publishing
- Release script for simplified version bumping
- Staging environment Helm values configuration
- Comprehensive release process documentation

## [0.1.0] - 2026-02-01

### Added
- Initial release of agent_bus multi-agent SWE system
- 12 specialized AI agents (PRD, Architect, UI/UX, Developer, QA, Security, Tech Writer, Support, PM, Memory)
- FastAPI-based orchestration system with async job processing
- Redis task queue and PostgreSQL state persistence
- ChromaDB-based memory system with pattern recognition
- Complete Kubernetes deployment manifests and Helm charts
- GPU worker support for ML/CV workloads
- Claude Skills integration system with allowlist management
- Comprehensive observability (Prometheus metrics, structured logging)
- Docker Compose for local development
- CI/CD pipeline with automated testing
- Human-in-the-loop approval gates
- Web UI for requirements submission and project monitoring

### Infrastructure
- Multi-stage Docker builds with optimization
- Kubernetes manifests for production deployment
- Helm charts with dev/staging/prod configurations
- GPU job templates with NVIDIA device plugin support
- Horizontal Pod Autoscaling (HPA) configuration
- Prometheus metrics and Grafana dashboards
- External secrets support (AWS/GCP/Azure)

### Documentation
- Complete deployment guides (Docker, K8s, Helm)
- Skills system documentation
- Memory system architecture
- GPU workers setup guide
- Observability and monitoring guide
- Release process documentation

[Unreleased]: https://github.com/tefj-fun/agent_bus/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/tefj-fun/agent_bus/releases/tag/v0.1.0
