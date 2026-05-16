"""CLI entry point for the code review agent."""

import argparse
import json
import logging
import sys

from rich.console import Console
from rich.panel import Panel

from .config import settings
from .git.repo_manager import RepoManager
from .agent.review_agent import CodeReviewAgent
from .output.formatter import OutputFormatter
from .output.models import ReviewReport

console = Console()


def setup_logging(level: str):
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def review_commit(repo_path: str, commit_sha: str, model: str | None = None) -> ReviewReport:
    """Review a specific commit."""
    console.print(f"[bold blue]Fetching diff for commit {commit_sha}...[/]")
    diff_result = RepoManager.get_diff_from_commit(repo_path, commit_sha)
    console.print(
        f"[green]Found {diff_result.total_files} changed files, "
        f"+{diff_result.total_added} -{diff_result.total_deleted} lines[/]"
    )

    agent = CodeReviewAgent(model=model)
    console.print("[bold blue]Running AI review...[/]")
    report = agent.review_diff(diff_result, repo_path)
    return report


def review_branch_diff(repo_path: str, base_ref: str, head_ref: str, model: str | None = None) -> ReviewReport:
    """Review the diff between two branches/refs."""
    console.print(f"[bold blue]Fetching diff between {base_ref} and {head_ref}...[/]")
    diff_result = RepoManager.get_diff(repo_path, base_ref, head_ref)
    console.print(
        f"[green]Found {diff_result.total_files} changed files, "
        f"+{diff_result.total_added} -{diff_result.total_deleted} lines[/]"
    )

    agent = CodeReviewAgent(model=model)
    console.print("[bold blue]Running AI review...[/]")
    report = agent.review_diff(diff_result, repo_path)
    return report


def output_report(report: ReviewReport, fmt: str, output_path: str | None):
    """Output the review report in the specified format."""
    if fmt == "json":
        content = OutputFormatter.format_as_json(report)
    elif fmt == "markdown":
        content = OutputFormatter.format_as_markdown(report)
    else:
        content = OutputFormatter.format_as_markdown(report)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        console.print(f"[green]Report saved to {output_path}[/]")
    else:
        if fmt == "json":
            console.print(content)
        else:
            console.print(Panel(content, title="Code Review Report", border_style="blue"))


def main():
    parser = argparse.ArgumentParser(
        description="Intelligent Code Review Agent - AI-powered code review using Claude"
    )
    parser.add_argument("repo_path", help="Path to git repository")
    parser.add_argument("--commit", help="Review a specific commit (SHA or 'HEAD')")
    parser.add_argument("--base", help="Base branch/ref for comparison")
    parser.add_argument("--head", help="Head branch/ref for comparison")
    parser.add_argument(
        "--format", "-f",
        choices=["json", "markdown"],
        default="markdown",
        help="Output format (default: markdown)",
    )
    parser.add_argument("--output", "-o", help="Output file path (default: stdout)")
    parser.add_argument("--model", help=f"Claude model to use (default: {settings.claude_model})")
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=settings.log_level,
        help="Logging level",
    )

    args = parser.parse_args()
    setup_logging(args.log_level)

    # Validate inputs
    if not args.commit and not (args.base and args.head):
        console.print(
            "[red]Error: Specify either --commit or both --base and --head[/]"
        )
        parser.print_help()
        sys.exit(1)

    if args.commit and (args.base or args.head):
        console.print(
            "[red]Error: Use either --commit OR --base/--head, not both[/]"
        )
        parser.print_help()
        sys.exit(1)

    try:
        if args.commit:
            report = review_commit(args.repo_path, args.commit, model=args.model)
        else:
            report = review_branch_diff(args.repo_path, args.base, args.head, model=args.model)

        output_report(report, args.format, args.output)

        # Exit with error code if critical issues found
        if report.critical_count > 0:
            sys.exit(2)

    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/]")
        logging.exception("Full traceback:")
        sys.exit(1)


if __name__ == "__main__":
    main()
