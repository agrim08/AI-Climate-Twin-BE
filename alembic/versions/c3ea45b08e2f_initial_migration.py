"""initial migration

Revision ID: c3ea45b08e2f
Revises: 
Create Date: 2026-06-17 19:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c3ea45b08e2f'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create districts table
    op.create_table(
        'districts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('state', sa.String(length=100), nullable=False),
        sa.Column('district_name', sa.String(length=100), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_districts_id', 'districts', ['id'], unique=False)
    op.create_index('ix_districts_state', 'districts', ['state'], unique=False)
    op.create_index('ix_districts_district_name', 'districts', ['district_name'], unique=False)

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('role', sa.Enum('admin', 'researcher', 'citizen', name='user_role'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # Create climate_observations table
    op.create_table(
        'climate_observations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('district_id', sa.Integer(), nullable=False),
        sa.Column('rainfall', sa.Float(), nullable=False),
        sa.Column('temperature', sa.Float(), nullable=False),
        sa.Column('humidity', sa.Float(), nullable=False),
        sa.Column('observation_date', sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(['district_id'], ['districts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_climate_observations_id', 'climate_observations', ['id'], unique=False)
    op.create_index('ix_climate_obs_district_date', 'climate_observations', ['district_id', 'observation_date'], unique=False)

    # Create forecasts table
    op.create_table(
        'forecasts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('district_id', sa.Integer(), nullable=False),
        sa.Column('predicted_rainfall', sa.Float(), nullable=False),
        sa.Column('predicted_temperature', sa.Float(), nullable=False),
        sa.Column('forecast_date', sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(['district_id'], ['districts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_forecasts_id', 'forecasts', ['id'], unique=False)
    op.create_index('ix_forecasts_district_date', 'forecasts', ['district_id', 'forecast_date'], unique=False)

    # Create simulation_results table
    op.create_table(
        'simulation_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('district_id', sa.Integer(), nullable=False),
        sa.Column('rainfall_change', sa.Float(), nullable=False),
        sa.Column('temperature_change', sa.Float(), nullable=False),
        sa.Column('humidity_change', sa.Float(), nullable=False),
        sa.Column('result_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['district_id'], ['districts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_simulation_results_id', 'simulation_results', ['id'], unique=False)
    op.create_index('ix_sim_results_district_id', 'simulation_results', ['district_id'], unique=False)
    op.create_index('ix_sim_results_user_id', 'simulation_results', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_sim_results_user_id', table_name='simulation_results')
    op.drop_index('ix_sim_results_district_id', table_name='simulation_results')
    op.drop_index('ix_simulation_results_id', table_name='simulation_results')
    op.drop_table('simulation_results')
    
    op.drop_index('ix_forecasts_district_date', table_name='forecasts')
    op.drop_index('ix_forecasts_id', table_name='forecasts')
    op.drop_table('forecasts')
    
    op.drop_index('ix_climate_obs_district_date', table_name='climate_observations')
    op.drop_index('ix_climate_observations_id', table_name='climate_observations')
    op.drop_table('climate_observations')
    
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')
    
    # Drop enum type associated with users.role
    sa.Enum(name='user_role').drop(op.get_bind(), checkfirst=False)

    op.drop_index('ix_districts_district_name', table_name='districts')
    op.drop_index('ix_districts_state', table_name='districts')
    op.drop_index('ix_districts_id', table_name='districts')
    op.drop_table('districts')
