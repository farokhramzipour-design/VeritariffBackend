"""invoice validation tasks and columns

Revision ID: 0003_invoice_validation
Revises: 0002_invoices
Create Date: 2026-02-02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_invoice_validation"
down_revision = "0002_invoices"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # invoices table updates
    op.alter_column("invoices", "vendor_name", new_column_name="supplier_name")
    op.add_column("invoices", sa.Column("incoterm", sa.String(length=10), nullable=True))
    op.add_column("invoices", sa.Column("total_value", sa.Numeric(18, 6), nullable=True))
    op.add_column("invoices", sa.Column("freight_cost", sa.Numeric(18, 6), nullable=True))
    op.add_column("invoices", sa.Column("insurance_cost", sa.Numeric(18, 6), nullable=True))
    op.add_column("invoices", sa.Column("status", sa.String(length=32), nullable=False, server_default="DRAFT"))
    op.add_column("invoices", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))

    # rename invoice_items -> invoice_line_items
    op.rename_table("invoice_items", "invoice_line_items")
    op.add_column("invoice_line_items", sa.Column("extracted_hs_code", sa.String(length=20), nullable=True))
    op.add_column("invoice_line_items", sa.Column("validated_hs_code", sa.String(length=20), nullable=True))
    op.add_column("invoice_line_items", sa.Column("hs_confidence", sa.Numeric(5, 3), nullable=True))
    op.add_column("invoice_line_items", sa.Column("metadata_jsonb", sa.JSON(), nullable=True))

    op.create_table(
        "validation_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("line_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("task_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("payload_jsonb", sa.JSON(), nullable=True),
        sa.Column("resolution_jsonb", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["line_item_id"], ["invoice_line_items.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("validation_tasks")
    op.drop_column("invoice_line_items", "metadata_jsonb")
    op.drop_column("invoice_line_items", "hs_confidence")
    op.drop_column("invoice_line_items", "validated_hs_code")
    op.drop_column("invoice_line_items", "extracted_hs_code")
    op.rename_table("invoice_line_items", "invoice_items")

    op.drop_column("invoices", "updated_at")
    op.drop_column("invoices", "status")
    op.drop_column("invoices", "insurance_cost")
    op.drop_column("invoices", "freight_cost")
    op.drop_column("invoices", "total_value")
    op.drop_column("invoices", "incoterm")
    op.alter_column("invoices", "supplier_name", new_column_name="vendor_name")
