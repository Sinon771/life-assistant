import httpx
import json
from typing import Dict, Any, Optional
from app.config import get_settings

settings = get_settings()

SYSTEM_PROMPT_TIME_PARSE = """你是一个生活助手的时间解析专家。用户会用自然语言描述提醒需求，你需要精确解析成结构化数据。

当前时间: {current_time}
用户时区: {timezone}

你必须返回**严格合法**的JSON，格式如下：
{{
    "intent": "create_reminder" | "snooze" | "cancel" | "query" | "chat",
    "title": "提醒标题，简短明确",
    "description": "详细描述，可选",
    "trigger_at": "ISO 8601 格式的时间字符串，如 2024-01-15T14:30:00+08:00",
    "repeat_rule": null | "daily" | "weekly" | "weekdays" | "weekends" | "custom:CRON表达式",
    "repeat_end_at": null | "ISO 8601 结束时间",
    "snooze_minutes": null | 数字,
    "cancel_reminder_id": null | 数字,
    "confidence": 0.0-1.0,
    "reply_message": "给用户的自然语言回复"
}}

解析规则：
1. "两分钟后提醒我喝水" → trigger_at是当前时间+2分钟，title="喝水"
2. "每天早上8点提醒我喝水" → repeat_rule="daily", trigger_at设置为最近的明天8点（如果今天8点已过）或今天8点
3. "每周一早上9点开会" → repeat_rule="weekly", trigger_at设置为下一个周一9点
4. "工作日每天早上提醒我打卡" → repeat_rule="weekdays"
5. "推迟10分钟" → intent="snooze", snooze_minutes=10
6. "取消刚才的提醒" → intent="cancel"
7. "我有什么待办" → intent="query"
8. 纯聊天 → intent="chat"

注意：
- 如果用户说"明天"，指的是明天的同一时间点
- "后天"是后天同一时间点
- "下周三"是下一个周三
- "半小时后" = 30分钟后
- "一刻钟后" = 15分钟后
- "一刻" = 15分钟

只返回JSON，不要任何其他文字。"""


class LLMService:
    def __init__(self):
        self.provider = settings.llm_provider
        if self.provider == "siliconflow":
            self.api_key = settings.siliconflow_api_key
            self.base_url = settings.siliconflow_base_url
            self.model = settings.siliconflow_model
        else:
            self.api_key = settings.kimi_api_key
            self.base_url = settings.kimi_base_url
            self.model = settings.kimi_model
    
    async def chat(self, messages: list, temperature: float = 0.3) -> str:
        """通用聊天接口"""
        if not self.api_key:
            raise ValueError(f"API key not configured for provider: {self.provider}")
        
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 2048
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
    
    async def parse_time_intent(
        self, 
        user_message: str, 
        current_time: str,
        timezone: str = "Asia/Shanghai",
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """解析用户消息中的时间和意图"""
        system_prompt = SYSTEM_PROMPT_TIME_PARSE.format(
            current_time=current_time,
            timezone=timezone
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
        ]
        
        if context:
            messages.append({"role": "system", "content": f"上下文：{context}"})
        
        messages.append({"role": "user", "content": user_message})
        
        try:
            content = await self.chat(messages, temperature=0.1)
            # 清理可能的 markdown 代码块
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            result = json.loads(content)
            return result
        except json.JSONDecodeError:
            return {
                "intent": "chat",
                "reply_message": "抱歉，我没理解您的意思，可以再说一次吗？",
                "confidence": 0.0
            }
        except Exception as e:
            return {
                "intent": "chat", 
                "reply_message": f"服务暂时出错了: {str(e)}",
                "confidence": 0.0
            }
    
    async def generate_chat_reply(
        self, 
        messages: list,
        system_prompt: Optional[str] = None
    ) -> str:
        """生成普通聊天回复"""
        chat_messages = []
        if system_prompt:
            chat_messages.append({"role": "system", "content": system_prompt})
        chat_messages.extend(messages)
        return await self.chat(chat_messages, temperature=0.7)


llm_service = LLMService()
