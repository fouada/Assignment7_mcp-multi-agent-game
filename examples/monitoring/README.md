# Production Monitoring Setup

This directory contains production-grade monitoring configuration for the MCP Game League system.

## Overview

The monitoring stack provides three pillars of observability:
1. **Metrics** (Prometheus) - Performance and health metrics
2. **Tracing** (Jaeger/OpenTelemetry) - Distributed request tracing
3. **Dashboards** (Grafana) - Visualization and alerting

## Quick Start

### 1. Start Monitoring Stack

Use Docker Compose to start Prometheus, Grafana, and Jaeger:

```bash
cd examples/monitoring
docker compose up -d
```

### 2. Access Dashboards

- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Jaeger UI**: http://localhost:16686

### 3. Import Grafana Dashboard

1. Open Grafana at http://localhost:3000
2. Go to Dashboards → Import
3. Upload `grafana_dashboard.json`
4. Select Prometheus datasource
5. Click Import

## Metrics Reference

### Game Metrics

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `game_requests_total` | Counter | Total game requests | `type`, `server_type`, `status` |
| `game_request_duration_seconds` | Histogram | Request duration | `type`, `server_type` |
| `active_games` | Gauge | Currently active games | - |
| `games_total` | Counter | Total games completed | - |
| `game_rounds_total` | Counter | Total rounds played | - |

### Strategy Metrics

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `strategy_decisions_total` | Counter | Total strategy decisions | - |
| `strategy_decision_duration_seconds` | Histogram | Decision time | - |

### System Metrics

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `event_bus_events_total` | Counter | Total events emitted | - |
| `plugin_load_errors_total` | Counter | Plugin load failures | - |
| `plugins_loaded` | Gauge | Loaded plugins | - |
| `middleware_errors_total` | Counter | Middleware errors | - |
| `middleware_duration_seconds` | Histogram | Middleware execution time | - |

### Server Info

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `server_info` | Gauge | Server metadata | `server_type`, `server_name`, `league_id` |

## Dashboard Panels

### 1. Request Rate (req/s)
Real-time request rate per message type and server type.

**Query**:
```promql
rate(game_requests_total[1m])
```

### 2. Request Duration (p50, p90, p99)
Request latency percentiles for SLA monitoring.

**Queries**:
```promql
histogram_quantile(0.50, rate(game_request_duration_seconds_bucket[5m]))
histogram_quantile(0.90, rate(game_request_duration_seconds_bucket[5m]))
histogram_quantile(0.99, rate(game_request_duration_seconds_bucket[5m]))
```

### 3. Error Rate (%)
Percentage of failed requests with alert threshold.

**Query**:
```promql
rate(game_requests_total{status="error"}[5m]) / rate(game_requests_total[5m]) * 100
```

**Alert**: Fires when error rate > 5%

### 4. Active Games
Current number of in-progress games.

**Query**:
```promql
active_games
```

### 5. Strategy Decision Duration
Time taken for AI strategy decisions (p95).

**Query**:
```promql
histogram_quantile(0.95, rate(strategy_decision_duration_seconds_bucket[5m]))
```

### 6. Event Bus Activity
Events emitted per second.

**Query**:
```promql
rate(event_bus_events_total[1m])
```

### 7-8. Plugin Metrics
Loaded plugins and error counts.

**Queries**:
```promql
plugins_loaded
plugin_load_errors_total
```

### 9-10. Middleware Metrics
Middleware errors and execution time.

**Queries**:
```promql
rate(middleware_errors_total[5m])
histogram_quantile(0.90, rate(middleware_duration_seconds_bucket[5m]))
```

### 11-12. Traffic Distribution
Pie charts showing request distribution by type and server.

**Queries**:
```promql
sum by (type) (game_requests_total)
sum by (server_type) (game_requests_total)
```

## Docker Compose Configuration

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana_dashboard.json:/etc/grafana/provisioning/dashboards/mcp_game.json
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false

  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"  # Jaeger UI
      - "14268:14268"  # Jaeger collector
      - "4318:4318"    # OTLP HTTP receiver
    environment:
      - COLLECTOR_OTLP_ENABLED=true

