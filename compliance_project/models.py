"""Dataclasses describing the compliance domain model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

ISO_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


def utc_now() -> str:
    return datetime.utcnow().strftime(ISO_FORMAT)


@dataclass
class ComplianceBlock:
    block_id: str
    node_id: str
    block_type: Optional[str]
    content: str
    source: Optional[str] = None
    source_page: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    sequence: int = 0


@dataclass
class ComplianceNode:
    node_id: str
    title: str
    summary: Optional[str]
    category: Optional[str]
    tags: List[str] = field(default_factory=list)
    image: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    blocks: List[ComplianceBlock] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
