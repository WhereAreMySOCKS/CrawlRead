from pydantic import BaseModel,Field


class TranslationRequest(BaseModel):
    q: str = Field(..., description="待翻译文本")
    from_lang: str = Field("auto", description="源语言，默认 auto 自动检测")
    to_lang: str = Field(..., description="目标语言，必须指定")

class TranslationResponse(BaseModel):
    success: bool
    src_text: str
    dst_text: str

