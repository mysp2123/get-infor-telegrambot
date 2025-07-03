import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Optional
import os
from dataclasses import dataclass
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import aiohttp
from bs4 import BeautifulSoup
import re
import time
import json
import random
from urllib.parse import urljoin, urlparse
import hashlib
import google.generativeai as genai
from dotenv import load_dotenv

# Import custom components
from .facebook_publisher import FacebookPublisher
from .google_ai_image_generator import GoogleAIImageGenerator

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

@dataclass
class NewsArticle:
    title: str
    content: str
    url: str
    source: str
    score: float = 0.0
    summary: str = ""
    category: str = ""
    sentiment: float = 0.0
    reading_time: int = 0
    word_count: int = 0
    content_hash: str = ""
    keywords: Optional[List[str]] = None
    credibility_score: float = 0.0
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
        self.word_count = len(self.content.split())
        self.reading_time = max(1, self.word_count // 200)
        self.content_hash = hashlib.md5(self.content.encode()).hexdigest()

class ContentAnalyzer:
    """AI Content Analysis"""
    
    def __init__(self):
        self.categories = {
            'politics': ['politics', 'government', 'election', 'policy', 'chính trị'],
            'business': ['business', 'economy', 'market', 'trade', 'kinh doanh'],
            'technology': ['technology', 'tech', 'AI', 'software', 'công nghệ'],
            'health': ['health', 'medical', 'medicine', 'y tế'],
            'sports': ['sports', 'football', 'basketball', 'thể thao'],
            'world': ['international', 'global', 'world', 'thế giới']
        }
    
    def classify_category(self, title: str, content: str) -> str:
        """Classify article category"""
        text = f"{title} {content}".lower()
        category_scores = {}
        
        for category, keywords in self.categories.items():
            score = sum(text.count(keyword) for keyword in keywords)
            category_scores[category] = score
        
        if not category_scores:
            return 'general'
        best_category = max(category_scores.keys(), key=lambda k: category_scores[k])
        return best_category if category_scores[best_category] > 0 else 'general'
    
    def analyze_sentiment(self, text: str) -> float:
        """Basic sentiment analysis"""
        positive_words = ['good', 'great', 'excellent', 'positive', 'success', 'tốt', 'tuyệt vời']
        negative_words = ['bad', 'terrible', 'negative', 'fail', 'crisis', 'xấu', 'tệ']
        
        text_lower = text.lower()
        pos_count = sum(text_lower.count(word) for word in positive_words)
        neg_count = sum(text_lower.count(word) for word in negative_words)
        
        if pos_count + neg_count == 0:
            return 0.0
        return (pos_count - neg_count) / (pos_count + neg_count)
    
    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """Extract keywords from text"""
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        words = [word for word in words if word not in stop_words]
        
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words[:max_keywords]]
    
    def calculate_credibility(self, article: NewsArticle) -> float:
        """Calculate article credibility score"""
        score = 0.5
        
        # Source credibility
        trusted_sources = ['reuters', 'bbc', 'apnews', 'vnexpress']
        if article.source.lower() in trusted_sources:
            score += 0.3
        
        # Content length
        if article.word_count > 200:
            score += 0.1
        
        # Check for suspicious content
        suspicious_words = ['shocking', 'unbelievable', 'sốc', 'không thể tin']
        if any(word in article.title.lower() for word in suspicious_words):
            score -= 0.1
        
        return max(0.0, min(1.0, score))

