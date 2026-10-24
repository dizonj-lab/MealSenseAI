"""Custom foods, labelled training samples (memory + next training cycle), training consent

Revision ID: 0004
Revises: 0003
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("training_consent", sa.Boolean, nullable=False, server_default=sa.false()))
    op.create_table(
        "custom_foods",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("serving_g", sa.Float, nullable=False),
        sa.Column("serving_desc", sa.String(80), nullable=False),
        sa.Column("per_100g", sa.JSON, nullable=False),
        sa.Column("glycemic_index", sa.Float),
        sa.Column("aliases", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "training_samples",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("meal_id", sa.Integer, sa.ForeignKey("meals.id", ondelete="CASCADE"), index=True),
        sa.Column("food_id", sa.Integer, unique=True),
        sa.Column("view", sa.String(10), nullable=False),
        sa.Column("image_path", sa.String(500), nullable=False),
        sa.Column("bbox", sa.JSON),
        sa.Column("label", sa.String(120), nullable=False),
        sa.Column("nutrition_key", sa.String(80)),
        sa.Column("taxonomy_class", sa.String(120)),
        sa.Column("custom_food_id", sa.Integer, sa.ForeignKey("custom_foods.id", ondelete="SET NULL")),
        sa.Column("model_label", sa.String(120)),
        sa.Column("model_score", sa.Float),
        sa.Column("fingerprint", sa.JSON, nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("model_version", sa.String(80)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("training_samples")
    op.drop_table("custom_foods")
    op.drop_column("users", "training_consent")
