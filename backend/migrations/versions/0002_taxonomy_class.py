"""EXP-002: record the taxonomy class chosen for each food (model prediction or user override)

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("meal_foods", sa.Column("taxonomy_class", sa.String(length=120), nullable=True))


def downgrade():
    op.drop_column("meal_foods", "taxonomy_class")
