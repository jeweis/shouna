import base64
import logging
from typing import Optional

import httpx

from app.schemas.ai import AIAnalyzedResult

logger = logging.getLogger(__name__)

class BaseAIClient:
    """
    轻量化 AI 图像分析客户端抽象基类
    """
    async def analyze_image(self, image_bytes: bytes) -> Optional[AIAnalyzedResult]:
        """
        异步分析上传的物品图片，并返回 Pydantic 结构化识别数据。
        """
        raise NotImplementedError("analyze_image 方法必须在子类中实现")

    def _get_image_base64(self, image_bytes: bytes) -> str:
        """
        辅助方法：将图片的二进制字节流转换为 Base64 编码字符串。
        """
        return base64.b64encode(image_bytes).decode("utf-8")


class OpenAICompatibleClient(BaseAIClient):
    """
    基于 OpenAI 协议兼容的轻量化 AI 客户端（原生 HTTPX 异步调用）
    """
    def __init__(self, api_key: str, base_url: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key
        # 默认使用 OpenAI 官方端点
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        # 默认使用具有优秀性价比的 vision 兼容模型
        self.model = model or "gpt-4o-mini"

    async def analyze_image(self, image_bytes: bytes) -> Optional[AIAnalyzedResult]:
        img_b64 = self._get_image_base64(image_bytes)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # 构建标准的 Pydantic JSON Schema 提取提示
        prompt = (
            "分析这张物品的照片，并返回一个合法的 JSON 数据，绝不能有 ```json 代码块等格式标记，只能返回纯 JSON。"
            "必须包含以下五个 JSON 键：\n"
            "1. 'name': 识别出的具体物品名称（字符串，如：灰色针织羊毛开衫、蓝色金属保温杯）。\n"
            "2. 'description': 物品外观或用途的简短描述（字符串，如：灰色厚针织材质，适合冬季保暖）。\n"
            "3. 'suggested_location': 建议存放的空间名字（字符串，如：衣柜、厨房台面、书桌）。\n"
            "4. 'tags': 提取的分类与特性标签列表（字符串数组，如：['衣服', '针织衫', '灰色', '冬季']）。\n"
            "5. 'confidence': 识别的置信度评分（浮点数，0.0 到 1.0 之间）。"
        )

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}
                        }
                    ]
                }
            ],
            "temperature": 0.1
        }

        # 尝试启用 structured output (部分支持 response_format 的 OpenAI 兼容接口，如 GPT-4o)
        if "gpt-4o" in self.model.lower():
            payload["response_format"] = {"type": "json_object"}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                res_data = response.json()

                content = res_data["choices"][0]["message"]["content"].strip()

                # 清除可能的大模型 markdown json 标记包围
                if content.startswith("```"):
                    lines = content.splitlines()
                    if lines[0].startswith("```json"):
                        content = "\n".join(lines[1:-1])
                    else:
                        content = "\n".join(lines[1:-1])

                # 校验并解析成 Pydantic 模型
                return AIAnalyzedResult.model_validate_json(content)
        except Exception as e:
            logger.error(f"OpenAICompatibleClient 调用图像识别失败: {str(e)}")
            return None


class AnthropicCompatibleClient(BaseAIClient):
    """
    基于 Anthropic Claude 协议的轻量化 AI 客户端（使用 HTTPX 原生异步 Messages API）
    """
    def __init__(self, api_key: str, base_url: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key
        # 默认使用 Anthropic 官方 Messages 端点
        self.base_url = (base_url or "https://api.anthropic.com/v1").rstrip("/")
        # 默认使用最优秀的 Claude 3.5 Sonnet 模型
        self.model = model or "claude-3-5-sonnet-latest"

    async def analyze_image(self, image_bytes: bytes) -> Optional[AIAnalyzedResult]:
        img_b64 = self._get_image_base64(image_bytes)

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        # 构建标准的 Pydantic JSON Schema 提取提示
        prompt = (
            "分析这张物品的照片，并在最后只返回一个合法的 JSON 数据，决不能有 ```json 代码块等格式标记，只能返回纯 JSON。"
            "必须包含以下五个 JSON 键：\n"
            "1. 'name': 识别出的具体物品名称（字符串，如：灰色针织羊毛开衫、蓝色金属保温杯）。\n"
            "2. 'description': 物品外观或用途的简短描述（字符串，如：灰色厚针织材质，适合冬季保暖）。\n"
            "3. 'suggested_location': 建议存放的空间名字（字符串，如：衣柜、厨房台面、书桌）。\n"
            "4. 'tags': 提取的分类与特性标签列表（字符串数组，如：['衣服', '针织衫', '灰色', '冬季']）。\n"
            "5. 'confidence': 识别的置信度评分（浮点数，0.0 到 1.0 之间）。"
        )

        payload = {
            "model": self.model,
            "max_tokens": 1000,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": img_b64
                            }
                        },
                        {"type": "text", "text": prompt}
                    ]
                }
            ],
            "temperature": 0.1
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/messages",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                res_data = response.json()

                # Anthropic 返回的是 content 数组的第一个 text 块
                content = res_data["content"][0]["text"].strip()

                # 清除可能的大模型 markdown json 标记包围
                if content.startswith("```"):
                    lines = content.splitlines()
                    if lines[0].startswith("```json"):
                        content = "\n".join(lines[1:-1])
                    else:
                        content = "\n".join(lines[1:-1])

                return AIAnalyzedResult.model_validate_json(content)
        except Exception as e:
            logger.error(f"AnthropicCompatibleClient 调用图像识别失败: {str(e)}")
            return None


def get_ai_client() -> Optional[BaseAIClient]:
    """
    根据 app settings 自动工厂化加载对应的 AI 图像分析客户端。
    """
    from app.core.config import settings

    if not settings.AI_API_KEY:
        return None

    provider = (settings.AI_PROVIDER or "openai").lower()
    if provider == "openai":
        return OpenAICompatibleClient(
            api_key=settings.AI_API_KEY,
            base_url=settings.AI_BASE_URL,
            model=settings.AI_MODEL
        )
    elif provider == "anthropic":
        return AnthropicCompatibleClient(
            api_key=settings.AI_API_KEY,
            base_url=settings.AI_BASE_URL,
            model=settings.AI_MODEL
        )
    else:
        logger.warning(f"未知的 AI Provider 厂商配置: {settings.AI_PROVIDER}")
        return None
