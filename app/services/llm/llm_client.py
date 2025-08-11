import json
import re
import fcntl
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from openai import OpenAI

from app.core.config import get_api_config
from app.models.api_models import LLMResponse
from utils.logger_util import logger


class FileLock:
    """使用 fcntl 实现的跨进程文件锁"""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.file = None

    def __enter__(self):
        self.file = open(self.file_path, 'a+')
        # 获取排他锁，非阻塞模式
        try:
            fcntl.flock(self.file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            logger.warning(f"文件 {self.file_path} 已被锁定，等待...")
            # 阻塞模式等待锁
            fcntl.flock(self.file, fcntl.LOCK_EX)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # 释放锁并关闭文件
        fcntl.flock(self.file, fcntl.LOCK_UN)
        self.file.close()
        self.file = None


class LLMClient:
    def __init__(self):
        self.config = get_api_config().get("Qwen", {})
        self.api_key = self.config.get("api_key")
        self.model_name = self.config.get("model_name", "qwen-plus")
        self.url = self.config.get("api_url")

        # 阈值默认值
        self.max_prompt_tokens = self.config.get("max_prompt_tokens", 100_000)
        self.max_completion_tokens = self.config.get("max_completion_tokens", 100_000)

        if not self.api_key or not self.url:
            raise ValueError("未配置 Qwen API Key 或 API URL")

        self.client = OpenAI(api_key=self.api_key, base_url=self.url)

        # 模板
        template_dir = Path(__file__).resolve().parent.parent.parent / "templates" / "prompt"
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(["html", "xml"]),
        )

        # 计数文件 & 锁
        self.counter_path = Path(__file__).parent.parent.parent / "db" / "token_counter.json"
        self.lock = FileLock(self.counter_path)

        # 确保计数器文件存在
        if not self.counter_path.exists():
            with self.lock:
                if not self.counter_path.exists():
                    self.counter_path.write_text(
                        json.dumps({}, indent=2, ensure_ascii=False),
                        encoding="utf-8"
                    )

    # ---------- 私有工具 ----------
    def _load_counter(self) -> dict:
        """
        多模型 token 统计读取。
        返回当前模型的记录: {"prompt": int, "completion": int}
        """
        with self.lock:
            try:
                data = json.loads(self.counter_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                logger.warning("token_counter.json 损坏，已重置")
                data = {}

            if self.model_name not in data:
                data[self.model_name] = {"prompt": 0, "completion": 0}
                self.counter_path.write_text(
                    json.dumps(data, indent=2, ensure_ascii=False),
                    encoding="utf-8"
                )

            return data[self.model_name]

    def _save_counter(self, prompt: int, completion: int):
        """多模型 token 统计写入，只更新当前模型"""
        with self.lock:
            try:
                data = json.loads(self.counter_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                data = {}

            if self.model_name not in data:
                data[self.model_name] = {"prompt": 0, "completion": 0}

            data[self.model_name]["prompt"] = prompt
            data[self.model_name]["completion"] = completion

            self.counter_path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            logger.debug(
                f"[{self.model_name}] 更新 token 计数：prompt={prompt}, completion={completion}"
            )

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """粗略估算 token"""
        chinese = len(re.findall(r"[\u4e00-\u9fff]", text))
        english = len(re.findall(r"\b\w+\b", text))
        return chinese + int(english * 1.3)

    # ---------- 主入口 ----------
    def chat(
            self,
            template_name: str,
            variables: dict = None,
            history: list = None,
            **openai_kwargs,
    ) -> LLMResponse:
        logger.info(
            f"开始调用 chat | template={template_name} | model={self.model_name}"
        )

        # 1. 模板渲染
        try:
            tpl = self.env.get_template(template_name)
        except Exception as e:
            logger.error(f"模板加载失败：{e}")
            return LLMResponse(error=f"无法加载模板 {template_name}: {e}")

        prompt_text = tpl.render(**(variables or {}))
        est_prompt = self._estimate_tokens(prompt_text)
        est_completion = est_prompt * 2

        # 2. 历史 token 估算
        if history:
            for h in history:
                est_prompt += self._estimate_tokens(h.get("content", ""))

        # 3. 阈值判断
        counter = self._load_counter()
        total_prompt = counter["prompt"] + est_prompt
        total_completion = counter["completion"] + est_completion

        prompt_ratio = total_prompt / self.max_prompt_tokens
        completion_ratio = total_completion / self.max_completion_tokens
        if prompt_ratio >= 0.95 or completion_ratio >= 0.95:
            msg = (
                f"{self.model_name} Token 阈值超限：prompt_ratio={prompt_ratio:.2f}, "
                f"completion_ratio={completion_ratio:.2f}"
            )
            logger.warning(msg)
            return LLMResponse(error=msg)

        # 4. 调用前再次确认 model_name 未被外部修改
        if self.config.get("model_name") != self.model_name:
            logger.error("model_name 在调用前被修改，强制终止")
            return LLMResponse(error="model_name 在调用前被修改，禁止调用")

        # 5. 构造消息
        messages = [{"role": "system", "content": "你是一个考研英语名师"}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt_text})

        logger.info(f"真正调用 OpenAI | messages\n：{messages}\n")

        # 6. 调用大模型
        try:
            resp = self.client.chat.completions.create(
                model=self.model_name, messages=messages, **openai_kwargs
            )
        except Exception as e:
            logger.exception("OpenAI 调用异常")
            return LLMResponse(error=str(e))

        # 7. 更新计数
        usage = resp.usage
        self._save_counter(
            counter["prompt"] + usage.prompt_tokens,
            counter["completion"] + usage.completion_tokens,
        )

        logger.info(
            f"调用完成 | prompt_tokens={usage.prompt_tokens}, "
            f"completion_tokens={usage.completion_tokens}"
        )

        return LLMResponse(
            content=resp.choices[0].message.content if resp.choices else None,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
        )