class NewsTelegramBot:
    def __init__(self, telegram_token: str, gemini_api_key: str, facebook_access_token: Optional[str] = None, facebook_page_id: Optional[str] = None):
        self.telegram_token = telegram_token
        self.gemini_api_key = gemini_api_key
        self.facebook_access_token = facebook_access_token
        self.facebook_page_id = facebook_page_id
        
        # Configure Gemini AI
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Initialize content analyzer
        self.analyzer = ContentAnalyzer()
        
        # Initialize Facebook Publisher (if token provided)
        self.facebook_publisher = None
        if facebook_access_token:
            try:
                self.facebook_publisher = FacebookPublisher(facebook_access_token, facebook_page_id)
                logger.info("Facebook Publisher initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Facebook Publisher: {e}")
        
        # Initialize Google AI Image Generator
        self.image_generator = GoogleAIImageGenerator(gemini_api_key)
        
        # News sources configuration
        self.news_sources = {
            'vnexpress': {
                'base_url': 'https://vnexpress.net',
                'sections': ['/kinh-doanh', '/the-gioi', '/thoi-su'],
                'selectors': {
                    'articles': ['h3.title-news a', 'h2.title-news a'],
                    'title': ['h1.title-detail', 'h1'],
                    'content': ['article.fck_detail p', '.Normal p'],
                }
            },
            'reuters': {
                'base_url': 'https://www.reuters.com',
                'sections': ['/world/', '/business/'],
                'selectors': {
                    'articles': ['a[data-testid="Heading"]', '.story-title a'],
                    'title': ['h1'],
                    'content': ['div[data-testid="paragraph"] p'],
                }
            },
            'apnews': {
                'base_url': 'https://apnews.com',
                'sections': ['/hub/business', '/hub/world-news'],
                'selectors': {
                    'articles': ['.PageListStandardB-title a', '.CardHeadline a'],
                    'title': ['h1'],
                    'content': ['.Article p', '.RichTextStoryBody p'],
                }
            }
        }
        
        # User agents for scraping
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        
        # Keywords for relevance scoring
        self.keywords = ["Trump", "US", "tariffs", "trade war", "tax", "e-commerce", 
                        "economy", "politics", "business", "international", "Vietnam"]
        
        # Initialize application
        self.application = Application.builder().token(telegram_token).build()
        self.setup_handlers()
        
        # Ensure data directories exist
        os.makedirs('./data', exist_ok=True)
        os.makedirs('./logs', exist_ok=True)

    def setup_handlers(self):
        """Setup telegram handlers"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        if not update.message:
            return
        
        welcome_text = """
🤖 **CHÀO MỪNG ĐẾN BOT TIN TỨC AI** 

🔥 **Tính năng chính:**
• 📰 Tìm kiếm tin tức từ 3 nguồn uy tín
• 🤖 AI phân tích và xếp hạng 
• ✍️ Tạo bài viết Facebook tiếng Việt
• 🎨 Tạo hình ảnh bằng Google AI
• 📱 Đăng tự động lên Facebook

