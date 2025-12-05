"""Add priority field to roles table.

Revision ID: 0002
Revises: 0001
Create Date: 2024-12-05 00:01:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add priority column to roles table
    op.add_column(
        "roles",
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
    )

    # Add check constraint for non-negative priority
    op.create_check_constraint(
        "roles_priority_non_negative",
        "roles",
        "priority >= 0",
    )


def downgrade() -> None:
    # Drop check constraint
    op.drop_constraint("roles_priority_non_negative", "roles", type_="check")

    # Drop priority column
    op.drop_column("roles", "priority")
