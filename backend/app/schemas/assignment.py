from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from app.models.assignment import AssignmentStatusEnum


class OfficerAssignmentBase(BaseModel):
    officer_id: UUID
    zone_id: UUID
    task_description: str


class OfficerAssignmentCreate(OfficerAssignmentBase):
    pass


class OfficerAssignmentStatusUpdate(BaseModel):
    status: AssignmentStatusEnum


class OfficerAssignmentResponse(OfficerAssignmentBase):
    id: UUID
    status: AssignmentStatusEnum
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
