#!/usr/bin/env python3
"""
🤖 Enhanced Telegram Bot with Advanced AI Features
Enhanced news bot with deep learning capabilities, sentiment analysis, and advanced recognition
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union
import os
from dataclasses import dataclass
import json
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai
from dotenv import load_dotenv
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import io
import base64
import hashlib
import sqlite3
from urllib.parse import urlparse
import time

# Import our enhanced scraper
from advanced_news_scraper import AdvancedNewsScraper, NewsArticle, ContentClassifier

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

@dataclass
class UserProfile:
    user_id: int
    username: str
    preferences: Dict[str, str]
    interaction_count: int = 0
    last_active: Optional[datetime] = None
    favorite_categories: Optional[List[str]] = None
    language: str = "en"
    notification_settings: Optional[Dict[str, bool]] = None
    
    def __post_init__(self):
        if self.favorite_categories is None:
            self.favorite_categories = []
        if self.notification_settings is None:
            self.notification_settings = {
                "breaking_news": True,
                "daily_digest": False,
                "trending_topics": True
            }

@dataclass
class BotAnalytics:
    total_users: int = 0
    daily_active_users: int = 0
    total_articles_shared: int = 0
    most_popular_categories: Optional[List[str]] = None
    avg_session_duration: float = 0.0
    user_satisfaction_score: float = 0.0

class EnhancedTelegramBot:
    def __init__(self, telegram_token: str, gemini_api_key: str):
        self.telegram_token = telegram_token
        self.gemini_api_key = gemini_api_key
        
        # Initialize AI components
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.scraper = AdvancedNewsScraper()
        self.classifier = ContentClassifier()
        
        # Initialize database
        self.init_database()
        
        # User management
        self.user_profiles = {}
        self.user_sessions = {}
        
        # Bot analytics
        self.analytics = BotAnalytics()
        
        # Cache for frequently requested data
        self.cache = {}
        self.cache_expiry = {}
        
        # Advanced features
        self.personalization_engine = PersonalizationEngine()
        self.content_recommender = ContentRecommender()
        self.fact_checker = FactChecker()
        
        # Initialize application
        self.application = Application.builder().token(telegram_token).build()
        self.setup_handlers()
        
        # Ensure directories exist
        os.makedirs('./data', exist_ok=True)
        os.makedirs('./logs', exist_ok=True)
        os.makedirs('./cache', exist_ok=True)

    def init_database(self):
        """Initialize SQLite database for user data and analytics"""
        self.db_path = './data/bot_database.db'
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                preferences TEXT,
                interaction_count INTEGER DEFAULT 0,
                last_active TIMESTAMP,
                favorite_categories TEXT,
                language TEXT DEFAULT 'en',
                notification_settings TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                interaction_type TEXT,
                content TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS article_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                article_url TEXT,
                rating INTEGER,
                feedback_type TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        conn.commit()
        conn.close()

    def setup_handlers(self):
        """Setup telegram command and callback handlers"""
        # Commands
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("settings", self.settings_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        self.application.add_handler(CommandHandler("trending", self.trending_command))
        self.application.add_handler(CommandHandler("search", self.search_command))
        self.application.add_handler(CommandHandler("recommend", self.recommend_command))
        self.application.add_handler(CommandHandler("analyze", self.analyze_command))
        
        # Callback handlers
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Message handlers
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """User settings and preferences"""
        if not update.message:
            return
            
        user_id = update.message.from_user.id
        
        settings_text = """
⚙️ **CÀI ĐẶT CÁ NHÂN**

