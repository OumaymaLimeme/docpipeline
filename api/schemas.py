from datetime import datetime
from typing import Optional, List
from models import JobStatus

class JobOut(BaseModel):
    id:         str
    filename:   str
    file_type:  str
    status:     JobStatus
    result:     Optional[str] = None
    error:      Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class JobListOut(BaseModel):
    total: int
    page:  int
    limit: int
    jobs:  List[JobOut]