🚀 **Sẵn sàng bắt đầu?**
        """
        
        keyboard = [
            [InlineKeyboardButton("🔍 BẮT ĐẦU TÌM TIN TỨC", callback_data="start_news_search")],
            [InlineKeyboardButton("⚙️ CÀI ĐẶT", callback_data="settings"), 
             InlineKeyboardButton("ℹ️ HƯỚNG DẪN", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    def get_random_headers(self) -> Dict[str, str]:
        """Generate random headers to avoid blocking"""
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,vi;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

    async def scrape_source(self, source_name: str, max_articles: int = 10) -> List[NewsArticle]:
        """Scrape news from a source"""
        if source_name not in self.news_sources:
            logger.error(f"Unknown source: {source_name}")
            return []
        
        source_config = self.news_sources[source_name]
        articles = []
        
        for section in source_config['sections']:
            try:
                section_articles = await self._scrape_section(
                    source_name, section, max_articles // len(source_config['sections'])
                )
                articles.extend(section_articles)
                await asyncio.sleep(random.uniform(1, 3))
                
            except Exception as e:
                logger.error(f"Error scraping {source_name}{section}: {e}")
        
        return articles[:max_articles]

    async def _scrape_section(self, source_name: str, section: str, max_items: int) -> List[NewsArticle]:
        """Scrape a section"""
        source_config = self.news_sources[source_name]
        base_url = source_config['base_url']
        section_url = urljoin(base_url, section)
        
        articles = []
        
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(
                headers=self.get_random_headers(),
                timeout=timeout
            ) as session:
                
                async with session.get(section_url) as response:
                    if response.status != 200:
                        logger.error(f"HTTP {response.status} for {section_url}")
                        return articles
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Find article links
                    article_links = []
                    for selector in source_config['selectors']['articles']:
                        links = soup.select(selector)
                        article_links.extend(links)
                        if len(article_links) >= max_items:
                            break
                    
                    # Remove duplicates
                    seen_hrefs = set()
                    unique_links = []
                    for link in article_links[:max_items]:
                        href = link.get('href')
                        if href and href not in seen_hrefs:
                            seen_hrefs.add(href)
                            unique_links.append(link)
                    
                    # Process links
                    for i, link in enumerate(unique_links):
                        try:
                            href = link.get('href')
                            if not href:
                                continue
                            
                            # Handle relative URLs
                            if href.startswith('http'):
                                article_url = href
                            else:
                                article_url = urljoin(base_url, href)
                            
                            title_hint = link.get_text(strip=True)
                            
                            # Scrape article content
                            article = await self._scrape_article(
                                source_name, article_url, title_hint, session
                            )
                            
                            if article:
                                # Enhance with AI analysis
                                article.category = self.analyzer.classify_category(article.title, article.content)
                                article.sentiment = self.analyzer.analyze_sentiment(f"{article.title} {article.content}")
                                article.keywords = self.analyzer.extract_keywords(f"{article.title} {article.content}")
                                article.credibility_score = self.analyzer.calculate_credibility(article)
                                
                                articles.append(article)
                            
                            await asyncio.sleep(random.uniform(0.5, 1.5))
                            
                        except Exception as e:
                            logger.error(f"Error processing article link: {e}")
        
        except Exception as e:
            logger.error(f"Error scraping section {section_url}: {e}")
        
        return articles

    async def _scrape_article(self, source_name: str, url: str, title_hint: str = "", session: Optional[aiohttp.ClientSession] = None) -> Optional[NewsArticle]:
        """Scrape article content"""
        source_config = self.news_sources[source_name]
        
        try:
            should_close_session = False
            if session is None:
                session = aiohttp.ClientSession(headers=self.get_random_headers())
                should_close_session = True
            
            try:
                async with session.get(url) as response:
                    if response.status != 200:
                        return None
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Remove unwanted elements
                    for tag in soup(['script', 'style', 'nav', 'header', 'footer']):
                        tag.decompose()
                    
                    # Extract title
                    title = ""
                    for selector in source_config['selectors']['title']:
                        try:
                            title_elem = soup.select_one(selector)
                            if title_elem:
                                title = title_elem.get_text(strip=True)
                                break
                        except:
                            continue
                    
                    if not title and title_hint:
                        title = title_hint
                    
                    if not title:
                        return None
                    
                    # Extract content
                    content_parts = []
                    for selector in source_config['selectors']['content']:
                        try:
                            content_elems = soup.select(selector)
                            for elem in content_elems:
                                text = elem.get_text(strip=True)
                                if text and len(text) > 20:
                                    content_parts.append(text)
                        except:
                            continue
                    
                    content = ' '.join(content_parts)
                    
                    # Skip if content is too short
                    if len(content) < 100:
                        return None
                    
                    # Create article
                    article = NewsArticle(
                        title=title,
                        content=content[:2000],  # Limit content length
                        url=url,
                        source=source_name.title()
                    )
                    
                    return article
                    
            finally:
                if should_close_session and session:
                    await session.close()
        
        except Exception as e:
            logger.error(f"Error scraping article {url}: {e}")
        
        return None

    async def fetch_news(self) -> List[NewsArticle]:
        """Fetch news from all sources"""
        all_articles = []
        
        # Scrape from all sources
        for source_name in self.news_sources.keys():
            try:
                articles = await self.scrape_source(source_name, max_articles=5)
                all_articles.extend(articles)
                logger.info(f"Scraped {len(articles)} articles from {source_name}")
            except Exception as e:
                logger.error(f"Error scraping {source_name}: {e}")
        
        # Remove duplicates based on content hash
        unique_articles = []
        seen_hashes = set()
        
        for article in all_articles:
            if article.content_hash not in seen_hashes:
                seen_hashes.add(article.content_hash)
                unique_articles.append(article)
        
        logger.info(f"Total unique articles: {len(unique_articles)}")
        return unique_articles

    def calculate_relevance_score(self, article: NewsArticle) -> float:
        """Calculate article relevance score"""
        score = 0.0
        text = f"{article.title} {article.content}".lower()
        
        # Keyword matching
        keyword_score = sum(text.count(keyword.lower()) for keyword in self.keywords)
        score += keyword_score * 0.1
        
        # Credibility score
        score += article.credibility_score * 0.3
        
        # Content length bonus
        if article.word_count > 300:
            score += 0.2
        
        return min(score, 1.0)

    async def generate_vietnamese_content(self, article: NewsArticle) -> str:
        """Generate Vietnamese content using Gemini AI"""
        try:
            prompt = f"""
            Tạo bài viết Facebook tiếng Việt từ tin tức này:
            
            Tiêu đề: {article.title}
            Nội dung: {article.content[:1500]}
            Nguồn: {article.source}
            
            Yêu cầu:
            - Viết bằng tiếng Việt tự nhiên
            - Tóm tắt thông tin chính
            - Thêm emoji phù hợp
            - Độ dài 150-200 từ
            - Cuối bài thêm hashtag liên quan
            """
            
            response = self.model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            logger.error(f"Error generating Vietnamese content: {e}")
            return f"📰 **{article.title}**\n\n{article.content[:300]}...\n\n🔗 Nguồn: {article.source}"

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        if not query or not query.data:
            return
            
        await query.answer()
        
        if query.data == "start_news_search":
            await self.process_news_search(query.message, context)
        elif query.data == "settings":
            await self.send_settings(query.message)
        elif query.data == "help":
            await self.send_help(query.message)
        elif query.data.startswith("post_facebook_"):
            article_index = int(query.data.split("_")[-1])
            await self.handle_facebook_post(update, context, article_index)
        elif query.data.startswith("regenerate_image_"):
            article_index = int(query.data.split("_")[-1])
            await self.handle_image_regeneration(update, context, article_index)
        elif query.data.startswith("edit_content_"):
            article_index = int(query.data.split("_")[-1])
            await self.handle_content_edit(update, context, article_index)
    
    async def handle_content_edit(self, update: Update, context: ContextTypes.DEFAULT_TYPE, article_index: int):
        """Handle content editing"""
        query = update.callback_query
        if not query or not query.message:
            return
        
        await query.answer()
        
        try:
            if not context.user_data:
                await query.message.reply_text("❌ Không tìm thấy dữ liệu bài viết.")
                return
                
            article_data = context.user_data.get(f'article_{article_index}')
            if not article_data:
                await query.message.reply_text("❌ Không tìm thấy dữ liệu bài viết.")
                return
            
            article = article_data['article']
            current_content = article_data['vietnamese_content']
            
            edit_msg = f"""