volumes:
  prometheus_data:
  grafana_data:
```

Create `prometheus.yml`:

```yaml
global:
  scrape_interval: 5s
  evaluation_interval: 5s

scrape_configs:
  - job_name: 'mcp_game_league_manager'
    static_configs:
      - targets: ['host.docker.internal:8000']
        labels:
          service: 'league_manager'

  - job_name: 'mcp_game_referees'
    static_configs:
      - targets: ['host.docker.internal:8001', 'host.docker.internal:8002']
        labels:
          service: 'referee'

  - job_name: 'mcp_game_players'
    static_configs:
      - targets: ['host.docker.internal:8101', 'host.docker.internal:8102']
        labels:
          service: 'player'
```

## Health Checks

The system provides Kubernetes-compatible health check endpoints:

### Liveness Probe
**Endpoint**: `/tools/call` with `tool_name=get_health_live`

Checks if the process is alive. Use for Kubernetes liveness probes.

**Response**:
```json
{
  "success": true,
  "status": "healthy",
  "message": "Process is alive",
  "details": {
    "uptime_seconds": 3600.5,
    "pid": 12345
  }
}
```

**Kubernetes Config**:
```yaml
livenessProbe:
  httpGet:
    path: /tools/call?tool_name=get_health_live
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 30
```

### Readiness Probe
**Endpoint**: `/tools/call` with `tool_name=get_health_ready`

Checks if the service can accept requests. Use for Kubernetes readiness probes.

**Response**:
```json
{
  "success": true,
  "status": "healthy",
  "message": "Service is ready",
  "details": {
    "initialization_complete": true,
    "dependencies_available": true
  }
}
```

**Kubernetes Config**:
```yaml
readinessProbe:
  httpGet:
    path: /tools/call?tool_name=get_health_ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
```

### Full Health Report
**Endpoint**: `/tools/call` with `tool_name=get_health`

Comprehensive health report with all checks.

**Response**:
```json
{
  "success": true,
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00.123Z",
  "checks": {
    "liveness": {
      "status": "healthy",
      "message": "Process is alive",
      "details": {"uptime_seconds": 3600.5, "pid": 12345}
    },
    "readiness": {
      "status": "healthy",
      "message": "Service is ready",
      "details": {"initialization_complete": true}
    },
    "resources": {
      "status": "healthy",
      "message": "Resources within limits",
      "details": {
        "cpu_percent": 45.2,
        "memory_percent": 60.1,
        "disk_percent": 30.5
      }
    }
  }
}
```

## Distributed Tracing

### Viewing Traces in Jaeger

1. Open Jaeger UI at http://localhost:16686
2. Select service: `mcp_game_league_manager`, `mcp_game_referee`, or `mcp_game_player`
3. Click "Find Traces"

### Trace Context Propagation

Traces automatically propagate across service calls using W3C Trace Context:

```
Client Request → League Manager → Referee → Player
    |                |              |         |
    └─ trace_id ─────┴──────────────┴─────────┘
```

Each span includes:
- **Span Name**: Operation name (e.g., "protocol.game_started")
- **Attributes**: Message type, sender, server type
- **Events**: Key milestones (handler called, middleware completed)
- **Duration**: Execution time

### Example Trace

```
trace_id: 4bf92f3577b34da6a3ce929d0e0e4736
├─ protocol.game_started (league_manager) - 45ms
│  ├─ middleware.before (tracing) - 0.1ms
│  ├─ middleware.before (logging) - 0.2ms
│  ├─ middleware.before (auth) - 1.5ms
│  ├─ handler.call - 40ms
│  └─ middleware.after (all) - 3.2ms
└─ http.send_protocol_message (referee) - 120ms
   └─ protocol.game_invitation (referee) - 115ms
