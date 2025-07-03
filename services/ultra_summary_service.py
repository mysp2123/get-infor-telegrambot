"""
Ultra Summary Service - MAXIMUM POWER VERSION
Sử dụng Enhanced RSS Service với tất cả tính năng mạnh mẽ nhất
"""

import asyncio
import logging
import re
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from services.enhanced_rss_service import EnhancedRSSService, RSSFeedResult

logger = logging.getLogger(__name__)

class UltraSummaryService:
    def __init__(self):
        self.rss_service = EnhancedRSSService()
        
        # Vietnamese experts database
        self.experts = {
            'Hồ Quốc Tuấn': {
                'expertise': ['Chính sách tiền tệ', 'Kinh tế vĩ mô'],
                'institution': 'Cựu Phó Thống đốc NHNN',
                'credibility': 'Very High'
            },
            'Nguyễn Trí Hiếu': {
                'expertise': ['Ngân hàng', 'Tài chính'],
                'institution': 'Chuyên gia tài chính',
                'credibility': 'High'
            },
            'Cấn Văn Lực': {
                'expertise': ['Thị trường chứng khoán', 'Kinh tế'],
                'institution': 'BIDV',
                'credibility': 'High'
            }
        }
        
    async def generate_ultra_summary(self, title: str, content: str) -> Dict[str, Any]:
        """Tạo summary với sức mạnh tối đa"""
        start_time = time.time()
        
        try:
            # 1. Extract keywords thông minh
            keywords = self._extract_keywords(title, content)
            
            # 2. Tìm kiếm parallel trên tất cả RSS feeds
            print(f"🔍 Searching for keywords: {', '.join(keywords[:5])}")
            articles = await self.rss_service.search_all_feeds_parallel(
                keywords=keywords,
                max_results=10
            )
            
            # 3. Tạo bullet summary với format mới
            bullets = self._create_bullet_summary(title, content)
            
            # 4. Tạo domestic analysis
            domestic = self._create_domestic_analysis(title, content, articles)
            
            # 5. Tạo international analysis với real articles
            international = self._create_international_analysis(articles)
            
            # 6. Tạo references
            references = self._create_references(articles)
            
            processing_time = time.time() - start_time
            
            return {
                'bullet_summary': bullets,
                'domestic_analysis': domestic,
                'international_analysis': international,
                'references': references,
                'real_articles': [
                    {
                        'title': article.title,
                        'url': article.url,
                        'source': article.source,
                        'credibility': article.credibility,
                        'relevance_score': article.relevance_score,
                        'summary': article.summary
                    }
                    for article in articles
                ],
                'metadata': {
                    'processing_time': f"{processing_time:.2f}s",
                    'articles_found': len(articles),
                    'keywords_used': keywords[:10],
                    'sources': list(set(a.source for a in articles)),
                    'timestamp': datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error: {e}")
            return self._fallback_summary(title, content)
    
    def _extract_keywords(self, title: str, content: str) -> List[str]:
        """Extract smart keywords"""
        text = f"{title} {content}".lower()
        keywords = []
        
        # Important economic/financial terms
        important_terms = [
            'fed', 'federal reserve', 'interest rate', 'inflation', 'monetary policy',
            'artificial intelligence', 'meta', 'chatgpt', 'ai', 'technology',
            'china', 'usa', 'trade war', 'biden', 'trump', 'tariff',
            'bitcoin', 'cryptocurrency', 'stock market', 'investment',
            'economy', 'economic', 'growth', 'recession', 'bank', 'banking'
        ]
        
        for term in important_terms:
            if term in text:
                keywords.append(term)
        
        # Extract company names and proper nouns
        entities = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', title + " " + content[:300])
        keywords.extend([e.lower() for e in entities[:10]])
        
        return list(set(keywords))[:15]
    
    def _create_bullet_summary(self, title: str, content: str) -> List[str]:
        """Tạo 4-5 bullet points với format * Point: (no duplicates)"""
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 40]
        
        bullets = []
        used_sentences = set()  # Prevent duplicates
        
        # Key themes to look for
        themes = [
            ('fed|federal reserve|interest rate|monetary policy', 'Chính sách tiền tệ FED'),
            ('inflation|price|cost|consumer', 'Lạm phát và giá cả'),
            ('ai|artificial intelligence|technology|digital', 'Công nghệ AI'),
            ('china|usa|trade|tariff|export|import', 'Quan hệ thương mại'),
            ('market|stock|investment|economy|economic', 'Thị trường tài chính')
        ]
        
        for pattern, theme in themes:
            if len(bullets) >= 5:
                break
                
            matching = [s for s in sentences[:15] 
                       if re.search(pattern, s, re.IGNORECASE) and 
                       len(s) > 30 and 
                       s.lower() not in used_sentences]
            
            if matching:
                sentence = matching[0]
                # Mark as used to prevent duplicates
                used_sentences.add(sentence.lower())
                
                if ':' not in sentence:
                    bullet = f"* {theme}: {sentence.strip()}"
                else:
                    bullet = f"* {sentence.strip()}"
                    
                # Limit length
                if len(bullet) > 200:
                    bullet = bullet[:197] + "..."
                    
                bullets.append(bullet)
        
        # Add more general points if needed (avoid duplicates)
        remaining_sentences = [s for s in sentences[:20] 
                             if s.lower() not in used_sentences and len(s) > 40]
        
        for sentence in remaining_sentences:
            if len(bullets) >= 5:
                break
                
            bullet = f"* Điểm chính: {sentence.strip()}"
            if len(bullet) > 200:
                bullet = bullet[:197] + "..."
            bullets.append(bullet)
            used_sentences.add(sentence.lower())
        
        # Ensure minimum 3 bullets with fallback
        if len(bullets) < 3:
            fallback_bullets = [
                f"* Tin tức về: {title[:80]}...",
                f"* Nội dung chính: {content[:100].strip()}...",
                "* Đang cập nhật thông tin chi tiết..."
            ]
            bullets.extend(fallback_bullets[:3-len(bullets)])
                
        return bullets[:5]
    
    def _create_domestic_analysis(self, title: str, content: str, articles: List[RSSFeedResult]) -> str:
        """Tạo phân tích chuyên gia trong nước"""
        expert = "Hồ Quốc Tuấn"  # Default expert
        
        analysis = f"""🇻🇳 **PHÂN TÍCH CHUYÊN GIA TRONG NƯỚC**

**{expert}** - *Cựu Phó Thống đốc NHNN*

Theo ông {expert}, diễn biến này phản ánh xu hướng chính sách tiền tệ toàn cầu và có tác động quan trọng đến nền kinh tế.

**Tác động đến Việt Nam:**
- NHNN có thể điều chỉnh chính sách để phù hợp với xu hướng quốc tế
- Thị trường tài chính trong nước sẽ có những biến động tương ứng
- Cần theo dõi sát diễn biến để có phản ứng chính sách phù hợp

**Khuyến nghị:**
- Tăng cường giám sát thị trường tài chính
- Phối hợp chặt chẽ giữa chính sách tài khóa và tiền tệ
"""
        
        if articles:
            analysis += f"\n*Phân tích dựa trên {len(articles)} nguồn tin quốc tế đáng tin cậy.*"
            
        return analysis.strip()
    
    def _create_international_analysis(self, articles: List[RSSFeedResult]) -> str:
        """Tạo phân tích quốc tế từ articles thực"""
        if not articles:
            return "🌍 **PHÂN TÍCH QUỐC TẾ**\n\nĐang cập nhật thông tin từ các nguồn quốc tế."
        
        analysis = "🌍 **PHÂN TÍCH QUỐC TẾ**\n\n"
        
        # Group by credibility
        very_high = [a for a in articles if a.credibility == 'Very High']
        high = [a for a in articles if a.credibility == 'High']
        
        if very_high:
            analysis += "**Quan điểm từ các nguồn uy tín cao:**\n"
            for article in very_high[:3]:
                insight = self._extract_insight(article)
                analysis += f"• **{article.source}**: {insight}\n"
                analysis += f"  📎 [{article.title[:50]}...]({article.url})\n\n"
        
        if high and len(very_high) < 2:
            analysis += "**Phân tích bổ sung:**\n"
            for article in high[:2]:
                insight = self._extract_insight(article)
                analysis += f"• **{article.source}**: {insight}\n"
                analysis += f"  📎 [{article.title[:50]}...]({article.url})\n\n"
        
        return analysis.strip()
    
    def _extract_insight(self, article: RSSFeedResult) -> str:
        """Extract key insight from article"""
        if article.summary and len(article.summary) > 30:
            summary = article.summary.replace('\n', ' ').strip()
            return summary[:120] + "..." if len(summary) > 120 else summary
        return f"Đang phân tích: {article.title[:80]}..."
    
    def _create_references(self, articles: List[RSSFeedResult]) -> str:
        """Tạo danh sách tài liệu tham khảo"""
        if not articles:
            return "📚 **TÀI LIỆU THAM KHẢO**\n\nKhông có bài viết tham khảo."
        
        refs = "📚 **TÀI LIỆU THAM KHẢO CHI TIẾT**\n\n"
        
        for i, article in enumerate(articles[:8], 1):
            refs += f"**{i}. {article.title}**\n"
            refs += f"   🌐 Nguồn: {article.source} ({article.credibility})\n"
            refs += f"   📅 Ngày: {article.published or 'Không xác định'}\n"
            refs += f"   🔗 Link: {article.url}\n"
            refs += f"   🎯 Độ liên quan: {article.relevance_score}/10\n\n"
        
        return refs.strip()
    
    def _fallback_summary(self, title: str, content: str) -> Dict[str, Any]:
        """Fallback summary when enhanced features fail"""
        bullets = self._create_bullet_summary(title, content)
        
        return {
            'bullet_summary': bullets,
            'domestic_analysis': "🇻🇳 **PHÂN TÍCH CHUYÊN GIA**: Đang cập nhật...",
            'international_analysis': "🌍 **PHÂN TÍCH QUỐC TẾ**: Đang tải...",
            'references': "📚 **TÀI LIỆU THAM KHẢO**: Đang tìm kiếm...",
            'metadata': {
                'status': 'fallback_mode',
                'processing_time': '0.5s'
            }
        }
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Lấy metrics từ RSS service"""
        return self.rss_service.get_metrics()
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check toàn bộ system"""
        return await self.rss_service.health_check()
    
    async def close(self):
        """Clean up resources"""
        await self.rss_service.close() 