✏️ **CHỈNH SỬA NỘI DUNG #{article_index + 1}**

📰 **Tiêu đề gốc:** {article.title}

📝 **Nội dung hiện tại:**
{current_content}

💡 **Hướng dẫn:** Gửi tin nhắn mới để thay thế nội dung này.
            """
            
            await query.message.reply_text(edit_msg, parse_mode='Markdown')
            
            # Set context for next message
            context.user_data['editing_article'] = article_index
            
        except Exception as e:
            logger.error(f"Error in content edit: {e}")
            await query.message.reply_text(f"❌ Lỗi chỉnh sửa: {str(e)}")

    async def process_news_search(self, message, context):
        """Process news search request với đầy đủ tính năng"""
        # Send loading message
        loading_msg = await message.reply_text("🔍 Đang tìm kiếm tin tức mới nhất...")
        
        try:
            # Fetch news
            articles = await self.fetch_news()
            
            if not articles:
                await loading_msg.edit_text("❌ Không tìm thấy tin tức nào. Vui lòng thử lại sau.")
                return
            
            # Calculate relevance scores
            for article in articles:
                article.score = self.calculate_relevance_score(article)
            
            # Sort by relevance
            articles.sort(key=lambda x: x.score, reverse=True)
            
            # Show results
            await loading_msg.edit_text(f"✅ Tìm thấy {len(articles)} bài viết. Đang xử lý với AI...")
            
            # Process top articles với đầy đủ tính năng
            for i, article in enumerate(articles[:3]):  # Top 3 articles
                try:
                    # 1. Tạo nội dung Facebook tiếng Việt
                    vietnamese_content = await self.generate_vietnamese_content(article)
                    
                    # 2. Tạo hình ảnh
                    await loading_msg.edit_text(f"🎨 Đang tạo hình ảnh cho bài #{i+1}...")
                    image_path = self.image_generator.create_news_image(
                        article.title, 
                        article.content, 
                        article.keywords or []
                    )
                    
                    # 3. Hiển thị kết quả
                    message_text = f"""
📰 **BÀI VIẾT #{i+1}**
📊 Điểm: {article.score:.2f} | 📂 {article.category} | 🎭 Sentiment: {article.sentiment:.2f}