```

## Alerting

### Recommended Alerts

**High Error Rate**:
```yaml
- alert: HighErrorRate
  expr: rate(game_requests_total{status="error"}[5m]) / rate(game_requests_total[5m]) > 0.05
  for: 2m
  annotations:
    summary: "High error rate detected"
    description: "Error rate is {{ $value | humanizePercentage }}"
```

**Slow Requests**:
```yaml
- alert: SlowRequests
  expr: histogram_quantile(0.95, rate(game_request_duration_seconds_bucket[5m])) > 1.0
  for: 5m
  annotations:
    summary: "Requests are slow"
    description: "P95 latency is {{ $value }}s"
```

**Plugin Load Failures**:
```yaml
- alert: PluginLoadFailures
  expr: increase(plugin_load_errors_total[5m]) > 0
  annotations:
    summary: "Plugin failed to load"
    description: "{{ $value }} plugin load errors in last 5m"
```

**Middleware Errors**:
```yaml
- alert: MiddlewareErrors
  expr: rate(middleware_errors_total[5m]) > 1
  for: 5m
  annotations:
    summary: "High middleware error rate"
    description: "{{ $value }} middleware errors/sec"
```

## Performance Tuning

### Metrics Collection Overhead

- **Baseline**: ~0.1ms per request
- **With all metrics**: ~0.5ms per request
- **Impact**: <1% of total request time

### Sampling Strategies

**Low Traffic (<100 req/s)**:
- Tracing: 100% sampling
- Metrics: All requests

**Medium Traffic (100-1000 req/s)**:
- Tracing: 10% sampling (default)
- Metrics: All requests

**High Traffic (>1000 req/s)**:
- Tracing: 1-5% sampling
- Metrics: All requests (lightweight)
- Consider metric aggregation

### Configuration

Update `config/observability/observability_config.json`:

```json
{
  "metrics": {
    "enabled": true
  },
  "tracing": {
    "enabled": true,
    "sample_rate": 0.1
  },
  "health_checks": {
    "enabled": true,
    "cache_ttl_seconds": 5
  }
}
```

## Troubleshooting

### Metrics Not Appearing

1. **Check endpoint**: `curl http://localhost:8000/tools/call?tool_name=get_metrics`
2. **Verify Prometheus scraping**: Check Prometheus targets at http://localhost:9090/targets
3. **Check logs**: Look for "Observability initialized" in server logs

### Traces Not Appearing

1. **Check Jaeger receiver**: Ensure port 4318 is accessible
2. **Verify sampling**: Increase `sample_rate` to 1.0 for testing
3. **Check trace ID**: Look for `trace_id` in log messages

### Health Checks Failing

1. **Check resource limits**: Verify CPU/memory/disk thresholds
2. **Check dependencies**: Ensure all services are reachable
3. **Review logs**: Look for health check errors

## Best Practices

### 1. Use Labels Wisely
```python
# Good - specific, low cardinality
metrics.increment("game_requests_total", labels={"type": "game_started", "server_type": "referee"})

# Bad - high cardinality (unbounded values)
metrics.increment("game_requests_total", labels={"player_id": "P12345"})
```

### 2. Sample High-Volume Traces
```python
# Production sampling
tracing.initialize(sample_rate=0.1)  # 10%

# Development/debugging
tracing.initialize(sample_rate=1.0)  # 100%
```

### 3. Cache Health Checks
```python
# Use caching to reduce load
report = await health.get_health()  # Uses 5s cache

# Force fresh check
health._last_check_time = None
report = await health.get_health()
```

### 4. Monitor Monitor
- Set up alerts for Prometheus/Grafana/Jaeger downtime
- Monitor metric cardinality
- Track storage usage

## Further Reading

- [Prometheus Best Practices](https://prometheus.io/docs/practices/)
- [OpenTelemetry Specification](https://opentelemetry.io/docs/specs/otel/)
- [Grafana Dashboard Design](https://grafana.com/docs/grafana/latest/dashboards/)
- [SRE Workbook - Monitoring](https://sre.google/workbook/monitoring/)
