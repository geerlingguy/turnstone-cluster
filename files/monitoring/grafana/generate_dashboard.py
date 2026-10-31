#!/usr/bin/env python3
"""Generates turnstone-cluster.json, the provisioned Grafana dashboard.

Usage: python3 files/monitoring/grafana/generate_dashboard.py \
           files/monitoring/grafana/turnstone-cluster.json
"""
import json, sys
DS = {"type": "prometheus", "uid": "prometheus"}
pid = [0]
def nid():
    pid[0] += 1; return pid[0]

def target(expr, legend="", ref="A", instant=False):
    t = {"datasource": DS, "expr": expr, "legendFormat": legend, "refId": ref}
    if instant: t["instant"] = True; t["range"] = False
    return t

def stat(title, exprs, unit, x, y, w=3, h=4, decimals=0, thresholds=None, max_=None, no_value=None):
    steps = thresholds or [{"color": "green", "value": None}]
    p = {"id": nid(), "type": "stat", "title": title, "datasource": DS,
         "gridPos": {"x": x, "y": y, "w": w, "h": h},
         "targets": [target(e, l, chr(65 + i)) for i, (e, l) in enumerate(exprs)],
         "fieldConfig": {"defaults": {"unit": unit, "decimals": decimals, "min": 0,
                                       "color": {"mode": "thresholds"},
                                       "thresholds": {"mode": "absolute", "steps": steps}},
                         "overrides": []},
         "options": {"reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
                     "colorMode": "value", "graphMode": "area", "textMode": "auto",
                     "justifyMode": "auto", "orientation": "auto"}}
    if max_ is not None: p["fieldConfig"]["defaults"]["max"] = max_
    if no_value is not None: p["fieldConfig"]["defaults"]["noValue"] = no_value
    return p

def ts(title, exprs, unit, x, y, w=12, h=7, max_=None):
    p = {"id": nid(), "type": "timeseries", "title": title, "datasource": DS,
         "gridPos": {"x": x, "y": y, "w": w, "h": h},
         "targets": [target(e, l, chr(65 + i)) for i, (e, l) in enumerate(exprs)],
         "fieldConfig": {"defaults": {"unit": unit, "min": 0,
                                       "custom": {"lineWidth": 2, "fillOpacity": 10, "showPoints": "never",
                                                  "spanNulls": True}},
                         "overrides": []},
         "options": {"legend": {"displayMode": "list", "placement": "bottom", "showLegend": True},
                     "tooltip": {"mode": "multi", "sort": "desc"}}}
    if max_ is not None: p["fieldConfig"]["defaults"]["max"] = max_
    return p

PCT = [{"color": "green", "value": None}, {"color": "yellow", "value": 70}, {"color": "red", "value": 90}]
N = '{node="$node"}'
panels = []

# Cluster overview.
panels.append({"id": nid(), "type": "row", "title": "Cluster", "collapsed": False,
               "gridPos": {"x": 0, "y": 0, "w": 24, "h": 1}, "panels": []})
panels += [
    stat("Decode tokens/s", [("sum(llm:decode:tokens_per_second)", "")], "none", 0, 1, 6),
    stat("Prefill tokens/s", [("sum(llm:prefill:tokens_per_second)", "")], "none", 6, 1, 6),
    stat("Requests", [("sum(llm:requests_running)", "running"), ("sum(llm:requests_waiting)", "waiting")],
         "none", 12, 1, 6),
    stat("GPU power", [("sum(gpu:power:watts)", "")], "watt", 18, 1, 6),
    ts("Decode tokens/s by node", [("llm:decode:tokens_per_second", "{{node}}")], "none", 0, 5, 24, 7),
]

# Turnstone itself (scraped from each Turnstone node's and the console's
# /metrics). Includes cloud models like Claude, which have no server to scrape.
# Bucket series are renamed to *_bucket at scrape time (see prometheus.yml.j2).
JUDGE_BUCKETS = "turnstone_judge_llm_latency_seconds_bucket"
y = 12
panels.append({"id": nid(), "type": "row", "title": "Turnstone", "collapsed": False,
               "gridPos": {"x": 0, "y": y, "w": 24, "h": 1}, "panels": []})
