"""
Git operations wrapper for SpecKit Agent System.

This module provides GitPython-based wrappers for common git operations
including branch management, status checking, and repository information.
"""

from pathlib import Path
from typing import Optional, List, Tuple
import git
from git import Repo, GitCommandError


class GitOperationError(Exception):
    """Raised when a git operation fails."""
    pass


class GitOps:
    """
    Wrapper for git operations using GitPython.

    Provides safe, convenient methods for branch operations, status checking,
    and repository management.
    """

    def __init__(self, repo_path: Optional[Path] = None):
        """
        Initialize git operations.

        Args:
            repo_path: Path to git repository. If None, uses current directory.

        Raises:
            GitOperationError: If repository is not found or invalid
        """
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()

        try:
            self.repo = Repo(self.repo_path, search_parent_directories=True)
        except git.InvalidGitRepositoryError:
            raise GitOperationError(f"Not a git repository: {self.repo_path}")
        except git.NoSuchPathError:
            raise GitOperationError(f"Path does not exist: {self.repo_path}")

    def get_current_branch(self) -> str:
        """
        Get the name of the current branch.

        Returns:
            Current branch name

        Raises:
            GitOperationError: If operation fails
        """
        try:
            return self.repo.active_branch.name
        except TypeError:
            # Detached HEAD state
            return "HEAD"
        except Exception as e:
            raise GitOperationError(f"Failed to get current branch: {e}")

    def branch_exists(self, branch_name: str) -> bool:
        """
        Check if a branch exists.

        Args:
            branch_name: Branch name to check

        Returns:
            True if branch exists
        """
        try:
            return branch_name in [b.name for b in self.repo.branches]
        except Exception:
            return False

    def create_branch(
        self,
        branch_name: str,
        base_branch: Optional[str] = None,
        checkout: bool = True
    ) -> None:
        """
        Create a new branch.

        Args:
            branch_name: Name for the new branch
            base_branch: Base branch to branch from (default: current branch)
            checkout: If True, checkout the new branch after creating

        Raises:
            GitOperationError: If branch creation fails
        """
        try:
            # Check if branch already exists
            if self.branch_exists(branch_name):
                raise GitOperationError(f"Branch already exists: {branch_name}")

            # Determine base commit
            if base_branch:
                if not self.branch_exists(base_branch):
                    raise GitOperationError(f"Base branch does not exist: {base_branch}")
                base_commit = self.repo.branches[base_branch].commit
            else:
                base_commit = self.repo.head.commit

            # Create new branch
            new_branch = self.repo.create_head(branch_name, base_commit)

            # Checkout if requested
            if checkout:
                new_branch.checkout()

        except GitCommandError as e:
            raise GitOperationError(f"Failed to create branch '{branch_name}': {e}")
        except Exception as e:
            raise GitOperationError(f"Failed to create branch '{branch_name}': {e}")

    def checkout_branch(
        self,
        branch_name: str,
        create_if_missing: bool = False
    ) -> None:
        """
        Checkout a branch.

        Args:
            branch_name: Branch name to checkout
            create_if_missing: If True, create branch if it doesn't exist

        Raises:
            GitOperationError: If checkout fails
        """
        try:
            if not self.branch_exists(branch_name):
                if create_if_missing:
                    self.create_branch(branch_name, checkout=True)
                    return
                else:
                    raise GitOperationError(f"Branch does not exist: {branch_name}")

            # Checkout existing branch
            self.repo.branches[branch_name].checkout()

        except GitCommandError as e:
            raise GitOperationError(f"Failed to checkout branch '{branch_name}': {e}")
        except Exception as e:
            raise GitOperationError(f"Failed to checkout branch '{branch_name}': {e}")

    def get_status(self) -> Tuple[List[str], List[str], List[str]]:
        """
        Get repository status.

        Returns:
            Tuple of (modified_files, untracked_files, staged_files)
        """
        try:
            # Modified files (including staged)
            modified = [item.a_path for item in self.repo.index.diff(None)]

            # Untracked files
            untracked = self.repo.untracked_files

            # Staged files
            staged = [item.a_path for item in self.repo.index.diff('HEAD')]

            return modified, untracked, staged

        except Exception as e:
            raise GitOperationError(f"Failed to get repository status: {e}")

    def has_uncommitted_changes(self) -> bool:
        """
        Check if repository has uncommitted changes.

        Returns:
            True if there are uncommitted changes
        """
        modified, untracked, _ = self.get_status()
        return len(modified) > 0 or len(untracked) > 0

    def get_repo_root(self) -> Path:
        """
        Get the repository root directory.

        Returns:
            Path to repository root
        """
        return Path(self.repo.working_dir)

    def get_remote_url(self, remote_name: str = "origin") -> Optional[str]:
        """
        Get remote repository URL.

        Args:
            remote_name: Remote name (default: origin)

        Returns:
            Remote URL, or None if remote doesn't exist
        """
        try:
            if remote_name in self.repo.remotes:
                return self.repo.remotes[remote_name].url
            return None
        except Exception:
            return None

    def get_commit_info(self, ref: str = "HEAD") -> dict:
        """
        Get commit information.

        Args:
            ref: Git reference (default: HEAD)

        Returns:
            Dictionary with commit information
        """
        try:
            commit = self.repo.commit(ref)
            return {
                "sha": commit.hexsha,
                "short_sha": commit.hexsha[:7],
                "author": str(commit.author),
                "author_email": commit.author.email,
                "message": commit.message.strip(),
                "date": commit.committed_datetime.isoformat()
            }
        except Exception as e:
            raise GitOperationError(f"Failed to get commit info for '{ref}': {e}")

    def is_clean_working_tree(self) -> bool:
        """
        Check if working tree is clean (no uncommitted changes).

        Returns:
            True if working tree is clean
        """
        try:
            return not self.repo.is_dirty(untracked_files=True)
        except Exception:
            return False

    def get_branch_list(self, remote: bool = False) -> List[str]:
        """
        Get list of branches.

        Args:
            remote: If True, return remote branches instead of local

        Returns:
            List of branch names
        """
        try:
            if remote:
                return [ref.name for ref in self.repo.remotes.origin.refs]
            else:
                return [branch.name for branch in self.repo.branches]
        except Exception:
            return []

    def get_tracking_branch(self, branch_name: Optional[str] = None) -> Optional[str]:
        """
        Get the remote tracking branch for a local branch.

        Args:
            branch_name: Branch name (default: current branch)

        Returns:
            Remote tracking branch name, or None if not set
        """
        try:
            if branch_name is None:
                branch = self.repo.active_branch
            else:
                branch = self.repo.branches[branch_name]

            tracking_branch = branch.tracking_branch()
            return tracking_branch.name if tracking_branch else None

        except Exception:
            return None


def get_git_ops(repo_path: Optional[Path] = None) -> GitOps:
    """
    Get a GitOps instance.

    Args:
        repo_path: Optional path to repository

    Returns:
        GitOps instance
    """
    return GitOps(repo_path)


def get_current_branch(repo_path: Optional[Path] = None) -> str:
    """
    Convenience function to get current branch name.

    Args:
        repo_path: Optional path to repository

    Returns:
        Current branch name
    """
    ops = GitOps(repo_path)
    return ops.get_current_branch()


def branch_exists(branch_name: str, repo_path: Optional[Path] = None) -> bool:
    """
    Convenience function to check if a branch exists.

    Args:
        branch_name: Branch name to check
        repo_path: Optional path to repository

    Returns:
        True if branch exists
    """
    ops = GitOps(repo_path)
    return ops.branch_exists(branch_name)
