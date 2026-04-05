"""
Chaos Engineering endpoints for RCA demo.
These simulate real production issues that show up on dashboards.
"""
import os
import time
import random
import threading
import json
from flask import Blueprint, jsonify, request
from app.logging_config import get_logger

chaos_bp = Blueprint("chaos", __name__, url_prefix="/chaos")
logger = get_logger("chaos")

# File-based chaos state so all workers and containers can read it
# Uses shared volume mounted at /tmp/chaos
CHAOS_FILE = "/tmp/chaos/state.json"

def _read_chaos_state():
    """Read chaos state from file."""
    try:
        with open(CHAOS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "slow_responses": False,
            "slow_response_delay": 0,
            "error_rate": 0,
            "memory_leak": False,
            "db_slow": False,
            "db_slow_delay": 0,
        }

def _write_chaos_state(state):
    """Write chaos state to file."""
    with open(CHAOS_FILE, "w") as f:
        json.dump(state, f)

# Legacy in-memory state for memory leak only (can't persist that)
_chaos_state = {
    "memory_leak_data": [],
}


def get_chaos_state():
    """Get current chaos state (for use by other modules)."""
    return _read_chaos_state()


@chaos_bp.route("/status", methods=["GET"])
def chaos_status():
    """Get current chaos injection status."""
    state = _read_chaos_state()
    return jsonify({
        "chaos_enabled": any([
            state["slow_responses"],
            state["error_rate"] > 0,
            state["db_slow"],
        ]),
        "slow_responses": {
            "enabled": state["slow_responses"],
            "delay_ms": state["slow_response_delay"],
        },
        "error_injection": {
            "enabled": state["error_rate"] > 0,
            "rate_percent": state["error_rate"],
        },
        "memory_leak": {
            "enabled": False,
            "allocated_mb": len(_chaos_state["memory_leak_data"]) * 10 / 1024,
        },
        "db_slowdown": {
            "enabled": state["db_slow"],
            "delay_ms": state["db_slow_delay"],
        },
    })


@chaos_bp.route("/reset", methods=["POST"])
def chaos_reset():
    """Reset all chaos injection - return to normal."""
    _write_chaos_state({
        "slow_responses": False,
        "slow_response_delay": 0,
        "error_rate": 0,
        "memory_leak": False,
        "db_slow": False,
        "db_slow_delay": 0,
    })
    _chaos_state["memory_leak_data"].clear()

    logger.info("Chaos reset - all systems normal", extra={
        "component": "chaos",
        "action": "reset",
    })

    return jsonify({"status": "ok", "message": "All chaos injection disabled"})


@chaos_bp.route("/slow", methods=["POST"])
def inject_slow_responses():
    """
    Inject slow response times.

    Dashboard symptom: LATENCY p95 goes RED, latency graphs spike
    RCA path: Dashboard shows latency spike -> Logs show slow responses -> Find this chaos injection

    POST /chaos/slow {"delay_ms": 3000}
    """
    data = request.get_json(silent=True) or {}
    delay_ms = data.get("delay_ms", 2000)

    state = _read_chaos_state()
    state["slow_responses"] = True
    state["slow_response_delay"] = delay_ms
    _write_chaos_state(state)

    logger.warning("CHAOS: Slow response injection enabled", extra={
        "component": "chaos",
        "action": "slow_responses",
        "delay_ms": delay_ms,
    })

    return jsonify({
        "status": "chaos_enabled",
        "type": "slow_responses",
        "delay_ms": delay_ms,
        "message": f"All responses will be delayed by {delay_ms}ms"
    })


@chaos_bp.route("/errors", methods=["POST"])
def inject_errors():
    """
    Inject random 500 errors at a specified rate.

    Dashboard symptom: ERROR % goes YELLOW/RED, error rate graph spikes
    RCA path: Dashboard shows error spike -> Logs show 500s with "CHAOS" -> Find this injection

    POST /chaos/errors {"rate": 30}  # 30% of requests will fail
    """
    data = request.get_json(silent=True) or {}
    rate = min(100, max(0, data.get("rate", 20)))

    _chaos_state["error_rate"] = rate

    logger.warning("CHAOS: Error injection enabled", extra={
        "component": "chaos",
        "action": "error_injection",
        "rate_percent": rate,
    })

    return jsonify({
        "status": "chaos_enabled",
        "type": "error_injection",
        "rate_percent": rate,
        "message": f"{rate}% of requests will return 500 errors"
    })


