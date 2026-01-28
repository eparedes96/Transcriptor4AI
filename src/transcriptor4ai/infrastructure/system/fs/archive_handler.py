from __future__ import annotations

"""
FileSystem Archive Management Service.

Handles decompression and integrity verification of ZIP archives.
Specifically optimized for the OTA (Over-The-Air) update system to identify
and extract application binaries across different packaging structures.
"""

import logging
import os
import zipfile
from typing import Optional

# Local module logger
logger = logging.getLogger(__name__)


# ==============================================================================
# PUBLIC ARCHIVE API
# ==============================================================================

def unpack_executable_from_zip(zip_path: str, extract_to: str) -> Optional[str]:
    """
    Identify and extract the primary executable from a compressed update package.

    Args:
        zip_path: Absolute path to the source .zip file.
        extract_to: Destination directory for the extraction.

    Returns:
        Optional[str]: Absolute path to the extracted binary, or None on failure.
    """
    # 1. VALIDATION: Ensure source is a valid ZIP archive
    if not zipfile.is_zipfile(zip_path):
        logger.error(f"ArchiveHandler: Invalid or corrupted ZIP archive -> {zip_path}")
        return None

    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            # 2. DISCOVERY: Filter archive members for executable extensions
            content_list = zf.namelist()
            exe_files = [f for f in content_list if f.lower().endswith(".exe")]

            if not exe_files:
                logger.warning(f"ArchiveHandler: No executable found in {zip_path}")
                return None

            # 3. HEURISTIC: Select the best candidate (prioritize 'transcriptor' name)
            # Falls back to the first .exe found if the naming convention differs.
            target_member = next(
                (f for f in exe_files if "transcriptor" in f.lower()),
                exe_files[0]
            )

            # 4. EXTRACTION: Persist the selected binary to the staging directory
            logger.debug(f"ArchiveHandler: Extracting '{target_member}' to '{extract_to}'")
            zf.extract(target_member, extract_to)

            return os.path.join(extract_to, target_member)

    except (zipfile.BadZipFile, OSError) as e:
        # Handles filesystem locks (Windows) or corrupted headers
        logger.error(f"ArchiveHandler: Extraction critical failure: {e}")
        return None