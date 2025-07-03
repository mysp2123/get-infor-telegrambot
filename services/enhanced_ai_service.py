#!/usr/bin/env python3
"""
Enhanced AI Service with Groq + Gemini Integration
Sử dụng Groq làm primary provider, Gemini làm fallback
"""

import asyncio
import aiohttp
import json
import logging
from typing import List, Dict, Optional
from datetime import datetime
import google.generativeai as genai
from config import Config
from models.article import Article

logger = logging.getLogger(__name__)

class EnhancedAIService:
    """Enhanced AI Service with Groq primary, Gemini fallback"""
    
    def __init__(self):
        self.config = Config()
        
        # Groq configuration
        self.groq_api_keys = [
            "your-groq-key-1-here",
            "your-groq-key-2-here",
            "your-groq-key-3-here"
        ]
        self.current_groq_key_index = 0
        
        # Gemini fallback configuration
        self.gemini_api_keys = self.config.get_active_api_keys('gemini')
        self.current_gemini_key_index = 0
        
        # Groq models prioritized by performance
        self.groq_models = [
            "llama-3.3-70b-versatile",  # Latest and most capable
            "meta-llama/llama-4-scout-17b-16e-instruct",  # NEW Llama 4
            "deepseek-r1-distill-llama-70b",  # Good reasoning
            "llama-3.1-8b-instant",  # Fast for simple tasks
            "gemma2-9b-it"  # Good alternative
        ]
        
        # Initialize Gemini fallback
        self._setup_gemini_fallback()
        
        # Usage stats
        self.usage_stats = {
            'groq_requests': 0,
            'groq_success': 0,
            'gemini_requests': 0,
            'gemini_success': 0,
            'total_requests': 0
        }
        
    def _setup_gemini_fallback(self):
        """Setup Gemini as fallback"""
        if self.gemini_api_keys:
            try:
                genai.configure(api_key=self.gemini_api_keys[self.current_gemini_key_index])
                self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
                logger.info("✅ Gemini fallback configured successfully")
            except Exception as e:
                logger.error(f"❌ Gemini fallback setup failed: {e}")
                self.gemini_model = None
        else:
            self.gemini_model = None
            logger.warning("⚠️ No Gemini API keys found for fallback")
    
    async def _make_groq_request(self, prompt: str, model: str = None, max_tokens: int = 1000, temperature: float = 0.7) -> Dict:
        """Make request to Groq API"""
        if not model:
            model = self.groq_models[0]  # Default to best model
            
        headers = {
            "Authorization": f"Bearer {self.groq_api_keys[self.current_groq_key_index]}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        self.usage_stats['groq_requests'] += 1
        self.usage_stats['total_requests'] += 1
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        content = result['choices'][0]['message']['content']
                        self.usage_stats['groq_success'] += 1
                        logger.info(f"✅ Groq request successful with {model}")
                        return {
                            'success': True,
                            'content': content,
                            'provider': 'groq',
                            'model': model
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Groq API error {response.status}: {error_text}")
                        
                        # Try to rotate key if quota exceeded
                        if response.status == 429:
                            self._rotate_groq_key()
                            
                        return {
                            'success': False,
                            'error': f"Groq API error {response.status}",
                            'provider': 'groq'
                        }
                        
        except asyncio.TimeoutError:
            logger.error("⏱️ Groq API timeout")
            return {'success': False, 'error': 'Groq API timeout', 'provider': 'groq'}
        except Exception as e:
            logger.error(f"❌ Groq request failed: {e}")
            return {'success': False, 'error': str(e), 'provider': 'groq'}
    
    def _rotate_groq_key(self):
        """Rotate to next Groq API key"""
        self.current_groq_key_index = (self.current_groq_key_index + 1) % len(self.groq_api_keys)
        logger.info(f"🔄 Rotated to Groq key #{self.current_groq_key_index + 1}")
    
    async def _make_gemini_request(self, prompt: str) -> Dict:
        """Make request to Gemini API as fallback"""
        if not self.gemini_model:
            return {'success': False, 'error': 'Gemini not configured', 'provider': 'gemini'}
        
        self.usage_stats['gemini_requests'] += 1
        
        try:
            response = await asyncio.to_thread(self.gemini_model.generate_content, prompt)
            content = response.text
            self.usage_stats['gemini_success'] += 1
            logger.info("✅ Gemini fallback request successful")
            return {
                'success': True,
                'content': content,
                'provider': 'gemini',
                'model': 'gemini-1.5-flash'
            }
        except Exception as e:
            logger.error(f"❌ Gemini fallback failed: {e}")
            return {'success': False, 'error': str(e), 'provider': 'gemini'}
    
    async def generate_content(self, prompt: str, prefer_fast: bool = False) -> str:
        """Generate content with Groq primary, Gemini fallback"""
        
        # Choose model based on task
        if prefer_fast:
            model = "llama-3.1-8b-instant"  # Fast model for simple tasks
        else:
            model = "llama-3.3-70b-versatile"  # Best model for complex tasks
        
        # Try Groq first
        logger.info(f"🚀 Trying Groq with model: {model}")
        result = await self._make_groq_request(prompt, model)
        
        if result['success']:
            return result['content']
        
        # Try different Groq model if first failed
        for backup_model in self.groq_models[1:]:
            if backup_model != model:
                logger.info(f"🔄 Trying backup Groq model: {backup_model}")
                result = await self._make_groq_request(prompt, backup_model)
                if result['success']:
                    return result['content']
        
        # Fallback to Gemini
        logger.info("⚠️ Groq failed, falling back to Gemini")
        result = await self._make_gemini_request(prompt)
        
        if result['success']:
            return result['content']
        
        # All failed
        logger.error("❌ All AI providers failed")
        return "❌ Xin lỗi, không thể tạo nội dung lúc này. Vui lòng thử lại sau."
    
    async def generate_custom_content(self, prompt: str) -> str:
        """Generate custom content (alias for compatibility)"""
        return await self.generate_content(prompt)
    
    async def generate_article_summary(self, article: Article) -> str:
        """Generate Vietnamese summary for article"""
        prompt = f"""
        Tóm tắt bài báo sau đây bằng tiếng Việt, nêu bật tính liên quan và sức hấp dẫn:
        
        Tiêu đề: {article.title}
        Nội dung: {article.content[:1500]}...
        Nguồn: {article.source}
        
        Tập trung vào:
        - Các điểm chính và ý nghĩa
        - Tại sao câu chuyện này quan trọng
        - Các khía cạnh gây tranh cãi hoặc thú vị
        - Tác động đến Việt Nam (nếu có)
        
        Viết ngắn gọn (100-150 từ), phong cách chuyên gia nhưng dễ hiểu.
        """
        
        return await self.generate_content(prompt, prefer_fast=True)
    
    async def generate_facebook_post(self, article: Article, style: str = "expert", expert_posts: List[Dict] = None) -> str:
        """Generate Facebook post with specified style"""
        
        # Style templates
        style_prompts = {
            "expert": "Viết với giọng điệu chuyên gia có uy tín, phân tích chuyên sâu",
            "friendly": "Viết thân thiện, gần gũi như nói chuyện với bạn bè",
            "news": "Viết theo phong cách báo chí, khách quan và chính xác",
            "debate": "Viết theo phong cách tranh luận, nêu nhiều quan điểm",
            "educational": "Viết theo phong cách giáo dục, giải thích dễ hiểu",
            "inspirational": "Viết theo phong cách truyền cảm hứng, tích cực"
        }
        
        style_instruction = style_prompts.get(style, style_prompts["expert"])
        
        expert_context = ""
        if expert_posts:
            expert_context = f"""
            
            Các bài viết liên quan từ chuyên gia:
            {chr(10).join([post.get('content', '')[:200] + '...' for post in expert_posts[:3]])}
            """
        
        prompt = f"""
        Tạo một bài viết Facebook bằng tiếng Việt (250-400 từ) dựa trên bài báo này:
        
        Tiêu đề: {article.title}
        Nội dung: {article.content[:2000]}
        URL: {article.url}
        Nguồn: {article.source}
        {expert_context}
        
        Phong cách: {style_instruction}
        
        Yêu cầu:
        - Thêm yếu tố hấp dẫn và dễ chia sẻ
        - Thêm hashtag phù hợp
        - Tham khảo nguồn tin
        - Phân tích tác động (nếu có)
        - Sử dụng emoji phù hợp
        - Tránh markdown phức tạp
        
        Viết tự nhiên, không sử dụng ký tự đặc biệt gây lỗi.
        """
        
        return await self.generate_content(prompt)
    
    async def generate_image_prompt(self, article: Article, context: str = "") -> str:
        """Generate image prompt based on article content"""
        prompt = f"""
        Tạo prompt tạo ảnh AI chi tiết cho bài báo này:
        
        Tiêu đề: {article.title}
        Nội dung chính: {article.content[:1000]}
        Context: {context}
        
        Yêu cầu prompt:
        - Mô tả hình ảnh cụ thể, rõ ràng
        - Phù hợp với nội dung bài báo
        - Phong cách chuyên nghiệp, tin tức
        - Thêm logo PioneerX góc dưới phải
        - Màu sắc phù hợp với chủ đề
        - Không chứa text trong ảnh
        
        Chỉ trả về prompt tiếng Anh, không giải thích thêm.
        """
        
        return await self.generate_content(prompt, prefer_fast=True)
    
    def get_usage_stats(self) -> Dict:
        """Get current usage statistics"""
        return {
            **self.usage_stats,
            'groq_success_rate': f"{(self.usage_stats['groq_success'] / max(self.usage_stats['groq_requests'], 1) * 100):.1f}%",
            'gemini_success_rate': f"{(self.usage_stats['gemini_success'] / max(self.usage_stats['gemini_requests'], 1) * 100):.1f}%",
            'current_groq_key': self.current_groq_key_index + 1,
            'available_groq_keys': len(self.groq_api_keys),
            'gemini_fallback_available': self.gemini_model is not None
        }
    
    def get_api_status(self) -> dict:
        """Get API status for compatibility"""
        return self.get_usage_stats() 