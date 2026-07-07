from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class FreightInvoiceSchema(BaseModel):
    tracking_id: str
    total_charge: float
    currency: str
    fuel_surcharge: float
    base_freight_rate: float


class AuditResult(BaseModel):
    tracking_id: str
    client_id: str
    total_charge: float
    currency: str
    fuel_surcharge: float
    base_freight_rate: float
    overcharge_amount: float = 0.0
    fee_earned: float = 0.0
    status: str = "PROCESSING"
    dispute_sent: bool = False


class DisputeResult(BaseModel):
    audit_id: int
    tracking_id: str
    overcharge: float
    fee_earned: float
    status: str
    dispute_sent: bool
