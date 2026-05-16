"""Git repository management using GitPython."""

import os
import tempfile

import git

from .models import ChangeType, ChangedFile, DiffResult
from .diff_parser import DiffParser
from ..config import settings
from ..plc.file_support import has_plc_project_extension, is_plc_project_file


class RepoManager:
    """Manages git repository operations."""

    @staticmethod
    def clone_repo(url: str, target_dir: str | None = None) -> str:
        """Clone a remote repository. Returns the local path."""
        if target_dir is None:
            target_dir = tempfile.mkdtemp(prefix="code-review-")
        git.Repo.clone_from(url, target_dir)
        return target_dir

    @staticmethod
    def open_repo(repo_path: str) -> git.Repo:
        """Open an existing git repository."""
        return git.Repo(repo_path)

    @classmethod
    def get_diff(
        cls, repo_path: str, base_ref: str, head_ref: str
    ) -> DiffResult:
        """Get the diff between two refs (branches, commits, tags)."""
        repo = cls.open_repo(repo_path)

        base_commit = repo.commit(base_ref)
        head_commit = repo.commit(head_ref)

        diff_index = base_commit.diff(head_commit, create_patch=True)

        files = []
        for diff_item in diff_index:
            changed_file = cls._parse_diff_item(diff_item, repo_path)
            if changed_file is not None:
                files.append(changed_file)

        return DiffResult(
            commit_sha=head_ref,
            base_ref=base_ref,
            head_ref=head_ref,
            files=files,
        )

    @classmethod
    def get_diff_from_commit(
        cls, repo_path: str, commit_sha: str
    ) -> DiffResult:
        """Get the diff for a single commit (compared to its parent)."""
        repo = cls.open_repo(repo_path)
        commit = repo.commit(commit_sha)

        if not commit.parents:
            # Initial commit — diff against empty tree
            parent = git.NULL_TREE
        else:
            parent = commit.parents[0]

        diff_index = commit.diff(parent, create_patch=True)

        files = []
        for diff_item in diff_index:
            changed_file = cls._parse_diff_item(diff_item, repo_path)
            if changed_file is not None:
                files.append(changed_file)

        return DiffResult(
            commit_sha=commit_sha,
            base_ref=commit.parents[0].hexsha if commit.parents else None,
            head_ref=commit_sha,
            files=files,
        )

    @staticmethod
    def get_file_content(repo_path: str, file_path: str, ref: str) -> str | None:
        """Get file content at a specific ref."""
        try:
            repo = git.Repo(repo_path)
            commit = repo.commit(ref)
            blob = commit.tree / file_path
            return blob.data_stream.read().decode("utf-8", errors="ignore")
        except (git.exc.GitCommandError, KeyError, UnicodeDecodeError):
            return None

    @staticmethod
    def list_changed_files(
        repo_path: str, base_ref: str, head_ref: str
    ) -> list[str]:
        """List files changed between two refs."""
        repo = git.Repo(repo_path)
        base_commit = repo.commit(base_ref)
        head_commit = repo.commit(head_ref)
        diff_index = base_commit.diff(head_commit)
        return [
            d.a_path or d.b_path
            for d in diff_index
            if (d.a_path or d.b_path)
        ]

    @classmethod
    def _parse_diff_item(
        cls, diff_item, repo_path: str
    ) -> ChangedFile | None:
        """Parse a single git diff item into a ChangedFile model."""
        # Determine file path
        file_path = diff_item.b_path or diff_item.a_path
        if not file_path:
            return None

        # Skip binary files
        if diff_item.diff is None:
            return None

        diff_text = diff_item.diff
        if isinstance(diff_text, bytes):
            try:
                diff_text = diff_text.decode("utf-8", errors="ignore")
            except UnicodeDecodeError:
                return None

        # Skip binary file diffs (very short diffs with no-newline marker)
        if "\\ No newline at end of file" in diff_text and len(diff_text.strip()) < 100:
            return None

        # Determine change type
        if diff_item.new_file:
            change_type = ChangeType.ADDED
        elif diff_item.deleted_file:
            change_type = ChangeType.DELETED
        elif diff_item.renamed_file:
            change_type = ChangeType.RENAMED
        else:
            change_type = ChangeType.MODIFIED

        # Detect language from extension
        language = cls._detect_language(file_path)
        if language is None:
            full_path = os.path.join(repo_path, file_path)
            if has_plc_project_extension(full_path) and is_plc_project_file(full_path):
                language = "structured_text"

        # Parse hunks
        hunks = DiffParser.parse_unified_diff(diff_text)

        # Get full file content (only for non-deleted files)
        new_content = None
        old_content = None
        if change_type != ChangeType.DELETED:
            try:
                new_content = cls.get_file_content(
                    repo_path, file_path, "HEAD"
                )
            except Exception:
                pass
        if change_type != ChangeType.ADDED:
            try:
                old_content = cls.get_file_content(
                    repo_path, diff_item.a_path or file_path, "HEAD~1"
                )
            except Exception:
                pass

        return ChangedFile(
            file_path=file_path,
            change_type=change_type,
            language=language,
            hunks=hunks,
            old_content=old_content,
            new_content=new_content,
        )

    @staticmethod
    def _detect_language(file_path: str) -> str | None:
        """Detect programming language from file extension."""
        _, ext = os.path.splitext(file_path)
        language = settings.language_map.get(ext.lower())
        if language:
            return language
        return None
