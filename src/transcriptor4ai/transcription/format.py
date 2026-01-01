from __future__ import annotations

# -----------------------------------------------------------------------------
# Output Formatting
# -----------------------------------------------------------------------------
def _append_entry(output_path: str, rel_path: str, content: str) -> None:
    """
    Append a file content entry to the consolidated output file.

    Format:
    -------------------- (separator)
    <relative_path>
    <file_content>

    Args:
        output_path: Destination file path.
        rel_path: Relative path of the source file (header).
        content: The actual content of the source file.
    """
    # Use a standard separator length (200 chars)
    separator = "-" * 200

    with open(output_path, "a", encoding="utf-8") as out:
        out.write(f"{separator}\n")
        out.write(f"{rel_path}\n")
        # Ensure consistent spacing: trim trailing newline then add exactly one
        out.write(content.rstrip("\n") + "\n")