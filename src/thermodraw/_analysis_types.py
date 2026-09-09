"""Serialized analysis contracts. Dictionary keys are additive within 1.x."""
from typing import Any, Dict, List, Optional, TypedDict


class _UpdateFields(TypedDict):
    entity: str
    id: str
    field: str
    value: float
    unit: str


class PhysicsUpdate(_UpdateFields, total=False):
    index: int


class PhysicsReport(TypedDict):
    status: str
    input_hash: str
    components: List[Dict[str, Any]]
    volumes: List[Dict[str, Any]]
    updates: List[PhysicsUpdate]
    coverage: Dict[str, Any]


class _AssessmentFields(TypedDict):
    status: str
    issues: List[Dict[str, Any]]
    systems: List[Dict[str, Any]]
    result: Optional[PhysicsReport]
    applied: Optional[Dict[str, Any]]
    changes: List[Dict[str, Any]]
    comparisons: List[Dict[str, Any]]


class AssessmentReport(_AssessmentFields, total=False):
    input_hash: str
    scenario_hash: str
    effective_inputs: Dict[str, Any]


ValidAssessmentReport = AssessmentReport
