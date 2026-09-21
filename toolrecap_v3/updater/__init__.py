"""Updater module for ToolRecap V3."""

from toolrecap_v3.updater.archive import (
    DEFAULT_MAX_FILE_COUNT,
    DEFAULT_MAX_RATIO,
    DEFAULT_MAX_UNCOMPRESSED_BYTES,
    calculate_sha256,
    parse_sha256_content,
    safe_extract_zip,
    verify_checksum,
)
from toolrecap_v3.updater.helper import (
    apply_staged_update_with_rollback,
    is_process_running,
    wait_for_process_exit,
)
from toolrecap_v3.updater.manager import (
    UpdateCheckResult,
    UpdateManager,
)
from toolrecap_v3.updater.semver import (
    SemVer,
)
from toolrecap_v3.updater.validator import (
    validate_package,
)

__all__ = [
    "SemVer",
    "calculate_sha256",
    "parse_sha256_content",
    "verify_checksum",
    "safe_extract_zip",
    "validate_package",
    "apply_staged_update_with_rollback",
    "is_process_running",
    "wait_for_process_exit",
    "UpdateCheckResult",
    "UpdateManager",
    "DEFAULT_MAX_UNCOMPRESSED_BYTES",
    "DEFAULT_MAX_FILE_COUNT",
    "DEFAULT_MAX_RATIO",
]
