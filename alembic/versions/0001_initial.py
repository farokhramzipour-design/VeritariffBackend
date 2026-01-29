"""initial

Revision ID: 0001_initial
Revises: 
Create Date: 2026-01-28
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE planenum AS ENUM ('free', 'pro'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
    )
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE accounttypeenum AS ENUM ('free', 'uk_exporter', 'forwarder', 'eu_member', 'admin'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
    )
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE statusenum AS ENUM ('active', 'pending', 'blocked'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
    )
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE authproviderenum AS ENUM ('google', 'microsoft'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
    )
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE invitestatusenum AS ENUM ('pending', 'accepted', 'expired', 'cancelled'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
    )

    plan_enum = postgresql.ENUM("free", "pro", name="planenum", create_type=False)
    account_enum = postgresql.ENUM("free", "uk_exporter", "forwarder", "eu_member", "admin", name="accounttypeenum", create_type=False)
    status_enum = postgresql.ENUM("active", "pending", "blocked", name="statusenum", create_type=False)
    auth_enum = postgresql.ENUM("google", "microsoft", name="authproviderenum", create_type=False)
    invite_enum = postgresql.ENUM("pending", "accepted", "expired", "cancelled", name="invitestatusenum", create_type=False)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=True),
        sa.Column("last_name", sa.String(length=100), nullable=True),
        sa.Column("plan", plan_enum, nullable=False),
        sa.Column("account_type", account_enum, nullable=False),
        sa.Column("status", status_enum, nullable=False),
        sa.Column("auth_provider", auth_enum, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "companies_uk",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_number", sa.String(length=50), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("company_status", sa.String(length=50), nullable=False),
        sa.Column("registered_office_address", sa.JSON(), nullable=True),
        sa.Column("sic_codes", sa.JSON(), nullable=True),
        sa.Column("vat_number", sa.String(length=50), nullable=True),
        sa.Column("eori_number", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id"),
    )

    op.create_table(
        "teams",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("seat_limit", sa.Integer(), nullable=False),
        sa.Column("seat_used", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="SET NULL"),
    )

    op.create_table(
        "team_memberships",
        sa.Column("team_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("role_in_team", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "shipments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="SET NULL"),
    )

    op.create_table(
        "shipment_forwarders",
        sa.Column("shipment_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.ForeignKeyConstraint(["shipment_id"], ["shipments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "buyers_eu",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("shipment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("country_code", sa.String(length=5), nullable=False),
        sa.Column("vat_number", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("address", sa.JSON(), nullable=True),
        sa.Column("is_vat_valid", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["shipment_id"], ["shipments.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("shipment_id"),
    )

    op.create_table(
        "forwarder_invites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", invite_enum, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_forwarder_invites_email", "forwarder_invites", ["email"])
    op.create_unique_constraint("uq_forwarder_invites_token", "forwarder_invites", ["token_hash"])

    op.create_table(
        "oauth_states",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("state_hash", sa.String(length=128), nullable=False),
        sa.Column("nonce", sa.String(length=128), nullable=True),
        sa.Column("redirect_uri", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_unique_constraint("uq_oauth_states_hash", "oauth_states", ["state_hash"])

    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_unique_constraint("uq_refresh_tokens_hash", "refresh_tokens", ["token_hash"])


def downgrade() -> None:
    op.drop_table("refresh_tokens")
    op.drop_table("oauth_states")
    op.drop_table("forwarder_invites")
    op.drop_table("buyers_eu")
    op.drop_table("shipment_forwarders")
    op.drop_table("shipments")
    op.drop_table("team_memberships")
    op.drop_table("teams")
    op.drop_table("companies_uk")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    sa.Enum(name="invitestatusenum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="authproviderenum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="statusenum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="accounttypeenum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="planenum").drop(op.get_bind(), checkfirst=True)
