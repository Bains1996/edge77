from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class FreightInvoiceSchema(BaseModel):
    tracking_id: str
    total_charge: float
    currency: str
    fuel_surcharge: float
    base_freight_rate: float
    carrier_name: str = ""
    accessorial_charges: float = 0.0
    accessorial_description: str = ""
    billed_weight: float = 0.0
    freight_class: str = ""
    declared_value: float = 0.0
    num_pieces: int = 0
    num_pallets: int = 0
    distance_miles: float = 0.0
    discount_pct: float = 0.0
    insurance_charge: float = 0.0
    tax_amount: float = 0.0
    pickup_date: str = ""
    delivery_date: str = ""


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
