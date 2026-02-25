"""
CLI entry point for SpecKit Agent System.

This module provides the main Click-based command-line interface for the agent system,
including command registration and execution.
"""

import sys
import click
from pathlib import Path
from typing import Optional


# Version information
__version__ = "0.1.0"


class Config:
    """Global configuration object for CLI context."""

    def __init__(self):
        self.verbose = False
        self.repo_root = Path.cwd()
        self.debug = False


# Create pass decorator for config
pass_config = click.make_pass_decorator(Config, ensure=True)


@click.group()
@click.version_option(version=__version__, prog_name="speckit-agent")
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Enable verbose output'
)
@click.option(
    '--debug',
    is_flag=True,
    help='Enable debug mode'
)
@click.pass_context
def cli(ctx, verbose: bool, debug: bool):
    """
    SpecKit Agent System - AI-driven Spec-Driven Development workflows.

    This system provides constitution-governed workflow execution for software development,
    including specification generation, planning, task breakdown, and governance enforcement.

    \b
    Available Commands:
      specify       Generate feature specification from natural language
      constitution  Create or update project constitution
      plan          Generate implementation plan from specification
      tasks         Generate task list from plan
      adr           Document architectural decision
      draft         Create communication draft for human approval

    \b
    Examples:
      # Create a project constitution
      speckit-agent constitution principles.txt

      # Generate a feature specification
      speckit-agent specify "Add user authentication with JWT tokens"

      # Generate implementation plan
      speckit-agent plan

    For more information on a specific command, run:
      speckit-agent COMMAND --help
    """
    # Initialize config
    ctx.ensure_object(Config)
    ctx.obj.verbose = verbose
    ctx.obj.debug = debug

    if debug:
        click.echo(f"Debug mode enabled", err=True)
        click.echo(f"Repository root: {ctx.obj.repo_root}", err=True)


@cli.command()
@click.argument('feature_description', required=False)
@click.option(
    '--interactive', '-i',
    is_flag=True,
    help='Use interactive mode to provide feature description'
)
@click.option(
    '--short-name', '-s',
    help='Short name for the feature (2-4 words)'
)
@pass_config
def specify(
    config: Config,
    feature_description: Optional[str],
    interactive: bool,
    short_name: Optional[str]
):
    """
    Generate a feature specification from natural language description.

    This command creates a structured specification document in specs/<feature>/spec.md
    with user stories, requirements, and success criteria.

    \b
    Arguments:
      FEATURE_DESCRIPTION  Natural language description of the feature

    \b
    Examples:
      speckit-agent specify "Add user authentication with JWT tokens"
      speckit-agent specify "Implement payment processing" --short-name "payment-system"
      speckit-agent specify --interactive
    """
    from .commands.specify import execute_specify, SpecificationError

    # Get feature description
    if interactive or not feature_description:
        if not interactive:
            click.echo("Error: FEATURE_DESCRIPTION is required (or use --interactive)")
            sys.exit(1)

        click.echo("Interactive mode:")
        feature_description = click.prompt("Enter feature description")

    if not feature_description or not feature_description.strip():
        click.echo("Error: Feature description cannot be empty")
        sys.exit(1)

    # Execute specification generation
    try:
        result = execute_specify(
            feature_description=feature_description.strip(),
            short_name=short_name,
            api_key=None,  # Will read from environment
            verbose=config.verbose
        )

        # Exit successfully
        sys.exit(0)

    except SpecificationError as e:
        click.echo(f"\nError: {e}", err=True)
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo("\n\nInterrupted by user", err=True)
        sys.exit(130)
    except Exception as e:
        click.echo(f"\nUnexpected error: {e}", err=True)
        if config.debug:
            raise
        sys.exit(1)


@cli.command()
@click.argument('constitution_content', required=False)
@click.option(
    '--file', '-f',
    type=click.Path(exists=True),
    help='Path to constitution file'
)
@click.option(
    '--interactive', '-i',
    is_flag=True,
    help='Use interactive mode to provide principles'
)
@pass_config
def constitution(
    config: Config,
    constitution_content: Optional[str],
    file: Optional[str],
    interactive: bool
):
    """
    Create or update the project constitution.

    The constitution defines governance principles and rules that all
    development work must comply with.

    \b
    Arguments:
      CONSTITUTION_CONTENT  Inline constitution content or principles

    \b
    Examples:
      speckit-agent constitution --file principles.txt
      speckit-agent constitution "Principle 1: One Question at a Time..."
      speckit-agent constitution --interactive
    """
    from .commands.constitution import execute_constitution, ConstitutionError

    # Determine input source
    is_file_path = False
    content = None

    if file:
        # Use file path
        content = file
        is_file_path = True
    elif constitution_content:
        # Use inline content
        content = constitution_content
        is_file_path = False
    elif interactive:
        # Interactive mode: prompt for content
        click.echo("Interactive mode:")
        click.echo("Enter constitution principles (end with Ctrl+D on Unix or Ctrl+Z on Windows):")
        lines = []
        try:
            while True:
                line = input()
                lines.append(line)
        except EOFError:
            pass
        content = "\n".join(lines)
        is_file_path = False
    else:
        click.echo("Error: Must provide constitution content via argument, --file, or --interactive")
        click.echo("Run 'speckit-agent constitution --help' for usage information")
        sys.exit(1)

    if not content or (not is_file_path and not content.strip()):
        click.echo("Error: Constitution content cannot be empty")
        sys.exit(1)

    # Execute constitution processing
    try:
        result = execute_constitution(
            content=content if not is_file_path else content,
            is_file_path=is_file_path,
            api_key=None,  # Will read from environment
            verbose=config.verbose
        )

        # Exit successfully
        sys.exit(0)

    except ConstitutionError as e:
        click.echo(f"\nError: {e}", err=True)
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo("\n\nInterrupted by user", err=True)
        sys.exit(130)
    except Exception as e:
        click.echo(f"\nUnexpected error: {e}", err=True)
        if config.debug:
            raise
        sys.exit(1)


