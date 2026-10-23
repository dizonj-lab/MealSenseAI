"""User-entered (measured) glucose readings

Revision ID: 0003
Revises: 0002
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "glucose_readings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("meal_id", sa.Integer, sa.ForeignKey("meals.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("value_mmol", sa.Float, nullable=False),
        sa.Column("entered_unit", sa.String(10), nullable=False),
        sa.Column("context", sa.String(20), nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("note", sa.String(200)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("glucose_readings")
