"""Add access tracking for admins and kiosk volunteers

Revision ID: add806ffb00c
Revises: 221a27f754a0
Create Date: 2026-11-27 20:00:34.937149

"""


# revision identifiers, used by Alembic.
revision = 'add806ffb00c'
down_revision = '221a27f754a0'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


try:
    is_sqlite = op.get_context().dialect.name == 'sqlite'
except Exception:
    is_sqlite = False

if is_sqlite:
    op.get_context().connection.execute('PRAGMA foreign_keys=ON;')
    utcnow_server_default = "(datetime('now', 'utc'))"
else:
    utcnow_server_default = "timezone('utc', current_timestamp)"

def sqlite_column_reflect_listener(inspector, table, column_info):
    """Adds parenthesis around SQLite datetime defaults for utcnow."""
    if column_info['default'] == "datetime('now', 'utc')":
        column_info['default'] = utcnow_server_default

sqlite_reflect_kwargs = {
    'listeners': [('column_reflect', sqlite_column_reflect_listener)]
}

# ===========================================================================
# HOWTO: Handle alter statements in SQLite
#
# def upgrade():
#     if is_sqlite:
#         with op.batch_alter_table('table_name', reflect_kwargs=sqlite_reflect_kwargs) as batch_op:
#             batch_op.alter_column('column_name', type_=sa.Unicode(), server_default='', nullable=False)
#     else:
#         op.alter_column('table_name', 'column_name', type_=sa.Unicode(), server_default='', nullable=False)
#
# ===========================================================================


def upgrade():
    op.create_table('access_tracking',
    sa.Column('id', sa.Uuid(as_uuid=False), nullable=False),
    sa.Column('created', sa.DateTime(timezone=True), nullable=False),
    sa.Column('last_updated', sa.DateTime(timezone=True), nullable=False),
    sa.Column('external_id', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('last_synced', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('when', sa.DateTime(timezone=True), nullable=False),
    sa.Column('access_type', sa.Integer(), nullable=False),
    sa.Column('who', sa.Unicode(), nullable=False),
    sa.Column('supervisor', sa.Unicode(), nullable=False),
    sa.Column('ip_address', sa.Unicode(), nullable=False),
    sa.Column('logged_in', sa.DateTime(timezone=True), nullable=True),
    sa.Column('logged_out', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_access_tracking'))
    )

def downgrade():
    op.drop_table('access_tracking')
