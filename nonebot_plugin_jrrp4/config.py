from typing import List

from pydantic import BaseModel, Field


class Config(BaseModel):
    jrrp_high_list: List[str] = Field(default_factory=list)
    jrrp_low_list: List[str] = Field(default_factory=list)
