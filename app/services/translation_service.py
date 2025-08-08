import hashlib
import random
import httpx
from typing import Dict, Any

from app.core.config import get_api_config
from app.models.api_models import TranslationRequest
from utils.logger_util import logger


class TranslationService:
    def __init__(self):
        baidu_trans_config = get_api_config().get("baidu_translate", {})
        dictionaryapi_url = get_api_config().get("dictionaryapi", {})
        self.app_id = baidu_trans_config.get("app_id")
        self.app_key = baidu_trans_config.get("app_key")
        self.baidu_api_url = baidu_trans_config.get("api_url")
        self.dictionaryapi_url = dictionaryapi_url.get("api_url")

        if not self.app_id or not self.app_key or not self.baidu_api_url or not self.dictionaryapi_url:
            raise ValueError("配置缺失，请检查 config.yaml 的 api 配置")


    @staticmethod
    def _generate_sign(app_id: str, query: str, salt: str, app_key: str) -> str:
        sign_str = f"{app_id}{query}{salt}{app_key}"
        return hashlib.md5(sign_str.encode("utf-8")).hexdigest()

    async def baidu_translate(self, tans_req:TranslationRequest) -> Dict[str, Any]:
        try:
            salt = str(random.randint(32768, 65536))
            sign = self._generate_sign(self.app_id, tans_req.q, salt, self.app_key)

            params = {
                "q": tans_req.q,
                "from": tans_req.from_lang,
                "to": tans_req.to_lang,
                "appid": self.app_id,
                "salt": salt,
                "sign": sign
            }

            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(self.baidu_api_url, data=params)
                resp.raise_for_status()
                data = resp.json()

            if "error_code" in data:
                return {"success": False, "error": data.get("error_msg", "未知错误"), "code": data["error_code"]}

            return {
                "success": True,
                "from": data.get("from"),
                "to": data.get("to"),
                "result": [item.get("dst") for item in data.get("trans_result", [])]
            }

        except Exception as e:
            logger.exception(f"调用百度翻译失败: {e}")
            return {"success": False, "error": str(e)}

    import httpx
    import logging

    logger = logging.getLogger(__name__)

    async def dictionaryapi_translate(self, word: str):
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(f"{self.dictionaryapi_url}/{word}")
                resp.raise_for_status()
                try:
                    data = resp.json()
                    # 处理返回数据（可能是单词列表）
                    if isinstance(data, list):
                        for entry in data:
                            self._process_dictionary_entry(entry)
                    return data
                except ValueError:
                    logger.error("JSON 解析失败：响应不是有效的 JSON")
                    return {"error": "Invalid JSON format"}
        except Exception as e:
            logger.error(f"字典API请求失败: {str(e)}")
            return {"error": "API request failed"}

    def _process_dictionary_entry(self, entry: dict):
        """处理单个词典条目"""
        # 删除顶层 phonetic 字段
        if "phonetic" in entry:
            del entry["phonetic"]

        # 处理 phonetics 数组
        if "phonetics" in entry and isinstance(entry["phonetics"], list):
            phonetics = entry["phonetics"]
            selected_phonetic = None

            # 查找美式发音
            for item in phonetics:
                audio = item.get("audio", "").lower()
                if "us" in audio:  # 检查是否包含美式标识
                    selected_phonetic = item
                    break

            # 没有美式则取第一个
            if not selected_phonetic and phonetics:
                selected_phonetic = phonetics[0]

            # 更新 phonetics 数组
            entry["phonetics"] = [selected_phonetic] if selected_phonetic else []

    async def translate(self, req: TranslationRequest):
        if len(req.q.split()) == 1:
            # 如果是单个单词，调用开源词典
            return await self.dictionaryapi_translate(req.q)
        else:
            # 否则使用百度翻译
            return await self.baidu_translate(req)


