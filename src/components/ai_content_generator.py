"""
AI Content Generator using Google Gemini for creating Facebook posts
"""

import os
import google.generativeai as genai
from typing import List, Optional
from src.components.news_scraper import NewsArticle
from src.components.facebook_scraper import FacebookPost
from src.utils.logger import get_logger

logger = get_logger(__name__)

class AIContentGenerator:
    """AI content generator for Facebook posts"""
    
    def __init__(self):
        self.api_key = os.getenv('GOOGLE_AI_API_KEY')
        if not self.api_key:
            raise ValueError("GOOGLE_AI_API_KEY not found in environment variables")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Vietnamese post templates and style guidelines
        self.style_guidelines = {
            'tone': 'expert, humorous, critical',
            'language': 'Vietnamese',
            'length': '250-400 words',
            'style': 'incorporate humor, criticism, slang where appropriate',
            'format': 'engaging Facebook post with emojis'
        }

    def generate_facebook_post(self, article: NewsArticle, 
                             related_posts: List[FacebookPost] = None) -> str:
        """
        Generate a Vietnamese Facebook post based on the article and related posts
        
        Args:
            article (NewsArticle): The selected news article
            related_posts (List[FacebookPost]): Related Facebook posts if any
            
        Returns:
            str: Generated Facebook post content
        """
        try:
            logger.info(f"Generating Facebook post for article: {article.title[:50]}...")
            
            # Prepare the prompt
            prompt = self._create_prompt(article, related_posts)
            
            # Generate content using Gemini
            response = self.model.generate_content(prompt)
            
            if response and response.text:
                generated_post = response.text.strip()
                logger.info("Facebook post generated successfully")
                return generated_post
            else:
                logger.error("Empty response from Gemini")
                return self._create_fallback_post(article)
                
        except Exception as e:
            logger.error(f"Error generating Facebook post: {str(e)}")
            return self._create_fallback_post(article)

    def _create_prompt(self, article: NewsArticle, 
                      related_posts: List[FacebookPost] = None) -> str:
        """Create a detailed prompt for Gemini"""
        
        prompt = f"""
Hãy viết một bài đăng Facebook bằng tiếng Việt về bài báo tin tức sau đây. 
Bài đăng cần có phong cách chuyên gia, có thể mang tính hài hước, phê phán, và sử dụng tiếng lóng phù hợp.

**THÔNG TIN BÁI BÁO:**
Tiêu đề: {article.title}
Nguồn: {article.source}
Tóm tắt: {article.summary}
Nội dung chính: {article.content[:1000]}...

**YÊU CẦU:**
- Độ dài: 250-400 từ
- Ngôn ngữ: Tiếng Việt
- Phong cách: Chuyên gia, có thể hài hước, phê phán
- Tông điệu: Thông minh, sâu sắc, có thể mỉa mai khi phù hợp
- Sử dụng emoji phù hợp
- Kết thúc với hashtag liên quan

**HƯỚNG DẪN VIẾT:**
1. Mở đầu bằng một câu hỏi hoặc nhận xét thu hút sự chú ý
2. Phân tích vấn đề một cách sâu sắc
3. Đưa ra quan điểm cá nhân hoặc dự đoán
4. Kết thúc bằng câu hỏi để tương tác với người đọc
5. Thêm 3-5 hashtag phù hợp

**CHỦ ĐỀ QUAN TRỌNG CẦN TẬP TRUNG:**
- Nếu liên quan đến Trump, thuế quan, thương mại: phân tích tác động đến kinh tế
- Nếu liên quan đến chính trị Mỹ: góc nhìn từ việc tác động đến thế giới
- Nếu liên quan đến kinh tế: phân tích xu hướng và cơ hội

"""

        # Add related posts context if available
        if related_posts:
            prompt += f"\n**BÀI ĐĂNG LIÊN QUAN ĐÃ CÓ:**\n"
            for i, post in enumerate(related_posts[:3]):
                prompt += f"Bài đăng {i+1}: {post.caption[:200]}...\n"
            
            prompt += "\nHãy tham khảo các bài đăng trên để tạo ra nội dung bổ sung hoặc có góc nhìn khác biệt.\n"

        prompt += """
**VÍ DỤ PHONG CÁCH MONG MUỐN:**
"🔥 Trump vừa tuyên bố tăng thuế quan lên 60% với hàng Trung Quốc - và thị trường đã 'điên' ngay lập tức! 

Nhìn con số này mà tôi chỉ muốn hỏi: liệu ai đó có tính toán kỹ chưa? 🤔 Thuế quan cao = giá hàng tăng = người tiêu dùng Mỹ chịu khổ. Đây không phải là 'thắng', mà là 'tự bắn vào chân' theo cách elegantly nhất có thể!

Dĩ nhiên, các CEO công nghệ đang cười thầm vì họ đã dự trù sẵn kế hoạch B rồi. Còn các startup nhỏ? Chắc đang ngồi khóc trong toilet... 😅

Các bạn nghĩ sao? Đây là nước cờ thông minh hay là 'all-in' kiểu casino? 

#TradeWar #Trump #Economy #TaxPolicy #Business"

Bây giờ hãy viết bài đăng cho bài báo trên theo phong cách tương tự:
"""
        
        return prompt

    def _create_fallback_post(self, article: NewsArticle) -> str:
        """Create a simple fallback post if AI generation fails"""
        
        fallback_post = f"""
📰 **Tin tức nổi bật từ {article.source}**

{article.title}

{article.summary[:200]}...

Đây là một diễn biến đáng chú ý mà chúng ta cần theo dõi. Các bạn nghĩ sao về vấn đề này?

🔗 Nguồn: {article.source}

#News #Update #Analysis
"""
        
        return fallback_post

    def refine_post(self, original_post: str, user_feedback: str) -> str:
        """
        Refine the post based on user feedback
        
        Args:
            original_post (str): Original generated post
            user_feedback (str): User's feedback or corrections
            
        Returns:
            str: Refined post
        """
        try:
            logger.info("Refining post based on user feedback")
            
            prompt = f"""
Hãy sửa đổi bài đăng Facebook sau đây dựa trên phản hồi của người dùng:

**BÀI ĐĂNG GỐC:**
{original_post}

**PHẢN HỒI CỦA NGƯỜI DÙNG:**
{user_feedback}

**YÊU CẦU:**
- Giữ nguyên phong cách và độ dài tương tự
- Áp dụng các thay đổi theo phản hồi
- Đảm bảo nội dung vẫn hấp dẫn và chuyên nghiệp
- Giữ nguyên tiếng Việt và emoji phù hợp

Hãy trả về bài đăng đã được sửa đổi:
"""
            
            response = self.model.generate_content(prompt)
            
            if response and response.text:
                refined_post = response.text.strip()
                logger.info("Post refined successfully")
                return refined_post
            else:
                logger.error("Empty response when refining post")
                return original_post
                
        except Exception as e:
            logger.error(f"Error refining post: {str(e)}")
            return original_post

    def create_post_summary(self, article: NewsArticle) -> str:
        """
        Create a short summary of the article for ranking display
        
        Args:
            article (NewsArticle): News article
            
        Returns:
            str: Short summary for Telegram display
        """
        try:
            prompt = f"""
Tạo một tóm tắt ngắn gọn (50-80 từ) bằng tiếng Việt cho bài báo sau:

Tiêu đề: {article.title}
Nguồn: {article.source}
Tóm tắt: {article.summary}

Yêu cầu:
- 50-80 từ
- Tập trung vào điểm chính
- Phong cách súc tích, hấp dẫn
- Phù hợp để hiển thị trong danh sách lựa chọn

Chỉ trả về tóm tắt, không cần thêm gì khác:
"""
            
            response = self.model.generate_content(prompt)
            
            if response and response.text:
                summary = response.text.strip()
                return summary
            else:
                # Fallback summary
                return f"{article.title[:100]}... (Nguồn: {article.source})"
                
        except Exception as e:
            logger.error(f"Error creating summary: {str(e)}")
            return f"{article.title[:100]}... (Nguồn: {article.source})"
