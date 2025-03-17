"""Adding hotel lottery application

Revision ID: 5d8ddcd68f6d
Revises: 0578795f8d0b
Create Date: 2024-08-15 02:29:39.182464

"""


# revision identifiers, used by Alembic.
revision = '5d8ddcd68f6d'
down_revision = '0578795f8d0b'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.types import Date
import residue


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
    op.create_table('lottery_application',
    sa.Column('id', residue.UUID(), nullable=False),
    sa.Column('created', residue.UTCDateTime(), server_default=sa.text("timezone('utc', current_timestamp)"), nullable=False),
    sa.Column('last_updated', residue.UTCDateTime(), server_default=sa.text("timezone('utc', current_timestamp)"), nullable=False),
    sa.Column('external_id', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
    sa.Column('last_synced', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
    sa.Column('attendee_id', residue.UUID()),
    sa.Column('parent_application_id', residue.UUID(), nullable=True),
    sa.Column('room_group_name', sa.Unicode(), server_default='', nullable=False),
    sa.Column('invite_code', sa.Unicode(), server_default='', nullable=False),
    sa.Column('wants_room', sa.Boolean(), server_default='False', nullable=False),
    sa.Column('earliest_room_checkin_date', Date(), nullable=True),
    sa.Column('latest_room_checkin_date', Date(), nullable=True),
    sa.Column('earliest_room_checkout_date', Date(), nullable=True),
    sa.Column('latest_room_checkout_date', Date(), nullable=True),
    sa.Column('hotel_preference', sa.Unicode(), server_default='', nullable=False),
    sa.Column('room_type_preference', sa.Unicode(), server_default='', nullable=False),
    sa.Column('room_selection_priorities', sa.Unicode(), server_default='', nullable=False),
    sa.Column('wants_ada', sa.Boolean(), server_default='False', nullable=False),
    sa.Column('ada_requests', sa.Unicode(), server_default='', nullable=False),
    sa.Column('wants_suite', sa.Boolean(), server_default='False', nullable=False),
    sa.Column('earliest_suite_checkin_date', Date(), nullable=True),
    sa.Column('latest_suite_checkin_date', Date(), nullable=True),
    sa.Column('earliest_suite_checkout_date', Date(), nullable=True),
    sa.Column('latest_suite_checkout_date', Date(), nullable=True),
    sa.Column('suite_type_preference', sa.Unicode(), server_default='', nullable=False),
    sa.Column('suite_selection_priorities', sa.Unicode(), server_default='', nullable=False),
    sa.Column('terms_accepted', sa.Boolean(), server_default='False', nullable=False),
    sa.Column('suite_terms_accepted', sa.Boolean(), server_default='False', nullable=False),
    sa.ForeignKeyConstraint(['attendee_id'], ['attendee.id'], name=op.f('fk_lottery_application_attendee_id_attendee')),
    sa.ForeignKeyConstraint(['parent_application_id'], ['lottery_application.id'], name=op.f('fk_lottery_application_parent_application_id_lottery_application')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_lottery_application'))
    )


def downgrade():
    op.drop_table('lottery_application')