y += 1
panels += [
    stat("Workstreams", [("sum by (state) (turnstone_workstreams_by_state)", "{{state}}")],
         "none", 0, y, w=6),
    stat("Tool calls/min", [("sum(rate(turnstone_tool_calls_total[5m])) * 60", "")], "none", 6, y, decimals=1),
    stat("Judge calls/min", [('sum(rate(turnstone_judge_verdicts_total{tier="llm"}[5m])) * 60', "")],
         "none", 9, y, decimals=1),
    stat("Judge latency (mean)",
         # "> 0" drops the NaN from 0/0 when there were no judge calls.
         [("(sum(rate(turnstone_judge_llm_latency_seconds_sum[15m]))"
           " / sum(rate(turnstone_judge_llm_latency_seconds_count[15m]))) > 0", "")], "s", 12, y, decimals=1,
         no_value="no calls"),
    # Turnstone's buckets stop at 10s, so quantiles can't go above 10s. Show
    # the share of judge calls slower than that instead.
    stat("Judge calls > 10s",
         [(f'(1 - sum(rate({JUDGE_BUCKETS}{{le=~"10|10.0"}}[15m]))'
           " / sum(rate(turnstone_judge_llm_latency_seconds_count[15m]))) * 100"
           " and sum(rate(turnstone_judge_llm_latency_seconds_count[15m])) > 0", "")], "percent", 15, y,
         thresholds=[{"color": "green", "value": None}, {"color": "yellow", "value": 10},
                     {"color": "red", "value": 50}], max_=100, no_value="no calls"),
    stat("Tokens/min", [('sum(rate(turnstone_tokens_total{type=~"prompt|completion"}[5m])) * 60', "")],
         "short", 18, y),
    stat("Cache read tokens/min", [('sum(rate(turnstone_tokens_total{type="cache_read"}[5m])) * 60', "")],
         "short", 21, y),
]
y += 4
top = {"id": nid(), "type": "bargauge", "title": "Top workstreams by tokens (1h)", "datasource": DS,
       "gridPos": {"x": 16, "y": y, "w": 8, "h": 7},
       "targets": [dict(target(
           "topk(8, sum by (name) (increase(turnstone_workstream_prompt_tokens_total[1h])"
           " + increase(turnstone_workstream_completion_tokens_total[1h])))", "{{name}}"),
           instant=True, range=False)],
       "fieldConfig": {"defaults": {"unit": "short", "min": 0, "color": {"mode": "continuous-BlYlRd"}},
                       "overrides": []},
       "options": {"orientation": "horizontal", "displayMode": "gradient", "showUnfilled": True,
                   "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False}}}
panels += [
    ts("Tokens/min by type", [("sum by (type) (rate(turnstone_tokens_total[5m])) * 60", "{{type}}")],
       "short", 0, y, w=8),
    ts("Judge latency (mean)", [
        ("sum(rate(turnstone_judge_llm_latency_seconds_sum[5m]))"
         " / sum(rate(turnstone_judge_llm_latency_seconds_count[5m]))", "mean")], "s", 8, y, w=8),
    top,
]
y += 7

# One row per node.
panels.append({"id": nid(), "type": "row", "title": "$node", "repeat": "node", "collapsed": False,
               "gridPos": {"x": 0, "y": y, "w": 24, "h": 1}, "panels": []})
y += 1
panels += [
    stat("CPU", [(f"node:cpu_used:percent{N}", "")], "percent", 0, y, thresholds=PCT, max_=100),
    stat("RAM", [(f"node:memory_used:percent{N}", "")], "percent", 3, y, thresholds=PCT, max_=100),
    stat("GPU busy", [(f"gpu:busy:max_percent{N}", "")], "percent", 6, y, thresholds=PCT, max_=100),
    stat("GPU power", [(f"gpu:power:watts{N}", "")], "watt", 9, y),
    stat("Decode", [(f"llm:decode:tokens_per_second{N}", "")], "none", 12, y, decimals=1),
    stat("Prefill", [(f"llm:prefill:tokens_per_second{N}", "")], "none", 15, y),
    stat("Requests", [(f"llm:requests_running{N}", "running"), (f"llm:requests_waiting{N}", "waiting")],
         "none", 18, y),
    stat("KV cache", [(f"llm:kv_cache_used:percent{N}", "")], "percent", 21, y, decimals=1,
         thresholds=PCT, max_=100),
]
y += 4
panels += [
    ts("Tokens/s", [(f"llm:decode:tokens_per_second{N}", "decode"),
                    (f"llm:prefill:tokens_per_second{N}", "prefill")], "none", 0, y),
    ts("Utilization", [(f"node:cpu_used:percent{N}", "CPU"), (f"node:memory_used:percent{N}", "RAM"),
                       (f"gpu:busy:max_percent{N}", "GPU")], "percent", 12, y, max_=100),
]

dash = {
    "uid": "turnstone-cluster", "title": "Turnstone Cluster", "tags": ["turnstone"],
    "timezone": "browser", "editable": False, "graphTooltip": 1, "refresh": "10s",
    "schemaVersion": 39, "version": 1,
    "time": {"from": "now-1h", "to": "now"},
    "timepicker": {"refresh_intervals": ["5s", "10s", "30s", "1m", "5m"]},
    "templating": {"list": [{
        "name": "node", "label": "Node", "type": "query", "datasource": DS,
        "definition": "label_values(node:cpu_used:percent, node)",
        "query": {"query": "label_values(node:cpu_used:percent, node)", "refId": "nodes"},
        "refresh": 2, "multi": True, "includeAll": True, "sort": 1,
        "current": {"selected": True, "text": ["All"], "value": ["$__all"]}, "options": []}]},
    "annotations": {"list": []},
    "panels": panels,
}
json.dump(dash, open(sys.argv[1], "w"), indent=2)
print(f"{len(panels)} panels")
