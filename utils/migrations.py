import logging
from pathlib import Path


logger = logging.getLogger(__name__)


def migrate_format_md() -> dict:
    """Move root-level format.md to config/format.md if present.

    Idempotent and safe: will not overwrite an existing destination.
    Returns a status dictionary for diagnostics.
    """
    src = Path('format.md')
    dst_dir = Path('config')
    dst = dst_dir / 'format.md'

    if not src.exists():
        return {'migrated': False, 'reason': 'source_missing'}

    try:
        dst_dir.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            logger.info("config/format.md already exists; leaving root format.md in place")
            return {'migrated': False, 'reason': 'dest_exists'}

        src.rename(dst)
        logger.info("Migrated format.md -> config/format.md")
        return {'migrated': True}
    except Exception as e:
        logger.error(f"Failed to migrate format.md: {e}")
        return {'migrated': False, 'error': str(e)}