@cli.command()
@click.option(
    '--feature', '-f',
    help='Feature to generate plan for (default: current branch)'
)
@pass_config
def plan(config: Config, feature: Optional[str]):
    """
    Generate implementation plan from existing specification.

    This command creates plan.md, research.md, data-model.md, and contracts/
    based on the feature specification.

    Prerequisites: Feature specification must exist (run 'specify' first)

    \b
    Examples:
      speckit-agent plan
      speckit-agent plan --feature 001-ai-agent-system
    """
    from .commands.plan import execute_plan, PlanningError

    # Execute plan generation
    try:
        result = execute_plan(
            feature=feature,
            api_key=None,  # Will read from environment
            verbose=config.verbose
        )

        # Exit successfully
        sys.exit(0)

    except PlanningError as e:
        click.echo(f"\nError: {e}", err=True)
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo("\n\nInterrupted by user", err=True)
        sys.exit(130)
    except Exception as e:
        click.echo(f"\nUnexpected error: {e}", err=True)
        if config.debug:
            raise
        sys.exit(1)


@cli.command()
@click.option(
    '--feature', '-f',
    help='Feature to generate tasks for (default: current branch)'
)
@pass_config
def tasks(config: Config, feature: Optional[str]):
    """
    Generate task list from existing plan.

    This command creates tasks.md with dependency-ordered, parallelizable tasks
    organized by user story.

    Prerequisites: Specification and plan must exist

    \b
    Examples:
      speckit-agent tasks
      speckit-agent tasks --feature 001-ai-agent-system
    """
    from .commands.tasks import execute_tasks, TaskGenerationError

    # Execute task generation
    try:
        result = execute_tasks(
            feature=feature,
            api_key=None,  # Will read from environment
            verbose=config.verbose
        )

        # Exit successfully
        sys.exit(0)

    except TaskGenerationError as e:
        click.echo(f"\nError: {e}", err=True)
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo("\n\nInterrupted by user", err=True)
        sys.exit(130)
    except Exception as e:
        click.echo(f"\nUnexpected error: {e}", err=True)
        if config.debug:
            raise
        sys.exit(1)


@cli.command()
@click.argument('decision_title')
@click.option(
    '--context', '-c',
    help='Decision context or rationale'
)
@click.option(
    '--feature', '-f',
    help='Feature context for this ADR (default: current branch)'
)
@pass_config
def adr(config: Config, decision_title: str, context: Optional[str], feature: Optional[str]):
    """
    Document an architectural decision.

    Creates an ADR (Architecture Decision Record) in history/adr/ documenting
    a significant architectural decision with alternatives and rationale.

    The decision must pass a significance test (impact, alternatives, scope)
    before an ADR is created. You will be prompted for alternatives and
    consequences interactively.

    \b
    Arguments:
      DECISION_TITLE  Title of the architectural decision

    \b
    Examples:
      speckit-agent adr "Use PostgreSQL for data storage"
      speckit-agent adr "Choose REST over GraphQL" --context "API design decision"
      speckit-agent adr "Python over Node.js" --feature 001-ai-agent-system
    """
    from .commands.adr import execute_adr, ADRError

    # Execute ADR creation
    try:
        result = execute_adr(
            decision_title=decision_title,
            decision_context=context,
            feature=feature,
            api_key=None,  # ADR doesn't use AI
            verbose=config.verbose
        )

        # Exit successfully
        sys.exit(0)

    except ADRError as e:
        click.echo(f"\nError: {e}", err=True)
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo("\n\nInterrupted by user", err=True)
        sys.exit(130)
    except Exception as e:
        click.echo(f"\nUnexpected error: {e}", err=True)
        if config.debug:
            raise
        sys.exit(1)