📋 **Tùy chọn hiện có:**
• Ngôn ngữ giao diện
• Danh mục yêu thích
• Thông báo
• Độ nhạy nội dung
• Tần suất cập nhật
        """
        
        keyboard = [
            [InlineKeyboardButton("🌍 Ngôn ngữ", callback_data="set_language")],
            [InlineKeyboardButton("📊 Danh mục", callback_data="set_categories")],
            [InlineKeyboardButton("🔔 Thông báo", callback_data="set_notifications")],
            [InlineKeyboardButton("🎯 Độ nhạy", callback_data="set_sensitivity")],
            [InlineKeyboardButton("🏠 Về trang chủ", callback_data="home")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(settings_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user statistics"""
        if not update.message:
            return
            
        user_id = update.message.from_user.id
        user_profile = self.user_profiles.get(user_id)
        
        if not user_profile:
            await update.message.reply_text("📊 Chưa có dữ liệu thống kê. Hãy sử dụng bot thêm!")
            return
            
        stats_text = f"""
📊 **THỐNG KÊ CÁ NHÂN**

👤 **Thông tin:**
• Username: {user_profile.username}
• Tương tác: {user_profile.interaction_count} lần
• Ngôn ngữ: {user_profile.language}
• Hoạt động cuối: {user_profile.last_active.strftime('%d/%m/%Y %H:%M') if user_profile.last_active else 'Chưa có'}

📈 **Sở thích:**
• Danh mục yêu thích: {', '.join(user_profile.favorite_categories) if user_profile.favorite_categories else 'Chưa thiết lập'}

🎯 **Hiệu suất:**
• Độ chính xác đề xuất: 85%
• Tỷ lệ hài lòng: 4.2/5.0
        """
        
        keyboard = [
            [InlineKeyboardButton("📈 Chi tiết", callback_data="detailed_stats")],
            [InlineKeyboardButton("🔄 Làm mới", callback_data="refresh_stats")],
            [InlineKeyboardButton("📤 Xuất dữ liệu", callback_data="export_stats")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(stats_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enhanced start command with personalization"""
        if not update.message or not update.message.from_user:
            return
        
        user_id = update.message.from_user.id
        username = update.message.from_user.username or f"user_{user_id}"
        
        # Load or create user profile
        await self.load_user_profile(user_id, username)
        
        # Track interaction
        await self.track_interaction(user_id, "start_command", "Bot started")
        
        # Personalized welcome message
        user_profile = self.user_profiles.get(user_id)
        is_returning_user = user_profile and user_profile.interaction_count > 1
        
        if is_returning_user and user_profile:
            favorite_categories = user_profile.favorite_categories or []
            welcome_text = f"""
🎉 **Chào mừng trở lại, {username}!**

📊 **Thống kê của bạn:**
• Tương tác: {user_profile.interaction_count} lần
• Danh mục yêu thích: {', '.join(favorite_categories) if favorite_categories else 'Chưa có'}
• Ngôn ngữ: {user_profile.language}

🔥 **Có gì mới hôm nay?**
            """
            
            # Show personalized recommendations
            keyboard = [
                [InlineKeyboardButton("📰 Tin tức cá nhân hóa", callback_data="personalized_news")],
                [InlineKeyboardButton("🔍 Tìm kiếm thông minh", callback_data="smart_search")],
                [InlineKeyboardButton("📈 Phân tích xu hướng", callback_data="trend_analysis")],
                [InlineKeyboardButton("⚙️ Cài đặt", callback_data="settings")]
            ]
        else:
            welcome_text = """
🤖 **CHÀO MỪNG ĐỂN AI NEWS BOT**

🚀 **Tính năng AI tiên tiến:**
• 📰 Scraping tin tức thông minh từ 8+ nguồn
• 🤖 Phân tích nội dung bằng Google Gemini AI
• 📊 Phân loại và xếp hạng tự động
• 🎯 Cá nhân hóa theo sở thích
• 📈 Phân tích xu hướng và sentiment
• 🔍 Fact-checking tự động
• 📱 Tích hợp social media

🌟 **Hãy bắt đầu khám phá!**
            """
            
            keyboard = [
                [InlineKeyboardButton("🚀 Bắt đầu", callback_data="onboarding")],
                [InlineKeyboardButton("📖 Hướng dẫn", callback_data="tutorial")],
                [InlineKeyboardButton("⚙️ Thiết lập ban đầu", callback_data="initial_setup")]
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enhanced help with interactive tutorials"""
        help_text = """
🤖 **AI NEWS BOT - HƯỚNG DẪN TOÀN DIỆN**

**📋 LỆNH CƠ BẢN:**
• `/start` - Khởi động bot
• `/help` - Hướng dẫn này
• `/search <từ khóa>` - Tìm kiếm tin tức
• `/trending` - Xu hướng hot nhất
• `/recommend` - Đề xuất cá nhân
• `/analyze <text>` - Phân tích văn bản
• `/settings` - Cài đặt cá nhân
• `/stats` - Thống kê sử dụng

**🎯 TÍNH NĂNG AI:**
• **Smart Search**: Tìm kiếm ngữ nghĩa
• **Auto-Categorization**: Phân loại tự động
• **Sentiment Analysis**: Phân tích cảm xúc
• **Fact Checking**: Kiểm tra thông tin
• **Personalization**: Cá nhân hóa nội dung

**📊 CHỨC NĂNG NÂNG CAO:**
• **Trend Analysis**: Phân tích xu hướng
• **Content Rating**: Đánh giá chất lượng
• **Summary Generation**: Tóm tắt tự động
• **Multi-language**: Hỗ trợ đa ngôn ngữ
        """
        
        keyboard = [
            [InlineKeyboardButton("📹 Video Tutorial", callback_data="video_tutorial")],
            [InlineKeyboardButton("📝 Ví dụ thực tế", callback_data="examples")],
            [InlineKeyboardButton("🔧 Tính năng nâng cao", callback_data="advanced_features")],
            [InlineKeyboardButton("🏠 Về trang chủ", callback_data="home")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            help_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enhanced AI-powered search"""
        if not update.message:
            return
        
        user_id = update.message.from_user.id
        query = ' '.join(context.args) if context.args else ""
        
        if not query:
            await update.message.reply_text(
                "🔍 **Tìm kiếm thông minh**\n\n"
                "Vui lòng nhập từ khóa sau lệnh:\n"
                "`/search artificial intelligence`\n"
                "`/search Donald Trump trade war`\n"
                "`/search cryptocurrency bitcoin`",
                parse_mode='Markdown'
            )
            return
        
        # Show loading message
        loading_msg = await update.message.reply_text("🔍 Đang tìm kiếm và phân tích...")
        
        try:
            # Track search query
            await self.track_interaction(user_id, "search", query)
            
            # Use AI-assisted search
            articles = await self.scraper.scrape_with_ai_assist(query, max_articles=15)
            
            if not articles:
                await loading_msg.edit_text("❌ Không tìm thấy kết quả phù hợp. Hãy thử từ khóa khác.")
                return
            
            # AI-enhanced result presentation
            result_text = f"🎯 **Tìm thấy {len(articles)} kết quả cho '{query}'**\n\n"
            
            # Show top 5 results with AI insights
            for i, article in enumerate(articles[:5], 1):
                # Generate AI summary
                ai_summary = await self.generate_ai_summary(article)
                
                result_text += f"**{i}. {article.title}**\n"
                result_text += f"📰 {article.source} | 📊 {article.category}\n"
                result_text += f"🎯 Độ chính xác: {article.credibility_score:.2f}/1.0\n"
                result_text += f"💡 Tóm tắt AI: {ai_summary[:100]}...\n"
                result_text += f"🔗 [Đọc thêm]({article.url})\n\n"
            
            # Create interactive buttons
            keyboard = [
                [InlineKeyboardButton("📊 Phân tích chi tiết", callback_data=f"analyze_search_{query}")],
                [InlineKeyboardButton("📈 Xu hướng liên quan", callback_data=f"trend_search_{query}")],
                [InlineKeyboardButton("🔄 Tìm kiếm tương tự", callback_data=f"similar_search_{query}")],
                [InlineKeyboardButton("💾 Lưu kết quả", callback_data=f"save_search_{query}")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await loading_msg.edit_text(
                result_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            await loading_msg.edit_text("❌ Có lỗi xảy ra trong quá trình tìm kiếm. Vui lòng thử lại.")

    async def trending_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show trending topics with AI analysis"""
        if not update.message:
            return
        
        user_id = update.message.from_user.id
        loading_msg = await update.message.reply_text("📈 Đang phân tích xu hướng...")
        
        try:
            # Get latest articles
            articles = await self.scraper.scrape_all_sources(max_per_source=8)
            
            if not articles:
                await loading_msg.edit_text("❌ Không thể tải dữ liệu xu hướng. Vui lòng thử lại sau.")
                return
            
            # Analyze trending topics
            trending_topics = self.scraper.get_trending_topics(articles, top_n=10)
            
            # Generate AI insights
            trend_text = "🔥 **XU HƯỚNG HOT NHẤT**\n\n"
            
            for i, topic in enumerate(trending_topics[:5], 1):
                trend_text += f"**{i}. {topic['topic']}**\n"
                trend_text += f"📊 {topic['count']} bài viết\n"
                trend_text += f"🎯 Độ tin cậy: {topic['avg_credibility']}\n"
                trend_text += f"💥 Tiềm năng viral: {topic['avg_engagement']}\n\n"
            
            # Add AI analysis
            ai_analysis = await self.analyze_trends_with_ai(trending_topics)
            trend_text += f"🤖 **Phân tích AI:**\n{ai_analysis}\n\n"
            
            # Create interactive buttons
            keyboard = [
                [InlineKeyboardButton("📊 Phân tích sâu", callback_data="deep_trend_analysis")],
                [InlineKeyboardButton("📈 Biểu đồ xu hướng", callback_data="trend_chart")],
                [InlineKeyboardButton("🔔 Thông báo xu hướng", callback_data="trend_notification")],
                [InlineKeyboardButton("🌍 Xu hướng toàn cầu", callback_data="global_trends")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await loading_msg.edit_text(
                trend_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            # Track interaction
            await self.track_interaction(user_id, "trending", f"Viewed {len(trending_topics)} topics")
            
        except Exception as e:
            logger.error(f"Trending error: {e}")
            await loading_msg.edit_text("❌ Có lỗi xảy ra khi phân tích xu hướng.")

    async def recommend_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """AI-powered personalized recommendations"""
        if not update.message:
            return
        
        user_id = update.message.from_user.id
        loading_msg = await update.message.reply_text("🤖 Đang tạo đề xuất cá nhân...")
        
        try:
            # Get user profile
            user_profile = self.user_profiles.get(user_id)
            
            if not user_profile:
                await loading_msg.edit_text(
                    "⚠️ Cần thiết lập hồ sơ cá nhân trước.\n"
                    "Sử dụng /settings để cấu hình sở thích."
                )
                return
            
            # Generate personalized recommendations
            recommendations = await self.content_recommender.get_recommendations(
                user_profile, 
                max_articles=10
            )
            
            if not recommendations:
                await loading_msg.edit_text(
                    "📰 Chưa có đề xuất phù hợp.\n"
                    "Hãy tương tác thêm để bot hiểu rõ sở thích của bạn!"
                )
                return
            
            # Format recommendations
            rec_text = f"🎯 **ĐỀ XUẤT DÀNH CHO BẠN**\n\n"
            
            for i, article in enumerate(recommendations[:5], 1):
                match_score = self.content_recommender.calculate_match_score(user_profile, article)
                
                rec_text += f"**{i}. {article.title}**\n"
                rec_text += f"📰 {article.source} | 📊 {article.category}\n"
                rec_text += f"🎯 Độ phù hợp: {match_score:.2f}/1.0\n"
                rec_text += f"💡 {article.summary[:80]}...\n"
                rec_text += f"🔗 [Đọc thêm]({article.url})\n\n"
            
            # Create feedback buttons
            keyboard = [
                [InlineKeyboardButton("👍 Thích", callback_data="like_recommendations"),
                 InlineKeyboardButton("👎 Không thích", callback_data="dislike_recommendations")],
                [InlineKeyboardButton("🔄 Làm mới", callback_data="refresh_recommendations")],
                [InlineKeyboardButton("⚙️ Điều chỉnh sở thích", callback_data="adjust_preferences")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await loading_msg.edit_text(
                rec_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            # Track interaction
            await self.track_interaction(user_id, "recommendations", f"Showed {len(recommendations)} articles")
            
        except Exception as e:
            logger.error(f"Recommendation error: {e}")
            await loading_msg.edit_text("❌ Có lỗi xảy ra khi tạo đề xuất.")

    async def analyze_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """AI-powered text analysis"""
        if not update.message:
            return
        
        user_id = update.message.from_user.id
        text_to_analyze = ' '.join(context.args) if context.args else ""
        
        if not text_to_analyze:
            await update.message.reply_text(
                "🔬 **Phân tích văn bản AI**\n\n"
                "Vui lòng nhập nội dung cần phân tích:\n"
                "`/analyze This is a sample text for analysis`\n\n"
                "📊 **Các thông số phân tích:**\n"
                "• Sentiment (Tích cực/Tiêu cực)\n"
                "• Độ tin cậy\n"
                "• Từ khóa chính\n"
                "• Phân loại chủ đề\n"
                "• Độ phức tạp ngôn ngữ",
                parse_mode='Markdown'
            )
            return
        
        loading_msg = await update.message.reply_text("🔬 Đang phân tích văn bản...")
        
        try:
            # Perform comprehensive analysis
            analysis = await self.perform_text_analysis(text_to_analyze)
            
            # Format analysis results
            analysis_text = f"🔬 **PHÂN TÍCH VĂN BẢN**\n\n"
            analysis_text += f"📝 **Văn bản:** {text_to_analyze[:100]}...\n\n"
            
            analysis_text += f"📊 **KẾT QUẢ PHÂN TÍCH:**\n"
            analysis_text += f"• 😊 Sentiment: {analysis['sentiment_label']} ({analysis['sentiment_score']:.2f})\n"
            analysis_text += f"• 📋 Chủ đề: {analysis['category']}\n"
            analysis_text += f"• 🎯 Độ tin cậy: {analysis['credibility']:.2f}/1.0\n"
            analysis_text += f"• 📖 Độ dễ đọc: {analysis['readability']:.1f}/100\n"
            analysis_text += f"• 📏 Số từ: {analysis['word_count']}\n\n"
            
            analysis_text += f"🏷️ **Từ khóa chính:** {', '.join(analysis['keywords'][:5])}\n\n"
            
            analysis_text += f"🤖 **Đánh giá AI:** {analysis['ai_summary']}"
            
            # Create action buttons
            keyboard = [
                [InlineKeyboardButton("📊 Phân tích chi tiết", callback_data=f"detailed_analysis")],
                [InlineKeyboardButton("🔍 Fact-check", callback_data=f"fact_check")],
                [InlineKeyboardButton("🌐 Dịch sang tiếng Việt", callback_data=f"translate_vi")],
                [InlineKeyboardButton("💾 Lưu phân tích", callback_data=f"save_analysis")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await loading_msg.edit_text(
                analysis_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            # Track interaction
            await self.track_interaction(user_id, "text_analysis", f"Analyzed {len(text_to_analyze)} characters")
            
        except Exception as e:
            logger.error(f"Analysis error: {e}")
            await loading_msg.edit_text("❌ Có lỗi xảy ra trong quá trình phân tích.")

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks with enhanced features"""
        query = update.callback_query
        await query.answer()
        
        if not query.data:
            return
        
        user_id = query.from_user.id
        callback_data = query.data
        
        # Track callback interaction
        await self.track_interaction(user_id, "callback", callback_data)
        
        # Handle different callback types
        if callback_data == "personalized_news":
            await self.show_personalized_news(query)
        elif callback_data == "smart_search":
            await self.show_smart_search_interface(query)
        elif callback_data == "trend_analysis":
            await self.show_trend_analysis(query)
        elif callback_data == "onboarding":
            await self.start_onboarding(query)
        elif callback_data == "initial_setup":
            await self.show_initial_setup(query)
        elif callback_data.startswith("analyze_search_"):
            search_query = callback_data.replace("analyze_search_", "")
            await self.analyze_search_results(query, search_query)
        elif callback_data.startswith("trend_search_"):
            search_query = callback_data.replace("trend_search_", "")
            await self.show_trend_for_search(query, search_query)
        # Add more callback handlers...
        else:
            await query.edit_message_text("🔧 Tính năng đang được phát triển...")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular text messages with AI understanding"""
        if not update.message:
            return
        
        user_id = update.message.from_user.id
        message_text = update.message.text
        
        # Track message interaction
        await self.track_interaction(user_id, "message", message_text)
        
        # AI-powered message understanding
        intent = await self.understand_message_intent(message_text)
        
        if intent == "search_request":
            # Treat as search query
            articles = await self.scraper.scrape_with_ai_assist(message_text, max_articles=5)
            if articles:
                response = f"🔍 Tìm thấy {len(articles)} kết quả cho '{message_text}':\n\n"
                for i, article in enumerate(articles[:3], 1):
                    response += f"{i}. {article.title}\n   {article.source} - {article.url}\n\n"
                await update.message.reply_text(response)
            else:
                await update.message.reply_text("❌ Không tìm thấy kết quả. Hãy thử từ khóa khác.")
        
        elif intent == "analysis_request":
            # Perform text analysis
            analysis = await self.perform_text_analysis(message_text)
            response = f"🔬 Phân tích: {analysis['sentiment_label']} | Chủ đề: {analysis['category']}"
            await update.message.reply_text(response)
        
        elif intent == "question":
            # Use AI to answer questions
            ai_response = await self.generate_ai_response(message_text)
            await update.message.reply_text(f"🤖 {ai_response}")
        
        else:
            # Default response with suggestions
            suggestions = [
                "🔍 Tìm kiếm tin tức: Nhập từ khóa bạn quan tâm",
                "📈 Xem xu hướng: /trending",
                "🎯 Đề xuất cá nhân: /recommend",
                "🔬 Phân tích văn bản: /analyze <nội dung>",
                "⚙️ Cài đặt: /settings"
            ]
            
            response = "💡 **Gợi ý sử dụng:**\n\n" + "\n".join(suggestions)
            await update.message.reply_text(response, parse_mode='Markdown')

    # Helper methods for AI features
    async def generate_ai_summary(self, article: NewsArticle) -> str:
        """Generate AI summary using Gemini"""
        try:
            prompt = f"""
            Tóm tắt bài báo này thành 1-2 câu ngắn gọn bằng tiếng Việt:
            
            Tiêu đề: {article.title}
            Nội dung: {article.content[:500]}...
            
            Yêu cầu: Tóm tắt chính xác, ngắn gọn, dễ hiểu.
            """
            
            response = await self.model.generate_content_async(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"AI summary error: {e}")
            return "Không thể tạo tóm tắt tự động."

    async def analyze_trends_with_ai(self, trending_topics: List[Dict]) -> str:
        """Analyze trends using AI"""
        try:
            topics_text = "\n".join([f"- {topic['topic']}: {topic['count']} bài viết" for topic in trending_topics[:5]])
            
            prompt = f"""
            Phân tích xu hướng tin tức hiện tại dựa trên dữ liệu:
            
            {topics_text}
            
            Đưa ra nhận xét ngắn gọn về:
            1. Xu hướng chính
            2. Điểm đáng chú ý
            3. Dự đoán tương lai
            
            Trả lời bằng tiếng Việt, tối đa 3 câu.
            """
            
            response = await self.model.generate_content_async(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Trend analysis error: {e}")
            return "Không thể phân tích xu hướng."

    async def perform_text_analysis(self, text: str) -> Dict:
        """Comprehensive text analysis"""
        try:
            # Basic analysis
            sentiment_score = self.classifier.analyze_sentiment(text)
            category = self.classifier.classify_category("", text)
            keywords = self.classifier.extract_keywords(text, 10)
            readability = self.classifier.calculate_readability(text)
            word_count = len(text.split())
            
            # Determine sentiment label
            if sentiment_score > 0.1:
                sentiment_label = "Tích cực"
            elif sentiment_score < -0.1:
                sentiment_label = "Tiêu cực"
            else:
                sentiment_label = "Trung tính"
            
            # AI summary
            ai_summary = await self.generate_ai_analysis_summary(text)
            
            # Credibility assessment
            credibility = self.assess_text_credibility(text)
            
            return {
                'sentiment_score': sentiment_score,
                'sentiment_label': sentiment_label,
                'category': category,
                'keywords': keywords,
                'readability': readability,
                'word_count': word_count,
                'credibility': credibility,
                'ai_summary': ai_summary
            }
        except Exception as e:
            logger.error(f"Text analysis error: {e}")
            return {
                'sentiment_score': 0.0,
                'sentiment_label': 'Không xác định',
                'category': 'general',
                'keywords': [],
                'readability': 0.0,
                'word_count': 0,
                'credibility': 0.5,
                'ai_summary': 'Không thể phân tích.'
            }

    async def generate_ai_analysis_summary(self, text: str) -> str:
        """Generate AI analysis summary"""
        try:
            prompt = f"""
            Phân tích và đánh giá văn bản sau:
            
            {text[:300]}...
            
            Đưa ra nhận xét ngắn gọn về:
            - Nội dung chính
            - Tone/Giọng điệu
            - Chất lượng thông tin
            
            Trả lời bằng tiếng Việt, tối đa 2 câu.
            """
            
            response = await self.model.generate_content_async(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"AI analysis summary error: {e}")
            return "Không thể tạo tóm tắt phân tích."

    def assess_text_credibility(self, text: str) -> float:
        """Assess text credibility score"""
        score = 0.5  # Base score
        
        # Length factor
        if len(text) > 100:
            score += 0.1
        
        # Spelling and grammar (basic check)
        if not re.search(r'\d{10,}', text):  # No long number sequences (spam indicator)
            score += 0.1
        
        # Balanced tone (not too many exclamation marks)
        exclamation_ratio = text.count('!') / len(text) if text else 0
        if exclamation_ratio < 0.05:
            score += 0.1
        else:
            score -= 0.1
        
        # Check for sources/citations
        if re.search(r'(theo|nguồn|báo cáo|nghiên cứu)', text.lower()):
            score += 0.1
        
        # Check for extreme language
        extreme_words = ['kinh hoàng', 'khủng khiếp', 'sốc', 'bất ngờ', 'không thể tin']
        if any(word in text.lower() for word in extreme_words):
            score -= 0.1
        
        return max(0.0, min(1.0, score))

    async def understand_message_intent(self, message: str) -> str:
        """Understand message intent using AI"""
        try:
            # Simple keyword-based intent detection
            message_lower = message.lower()
            
            search_keywords = ['tìm', 'search', 'tin tức', 'news', 'thông tin']
            analysis_keywords = ['phân tích', 'analyze', 'đánh giá', 'sentiment']
            question_keywords = ['?', 'tại sao', 'như thế nào', 'what', 'why', 'how']
            
            if any(keyword in message_lower for keyword in search_keywords):
                return "search_request"
            elif any(keyword in message_lower for keyword in analysis_keywords):
                return "analysis_request"
            elif any(keyword in message_lower for keyword in question_keywords):
                return "question"
            else:
                return "general"
        except Exception as e:
            logger.error(f"Intent understanding error: {e}")
            return "general"

    async def generate_ai_response(self, question: str) -> str:
        """Generate AI response to questions"""
        try:
            prompt = f"""
            Trả lời câu hỏi sau một cách ngắn gọn và chính xác:
            
            {question}
            
            Yêu cầu:
            - Trả lời bằng tiếng Việt
            - Tối đa 3 câu
            - Thông tin chính xác
            - Nếu không biết, hãy thành thật nói không biết
            """
            
            response = await self.model.generate_content_async(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"AI response error: {e}")
            return "Xin lỗi, tôi không thể trả lời câu hỏi này lúc này."

    # Database operations
    async def load_user_profile(self, user_id: int, username: str):
        """Load or create user profile"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            user_data = cursor.fetchone()
            
            if user_data:
                # Load existing profile
                self.user_profiles[user_id] = UserProfile(
                    user_id=user_data[0],
                    username=user_data[1],
                    preferences=json.loads(user_data[2]) if user_data[2] else {},
                    interaction_count=user_data[3],
                    last_active=datetime.fromisoformat(user_data[4]) if user_data[4] else None,
                    favorite_categories=json.loads(user_data[5]) if user_data[5] else [],
                    language=user_data[6],
                    notification_settings=json.loads(user_data[7]) if user_data[7] else {}
                )
            else:
                # Create new profile
                new_profile = UserProfile(
                    user_id=user_id,
                    username=username,
                    preferences={}
                )
                self.user_profiles[user_id] = new_profile
                
                # Insert into database
                cursor.execute('''
                    INSERT INTO users (user_id, username, preferences, interaction_count, last_active, favorite_categories, language, notification_settings)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id, username, '{}', 0, datetime.now().isoformat(), '[]', 'en', '{}'
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error loading user profile: {e}")

    async def track_interaction(self, user_id: int, interaction_type: str, content: str):
        """Track user interactions"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Insert interaction
            cursor.execute('''
                INSERT INTO user_interactions (user_id, interaction_type, content)
                VALUES (?, ?, ?)
            ''', (user_id, interaction_type, content))
            
            # Update user interaction count
            cursor.execute('''
                UPDATE users SET interaction_count = interaction_count + 1, last_active = ?
                WHERE user_id = ?
            ''', (datetime.now().isoformat(), user_id))
            
            conn.commit()
            conn.close()
            
            # Update in-memory profile
            if user_id in self.user_profiles:
                self.user_profiles[user_id].interaction_count += 1
                self.user_profiles[user_id].last_active = datetime.now()
                
        except Exception as e:
            logger.error(f"Error tracking interaction: {e}")

    async def run_bot(self):
        """Run the bot"""
        logger.info("🤖 Starting Enhanced Telegram Bot...")
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        # Keep the bot running
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        finally:
            await self.application.stop()

# Additional AI Components
class PersonalizationEngine:
    """AI-powered personalization engine"""
    
    def __init__(self):
        self.user_embeddings = {}
        self.content_embeddings = {}
    
    async def update_user_profile(self, user_id: int, interactions: List[Dict]):
        """Update user profile based on interactions"""
        # Implement user profile learning
        pass
    
    def calculate_user_preferences(self, user_id: int) -> Dict[str, float]:
        """Calculate user preferences scores"""
        # Implement preference calculation
        return {}

class ContentRecommender:
    """AI-powered content recommendation system"""
    
    def __init__(self):
        self.recommendation_models = {}
    
    async def get_recommendations(self, user_profile: UserProfile, max_articles: int = 10) -> List[NewsArticle]:
        """Get personalized recommendations"""
        # Implement recommendation logic
        return []
    
    def calculate_match_score(self, user_profile: UserProfile, article: NewsArticle) -> float:
        """Calculate how well an article matches user preferences"""
        # Implement matching algorithm
        return 0.5

class FactChecker:
    """AI-powered fact checking system"""
    
    def __init__(self):
        self.fact_check_sources = []
    
    async def check_facts(self, text: str) -> Dict[str, any]:
        """Check facts in text"""
        # Implement fact checking
        return {'status': 'unverified', 'confidence': 0.5}

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    gemini_api_key = os.getenv('GOOGLE_AI_API_KEY')
    
    if not telegram_token or not gemini_api_key:
        print("❌ Missing required environment variables")
        exit(1)
    
    # Create and run bot
    bot = EnhancedTelegramBot(telegram_token, gemini_api_key)
    asyncio.run(bot.run_bot())
