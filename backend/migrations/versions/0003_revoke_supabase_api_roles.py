"""revoke Supabase API roles' access to app tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-29 09:50:00

Supabase grants its public API roles (anon, authenticated) every privilege on new tables, including
TRUNCATE, which row level security does not cover. The app reaches the database only as the table
owner, so those roles need nothing. Revoking them means a later mistake (RLS turned off, a new table
without RLS, a new API feature) still can't expose or wipe data.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

API_ROLES = ("anon", "authenticated")


def _roles_present() -> list[str]:
    bind = op.get_bind()
    rows = bind.exec_driver_sql("SELECT rolname FROM pg_roles WHERE rolname IN ('anon', 'authenticated')")
    return [row[0] for row in rows]


def upgrade() -> None:
    if op.get_context().dialect.name != "postgresql" or op.get_context().as_sql:
        return
    for role in _roles_present():
        op.execute(f"REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {role}")
        op.execute(f"REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM {role}")
        op.execute(f"REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM {role}")
        op.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM {role}")
        op.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM {role}")
        op.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON FUNCTIONS FROM {role}")


def downgrade() -> None:
    if op.get_context().dialect.name != "postgresql" or op.get_context().as_sql:
        return
    for role in _roles_present():
        op.execute(f"GRANT ALL ON ALL TABLES IN SCHEMA public TO {role}")
        op.execute(f"GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO {role}")
        op.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO {role}")
        op.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO {role}")
