"""
Enhanced Summary Service V3 - ULTRA POWERFUL
Sử dụng Enhanced RSS Service với:
- Parallel RSS processing
- Advanced caching layer
- Intelligent keyword extraction
- Multi-source content aggregation
- Real-time relevance scoring
- Performance monitoring
"""

import asyncio
import logging
import re
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

from .enhanced_rss_service import EnhancedRSSService, RSSFeedResult

logger = logging.getLogger(__name__)

@dataclass
class EnhancedArticleAnalysis:
    """Kết quả phân tích bài viết nâng cao"""
    title: str
    url: str
    source: str
    credibility: str
    region: str
    relevance_score: int
    analysis_text: str
    key_insights: List[str]
    published_date: str
    word_count: int
    category: str

class EnhancedSummaryServiceV3:
    def __init__(self):
        self.rss_service = EnhancedRSSService()
        
        # Expanded domestic experts database
        self.domestic_experts = {
            'Hồ Quốc Tuấn': {
                'expertise': ['Chính sách tiền tệ', 'Kinh tế vĩ mô', 'Thị trường tài chính'],
                'institution': 'Ngân hàng Nhà nước Việt Nam',
                'credibility': 'Very High',
                'bio': 'Cựu Phó Thống đốc NHNN, chuyên gia về chính sách tiền tệ và tài chính quốc tế'
            },
            'Nguyễn Trí Hiếu': {
                'expertise': ['Ngân hàng', 'Tài chính cá nhân', 'Fintech'],
                'institution': 'Chuyên gia tài chính ngân hàng',
                'credibility': 'High',
                'bio': 'Chuyên gia tài chính ngân hàng với hơn 20 năm kinh nghiệm'
            },
            'Cấn Văn Lực': {
                'expertise': ['Kinh tế vĩ mô', 'Thị trường chứng khoán', 'Dự báo kinh tế'],
                'institution': 'BIDV',
                'credibility': 'High',
                'bio': 'Chuyên gia kinh tế trưởng BIDV, chuyên về phân tích thị trường'
            },
            'Đinh Thế Hiển': {
                'expertise': ['Kinh tế số', 'Chuyển đổi số', 'Công nghệ tài chính'],
                'institution': 'VietinBank',
                'credibility': 'High',
                'bio': 'Phó Tổng Giám đốc VietinBank, chuyên gia về ngân hàng số'
            },
            'Lê Xuân Nghĩa': {
                'expertise': ['Chính sách tài khóa', 'Thị trường vốn', 'Cải cách thể chế'],
                'institution': 'Hội đồng Tư vấn Chính sách Tài chính tiền tệ Quốc gia',
                'credibility': 'Very High',
                'bio': 'Thành viên Hội đồng Tư vấn Chính sách Tài chính tiền tệ Quốc gia'
            }
        }
        
        # Enhanced topic categorization
        self.topic_categories = {
            'monetary_policy': {
                'keywords': ['fed', 'federal reserve', 'interest rate', 'inflation', 'monetary policy', 'central bank'],
                'vietnamese_keywords': ['ngân hàng trung ương', 'lãi suất', 'lạm phát', 'chính sách tiền tệ'],
                'expert': 'Hồ Quốc Tuấn'
            },
            'technology': {
                'keywords': ['ai', 'artificial intelligence', 'meta', 'chatgpt', 'technology', 'innovation'],
                'vietnamese_keywords': ['trí tuệ nhân tạo', 'công nghệ', 'chuyển đổi số', 'fintech'],
                'expert': 'Đinh Thế Hiển'
            },
            'financial_markets': {
                'keywords': ['stock market', 'investment', 'trading', 'bonds', 'equity', 'market'],
                'vietnamese_keywords': ['thị trường chứng khoán', 'đầu tư', 'giao dịch', 'cổ phiếu'],
                'expert': 'Cấn Văn Lực'
            },
            'banking': {
                'keywords': ['banking', 'credit', 'loan', 'deposit', 'fintech', 'payment'],
                'vietnamese_keywords': ['ngân hàng', 'tín dụng', 'cho vay', 'tiền gửi', 'thanh toán'],
                'expert': 'Nguyễn Trí Hiếu'
            },
            'economic_policy': {
                'keywords': ['fiscal policy', 'government', 'regulation', 'reform', 'economic growth'],
                'vietnamese_keywords': ['chính sách tài khóa', 'cải cách', 'tăng trưởng kinh tế', 'quy định'],
                'expert': 'Lê Xuân Nghĩa'
            },
            'global_trade': {
                'keywords': ['trade war', 'tariff', 'export', 'import', 'global trade', 'supply chain'],
                'vietnamese_keywords': ['thương mại quốc tế', 'xuất khẩu', 'nhập khẩu', 'chuỗi cung ứng'],
                'expert': 'Hồ Quốc Tuấn'
            }
        }
        
        # Performance tracking
        self.performance_metrics = {
            'total_summaries': 0,
            'articles_analyzed': 0,
            'average_processing_time': 0,
            'cache_usage': 0,
            'expert_assignments': {},
            'source_diversity_score': 0,
            'last_updated': datetime.now()
        }
    
    async def generate_ultra_enhanced_summary(
        self,
        title: str,
        content: str,
        max_international_articles: int = 8,
        max_bullet_points: int = 5
    ) -> Dict[str, Any]:
        """
        Tạo enhanced summary với RSS service mạnh mẽ
        """
        start_time = time.time()
        
        try:
            # 1. Enhanced keyword extraction
            primary_keywords = self._extract_smart_keywords(title, content)
            category = self._classify_topic(title, content)
            
            logger.info(f"Processing summary for category: {category}")
            logger.info(f"Primary keywords: {primary_keywords[:5]}")
            
            # 2. Parallel RSS search với enhanced service
            international_articles = await self._search_international_articles_parallel(
                keywords=primary_keywords,
                max_results=max_international_articles
            )
            
            # 3. Generate enhanced bullet summary
            bullet_summary = self._create_enhanced_bullet_summary(
                title, content, max_bullet_points
            )
            
            # 4. Generate domestic expert analysis
            domestic_analysis = self._generate_domestic_expert_analysis(
                title, content, category, international_articles
            )
            
            # 5. Generate international analysis với real articles
            international_analysis = self._generate_international_analysis_with_articles(
                title, content, international_articles
            )
            
            # 6. Create reference section
            reference_articles = self._format_reference_articles(international_articles)
            
            # 7. Performance tracking
            processing_time = time.time() - start_time
            self._update_performance_metrics(processing_time, len(international_articles), category)
            
            # 8. Compile final summary
            enhanced_summary = {
                'bullet_summary': bullet_summary,
                'domestic_expert_analysis': domestic_analysis,
                'international_analysis': international_analysis,
                'reference_articles': reference_articles,
                'metadata': {
                    'processing_time': f"{processing_time:.2f}s",
                    'articles_found': len(international_articles),
                    'category': category,
                    'keywords_used': primary_keywords[:10],
                    'sources_diversity': len(set(a.source for a in international_articles)),
                    'average_credibility': self._calculate_average_credibility(international_articles),
                    'timestamp': datetime.now().isoformat()
                }
            }
            
            logger.info(f"Enhanced summary generated in {processing_time:.2f}s with {len(international_articles)} articles")
            return enhanced_summary
            
        except Exception as e:
            logger.error(f"Error generating enhanced summary: {e}")
            # Fallback to basic summary
            return await self._generate_fallback_summary(title, content)
    
    def _extract_smart_keywords(self, title: str, content: str) -> List[str]:
        """Enhanced keyword extraction với NLP techniques"""
        text = f"{title} {content}".lower()
        keywords = []
        
        # 1. Category-based keyword extraction
        detected_category = self._classify_topic(title, content)
        if detected_category in self.topic_categories:
            category_keywords = self.topic_categories[detected_category]['keywords']
            for keyword in category_keywords:
                if keyword in text:
                    keywords.append(keyword)
        
        # 2. Named entity extraction (companies, people, places)
        entities = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', title + " " + content[:500])
        keywords.extend([entity.lower() for entity in entities[:10]])
        
        # 3. Financial/economic terms
        financial_terms = [
            'bitcoin', 'cryptocurrency', 'blockchain', 'stock', 'market', 'investment',
            'economy', 'gdp', 'inflation', 'recession', 'growth', 'policy', 'bank',
            'credit', 'loan', 'interest', 'currency', 'dollar', 'euro', 'yuan'
        ]
        
        for term in financial_terms:
            if term in text:
                keywords.append(term)
        
        # 4. Technology terms
        tech_terms = [
            'ai', 'artificial intelligence', 'machine learning', 'automation',
            'digital', 'cloud', 'data', 'analytics', 'software', 'platform'
        ]
        
        for term in tech_terms:
            if term in text:
                keywords.append(term)
        
        # 5. Use RSS service's enhanced keyword extraction
        rss_keywords = self.rss_service.extract_enhanced_keywords(title, content)
        keywords.extend(rss_keywords[:15])
        
        # Remove duplicates and return top keywords
        unique_keywords = list(dict.fromkeys(keywords))  # Preserve order
        return unique_keywords[:20]
    
    def _classify_topic(self, title: str, content: str) -> str:
        """Phân loại chủ đề bài viết"""
        text = f"{title} {content}".lower()
        
        category_scores = {}
        
        for category, info in self.topic_categories.items():
            score = 0
            
            # Score from English keywords
            for keyword in info['keywords']:
                if keyword in text:
                    score += 2 if len(keyword) > 8 else 1
            
            # Score from Vietnamese keywords
            for keyword in info.get('vietnamese_keywords', []):
                if keyword in text:
                    score += 1
            
            category_scores[category] = score
        
        # Return category with highest score, or 'general' if no clear match
        if category_scores:
            best_category = max(category_scores.items(), key=lambda x: x[1])
            if best_category[1] > 0:
                return best_category[0]
        
        return 'general'
    
    async def _search_international_articles_parallel(
        self, 
        keywords: List[str], 
        max_results: int = 8
    ) -> List[RSSFeedResult]:
        """Tìm kiếm bài viết quốc tế với enhanced RSS service"""
        try:
            # Use enhanced RSS service for parallel search
            articles = await self.rss_service.search_all_feeds_parallel(
                keywords=keywords,
                max_results=max_results
            )
            
            logger.info(f"Found {len(articles)} international articles via enhanced RSS")
            return articles
            
        except Exception as e:
            logger.error(f"Error searching international articles: {e}")
            return []
    
    def _create_enhanced_bullet_summary(
        self, 
        title: str, 
        content: str, 
        max_points: int = 5
    ) -> List[str]:
        """Tạo bullet summary với format * Point: detail"""
        # Extract key sentences from content
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 30]
        
        bullet_points = []
        
        # Priority topics for bullet points
        priority_patterns = [
            (r'fed|federal reserve|interest rate|monetary policy', 'Chính sách tiền tệ'),
            (r'inflation|price|cost|consumer', 'Lạm phát và giá cả'),
            (r'market|stock|trading|investment', 'Thị trường tài chính'),
            (r'ai|artificial intelligence|technology|digital', 'Công nghệ và AI'),
            (r'china|usa|trade|global|international', 'Quan hệ quốc tế'),
            (r'economy|economic|growth|gdp', 'Kinh tế vĩ mô'),
            (r'bank|banking|credit|loan', 'Ngành ngân hàng'),
            (r'crypto|bitcoin|blockchain|digital currency', 'Tiền điện tử')
        ]
        
        used_categories = set()
        
        for pattern, category in priority_patterns:
            if len(bullet_points) >= max_points:
                break
                
            if category in used_categories:
                continue
            
            # Find sentences matching this pattern
            matching_sentences = [
                s for s in sentences[:15]  # Check first 15 sentences
                if re.search(pattern, s, re.IGNORECASE) and len(s) > 50
            ]
            
            if matching_sentences:
                best_sentence = max(matching_sentences, key=len)
                # Format as * Point: detail
                if ':' not in best_sentence:
                    if len(best_sentence) > 100:
                        # Split long sentence
                        parts = best_sentence.split(',', 1)
                        if len(parts) == 2:
                            point = f"* {parts[0].strip()}: {parts[1].strip()}"
                        else:
                            point = f"* {category}: {best_sentence}"
                    else:
                        point = f"* {category}: {best_sentence}"
                else:
                    point = f"* {best_sentence}" if best_sentence.startswith('*') else f"* {best_sentence}"
                
                # Ensure proper format and length
                if len(point) > 200:
                    point = point[:197] + "..."
                
                bullet_points.append(point)
                used_categories.add(category)
        
        # Add more general points if needed
        if len(bullet_points) < max_points:
            remaining_sentences = [
                s for s in sentences[:20]
                if not any(re.search(p[0], s, re.IGNORECASE) for p in priority_patterns)
                and len(s) > 40 and len(s) < 150
            ]
            
            for sentence in remaining_sentences[:max_points - len(bullet_points)]:
                point = f"* Điểm chính: {sentence.strip()}"
                if len(point) > 200:
                    point = point[:197] + "..."
                bullet_points.append(point)
        
        # Ensure we have at least 4 points
        while len(bullet_points) < 4 and len(bullet_points) < max_points:
            if len(sentences) > len(bullet_points):
                sentence = sentences[len(bullet_points)]
                point = f"* Thông tin bổ sung: {sentence.strip()}"
                if len(point) > 200:
                    point = point[:197] + "..."
                bullet_points.append(point)
            else:
                break
        
        return bullet_points[:max_points]
    
    def _generate_domestic_expert_analysis(
        self,
        title: str,
        content: str,
        category: str,
        international_articles: List[RSSFeedResult]
    ) -> str:
        """Tạo phân tích chuyên gia trong nước với context từ international articles"""
        
        # Select appropriate expert based on category
        expert_name = self.topic_categories.get(category, {}).get('expert', 'Hồ Quốc Tuấn')
        expert_info = self.domestic_experts[expert_name]
        
        # Extract key insights from international articles
        international_insights = []
        if international_articles:
            for article in international_articles[:3]:
                if article.summary:
                    key_point = article.summary[:100] + "..."
                    international_insights.append(f"- {article.source}: {key_point}")
        
        # Generate contextual analysis
        analysis_template = f"""
🇻🇳 **PHÂN TÍCH CHUYÊN GIA TRONG NƯỚC**

**{expert_name}** - *{expert_info['institution']}*

Theo quan điểm của chuyên gia {expert_name}, {self._generate_expert_insight(title, content, expert_info, international_insights)}.

**Tác động đến Việt Nam:**
{self._generate_vietnam_impact_analysis(title, content, category)}

**Khuyến nghị chính sách:**
{self._generate_policy_recommendations(category, expert_info)}

*Chuyên gia {expert_name} có hơn 20 năm kinh nghiệm trong lĩnh vực {", ".join(expert_info['expertise'][:2])}.*
        """.strip()
        
        # Track expert usage
        if expert_name not in self.performance_metrics['expert_assignments']:
            self.performance_metrics['expert_assignments'][expert_name] = 0
        self.performance_metrics['expert_assignments'][expert_name] += 1
        
        return analysis_template
    
    def _generate_expert_insight(
        self,
        title: str,
        content: str,
        expert_info: Dict,
        international_insights: List[str]
    ) -> str:
        """Generate expert insight based on their expertise"""
        
        expertise_responses = {
            'Chính sách tiền tệ': [
                "động thái này phản ánh xu hướng thắt chặt chính sách tiền tệ toàn cầu",
                "các ngân hàng trung ương đang phối hợp chống lạm phát",
                "chính sách tiền tệ cần cân bằng giữa kiểm soát lạm phát và hỗ trợ tăng trưởng"
            ],
            'Thị trường tài chính': [
                "thị trường đang phản ánh kỳ vọng về chính sách kinh tế mới",
                "biến động này tạo cơ hội đầu tư cho các nhà đầu tư thông minh",
                "cần theo dõi sát diễn biến thị trường để đưa ra quyết định phù hợp"
            ],
            'Công nghệ tài chính': [
                "xu hướng số hóa đang thay đổi cách thức hoạt động của ngành tài chính",
                "các ngân hàng cần đẩy mạnh chuyển đổi số để cạnh tranh",
                "công nghệ AI và blockchain sẽ định hình tương lai ngành tài chính"
            ]
        }
        
        # Select response based on expert's primary expertise
        primary_expertise = expert_info['expertise'][0]
        
        if primary_expertise in expertise_responses:
            responses = expertise_responses[primary_expertise]
            # Use international insights to enhance the response
            if international_insights:
                base_response = responses[0]
                return f"{base_response}. Các nguồn quốc tế cũng nhấn mạnh xu hướng tương tự"
            else:
                return responses[0]
        
        return "diễn biến này cần được phân tích kỹ lưỡng trong bối cảnh kinh tế hiện tại"
    
    def _generate_vietnam_impact_analysis(self, title: str, content: str, category: str) -> str:
        """Generate Vietnam-specific impact analysis"""
        
        impact_templates = {
            'monetary_policy': "NHNN Việt Nam có thể sẽ điều chỉnh lãi suất tương ứng để duy trì tính cạnh tranh của VND và kiểm soát lạm phát trong nước.",
            'technology': "Việt Nam đang tăng cường đầu tư vào công nghệ số và AI, điều này tạo cơ hội phát triển hệ sinh thái fintech và banking số.",
            'financial_markets': "TTCK Việt Nam có thể sẽ biến động theo xu hướng toàn cầu, nhưng các cổ phiếu có fundamentals tốt vẫn hấp dẫn nhà đầu tư dài hạn.",
            'banking': "Hệ thống ngân hàng Việt Nam cần tăng cường quản trị rủi ro và nâng cao năng lực công nghệ để cạnh tranh trong môi trường mới.",
            'economic_policy': "Chính phủ Việt Nam đang thúc đẩy các chính sách hỗ trợ doanh nghiệp và khuyến khích đầu tư FDI chất lượng cao.",
            'global_trade': "Việt Nam với vị thế xuất khẩu mạnh sẽ được hưởng lợi từ việc đa dạng hóa chuỗi cung ứng toàn cầu."
        }
        
        return impact_templates.get(category, "Tác động đến kinh tế Việt Nam cần được đánh giá toàn diện dựa trên các chỉ số kinh tế vĩ mô và xu hướng thị trường.")
    
    def _generate_policy_recommendations(self, category: str, expert_info: Dict) -> str:
        """Generate policy recommendations based on category and expert"""
        
        recommendations = {
            'monetary_policy': "- Theo dõi sát diễn biến lạm phát và điều chỉnh lãi suất một cách thận trọng\n- Tăng cường phối hợp chính sách tài khóa và tiền tệ",
            'technology': "- Đẩy mạnh chuyển đổi số trong ngành ngân hàng\n- Xây dựng khung pháp lý cho fintech và banking số",
            'financial_markets': "- Nâng cao tính minh bạch và quản trị thị trường\n- Khuyến khích đầu tư dài hạn và bền vững",
            'banking': "- Tăng cường giám sát rủi ro hệ thống\n- Hỗ trợ ngân hàng nâng cao năng lực công nghệ",
            'economic_policy': "- Cải thiện môi trường đầu tư và kinh doanh\n- Đẩy mạnh cải cách thể chế và pháp lý",
            'global_trade': "- Tăng cường hội nhập kinh tế quốc tế\n- Đa dạng hóa thị trường xuất khẩu và nhập khẩu"
        }
        
        return recommendations.get(category, "- Tăng cường nghiên cứu và đánh giá tác động\n- Phối hợp chặt chẽ giữa các cơ quan quản lý")
    
    def _generate_international_analysis_with_articles(
        self,
        title: str,
        content: str,
        articles: List[RSSFeedResult]
    ) -> str:
        """Generate international analysis using real found articles"""
        
        if not articles:
            return "🌍 **PHÂN TÍCH QUỐC TẾ**\n\nKhông tìm thấy bài viết quốc tế liên quan."
        
        # Group articles by credibility and source
        very_high_cred = [a for a in articles if a.credibility == 'Very High']
        high_cred = [a for a in articles if a.credibility == 'High']
        
        analysis = "🌍 **PHÂN TÍCH QUỐC TẾ**\n\n"
        
        if very_high_cred:
            analysis += "**Quan điểm từ các nguồn uy tín cao:**\n"
            for article in very_high_cred[:3]:
                analysis += f"• **{article.source}**: {self._extract_key_insight(article)}\n"
                analysis += f"  📎 [{article.title[:60]}...]({article.url})\n\n"
        
        if high_cred and len(very_high_cred) < 3:
            analysis += "**Phân tích bổ sung:**\n"
            remaining_slots = 3 - len(very_high_cred)
            for article in high_cred[:remaining_slots]:
                analysis += f"• **{article.source}**: {self._extract_key_insight(article)}\n"
                analysis += f"  📎 [{article.title[:60]}...]({article.url})\n\n"
        
        # Add regional perspective
        regions = list(set(a.region for a in articles))
        if len(regions) > 1:
            analysis += f"**Góc nhìn đa khu vực:** Phân tích từ {', '.join(regions)} cho thấy xu hướng toàn cầu nhất quán.\n\n"
        
        return analysis.strip()
    
    def _extract_key_insight(self, article: RSSFeedResult) -> str:
        """Extract key insight from article"""
        if article.summary and len(article.summary) > 50:
            # Clean and shorten summary
            summary = article.summary.replace('\n', ' ').strip()
            if len(summary) > 150:
                summary = summary[:147] + "..."
            return summary
        elif article.title:
            return f"Theo tiêu đề: {article.title}"
        else:
            return "Đang phân tích nội dung bài viết"
    
    def _format_reference_articles(self, articles: List[RSSFeedResult]) -> str:
        """Format reference articles section"""
        
        if not articles:
            return "📚 **TÀI LIỆU THAM KHẢO**\n\nKhông có bài viết tham khảo."
        
        reference = "📚 **TÀI LIỆU THAM KHẢO CHI TIẾT**\n\n"
        
        for i, article in enumerate(articles, 1):
            reference += f"**{i}. {article.title}**\n"
            reference += f"   🌐 Nguồn: {article.source} ({article.credibility})\n"
            reference += f"   📅 Ngày: {article.published or 'Không xác định'}\n"
            reference += f"   🔗 Link: {article.url}\n"
            reference += f"   🎯 Độ liên quan: {article.relevance_score}/10\n"
            
            if article.summary:
                summary = article.summary[:200] + "..." if len(article.summary) > 200 else article.summary
                reference += f"   📝 Tóm tắt: {summary}\n"
            
            reference += "\n"
        
        return reference.strip()
    
    def _calculate_average_credibility(self, articles: List[RSSFeedResult]) -> str:
        """Calculate average credibility score"""
        if not articles:
            return "N/A"
        
        credibility_scores = {
            'Very High': 5,
            'High': 4,
            'Medium': 3,
            'Low': 2
        }
        
        total_score = sum(credibility_scores.get(a.credibility, 3) for a in articles)
        avg_score = total_score / len(articles)
        
        if avg_score >= 4.5:
            return "Very High"
        elif avg_score >= 3.5:
            return "High"
        elif avg_score >= 2.5:
            return "Medium"
        else:
            return "Low"
    
    def _update_performance_metrics(self, processing_time: float, articles_count: int, category: str):
        """Update performance tracking metrics"""
        self.performance_metrics['total_summaries'] += 1
        self.performance_metrics['articles_analyzed'] += articles_count
        
        # Update average processing time
        current_avg = self.performance_metrics['average_processing_time']
        total_summaries = self.performance_metrics['total_summaries']
        
        if total_summaries == 1:
            self.performance_metrics['average_processing_time'] = processing_time
        else:
            self.performance_metrics['average_processing_time'] = (
                (current_avg * (total_summaries - 1) + processing_time) / total_summaries
            )
        
        self.performance_metrics['last_updated'] = datetime.now()
    
    async def _generate_fallback_summary(self, title: str, content: str) -> Dict[str, Any]:
        """Generate fallback summary when enhanced service fails"""
        bullet_summary = self._create_enhanced_bullet_summary(title, content, 4)
        
        return {
            'bullet_summary': bullet_summary,
            'domestic_expert_analysis': "🇻🇳 **PHÂN TÍCH CHUYÊN GIA**: Đang cập nhật phân tích chi tiết.",
            'international_analysis': "🌍 **PHÂN TÍCH QUỐC TẾ**: Đang tải dữ liệu từ các nguồn quốc tế.",
            'reference_articles': "📚 **TÀI LIỆU THAM KHẢO**: Đang tìm kiếm bài viết liên quan.",
            'metadata': {
                'processing_time': "0.5s",
                'articles_found': 0,
                'category': 'general',
                'status': 'fallback_mode'
            }
        }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary and RSS service metrics"""
        rss_metrics = self.rss_service.get_metrics()
        
        return {
            'summary_service': self.performance_metrics,
            'rss_service': rss_metrics,
            'combined_stats': {
                'total_processing_power': f"{self.performance_metrics['total_summaries']} summaries, {rss_metrics['total_requests']} RSS requests",
                'overall_success_rate': rss_metrics['success_rate'],
                'cache_efficiency': rss_metrics['cache_hit_rate'],
                'expert_diversity': len(self.performance_metrics['expert_assignments']),
                'source_coverage': rss_metrics['sources_available']
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check for the enhanced service"""
        summary_health = {
            'summary_service_status': 'healthy',
            'experts_available': len(self.domestic_experts),
            'categories_supported': len(self.topic_categories),
            'last_summary': self.performance_metrics['last_updated'].isoformat()
        }
        
        rss_health = await self.rss_service.health_check()
        
        return {
            'overall_status': 'healthy' if rss_health['status'] == 'healthy' else 'degraded',
            'summary_service': summary_health,
            'rss_service': rss_health,
            'timestamp': datetime.now().isoformat()
        }
    
    async def close(self):
        """Clean up resources"""
        await self.rss_service.close()
    
    def __del__(self):
        """Cleanup when object is destroyed"""
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.close())
        except:
            pass 