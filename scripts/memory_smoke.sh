#!/usr/bin/env bash
set -euo pipefail

API_URL="${API_URL:-http://localhost:8000}"

echo "Checking memory health..."
curl -sS "${API_URL}/api/memory/health"
echo

echo "Upserting sample memory..."
curl -sS -X POST "${API_URL}/api/memory/upsert" \
  -H "Content-Type: application/json" \
  -d '{
    "doc_id": "smoke_prd_1",
    "text": "Sample PRD: analytics dashboard with alerts and KPI drilldowns.",
    "metadata": {"pattern_type":"prd","stage":"smoke"}
  }'
echo

echo "Querying memory..."
curl -sS -X POST "${API_URL}/api/memory/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "analytics dashboard alerts",
    "top_k": 3,
    "pattern_type": "prd"
  }'
echo