@cli.command()
@click.argument('purpose')
@click.option(
    '--type', '-t',
    'message_type',
    required=True,
    type=click.Choice(['email', 'whatsapp'], case_sensitive=False),
    help='Type of message to draft'
)
@click.option(
    '--recipient', '-r',
    help='Recipient name or description'
)
@click.option(
    '--context', '-c',
    help='Additional context for message generation'
)
@click.option(
    '--tone',
    type=click.Choice(['professional', 'friendly', 'formal', 'casual']),
    default='professional',
    help='Message tone (default: professional)'
)
@click.option(
    '--feature', '-f',
    help='Feature context for PHR routing'
)
@pass_config
def draft(
    config: Config,
    purpose: str,
    message_type: str,
    recipient: Optional[str],
    context: Optional[str],
    tone: str,
    feature: Optional[str]
):
    """
    Create a communication draft for human approval.

    Generates email or WhatsApp message drafts that require explicit
    human approval before any sending occurs. All drafts are clearly
    marked as DRAFT and saved to drafts/{type}/.

    \b
    Arguments:
      PURPOSE  The purpose/intent of the message

    \b
    Examples:
      speckit-agent draft "Notify team about new feature release" --type email
      speckit-agent draft "Request meeting time" --type whatsapp --recipient "John"
      speckit-agent draft "Project status update" --type email --tone formal
    """
    from .commands.draft import execute_draft, CommunicationError

    # Execute draft creation
    try:
        result = execute_draft(
            message_type=message_type,
            purpose=purpose,
            recipient=recipient,
            context=context,
            tone=tone,
            feature=feature,
            api_key=None,  # Will read from environment
            verbose=config.verbose
        )

        # Exit successfully
        sys.exit(0)

    except CommunicationError as e:
        click.echo(f"\nError: {e}", err=True)
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo("\n\nInterrupted by user", err=True)
        sys.exit(130)
    except Exception as e:
        click.echo(f"\nUnexpected error: {e}", err=True)
        if config.debug:
            raise
        sys.exit(1)


@cli.command()
@click.option(
    '--interval', '-i',
    default=5.0,
    type=float,
    help='Poll interval in seconds (default: 5)'
)
@click.option(
    '--vault', '-V',
    type=click.Path(exists=True),
    help='Path to Obsidian vault (default: obsidian_vault/ in repo root)'
)
@pass_config
def run(config: Config, interval: float, vault: Optional[str]):
    """
    Start the AI Employee in continuous monitoring mode.

    Watches obsidian_vault/Needs_Action/ for new .md files, processes them
    through Claude API, and writes results to Completed/.

    Files are moved out of Needs_Action/ after processing so they
    won't be picked up again.

    \b
    Examples:
      speckit-agent run
      speckit-agent run --interval 10
      speckit-agent run --vault /path/to/obsidian/vault
    """
    import sys
    sys.path.insert(0, str(config.repo_root / "src"))
    from ai_employee import AIEmployee

    repo_root = config.repo_root
    if vault:
        # If custom vault path, still use repo_root for other paths
        pass

    employee = AIEmployee(
        repo_root=repo_root,
        poll_interval=interval,
    )

    if vault:
        from pathlib import Path as P
        employee.vault_path = P(vault)
        employee.needs_action_path = employee.vault_path / "Needs_Action"
        employee.done_path = employee.vault_path / "Done"
        employee.logs_path = employee.vault_path / "Logs"
        employee.plans_path = employee.vault_path / "Plans"
        employee._setup_directories()

    click.echo(f"Starting AI Employee...")
    click.echo(f"  Vault:    {employee.vault_path}")
    click.echo(f"  Watching: {employee.needs_action_path}")
    click.echo(f"  Interval: {interval}s")
    click.echo(f"  AI:       {'Enabled' if employee.client else 'Disabled (no ANTHROPIC_API_KEY)'}")
    click.echo()

    employee.run()


@cli.command()
@pass_config
def version(config: Config):
    """Show version information."""
    click.echo(f"SpecKit Agent System v{__version__}")
    click.echo("Copyright © 2026 SpecKit Team")
    click.echo("License: MIT")


@cli.command()
@pass_config
def status(config: Config):
    """Show current workflow status."""
    from .core.workflow_orchestrator import get_orchestrator

    try:
        orchestrator = get_orchestrator()
        state = orchestrator.get_state()

        click.echo("=" * 70)
        click.echo("WORKFLOW STATUS")
        click.echo("=" * 70)

        if state.get("last_step"):
            click.echo(f"Last step: {state['last_step']}")
        else:
            click.echo("Last step: None (workflow not started)")

        if state.get("current_feature"):
            click.echo(f"Current feature: {state['current_feature']}")

        click.echo(f"Last updated: {state.get('last_updated', 'Never')}")

        # Show features
        features = state.get("features", {})
        if features:
            click.echo(f"\nFeatures ({len(features)}):")
            for feature_name, feature_state in features.items():
                steps = feature_state.get("steps_completed", [])
                click.echo(f"  - {feature_name}: {len(steps)} steps completed")
        else:
            click.echo("\nNo features in progress")

        click.echo("=" * 70)

    except Exception as e:
        click.echo(f"Error: Failed to load workflow status: {e}", err=True)
        sys.exit(1)


def main():
    """Main entry point for the CLI."""
    try:
        cli(obj=Config())
    except KeyboardInterrupt:
        click.echo("\n\nInterrupted by user", err=True)
        sys.exit(130)
    except Exception as e:
        click.echo(f"\nError: {e}", err=True)
        if '--debug' in sys.argv:
            raise
        sys.exit(1)


if __name__ == '__main__':
    main()
