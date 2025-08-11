from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


class TranslationRequest(BaseModel):
    q: str = Field(..., description="待翻译文本")
    from_lang: str = Field("auto", description="源语言，默认 auto 自动检测")
    to_lang: str = Field(..., description="目标语言，必须指定")

class TranslationResponse(BaseModel):
    success: bool
    src_text: str
    dst_text: str

@dataclass
class LLMResponse:
    content: Optional[str] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    error: Optional[str] = None

    def ok(self) -> bool:
        return self.error is None


class AnalyzeIn(BaseModel):
    text: str


class AnalyzeOut(BaseModel):
    content: str | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