@chaos_bp.route("/memory-leak", methods=["POST"])
def inject_memory_leak():
    """
    Simulate a memory leak by allocating memory that's never freed.

    Dashboard symptom: MEM % creeps up over time, eventually goes RED
    RCA path: Dashboard shows memory climbing -> Logs show memory warnings -> Find the leak

    POST /chaos/memory-leak {"mb_per_second": 5}
    """
    data = request.get_json(silent=True) or {}
    mb_per_second = data.get("mb_per_second", 2)

    _chaos_state["memory_leak"] = True

    def leak_memory():
        while _chaos_state["memory_leak"]:
            # Allocate 10KB chunks
            _chaos_state["memory_leak_data"].append("X" * 10240)
            allocated_mb = len(_chaos_state["memory_leak_data"]) * 10 / 1024

            if len(_chaos_state["memory_leak_data"]) % 100 == 0:
                logger.warning("Memory pressure increasing", extra={
                    "component": "memory",
                    "allocated_mb": round(allocated_mb, 2),
                    "warning": "potential_memory_leak",
                })

            time.sleep(0.01 / mb_per_second)  # Control leak rate

            # Safety cap at 500MB
            if allocated_mb > 500:
                logger.error("Memory leak safety cap reached", extra={
                    "component": "memory",
                    "allocated_mb": allocated_mb,
                })
                break

    thread = threading.Thread(target=leak_memory, daemon=True)
    thread.start()

    logger.warning("CHAOS: Memory leak injection started", extra={
        "component": "chaos",
        "action": "memory_leak",
        "mb_per_second": mb_per_second,
    })

    return jsonify({
        "status": "chaos_enabled",
        "type": "memory_leak",
        "mb_per_second": mb_per_second,
        "message": f"Memory leak started at ~{mb_per_second}MB/second"
    })


@chaos_bp.route("/db-slow", methods=["POST"])
def inject_db_slowdown():
    """
    Simulate slow database queries.

    Dashboard symptom: LATENCY spikes but only on DB-heavy endpoints
    RCA path: Dashboard shows latency -> Logs show slow DB queries -> Find db_slow chaos

    POST /chaos/db-slow {"delay_ms": 1000}
    """
    data = request.get_json(silent=True) or {}
    delay_ms = data.get("delay_ms", 1000)

    _chaos_state["db_slow"] = True
    _chaos_state["db_slow_delay"] = delay_ms

    logger.warning("CHAOS: Database slowdown injection enabled", extra={
        "component": "chaos",
        "action": "db_slow",
        "delay_ms": delay_ms,
    })

    return jsonify({
        "status": "chaos_enabled",
        "type": "db_slowdown",
        "delay_ms": delay_ms,
        "message": f"Database queries will be delayed by {delay_ms}ms"
    })


@chaos_bp.route("/cascade", methods=["POST"])
def inject_cascade_failure():
    """
    Simulate a cascade failure: slow DB -> timeout -> errors -> more load on remaining capacity.

    Dashboard symptom: Multiple signals degrade together
    RCA path: Complex - need to trace through latency -> errors -> find root cause

    POST /chaos/cascade
    """
    _chaos_state["db_slow"] = True
    _chaos_state["db_slow_delay"] = 2000
    _chaos_state["error_rate"] = 15
    _chaos_state["slow_responses"] = True
    _chaos_state["slow_response_delay"] = 500

    logger.error("CHAOS: Cascade failure injection - CRITICAL", extra={
        "component": "chaos",
        "action": "cascade_failure",
        "db_delay_ms": 2000,
        "error_rate": 15,
        "response_delay_ms": 500,
    })

    return jsonify({
        "status": "chaos_enabled",
        "type": "cascade_failure",
        "message": "Cascade failure simulation started: slow DB + errors + latency"
    })
