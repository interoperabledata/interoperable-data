from pathlib import Path
from typing import List

from .errors import RunnerError


def clear_directory_contents(path: Path) -> None:
    """
    Remove all children (files and subdirectories) from 'path', keeping 'path' itself.
    Create the directory if it does not exist.
    """
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
        return

    if not path.is_dir():
        raise RunnerError(f"Expected directory, found file: {path}")

    for child in path.iterdir():
        if child.is_dir():
            import shutil
            shutil.rmtree(child)
        else:
            child.unlink()


def list_files_in_dir(path: Path) -> List[Path]:
    """
    Non-recursive listing of files in a directory.
    """
    if not path.is_dir():
        raise RunnerError(f"Source directory does not exist: {path}")
    return sorted([p for p in path.iterdir() if p.is_file()])
