"""Training-data governance: admin role, email verification, per-sample consent and screening, audit log,
dataset versions, model candidates, admin-editable settings and prompts

Revision ID: 0007
Revises: 0006
"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("is_admin", sa.Boolean, nullable=False, server_default=sa.false()))
    op.add_column("users", sa.Column("email_verified_at", sa.DateTime(timezone=True)))
    op.add_column("users", sa.Column("contributor_status", sa.String(20), nullable=False, server_default="active"))

    for name, col in (
        ("consent_at", sa.Column("consent_at", sa.DateTime(timezone=True))),
        ("withdrawn_at", sa.Column("withdrawn_at", sa.DateTime(timezone=True))),
        ("status", sa.Column("status", sa.String(20), nullable=False, server_default="pending")),
        ("reasons", sa.Column("reasons", sa.JSON, nullable=False, server_default="[]")),
        ("audit", sa.Column("audit", sa.Boolean, nullable=False, server_default=sa.false())),
        ("model_candidates", sa.Column("model_candidates", sa.JSON, nullable=False, server_default="[]")),
        ("image_sha256", sa.Column("image_sha256", sa.String(64))),
        ("phash", sa.Column("phash", sa.String(16))),
        ("screened_at", sa.Column("screened_at", sa.DateTime(timezone=True))),
        ("reviewed_by", sa.Column("reviewed_by", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL"))),
        ("reviewed_at", sa.Column("reviewed_at", sa.DateTime(timezone=True))),
        ("review_note", sa.Column("review_note", sa.String(300))),
    ):
        op.add_column("training_samples", col)
    op.create_index("ix_training_samples_status", "training_samples", ["status"])
    op.create_index("ix_training_samples_label", "training_samples", ["label"])
    op.create_index("ix_training_samples_image_sha256", "training_samples", ["image_sha256"])

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("actor_id", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL"), index=True),
        sa.Column("action", sa.String(60), nullable=False),
        sa.Column("target_type", sa.String(40)),
        sa.Column("target_id", sa.String(80)),
        sa.Column("detail", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, index=True),
    )
    op.create_table(
        "dataset_versions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(60), nullable=False, unique=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("parent_id", sa.Integer, sa.ForeignKey("dataset_versions.id", ondelete="SET NULL")),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("notes", sa.String(500)),
        sa.Column("manifest", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "model_candidates",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(60), nullable=False, unique=True),
        sa.Column("dataset_version_id", sa.Integer, sa.ForeignKey("dataset_versions.id", ondelete="SET NULL")),
        sa.Column("report", sa.JSON, nullable=False),
        sa.Column("gate", sa.JSON, nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("shadow", sa.JSON, nullable=False),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("decided_by", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column("note", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(80), primary_key=True),
        sa.Column("value", sa.JSON),
        sa.Column("updated_by", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "prompt_versions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("key", sa.String(60), nullable=False, index=True),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("note", sa.String(300)),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("key", "version"),
    )
    # Consent given before this release covered the samples already recorded, so they keep it.
    op.execute("UPDATE training_samples SET consent_at = training_samples.created_at FROM users "
               "WHERE users.id = training_samples.user_id AND users.training_consent")


def downgrade():
    op.drop_table("prompt_versions")
    op.drop_table("app_settings")
    op.drop_table("model_candidates")
    op.drop_table("dataset_versions")
    op.drop_table("audit_log")
    for ix in ("ix_training_samples_image_sha256", "ix_training_samples_label", "ix_training_samples_status"):
        op.drop_index(ix, "training_samples")
    for c in ("review_note", "reviewed_at", "reviewed_by", "screened_at", "phash", "image_sha256", "model_candidates",
              "audit", "reasons", "status", "withdrawn_at", "consent_at"):
        op.drop_column("training_samples", c)
    for c in ("contributor_status", "email_verified_at", "is_admin"):
        op.drop_column("users", c)
