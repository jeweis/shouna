from typing import List, Optional
from pydantic import BaseModel, Field

class AIAnalyzedResult(BaseModel):
    name: str = Field(description="识别出的物品名称，如：灰色羊毛针织衫")
    description: Optional[str] = Field(default=None, description="物品外观或用途的简短描述")
    suggested_location: str = Field(description="建议归类的空间名称，如：衣柜")
    tags: List[str] = Field(default=[], description="提取的标签列表，如：['衣服', '保暖', '灰色', '冬季']")
    confidence: float = Field(0.9, description="置信度评分，0到1之间")