{vietnamese_content}

🔗 [Chi tiết]({article.url})
                    """
                    
                    # Send with image if available
                    if image_path and os.path.exists(image_path):
                        with open(image_path, 'rb') as photo:
                            sent_msg = await message.reply_photo(
                                photo=photo,
                                caption=message_text,
                                parse_mode='Markdown'
                            )
                    else:
                        sent_msg = await message.reply_text(
                            message_text, 
                            parse_mode='Markdown', 
                            disable_web_page_preview=True
                        )
                    
                    # 4. Thêm buttons cho hành động
                    keyboard = [
                        [
                            InlineKeyboardButton("🎨 Tạo lại ảnh", callback_data=f"regenerate_image_{i}"),
                            InlineKeyboardButton("✏️ Chỉnh sửa", callback_data=f"edit_content_{i}")
                        ],
                        [
                            InlineKeyboardButton("📱 ĐĂNG FACEBOOK", callback_data=f"post_facebook_{i}")
                        ]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await sent_msg.edit_reply_markup(reply_markup=reply_markup)
                    
                    # Store article data for callbacks
                    context.user_data[f'article_{i}'] = {
                        'article': article,
                        'vietnamese_content': vietnamese_content,
                        'image_path': image_path
                    }
                    
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Error processing article {i}: {e}")
                    error_msg = f"❌ Lỗi xử lý bài viết #{i+1}: {str(e)}"
                    await message.reply_text(error_msg)
        
        except Exception as e:
            logger.error(f"Error in news search: {e}")
            await loading_msg.edit_text("❌ Có lỗi xảy ra khi tìm kiếm tin tức. Vui lòng thử lại.")
    
    async def handle_facebook_post(self, update: Update, context: ContextTypes.DEFAULT_TYPE, article_index: int):
        """Handle Facebook posting"""
        query = update.callback_query
        if not query or not query.message:
            return
        
        await query.answer()
        
        if not self.facebook_publisher:
            await query.message.reply_text("❌ Facebook chưa được cấu hình. Vui lòng thêm FACEBOOK_ACCESS_TOKEN vào .env")
            return
        
        try:
            # Get article data
            if not context.user_data:
                await query.message.reply_text("❌ Không tìm thấy dữ liệu bài viết.")
                return
                
            article_data = context.user_data.get(f'article_{article_index}')
            if not article_data:
                await query.message.reply_text("❌ Không tìm thấy dữ liệu bài viết.")
                return
            
            article = article_data['article']
            vietnamese_content = article_data['vietnamese_content']
            image_path = article_data.get('image_path')
            
            # Show posting message
            posting_msg = await query.message.reply_text("📱 Đang đăng bài lên Facebook...")
            
            # Prepare image URL (upload to temporary hosting or use local file)
            image_url = None
            if image_path and os.path.exists(image_path):
                # For demo, we'll skip image upload and post text only
                # In production, you'd upload image to a hosting service first
                pass
            
            # Post to Facebook
            result = self.facebook_publisher.publish_post(
                message=vietnamese_content,
                image_url=image_url,
                link=article.url
            )
            
            if result['success']:
                success_msg = f"""
✅ **ĐĂNG FACEBOOK THÀNH CÔNG!**

