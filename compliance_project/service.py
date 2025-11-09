"""High level service utilities for interacting with compliance data."""

from __future__ import annotations

import json
import logging
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional, Sequence

from . import db
from .models import ComplianceBlock, ComplianceNode
from .seed import seed_if_empty

logger = logging.getLogger(__name__)


class ComplianceDataStore:
    """A standalone service that manages compliance nodes and content blocks."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = Path(db_path) if db_path else db.DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            db.ensure_schema(conn)
            seed_if_empty(conn)

    @contextmanager
    def _connect(self) -> Iterator[Any]:
        with db.connect(self.db_path) as conn:
            yield conn

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def load_nodes(self) -> List[Dict[str, Any]]:
        """Return all compliance nodes in a standardised dictionary format."""

        with self._connect() as conn:
            nodes = conn.execute(
                "SELECT * FROM compliance_nodes ORDER BY created_at ASC"
            ).fetchall()

            formatted: List[Dict[str, Any]] = []
            for node in nodes:
                blocks = conn.execute(
                    "SELECT * FROM compliance_blocks WHERE node_id = ?",
                    (node["node_id"],),
                ).fetchall()
                formatted.append(_format_record(node, blocks))

        return formatted

    def save_blocks(self, records: Sequence[Mapping[str, Any]]) -> None:
        """Persist compliance nodes and blocks from serialisable mappings."""

        if not records:
            return

        with self._connect() as conn:
            for record in records:
                node = _coerce_node(record)
                conn.execute(
                    """
                    INSERT INTO compliance_nodes (
                        node_id, title, summary, category, tags, image_meta, metadata, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(node_id) DO UPDATE SET
                        title=excluded.title,
                        summary=excluded.summary,
                        category=excluded.category,
                        tags=excluded.tags,
                        image_meta=excluded.image_meta,
                        metadata=excluded.metadata,
                        updated_at=excluded.updated_at
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

                conn.execute(
                    "DELETE FROM compliance_blocks WHERE node_id = ?",
                    (node.node_id,),
                )

                for block in node.blocks:
                    conn.execute(
                        """
                        INSERT INTO compliance_blocks (
                            block_id, node_id, block_type, content, source, source_page, metadata, sequence
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(block_id) DO UPDATE SET
                            node_id=excluded.node_id,
                            block_type=excluded.block_type,
                            content=excluded.content,
                            source=excluded.source,
                            source_page=excluded.source_page,
                            metadata=excluded.metadata,
                            sequence=excluded.sequence
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


# ----------------------------------------------------------------------
# Module level convenience wrappers
# ----------------------------------------------------------------------

def load_compliance_nodes(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Load all compliance nodes from the configured SQLite database."""

    return ComplianceDataStore(db_path=db_path).load_nodes()


def save_compliance_blocks(
    records: Sequence[Mapping[str, Any]], db_path: Optional[Path] = None
) -> None:
    """Save compliance data back to SQLite via the standalone project."""

    ComplianceDataStore(db_path=db_path).save_blocks(records)


# ----------------------------------------------------------------------
# Internal helpers
# ----------------------------------------------------------------------

def _format_record(node_row, block_rows) -> Dict[str, Any]:
    """Convert SQLite rows into serialisable dictionaries."""

    tags: List[str]
    tags_raw = node_row["tags"]
    if tags_raw in (None, ""):
        tags = []
    else:
        try:
            parsed = json.loads(tags_raw)
            tags = parsed if isinstance(parsed, list) else [str(parsed)]
        except json.JSONDecodeError:
            logger.warning("Could not decode tags for node %s", node_row["node_id"])
            tags = [tags_raw]

    image: Dict[str, Any]
    image_raw = node_row["image_meta"]
    if image_raw in (None, ""):
        image = {}
    else:
        try:
            image = json.loads(image_raw)
        except json.JSONDecodeError:
            image = {"url": image_raw}

    metadata_raw = node_row["metadata"]
    if metadata_raw in (None, ""):
        metadata = {}
    else:
        try:
            metadata = json.loads(metadata_raw)
        except json.JSONDecodeError:
            metadata = {"raw": metadata_raw}

    blocks: List[Dict[str, Any]] = []
    for row in block_rows:
        block_meta_raw = row["metadata"]
        if block_meta_raw in (None, ""):
            block_meta = {}
        else:
            try:
                block_meta = json.loads(block_meta_raw)
            except json.JSONDecodeError:
                block_meta = {"raw": block_meta_raw}

        blocks.append(
            {
                "block_id": row["block_id"],
                "node_id": row["node_id"],
                "block_type": row["block_type"],
                "content": row["content"],
                "source": row["source"],
                "source_page": row["source_page"],
                "metadata": block_meta,
                "sequence": row["sequence"],
            }
        )

    blocks.sort(key=lambda item: (item.get("sequence") or 0, item["block_id"]))

    return {
        "node_id": node_row["node_id"],
        "title": node_row["title"],
        "summary": node_row["summary"],
        "category": node_row["category"],
        "tags": tags,
        "image": image,
        "metadata": metadata,
        "created_at": node_row["created_at"],
        "updated_at": node_row["updated_at"],
        "blocks": blocks,
    }


def _coerce_node(payload: Mapping[str, Any]) -> ComplianceNode:
    """Normalise caller-provided mappings into ComplianceNode instances."""

    required = {"node_id", "title"}
    missing = required - payload.keys()
    if missing:
        raise ValueError(f"Missing required node keys: {sorted(missing)}")

    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    blocks_payload: Iterable[Mapping[str, Any]] = payload.get("blocks", [])
    blocks: List[ComplianceBlock] = []
    for index, block_payload in enumerate(blocks_payload):
        block_required = {"block_id", "content"}
        block_missing = block_required - block_payload.keys()
        if block_missing:
            raise ValueError(
                f"Missing required block keys for node {payload['node_id']}: {sorted(block_missing)}"
            )

        block_sequence = block_payload.get("sequence", index)
        blocks.append(
            ComplianceBlock(
                block_id=str(block_payload["block_id"]),
                node_id=str(block_payload.get("node_id", payload["node_id"])),
                block_type=block_payload.get("block_type"),
                content=str(block_payload["content"]),
                source=block_payload.get("source"),
                source_page=block_payload.get("source_page"),
                metadata=dict(block_payload.get("metadata", {})),
                sequence=int(block_sequence),
            )
        )

    node = ComplianceNode(
        node_id=str(payload["node_id"]),
        title=str(payload["title"]),
        summary=payload.get("summary"),
        category=payload.get("category"),
        tags=list(payload.get("tags", [])),
        image=dict(payload.get("image", {})),
        metadata=dict(payload.get("metadata", {})),
        blocks=blocks,
        created_at=payload.get("created_at", now),
        updated_at=payload.get("updated_at", now),
    )

    return node
