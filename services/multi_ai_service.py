#!/usr/bin/env python3
"""
Multi-Provider AI Service
Tránh giới hạn API bằng cách sử dụng nhiều nhà cung cấp và API keys
"""

import asyncio
import aiohttp
import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class AIProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    HUGGINGFACE = "huggingface"
    GROQ = "groq"
    TOGETHER = "together"
    REPLICATE = "replicate"
    OLLAMA = "ollama"
    LMSTUDIO = "lmstudio"

@dataclass
class APIKey:
    provider: AIProvider
    key: str
    name: str
    daily_limit: int = 1000
    hourly_limit: int = 100
    used_today: int = 0
    used_this_hour: int = 0
    last_used: Optional[datetime] = None
    is_active: bool = True
    error_count: int = 0

@dataclass
class AIRequest:
    prompt: str
    model: str = None
    max_tokens: int = 1000
    temperature: float = 0.7
    task_type: str = "chat"  # chat, image, embedding

class MultiAIService:
    """Service AI đa nhà cung cấp với khả năng tránh giới hạn"""
    
    def __init__(self):
        self.api_keys: List[APIKey] = []
        self.provider_configs = {
            AIProvider.OPENAI: {
                "chat_endpoint": "https://api.openai.com/v1/chat/completions",
                "image_endpoint": "https://api.openai.com/v1/images/generations",
                "models": ["gpt-3.5-turbo", "gpt-4", "dall-e-3", "dall-e-2"]
            },
            AIProvider.GROQ: {
                "chat_endpoint": "https://api.groq.com/openai/v1/chat/completions",
                "models": [
                    "llama-3.3-70b-versatile",  # Latest Llama 3.3 - recommended 
                    "llama-3.1-8b-instant",     # Fast 8B model
                    "gemma2-9b-it",             # Updated Gemma
                    "deepseek-r1-distill-llama-70b",  # Reasoning model
                    "deepseek-r1-distill-qwen-32b",   # Reasoning model
                    "qwen-qwq-32b",             # QwQ reasoning model
                    "meta-llama/llama-4-scout-17b-16e-instruct",    # NEW Llama 4!
                    "meta-llama/llama-4-maverick-17b-128e-instruct", # NEW Llama 4!
                    "mistral-saba-24b"          # Latest Mistral
                ]
            },
            AIProvider.TOGETHER: {
                "chat_endpoint": "https://api.together.xyz/v1/chat/completions",
                "models": ["meta-llama/Llama-3-70b-chat-hf", "mistralai/Mixtral-8x7B-Instruct-v0.1"]
            },
            AIProvider.HUGGINGFACE: {
                "chat_endpoint": "https://api-inference.huggingface.co/models/",
                "models": ["microsoft/DialoGPT-large", "facebook/blenderbot-400M-distill"]
            },
            AIProvider.OLLAMA: {
                "chat_endpoint": "http://localhost:11434/v1/chat/completions",
                "models_endpoint": "http://localhost:11434/api/tags",
                "models": ["llama3", "mistral", "codellama", "vicuna", "orca-mini"],
                "requires_api_key": False,
                "local": True
            },
            AIProvider.LMSTUDIO: {
                "chat_endpoint": "http://localhost:1234/v1/chat/completions",
                "models_endpoint": "http://localhost:1234/v1/models",
                "models": ["local-model"],  # Will be fetched dynamically
                "requires_api_key": False,
                "local": True
            }
        }
        self.request_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "provider_usage": {}
        }
        
    def add_api_keys(self, keys_config: List[Dict]):
        """Thêm nhiều API keys"""
        for config in keys_config:
            api_key = APIKey(
                provider=AIProvider(config["provider"]),
                key=config["key"],
                name=config.get("name", f"{config['provider']}_key"),
                daily_limit=config.get("daily_limit", 1000),
                hourly_limit=config.get("hourly_limit", 100)
            )
            self.api_keys.append(api_key)
            logger.info(f"✅ Added API key: {api_key.name}")
    
    def get_available_key(self, provider: AIProvider = None) -> Optional[APIKey]:
        """Lấy API key khả dụng theo provider hoặc tự động"""
        
        # Filter theo provider nếu có
        available_keys = [k for k in self.api_keys if k.is_active and k.error_count < 5]
        if provider:
            available_keys = [k for k in available_keys if k.provider == provider]
        
        if not available_keys:
            return None
            
        # Kiểm tra giới hạn thời gian
        now = datetime.now()
        valid_keys = []
        
        for key in available_keys:
            # Reset counters nếu đã qua ngày/giờ mới
            if key.last_used:
                if now.date() > key.last_used.date():
                    key.used_today = 0
                if now.hour > key.last_used.hour:
                    key.used_this_hour = 0
            
            # Kiểm tra limits
            if (key.used_today < key.daily_limit and 
                key.used_this_hour < key.hourly_limit):
                valid_keys.append(key)
        
        if not valid_keys:
            return None
            
        # Chọn key ít được sử dụng nhất
        return min(valid_keys, key=lambda k: k.used_today + k.used_this_hour)
    
    async def make_chat_request(self, request: AIRequest, preferred_provider: AIProvider = None) -> Dict:
        """Gửi yêu cầu chat với fallback system"""
        
        # Thử provider ưu tiên trước
        if preferred_provider:
            result = await self._try_provider_chat(request, preferred_provider)
            if result.get("success"):
                return result
        
        # Fallback qua các providers khác
        providers = [p for p in AIProvider if p != preferred_provider]
        random.shuffle(providers)  # Random order để phân tải
        
        for provider in providers:
            try:
                result = await self._try_provider_chat(request, provider)
                if result.get("success"):
                    return result
                    
                # Nghỉ một chút trước khi thử provider tiếp theo
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.warning(f"⚠️ Provider {provider.value} failed: {e}")
                continue
        
        # Tất cả providers đều fail
        self.request_stats["failed_requests"] += 1
        return {
            "success": False,
            "error": "All providers exhausted",
            "content": "Xin lỗi, tạm thời không thể xử lý yêu cầu. Vui lòng thử lại sau."
        }
    
    async def _try_provider_chat(self, request: AIRequest, provider: AIProvider) -> Dict:
        """Thử gửi request với một provider cụ thể"""
        
        # Check if provider needs API key
        config = self.provider_configs.get(provider)
        if not config:
            return {"success": False, "error": f"No config for {provider.value}"}
        
        api_key = None
        if config.get("requires_api_key", True):  # Default True for backward compatibility
            api_key = self.get_available_key(provider)
            if not api_key:
                return {"success": False, "error": f"No available key for {provider.value}"}
        
        try:
            headers = self._get_headers(provider, api_key.key if api_key else "")
            data = self._prepare_chat_data(request, provider)
            
            self.request_stats["total_requests"] += 1
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    config["chat_endpoint"],
                    headers=headers,
                    json=data,
                    timeout=30
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        content = self._extract_chat_content(result, provider)
                        
                        # Update usage stats only if we have an API key
                        if api_key:
                            api_key.used_today += 1
                            api_key.used_this_hour += 1
                            api_key.last_used = datetime.now()
                            api_key.error_count = 0  # Reset error count on success
                        
                        self.request_stats["successful_requests"] += 1
                        self._update_provider_stats(provider, True)
                        
                        provider_name = api_key.name if api_key else f"{provider.value}_local"
                        logger.info(f"✅ Success with {provider.value} ({provider_name})")
                        
                        return {
                            "success": True,
                            "content": content,
                            "provider": provider.value,
                            "model": data.get("model", "unknown")
                        }
                        
                    else:
                        error_data = await response.text()
                        
                        # Handle specific errors only if we have an API key
                        if api_key:
                            if response.status == 429:  # Rate limit
                                api_key.error_count += 1
                                logger.warning(f"⚠️ Rate limit hit for {provider.value}")
                            elif response.status == 401:  # Invalid key
                                api_key.is_active = False
                                logger.error(f"❌ Invalid API key for {provider.value}")
                        
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}: {error_data[:200]}"
                        }
                        
        except Exception as e:
            if api_key:
                api_key.error_count += 1
            self._update_provider_stats(provider, False)
            logger.error(f"❌ Error with {provider.value}: {e}")
            return {"success": False, "error": str(e)}
    
    def _get_headers(self, provider: AIProvider, api_key: str) -> Dict:
        """Tạo headers cho từng provider"""
        
        if provider == AIProvider.OPENAI:
            return {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
        elif provider == AIProvider.GROQ:
            return {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
        elif provider == AIProvider.TOGETHER:
            return {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
        elif provider == AIProvider.HUGGINGFACE:
            return {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
        elif provider in [AIProvider.OLLAMA, AIProvider.LMSTUDIO]:
            # Local providers don't need API keys
            return {"Content-Type": "application/json"}
        else:
            return {"Content-Type": "application/json"}
    
    def _prepare_chat_data(self, request: AIRequest, provider: AIProvider) -> Dict:
        """Chuẩn bị data cho từng provider"""
        
        # Chọn model phù hợp
        available_models = self.provider_configs[provider]["models"]
        model = request.model if request.model in available_models else available_models[0]
        
        if provider in [AIProvider.OPENAI, AIProvider.GROQ, AIProvider.TOGETHER, AIProvider.OLLAMA, AIProvider.LMSTUDIO]:
            return {
                "model": model,
                "messages": [{"role": "user", "content": request.prompt}],
                "max_tokens": request.max_tokens,
                "temperature": request.temperature
            }
        elif provider == AIProvider.HUGGINGFACE:
            return {
                "inputs": request.prompt,
                "parameters": {
                    "max_length": request.max_tokens,
                    "temperature": request.temperature
                }
            }
        else:
            return {"prompt": request.prompt}
    
    def _extract_chat_content(self, result: Dict, provider: AIProvider) -> str:
        """Trích xuất nội dung từ response của từng provider"""
        
        try:
            if provider in [AIProvider.OPENAI, AIProvider.GROQ, AIProvider.TOGETHER, AIProvider.OLLAMA, AIProvider.LMSTUDIO]:
                return result["choices"][0]["message"]["content"]
            elif provider == AIProvider.HUGGINGFACE:
                if isinstance(result, list) and len(result) > 0:
                    return result[0].get("generated_text", str(result[0]))
                return str(result)
            else:
                return str(result)
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"❌ Error extracting content from {provider.value}: {e}")
            return f"Response received but couldn't extract content: {str(result)[:200]}"
    
    def _update_provider_stats(self, provider: AIProvider, success: bool):
        """Cập nhật thống kê sử dụng provider"""
        
        if provider.value not in self.request_stats["provider_usage"]:
            self.request_stats["provider_usage"][provider.value] = {
                "success": 0, "failed": 0
            }
        
        if success:
            self.request_stats["provider_usage"][provider.value]["success"] += 1
        else:
            self.request_stats["provider_usage"][provider.value]["failed"] += 1
    
    def get_usage_stats(self) -> Dict:
        """Lấy thống kê sử dụng"""
        
        active_keys = len([k for k in self.api_keys if k.is_active])
        total_daily_usage = sum(k.used_today for k in self.api_keys)
        
        return {
            "total_api_keys": len(self.api_keys),
            "active_keys": active_keys,
            "total_daily_usage": total_daily_usage,
            "request_stats": self.request_stats,
            "key_details": [
                {
                    "name": k.name,
                    "provider": k.provider.value,
                    "used_today": k.used_today,
                    "daily_limit": k.daily_limit,
                    "is_active": k.is_active,
                    "error_count": k.error_count
                }
                for k in self.api_keys
            ]
        }
    
    def reset_daily_limits(self):
        """Reset daily limits (chạy hàng ngày)"""
        for key in self.api_keys:
            key.used_today = 0
            key.error_count = max(0, key.error_count - 1)  # Giảm error count
            if key.error_count == 0:
                key.is_active = True  # Reactive key nếu hết lỗi
        
        logger.info("🔄 Daily limits reset for all API keys")

# Sử dụng service
async def demo_multi_ai():
    """Demo sử dụng Multi-AI Service"""
    
    # Khởi tạo service
    ai_service = MultiAIService()
    
    # Thêm nhiều API keys
    keys_config = [
        {
            "provider": "openai",
            "key": "your-openai-key-here",
            "name": "OpenAI_Main",
            "daily_limit": 50,  # Limit thấp vì free tier
            "hourly_limit": 10
        },
        {
            "provider": "groq",
            "key": "your-groq-key-here",  # Free và rất nhanh
            "name": "Groq_Free",
            "daily_limit": 1000,
            "hourly_limit": 200
        },
        {
            "provider": "together",
            "key": "your-together-key-here",  # Giá rẻ
            "name": "Together_AI",
            "daily_limit": 500,
            "hourly_limit": 100
        }
    ]
    
    ai_service.add_api_keys(keys_config)
    
    # Test requests
    test_prompts = [
        "Viết một bài phân tích ngắn về thị trường chứng khoán Việt Nam",
        "Tóm tắt xu hướng công nghệ AI trong 2024",
        "Phân tích tác động của lạm phát đến kinh tế"
    ]
    
    print("🚀 Testing Multi-AI Service...")
    
    for i, prompt in enumerate(test_prompts, 1):
        print(f"\n--- Request {i} ---")
        print(f"Prompt: {prompt[:50]}...")
        
        request = AIRequest(
            prompt=prompt,
            max_tokens=500,
            temperature=0.7
        )
        
        result = await ai_service.make_chat_request(request)
        
        if result["success"]:
            print(f"✅ Provider: {result['provider']}")
            print(f"📝 Response: {result['content'][:100]}...")
        else:
            print(f"❌ Failed: {result['error']}")
        
        # Nghỉ giữa requests
        await asyncio.sleep(2)
    
    # In thống kê
    stats = ai_service.get_usage_stats()
    print(f"\n📊 Usage Stats:")
    print(f"Active Keys: {stats['active_keys']}/{stats['total_api_keys']}")
    print(f"Total Requests: {stats['request_stats']['total_requests']}")
    print(f"Success Rate: {stats['request_stats']['successful_requests']}/{stats['request_stats']['total_requests']}")

if __name__ == "__main__":
    asyncio.run(demo_multi_ai()) 