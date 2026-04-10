from pydantic import BaseModel, field_validator


class OrderRequest(BaseModel):
    item: str
    loyalty_card: bool = False

    @field_validator("item")
    @classmethod
    def item_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("item must not be blank")
        return v.strip()


class OrderResponse(BaseModel):
    id: int
    item: str
    price: float
    points: int
    status: str


class DownstreamOrderPayload(BaseModel):
    """Payload forwarded to the Go order service."""

    item: str
    price: float
    loyalty_card: bool
