import re
from typing import List, Dict, Optional

from app.services.llm.llm_client import LLMClient, LLMResponse
from utils.logger_util import logger


class LLMTextAnalysisService:
    """
    根据文本长度自动选择模板：
    1. 单词：words.j2
    2. 段落：paragraph.j2
    3. 全文：fulltext.j2
    """

    def __init__(self):
        self.client = LLMClient()

    # ---------- 私有工具 ----------
    @staticmethod
    def _classify(text: str) -> str:
        """
        分类逻辑：
        - 单词：纯英文/数字/连字符，且不含空格，长度 ≤ 30
        - 段落：1-5 句（以中文句号/英文句号/问号/感叹号分割）
        - 全文：其余情况
        """
        text = text.strip()
        if re.fullmatch(r"[A-Za-z0-9\-]{1,30}", text):
            return "words"
        else:
            return "paragraph"

    async def analyze(
        self,
        text: str,
        text_category : str = None,
        history: Optional[List[Dict[str, str]]] = None,
        **openai_kwargs,
    ) -> tuple[str, LLMResponse]:
        """
        text: 用户输入
        history: 可选对话历史 [{"role":"user","content":""}, ...]
        openai_kwargs: 透传给 LLMClient.chat，如 temperature、max_tokens
        """
        template_map = {
            "words": "words.j2",
            "paragraph": "paragraph.j2",
            "reading": "reading.j2",
        }

        _category = self._classify(text) if text_category is None or text_category == '' else text_category
        template = template_map[_category]
        logger.info(f"[LLMTextAnalysisService] 文本类别={_category}, 模板={template}")

        return _category,self.client.chat(
            template_name=template,
            variables={"text": text},
            history=history or [],
            **openai_kwargs,
        )