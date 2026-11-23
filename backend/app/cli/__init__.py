"""Operator commands exposed as console scripts (see pyproject ``[project.scripts]``).

There are deliberately no ``if __name__ == "__main__"`` blocks anywhere in the
code base; every command runs through these entry points.
"""

from app.cli.admin_cmd import add_center_command, export_openapi_command
from app.cli.cleanup_cmd import cleanup_command
from app.cli.db_cmd import db_roles_command
from app.cli.secrets_cmd import dev_secrets_command
from app.cli.seed_cmd import seed_command

__all__ = [
    "add_center_command",
    "cleanup_command",
    "db_roles_command",
    "dev_secrets_command",
    "export_openapi_command",
    "seed_command",
]