📱 Post ID: {result.get('post_id')}
📝 Nội dung: {len(vietnamese_content)} ký tự
🔗 Link gốc: Đã đính kèm
                """
                await posting_msg.edit_text(success_msg, parse_mode='Markdown')
                
                # Log successful post
                logger.info(f"Successfully posted to Facebook: {result.get('post_id')}")
                
            else:
                error_msg = f"❌ **LỖI ĐĂNG FACEBOOK**\n\n{result.get('message', 'Lỗi không xác định')}"
                await posting_msg.edit_text(error_msg, parse_mode='Markdown')
                
        except Exception as e:
            logger.error(f"Error posting to Facebook: {e}")
            await query.message.reply_text(f"❌ Lỗi đăng Facebook: {str(e)}")
    
    async def handle_image_regeneration(self, update: Update, context: ContextTypes.DEFAULT_TYPE, article_index: int):
        """Handle image regeneration"""
        query = update.callback_query
        if not query or not query.message:
            return
        
        await query.answer()
        
        try:
            # Get article data
            if not context.user_data:
                await query.message.reply_text("❌ Không tìm thấy dữ liệu bài viết.")
                return
                
            article_data = context.user_data.get(f'article_{article_index}')
            if not article_data:
                await query.message.reply_text("❌ Không tìm thấy dữ liệu bài viết.")
                return
            
            article = article_data['article']
            
            # Show regeneration message
            regen_msg = await query.message.reply_text("🎨 Đang tạo lại hình ảnh...")
            
            # Generate new image
            new_image_path = self.image_generator.create_news_image(
                article.title,
                article.content,
                article.keywords or []
            )
            
            if new_image_path and os.path.exists(new_image_path):
                # Update stored data
                if context.user_data:
                    context.user_data[f'article_{article_index}']['image_path'] = new_image_path
                
                # Send new image
                with open(new_image_path, 'rb') as photo:
                    await regen_msg.delete()
                    await query.message.reply_photo(
                        photo=photo,
                        caption=f"🎨 **Hình ảnh mới cho bài #{article_index + 1}**\n\n📰 {article.title}",
                        parse_mode='Markdown'
                    )
            else:
                await regen_msg.edit_text("❌ Không thể tạo hình ảnh mới. Vui lòng thử lại.")
                
        except Exception as e:
            logger.error(f"Error regenerating image: {e}")
            await query.message.reply_text(f"❌ Lỗi tạo ảnh: {str(e)}")

    async def send_settings(self, message):
        """Send settings menu"""
        settings_text = """
⚙️ **CÀI ĐẶT BOT**

🔧 **Cấu hình hiện tại:**
• 🤖 Google AI: ✅ Hoạt động
• 📰 Nguồn tin: VnExpress, Reuters, AP News
• 🎯 Từ khóa: Trump, US, tariffs, trade war...

📝 **Phân tích AI:**
• Phân loại category tự động
• Phân tích sentiment
• Tính điểm credibility
• Trích xuất keywords
        """
        
        keyboard = [[InlineKeyboardButton("🏠 TRANG CHỦ", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await message.reply_text(settings_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def send_help(self, message):
        """Send help menu"""
        help_text = """
ℹ️ **HƯỚNG DẪN SỬ DỤNG**

🚀 **Bắt đầu:**
1. Nhấn "🔍 BẮT ĐẦU TÌM TIN TỨC"
2. Bot tự động tìm tin từ 3 nguồn uy tín
3. AI xếp hạng theo độ liên quan

🤖 **Tính năng AI:**
• Phân tích sentiment của bài viết
• Phân loại category tự động
• Tính điểm tin cậy (credibility)
• Tạo bài viết tiếng Việt

💡 **Mẹo sử dụng:**
• Gõ "menu", "bắt đầu" để xem menu
• Bot hiểu tiếng Việt có dấu
• Kết quả được sắp xếp theo độ liên quan
        """
        
        keyboard = [
            [InlineKeyboardButton("🔍 BẮT ĐẦU NGAY", callback_data="start_news_search")],
            [InlineKeyboardButton("🏠 TRANG CHỦ", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await message.reply_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages"""
        if not update.message or not update.message.text:
            return
        
        text = update.message.text.lower().strip()
        
        if any(keyword in text for keyword in ['menu', 'start', 'bắt đầu', 'bat dau']):
            await self.start_command(update, context)
        elif any(keyword in text for keyword in ['tìm tin', 'tim tin', 'news', 'tin tức']):
            await self.process_news_search(update.message, context)
        elif any(keyword in text for keyword in ['help', 'hướng dẫn', 'huong dan']):
            await self.send_help(update.message)
        elif any(keyword in text for keyword in ['settings', 'cài đặt', 'cai dat']):
            await self.send_settings(update.message)
        else:
            await update.message.reply_text(
                "🤖 Xin chào! Gõ 'menu' để xem các tùy chọn hoặc nhấn /start để bắt đầu."
            )

    def run(self):
        """Run the bot"""
        logger.info("Starting Telegram bot...")
        self.application.run_polling()

if __name__ == "__main__":
    load_dotenv()
    
    # Get credentials from environment
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    
    if not telegram_token or not gemini_api_key:
        logger.error("Missing required environment variables")
        exit(1)
    
    # Create and run bot
    bot = NewsTelegramBot(telegram_token, gemini_api_key)
    bot.run()
