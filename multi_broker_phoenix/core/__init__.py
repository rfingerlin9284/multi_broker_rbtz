"""
Core system components for multi-broker autonomous trading.

This package contains:
- interfaces: Protocol definitions for broker connectors
- orchestrator: Multi-broker coordination and lifecycle management
- broker_supervisor: Per-broker circuit breaker and state machine
- gates: Auto-activation logic (connectivity, liquidity, OCO-readiness)
"""

__all__ = [
    "BrokerConnectorProtocol",
    "OCOUnsupportedError",
    "BrokerSupervisor",
    "BrokerGates",
    "Orchestrator",
]
