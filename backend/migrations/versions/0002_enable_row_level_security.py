"""enable row level security on Postgres

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-29 04:30:00

Hosts like Supabase publish every public table through a REST API that anyone holding the
project's public key can call. The app only talks to Postgres directly as the table owner,
which RLS does not restrict, so turning RLS on with no policies closes that API without
changing anything for the app.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = ["profiles", "meals", "meal_items", "custom_foods", "proposals", "chat_messages", "workouts", "alembic_version"]


def upgrade() -> None:
    if op.get_context().dialect.name != "postgresql":
        return
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    if op.get_context().dialect.name != "postgresql":
        return
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
