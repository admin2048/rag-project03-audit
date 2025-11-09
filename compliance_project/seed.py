"""Seed routines for bootstrapping the compliance database."""

from __future__ import annotations

import json
from typing import Sequence

from .models import ComplianceBlock, ComplianceNode, utc_now

SAMPLE_IMAGE = {
    "url": "https://example.com/images/esg-dashboard.png",
    "description": "ESG reporting dashboard mock-up",
}


def sample_nodes() -> Sequence[ComplianceNode]:
    now = utc_now()
    return [
        ComplianceNode(
            node_id="esg-policy-overview",
            title="ESG Policy Overview",
            summary="Highlights the organisation's environmental, social, and governance commitments.",
            category="policy",
            tags=["esg", "governance", "environment"],
            image=SAMPLE_IMAGE,
            metadata={"region": "global", "version": "1.0"},
            created_at=now,
            updated_at=now,
            blocks=[
                ComplianceBlock(
                    block_id="esg-policy-overview-intro",
                    node_id="esg-policy-overview",
                    block_type="text",
                    content="Our ESG policy guides sustainable decision-making across all departments.",
                    source="Corporate Sustainability Manual",
                    source_page=12,
                    metadata={"language": "en"},
                    sequence=0,
                ),
                ComplianceBlock(
                    block_id="esg-policy-overview-image",
                    node_id="esg-policy-overview",
                    block_type="image",
                    content=json.dumps(SAMPLE_IMAGE),
                    source=None,
                    source_page=None,
                    metadata={"alt": "Screenshot of ESG metrics"},
                    sequence=1,
                ),
            ],
        ),
        ComplianceNode(
            node_id="esg-risk-register",
            title="ESG Risk Register",
            summary="Monitors potential ESG risks with mitigation owners and due dates.",
            category="risk",
            tags=["risk", "esg", "mitigation"],
            image={},
            metadata={"department": "Risk Office"},
            created_at=now,
            updated_at=now,
            blocks=[
                ComplianceBlock(
                    block_id="esg-risk-register-table",
                    node_id="esg-risk-register",
                    block_type="table",
                    content=json.dumps(
                        {
                            "columns": ["Risk", "Owner", "Mitigation", "Due Date"],
                            "rows": [
                                ["Supply chain disruption", "Logistics Lead", "Diversify suppliers", "2024-06-01"],
                                ["Regulatory fines", "Compliance Officer", "Quarterly audits", "2024-03-15"],
                            ],
                        }
                    ),
                    metadata={"format": "json-table"},
                    sequence=0,
                )
            ],
        ),
    ]


def seed_if_empty(conn) -> None:
    """Populate the database with sample nodes if no user data exists."""

    node_count = conn.execute("SELECT COUNT(1) FROM compliance_nodes").fetchone()[0]
    if node_count:
        return

    for node in sample_nodes():
        conn.execute(
            """
            INSERT INTO compliance_nodes (
                node_id, title, summary, category, tags, image_meta, metadata, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                node.node_id,
                node.title,
                node.summary,
                node.category,
                json.dumps(node.tags),
                json.dumps(node.image),
                json.dumps(node.metadata),
                node.created_at,
                node.updated_at,
            ),
        )

        for block in node.blocks:
            conn.execute(
                """
                INSERT INTO compliance_blocks (
                    block_id, node_id, block_type, content, source, source_page, metadata, sequence
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    block.block_id,
                    block.node_id,
                    block.block_type,
                    block.content,
                    block.source,
                    block.source_page,
                    json.dumps(block.metadata),
                    block.sequence,
                ),
            )

    conn.commit()
