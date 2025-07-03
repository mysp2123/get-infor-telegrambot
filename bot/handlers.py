from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import asyncio
import re
import os
import logging
from datetime import datetime
from typing import List, Dict

from services.news_service import NewsService
from services.ai_service import AIService
from services.advanced_image_service import AdvancedImageService
from services.facebook_service import FacebookService
from services.market_data_service import MarketDataService
from services.market_scheduler import MarketScheduler
from services.ai_investment_analysis_service import AIInvestmentAnalysisService
from services.workflow_service import WorkflowService
from models.article import Article
from config import Config
from services.enhanced_financial_rss_service import EnhancedFinancialRSSService
from services.enhanced_ai_investment_analysis_service import EnhancedAIInvestmentAnalysisService

logger = logging.getLogger(__name__)

class BotHandlers:
    def __init__(self, news_service: NewsService, ai_service: AIService, 
                 advanced_image_service: AdvancedImageService, facebook_service: FacebookService,
                 logging_service, market_service: MarketDataService = None, market_scheduler: MarketScheduler = None):
        self.news_service = news_service
        self.ai_service = ai_service
        self.advanced_image_service = advanced_image_service
        self.facebook_service = facebook_service
        self.logging_service = logging_service
        self.market_service = market_service
        self.market_scheduler = market_scheduler
        self.user_sessions = {}
        self.config = Config()
        
        # Initialize AI Investment Analysis Service
        self.ai_investment_service = AIInvestmentAnalysisService()
        
        # Initialize Workflow Service for News-Facebook AI Agent
        self.workflow_service = WorkflowService(
            news_service, ai_service, advanced_image_service, 
            facebook_service, logging_service
        )
        
        # Share user_sessions between BotHandlers and WorkflowService
        self.workflow_service.user_sessions = self.user_sessions
        
        # Store logger for this module
        self.logger = logging.getLogger(__name__)
        
        # Add financial analysis services
        self.financial_rss_service = EnhancedFinancialRSSService()
        self.ai_investment_service = EnhancedAIInvestmentAnalysisService(
            financial_rss_service=self.financial_rss_service
        )
        
        logger.info("🤖 Enhanced Financial Analysis Services initialized")
    
    def _escape_markdown(self, text: str) -> str:
        """Safely escape markdown special characters to prevent parsing errors"""
        if not text:
            return ""
        
        # Escape markdown special characters
        special_chars = ['*', '_', '`', '[', ']', '(', ')', '~', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        
        for char in special_chars:
            text = text.replace(char, f'\\{char}')
        
        return text

    def _safe_markdown_message(self, text: str, use_markdown: bool = True) -> tuple[str, str]:
        """Return safe text and appropriate parse_mode"""
        if use_markdown:
            try:
                # Try to keep basic formatting but escape problematic content
                return text, 'Markdown'
            except:
                # Fallback to escaped text
                return self._escape_markdown(text), None
        else:
            return text, None

    async def _safe_send_message(self, context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str, **kwargs):
        """Safely send message with automatic markdown error handling"""
        try:
            # First try with Markdown if not disabled
            parse_mode = kwargs.get('parse_mode', 'Markdown')
            if parse_mode == 'Markdown':
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    **kwargs
                )
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    **kwargs
                )
        except Exception as e:
            if "parse entities" in str(e).lower() or "can't parse" in str(e).lower():
                # Remove problematic formatting and retry
                safe_text = self._escape_markdown(text)
                kwargs_safe = kwargs.copy()
                kwargs_safe.pop('parse_mode', None)  # Remove parse_mode
                
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=safe_text,
                    **kwargs_safe
                )
            else:
                # Re-raise other exceptions
                raise

    async def _safe_edit_message(self, message, text: str, **kwargs):
        """Safely edit message with automatic markdown error handling"""
        try:
            # First try with original formatting
            await message.edit_text(text, **kwargs)
        except Exception as e:
            if "parse entities" in str(e).lower() or "can't parse" in str(e).lower():
                # Remove problematic formatting and retry
                safe_text = self._escape_markdown(text)
                kwargs_safe = kwargs.copy()
                kwargs_safe.pop('parse_mode', None)  # Remove parse_mode
                
                await message.edit_text(safe_text, **kwargs_safe)
            else:
                # Re-raise other exceptions
                raise

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command"""
        welcome_message = """
🚀 **Chào mừng đến với AI News & Market Bot!**
*Bot tự động tạo tin tức & báo cáo thị trường với AI*

📰 **TIN TỨC & NỘI DUNG AI:**
• `/start` - Bắt đầu quy trình tin tức
• `/news` - Lấy tin tức mới nhất
• `/generate` - Tạo nội dung AI
• `Search:từ khóa` - Tìm tin theo chủ đề

🎨 **TẠO ẢNH AI (MỚI):**
• `/image` - Tạo ảnh từ text với Stability AI
• `/image_status` - Xem trạng thái API tạo ảnh
• Hỗ trợ: Stability AI, FLUX, SDXL, DeepAI
• Tự động chuyển API key khi lỗi

📊 **THỊ TRƯỜNG CHỨNG KHOÁN:**
• `/market` - Xem tình hình thị trường
• `/stocks VIC BID TCB` - Cổ phiếu Việt Nam
• `/global AAPL GOOGL` - Cổ phiếu quốc tế
• `/gold` - Giá vàng hiện tại
• `/report opening/closing` - Báo cáo chi tiết

🤖 **AI PHÂN TÍCH ĐẦU TƯ (ĐƠN GIẢN):**
• `/ai market` - Phân tích thị trường tổng quan
• `/ai stock VIC` - Phân tích cổ phiếu cụ thể  
• `/ai portfolio` - Tạo danh mục đầu tư thông minh
• `/ai gold` - Phân tích giá vàng
• `/ai sentiment` - Sentiment thị trường

⏰ **LỊCH BÁO CÁO TỰ ĐỘNG:**
• `/schedule` - Xem lịch báo cáo
• `/subscribe` - Đăng ký nhận báo cáo
• `/unsubscribe` - Hủy đăng ký
• Tự động: 8:45, 11:35, 12:55, 15:05, 19:00

🔧 **QUẢN LÝ & TRẠNG THÁI:**
• `/help` - Hướng dẫn chi tiết
• `/status` - Trạng thái hệ thống & API
• `/api_health` - Kiểm tra tình trạng API keys

💡 **BẮT ĐẦU:**
Gửi **"Start"** để bắt đầu quy trình tin tức tự động!
Hoặc thử `/image beautiful sunset landscape` để tạo ảnh AI!

🔥 **Tính năng mới:** API key rotation, web scraping, Stability AI premium
        """
        await update.message.reply_text(welcome_message, parse_mode='Markdown')

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command"""
        help_message = """
📋 **HƯỚNG DẪN SỬ DỤNG CHI TIẾT**

**🎨 TẠO ẢNH AI (TÍNH NĂNG MỚI):**
• `/image prompt` - Tạo ảnh từ mô tả
• `/image beautiful landscape sunset` - Ví dụ tạo ảnh
• Hỗ trợ: Tiếng Việt & Tiếng Anh
• Chất lượng: Premium với Stability AI
• Fallback: Tự động chuyển API khi lỗi

**📰 QUY TRÌNH TIN TỨC:**
• Gửi "Start" để bắt đầu
• Bot thu thập tin từ 15+ nguồn
• AI phân tích & tạo nội dung tiếng Việt
• Tự động tạo ảnh minh họa
• Đăng lên Facebook tự động

**🔍 TÌM KIẾM THEO CHỦ ĐỀ:**
• `Search:công nghệ AI` - Tin về AI
• `Search:kinh tế Việt Nam` - Tin kinh tế
• `Search:chứng khoán` - Tin thị trường
• Yêu cầu: 2-5 từ khóa, mỗi từ 2-20 ký tự

**📊 THỊ TRƯỜNG CHỨNG KHOÁN:**
• `/market` - Tổng quan thị trường
• `/stocks VIC BID TCB VCB` - Cổ phiếu VN
• `/global AAPL GOOGL MSFT` - Cổ phiếu US
• `/gold` - Giá vàng USD & VND
• `/report opening` - Báo cáo mở cửa
• `/report closing` - Báo cáo đóng cửa

**⏰ LỊCH TỰ ĐỘNG (GMT+7):**
• 08:45 - Báo cáo mở cửa thị trường
• 11:35 - Tổng kết buổi sáng  
• 12:55 - Dự báo buổi chiều
• 15:05 - Báo cáo đóng cửa
• 19:00 - Phân tích cuối ngày
• 17:00 (Thứ 6) - Tổng kết tuần

**🔧 QUẢN LÝ HỆ THỐNG:**
• `/status` - Trạng thái bot & services
• `/api_health` - Tình trạng API keys
• `/image_status` - Trạng thái tạo ảnh
• `/schedule add "Tên" 16:30` - Thêm lịch
• `/subscribe opening closing` - Chọn loại báo cáo

**🚀 TÍNH NĂNG NÂNG CAO:**
• API Key Rotation: Tự động chuyển key khi lỗi
• Web Scraping: Thu thập ảnh chất lượng cao
• AI Context Analysis: Phân tích nội dung thông minh
• Multi-provider Fallback: 4+ nhà cung cấp AI
• Enhanced Image Quality: Logo, filter, resize tự động

**❓ HỖ TRỢ:**
Gặp lỗi? Liên hệ admin hoặc gửi `/status` để kiểm tra!
        """
        await update.message.reply_text(help_message, parse_mode='Markdown')

    def _validate_keywords(self, keywords_text: str) -> tuple[bool, str]:
        """Validate keywords: 2-5 words, Vietnamese/English only"""
        # Clean and split keywords
        words = re.findall(r'[a-zA-ZÀ-ỹ]+', keywords_text)
        
        if len(words) < 2:
            return False, "❌ Cần ít nhất 2 từ khóa"
        elif len(words) > 5:
            return False, "❌ Tối đa 5 từ khóa"
        
        # Check word length
        for word in words:
            if len(word) < 2:
                return False, f"❌ Từ khóa '{word}' quá ngắn (tối thiểu 2 ký tự)"
            elif len(word) > 20:
                return False, f"❌ Từ khóa '{word}' quá dài (tối đa 20 ký tự)"
        
        return True, " ".join(words)
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages - including 'Start' trigger and keyword search"""
        user_id = update.effective_user.id
        message_text = update.message.text.strip()
        
        # Check for risk profile selection
        if context.user_data.get('waiting_for_risk_profile'):
            await self.handle_risk_profile_selection(update, context, message_text)
            return
        
        # Check for "Start" trigger - News-Facebook AI Agent Workflow
        if message_text.lower() == 'start' or message_text == "🔄 Bắt đầu lại":
            # Start the complete News-Facebook AI Agent Workflow
            await self.workflow_service.start_workflow(user_id, context, update.message.chat_id)
            return
        
        # Check for keyword search
        if message_text.lower().startswith('search:'):
            keywords_text = message_text[7:].strip()  # Remove 'search:' prefix
            
            # Validate keywords
            is_valid, result = self._validate_keywords(keywords_text)
            if not is_valid:
                await update.message.reply_text(
                    f"{result}\n\n"
                    "🔍 **Định dạng đúng:** Search:từ khóa 1 từ khóa 2\n"
                    "📝 **Yêu cầu:** 2-5 từ, mỗi từ 2-20 ký tự\n\n"
                    "💡 **Ví dụ:**\n"
                    "• Search:công nghệ AI\n"
                    "• Search:kinh tế Việt Nam"
                )
                return
            
            # Start keyword search
            await self.fetch_news_with_keywords(update, context, result)
            return
        
        # Check for article selection from reply keyboard
        if message_text in ["🥇 Chọn bài 1", "🥈 Chọn bài 2", "🥉 Chọn bài 3"]:
            await self.handle_article_selection_text(update, context, message_text)
            return
        
                # Check for sources review from reply keyboard
        if message_text in ["✅ Sử dụng các nguồn này", "❌ Bỏ qua và tạo bài thường", "🔄 Tìm lại nguồn khác"]:
            await self.handle_sources_review_text(update, context, message_text)
            return

        # Check for post approval from reply keyboard
        if message_text in ["✅ Duyệt bài viết", "✏️ Chỉnh sửa bài viết"]:
            await self.handle_post_approval_text(update, context, message_text)
            return

        # Check for image approval from reply keyboard  
        if message_text in ["✅ Duyệt ảnh", "🔄 Tạo lại ảnh"]:
            await self.handle_image_approval_text(update, context, message_text)
            return
        
# Removed complex keyboard commands - now using simple /ai commands
        
        # Check for restart/reset
        if message_text in ["🔄 Bắt đầu lại", "Start", "start", "/start"]:
            # Clear both old and new workflow sessions
            if user_id in self.user_sessions:
                del self.user_sessions[user_id]
            self.workflow_service.clear_user_session(user_id)
            
            if message_text == "🔄 Bắt đầu lại":
                await update.message.reply_text(
                    "🔄 **Đã reset quy trình**\n\n"
                    "📱 Gửi 'Start' để bắt đầu quy trình tin tức mới\n"
                    "🔍 Hoặc 'Search:từ khóa' để tìm kiếm theo chủ đề",
                    reply_markup=ReplyKeyboardRemove()
                )
            else:
                # Start new workflow automatically
                await self.workflow_service.start_workflow(user_id, context, update.message.chat_id)
            return
        
        # Handle workflow text interactions (edit requests, selections, etc.)
        workflow_session = self.workflow_service.get_user_session(user_id)
        if workflow_session:
            current_state = workflow_session.get('state')
            current_step = workflow_session.get('step')  # Also check step
            
            # Debug info for troubleshooting
            logger.info(f"User {user_id} workflow state: {current_state}, step: {current_step}, message: {message_text}")
            
            # Handle article selection from workflow (both old format and new)
            if (current_state == 'selecting_article' or current_step == 'selecting_article') and (message_text in ["1️⃣ Chọn bài 1", "2️⃣ Chọn bài 2", "3️⃣ Chọn bài 3", "🔄 Bắt đầu lại"] or message_text.startswith('Bài ')):
                try:
                    logger.info(f"Calling handle_article_selection_text for user {user_id} with message: {message_text}")
                    await self.workflow_service.handle_article_selection_text(user_id, message_text, context, update.message.chat_id)
                    logger.info(f"Successfully handled article selection for user {user_id}")
                except Exception as article_error:
                    logger.error(f"ERROR in handle_article_selection_text for user {user_id}: {article_error}")
                    import traceback
                    logger.error(f"Full traceback: {traceback.format_exc()}")
                    # Send error message to user
                    try:
                        await context.bot.send_message(
                            chat_id=update.message.chat_id,
                            text=f"❌ Lỗi xử lý chọn bài viết: {str(article_error)}\n\nVui lòng gửi 'Start' để thử lại."
                        )
                    except:
                        pass
                return
            
            # Handle post approval from workflow (PRIORITY CHECK)
            elif (current_state == 'approving_post' or 'generated_post' in workflow_session) and message_text in ["✅ Phê duyệt bài viết", "✏️ Chỉnh sửa bài viết", "🔄 Bắt đầu lại"]:
                # Fix state if needed
                if current_state != 'approving_post' and 'generated_post' in workflow_session:
                    workflow_session['state'] = 'approving_post'
                    workflow_session['step'] = 'approving_post'
                    logger.info(f"Fixed workflow state for user {user_id} to approving_post")
                
                if message_text == "✅ Phê duyệt bài viết":
                    await self.workflow_service.handle_post_approval_text(user_id, 'approve', context, update.message.chat_id)
                elif message_text == "✏️ Chỉnh sửa bài viết":
                    await self.workflow_service.handle_post_approval_text(user_id, 'edit', context, update.message.chat_id)
                elif message_text == "🔄 Bắt đầu lại":
                    self.workflow_service.clear_user_session(user_id)
                    await update.message.reply_text(
                        "🔄 **Đã reset quy trình**\n\n📱 Gửi 'Start' để bắt đầu lại",
                        reply_markup=ReplyKeyboardRemove()
                    )
                return
                
            # Handle writing style selection from workflow (if no generated_post yet)
            elif current_step == 'writing_style_selection' and 'generated_post' not in workflow_session:
                try:
                    logger.info(f"Calling handle_writing_style_selection for user {user_id} with message: {message_text}")
                    await self.workflow_service.handle_writing_style_selection(user_id, message_text, context, update.message.chat_id)
                    logger.info(f"Successfully handled writing style selection for user {user_id}")
                except Exception as style_error:
                    logger.error(f"ERROR in handle_writing_style_selection for user {user_id}: {style_error}")
                    import traceback
                    logger.error(f"Full traceback: {traceback.format_exc()}")
                    # Send error message to user
                    try:
                        await context.bot.send_message(
                            chat_id=update.message.chat_id,
                            text=f"❌ Lỗi xử lý phong cách viết: {str(style_error)}\n\nVui lòng gửi 'Start' để thử lại."
                        )
                    except:
                        pass
                return
            
            # Handle custom style input from workflow (if no generated_post yet)
            elif current_step == 'custom_style_input' and 'generated_post' not in workflow_session:
                await self.workflow_service.handle_custom_style_input(user_id, message_text, context, update.message.chat_id)
                return
            
            # Handle content approval from workflow (NEW)
            elif (current_state == 'approving_content' or current_step == 'content_approval') and message_text in ["✅ Chấp nhận nội dung", "🔄 Tạo bài viết mới", "🔄 Bắt đầu lại"]:
                if message_text == "✅ Chấp nhận nội dung":
                    # User accepts content, continue to image generation
                    workflow_session['state'] = 'generating_image'
                    await context.bot.send_message(
                        chat_id=update.message.chat_id,
                        text="✅ **Đã chấp nhận nội dung!**\n\n🎨 **Chuyển sang tạo hình ảnh...**",
                        reply_markup=ReplyKeyboardRemove(),
                        parse_mode='Markdown'
                    )
                    await self.workflow_service._step4_generate_image(user_id, context, update.message.chat_id)
                elif message_text == "🔄 Tạo bài viết mới":
                    # User wants to regenerate content, go back to writing style selection
                    workflow_session['state'] = 'selecting_writing_style'
                    workflow_session['step'] = 'writing_style_selection'
                    await context.bot.send_message(
                        chat_id=update.message.chat_id,
                        text="🔄 **Tạo bài viết mới!**\n\n📝 **Chọn lại phong cách viết...**",
                        reply_markup=ReplyKeyboardRemove(),
                        parse_mode='Markdown'
                    )
                    await self.workflow_service._step2_5_select_writing_style(user_id, context, update.message.chat_id, workflow_session['selected_article'])
                elif message_text == "🔄 Bắt đầu lại":
                    self.workflow_service.clear_user_session(user_id)
                    await update.message.reply_text(
                        "🔄 **Đã reset quy trình**\n\n📱 Gửi 'Start' để bắt đầu lại",
                        reply_markup=ReplyKeyboardRemove()
                    )
                return
            
            # Handle image approval from workflow
            elif (current_state == 'approving_image' or 'generated_image' in workflow_session) and message_text in ["✅ Phê duyệt hình ảnh", "🔄 Tạo lại hình ảnh", "🔄 Bắt đầu lại"]:
                # Fix state if needed
                if current_state != 'approving_image' and 'generated_image' in workflow_session:
                    workflow_session['state'] = 'approving_image'
                    workflow_session['step'] = 'approving_image'
                    logger.info(f"Fixed workflow state for user {user_id} to approving_image")
                
                if message_text == "✅ Phê duyệt hình ảnh":
                    await self.workflow_service.handle_image_approval_text(user_id, 'approve', context, update.message.chat_id)
                elif message_text == "🔄 Tạo lại hình ảnh":
                    await self.workflow_service.handle_image_approval_text(user_id, 'regenerate', context, update.message.chat_id)
                elif message_text == "🔄 Bắt đầu lại":
                    self.workflow_service.clear_user_session(user_id)
                    await update.message.reply_text(
                        "🔄 **Đã reset quy trình**\n\n📱 Gửi 'Start' để bắt đầu lại",
                        reply_markup=ReplyKeyboardRemove()
                    )
                return
            
            # Handle post editing
            elif current_state == 'editing_post':
                # User is providing edit request for post
                await self.workflow_service.handle_post_edit_request(user_id, message_text, context, update.message.chat_id)
                return
        
        # Handle other workflow steps
        if user_id in self.user_sessions:
            session = self.user_sessions[user_id]
            
            if session.get('step') == 'waiting_edit_feedback':
                # User provided feedback for post editing
                original_content = session.get('post_content', '')
                
                await update.message.reply_text("🔄 Đang chỉnh sửa bài viết theo yêu cầu...")
                
                try:
                    edited_content = await self.ai_service.edit_post_content(
                        original_content, message_text
                    )
                    
                    session['post_content'] = edited_content
                    session['step'] = 'post_approval'
                    
                    # Create approval buttons (reply keyboard)
                    keyboard = [
                        [KeyboardButton("✅ Duyệt bài viết")],
                        [KeyboardButton("✏️ Chỉnh sửa bài viết")]
                    ]
                    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
                    
                    await update.message.reply_text(
                        f"📝 **Bài viết đã được chỉnh sửa:**\n\n{edited_content}\n\n"
                        f"👆 Chọn hành động:",
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )
                    
                except Exception as e:
                    error_message = f"❌ Lỗi khi chỉnh sửa: {str(e)}"
                    safe_text, parse_mode = self._safe_markdown_message(error_message, use_markdown=False)
                    await update.message.reply_text(safe_text, parse_mode=parse_mode)
        else:
            # No active session
            await update.message.reply_text(
                "🤔 Hiện tại không có quy trình nào đang chạy.\n\n"
                "📱 Gửi 'Start' để bắt đầu quy trình tìm tin tức\n"
                "🔍 Hoặc 'Search:từ khóa' để tìm kiếm theo từ khóa\n"
                "📞 Hoặc /start để xem hướng dẫn"
            )
    
    async def handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle voice messages"""
        await update.message.reply_text(
            "🎤 **Tin nhắn thoại đã nhận!**\n\n"
            "🤖 Hiện tại bot chưa hỗ trợ xử lý tin nhắn thoại.\n"
            "📝 Vui lòng gửi tin nhắn text thay thế.\n\n"
            "💡 Gửi 'Start' để bắt đầu quy trình tìm tin tức!\n"
            "🔍 Hoặc 'Search:từ khóa' để tìm kiếm theo chủ đề"
        )

    async def fetch_news_with_keywords(self, update: Update, context: ContextTypes.DEFAULT_TYPE, keywords: str):
        """Handle news fetching with specific keywords"""
        user_id = update.effective_user.id
        
        # Send initial message
        progress_message = await update.message.reply_text(
            f"🔍 **Đang tìm kiếm tin tức về: '{keywords}'**\n\n"
            "📰 Guardian: Đang tải...\n"
            "📰 AP News: Đang tải...\n"
            "📰 Reuters: Đang tải...\n\n"
            "⏳ Vui lòng đợi..."
        )
        
        # Log start of process
        await self.logging_service.log_news_fetch_start()
        
        try:
            # Fetch and rank articles with keywords
            articles = await self.news_service.fetch_news_with_keywords(keywords)
            
            if not articles:
                await progress_message.edit_text(
                    f"❌ **Không tìm thấy tin tức về '{keywords}'**\n\n"
                    "💡 **Thử:**\n"
                    "• Sử dụng từ khóa khác\n"
                    "• Gửi 'Start' để xem tin tức tổng quát\n"
                    "• Kiểm tra kết nối mạng"
                )
                return
            
            # Continue with normal flow
            await self._process_articles(update, progress_message, articles, user_id, f"về '{keywords}'")
            
        except Exception as e:
            error_message = f"❌ **Lỗi khi tìm kiếm tin tức:** {str(e)}"
            safe_text, parse_mode = self._safe_markdown_message(error_message, use_markdown=False)
            await progress_message.edit_text(safe_text, parse_mode=parse_mode)
            await self.logging_service.log_error("news_fetch", str(e))
    
    async def fetch_news(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle news fetching and ranking - triggered by 'Start' message"""
        user_id = update.effective_user.id
        
        # Send initial message
        progress_message = await update.message.reply_text(
            "🔍 **Đang tìm kiếm tin tức mới nhất...**\n\n"
            "📰 Guardian: Đang tải...\n"
            "📰 AP News: Đang tải...\n"
            "📰 Reuters: Đang tải...\n\n"
            "⏳ Vui lòng đợi..."
        )
        
        # Log start of process
        await self.logging_service.log_news_fetch_start()
        
        try:
            # Fetch and rank articles
            articles = await self.news_service.fetch_all_news()
            
            if not articles:
                await progress_message.edit_text(
                    "❌ **Không tìm thấy tin tức phù hợp**\n\n"
                    "🔄 Vui lòng thử lại sau hoặc kiểm tra kết nối mạng"
                )
                return
            
            # Continue with normal flow
            await self._process_articles(update, progress_message, articles, user_id, "mới nhất")
            
        except Exception as e:
            error_message = f"❌ **Lỗi khi tìm kiếm tin tức:** {str(e)}"
            safe_text, parse_mode = self._safe_markdown_message(error_message, use_markdown=False)
            await progress_message.edit_text(safe_text, parse_mode=parse_mode)
            await self.logging_service.log_error("news_fetch", str(e))

    async def _process_articles(self, update: Update, progress_message, articles, user_id: int, search_type: str):
        """Common method to process articles after fetching"""
        # Update progress
        await progress_message.edit_text(
            f"✅ **Đã tìm thấy tin tức {search_type}!**\n\n"
            "🤖 Đang phân tích và xếp hạng bằng AI...\n"
            "📊 Tính điểm liên quan và sức hấp dẫn..."
        )
        
        # Generate summaries using Gemini
        summaries = await self.ai_service.summarize_articles(articles)
        
        # Store in user session
        self.user_sessions[user_id] = {
            'articles': articles,
            'summaries': summaries,
            'step': 'article_selection'
        }
        
        # Create reply keyboard for article selection  
        keyboard = [
            [KeyboardButton("🥇 Chọn bài 1")],
            [KeyboardButton("🥈 Chọn bài 2")],  
            [KeyboardButton("🥉 Chọn bài 3")],
            [KeyboardButton("🔄 Bắt đầu lại")]
        ]
        
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        # Send summaries with selection buttons (enhanced with details)
        message_text = f"🏆 **TOP 3 TIN TỨC {search_type.upper()}**\n\n"
        
        for i, summary in enumerate(summaries[:3]):  # Limit to top 3
            rank_emoji = ["🥇", "🥈", "🥉"][i]
            article = summary['article']
            
            # Shorten title to prevent overflow
            title = article.title
            if len(title) > 70:
                title = title[:70] + "..."
                
            # Generate AI-powered bullet point summary
            article_summary = await self._generate_bullet_summary(article)
            
            # Calculate breakdown scores for transparency
            relevance_component = self._calculate_relevance_breakdown(article)
            appeal_component = self._calculate_appeal_breakdown(article)
            total_score = summary['relevance_score']
            
            message_text += f"{rank_emoji} **#{i+1} - {title}**\n"
            message_text += f"📍 {article.source}\n"
            message_text += f"🔗 [Xem bài viết]({article.url})\n\n"
            
            # Add summary
            message_text += f"📝 **Tóm tắt:** {article_summary}\n\n"
            
            # Add detailed scoring breakdown
            message_text += f"⭐ **Điểm tổng: {total_score:.1f}/10**\n"
            message_text += f"├ 🎯 Liên quan: {relevance_component:.1f}\n"
            message_text += f"├ 🔥 Hấp dẫn: {appeal_component:.1f}\n"
            message_text += f"└ 📊 **Tiêu chí đánh giá:**\n"
            message_text += "   • Từ khóa chủ đề (0-6 điểm)\n"
            message_text += "   • Tính thời sự & độc quyền (0-4 điểm)\n"
            message_text += "   • Chất lượng nội dung (0-2 điểm)\n\n"
            message_text += "─" * 40 + "\n\n"
        
        message_text += "👇 **Sử dụng keyboard bên dưới để chọn bài viết:**"
        
        # Ensure message isn't too long (simplified version if needed)
        if len(message_text) > 4000:
            message_text = f"🏆 **TOP 3 TIN TỨC {search_type.upper()}**\n\n"
            for i, summary in enumerate(summaries[:3]):
                rank_emoji = ["🥇", "🥈", "🥉"][i]
                article = summary['article']
                title = article.title[:50] + "..." if len(article.title) > 50 else article.title
                total_score = summary['relevance_score']
                
                message_text += f"{rank_emoji} **#{i+1} - {title}**\n"
                message_text += f"📍 {article.source} | ⭐ {total_score:.1f}/10\n"
                message_text += f"🔗 [Link]({article.url})\n\n"
            
            message_text += "👇 **Sử dụng keyboard bên dưới để chọn bài viết:**\n"
            message_text += "💡 *Gửi 'chi tiết' để xem đầy đủ thông tin*"
        
        await progress_message.edit_text(
            message_text,
            parse_mode='Markdown'
        )
        
        # Send reply keyboard as a separate message to ensure it appears
        await update.message.reply_text(
            "🎯 **Chọn bài viết:**",
            reply_markup=reply_markup
        )
        
        # Log successful fetch
        await self.logging_service.log_news_fetch_complete(len(articles))

    async def handle_article_selection_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str):
        """Handle article selection from reply keyboard text"""
        user_id = update.effective_user.id
        
        if user_id not in self.user_sessions:
            await update.message.reply_text("❌ Phiên làm việc đã hết hạn. Gửi 'Start' để bắt đầu lại.")
            return
        
        # Map text to rank
        text_to_rank = {
            "🥇 Chọn bài 1": 1,
            "🥈 Chọn bài 2": 2,
            "🥉 Chọn bài 3": 3
        }
        
        rank = text_to_rank.get(message_text)
        if not rank:
            return
        
        session = self.user_sessions[user_id]
        
        if rank > len(session.get('articles', [])):
            await update.message.reply_text("❌ Bài viết không tồn tại.")
            return
            
        selected_article = session['articles'][rank - 1]
        session['selected_article'] = selected_article
        session['step'] = 'generating_post'
        
        rank_emoji = ["🥇", "🥈", "🥉"][rank - 1]
        await update.message.reply_text(
            f"✅ **Đã chọn bài viết {rank_emoji} #{rank}**\n\n"
            f"📰 **{selected_article.title}**\n"
            f"📍 Nguồn: {selected_article.source}\n\n"
            f"🔍 Đang tìm kiếm bài viết liên quan từ chuyên gia Ho Quoc Tuan...\n"
            f"🤖 Đang tạo bài viết Facebook bằng Gemini AI...",
            parse_mode='Markdown'
        )
        
        # Continue with post generation
        await self.generate_facebook_post(update, context, user_id)

    async def generate_facebook_post(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
        """Generate Facebook post content with international sources verification"""
        session = self.user_sessions[user_id]
        selected_article = session['selected_article']
        
        # Update progress with cleaner format
        await update.message.reply_text(
            f"🔍 **Đang tìm kiếm nguồn tin quốc tế**\n\n"
            f"📰 Tìm kiếm: Reuters, BBC, Bloomberg...\n"
            f"🌍 Loại trừ nguồn Việt Nam\n"
            f"⚡ Tóm tắt điểm chính",
            parse_mode='Markdown'
        )
        
        # Log user selection
        await self.logging_service.log_article_selection(
            session.get('rank', 1), selected_article.title
        )
        
        try:
            # Search for international sources
            international_sources = await self.news_service.search_international_sources(
                selected_article.title, selected_article.summary or selected_article.content[:500]
            )
            
            # Get expert context for Facebook posting
            expert_context = await self._get_expert_facebook_context()
            facebook_context = expert_context.get('facebook_context', {})
            
            # Store in session
            session['international_sources'] = international_sources
            session['expert_context'] = expert_context
            session['facebook_context'] = facebook_context
            session['step'] = 'sources_review'
            
            if international_sources:
                # Clean sources display format
                sources_text = f"🌍 **{len(international_sources)} nguồn quốc tế tìm thấy**\n\n"
                
                for i, source in enumerate(international_sources[:3], 1):
                    title_short = source['title'][:50] + "..." if len(source['title']) > 50 else source['title']
                    sources_text += f"**{i}. {source['source']}**\n"
                    sources_text += f"📄 {title_short}\n"
                    sources_text += f"🔗 {source['url']}\n\n"
                
                sources_text += "❓ Sử dụng các nguồn này để tạo bài viết?"
                
                # Simple verification buttons
                keyboard = [
                    [KeyboardButton("✅ Có, sử dụng")],
                    [KeyboardButton("❌ Không, bỏ qua")],
                    [KeyboardButton("🔄 Tìm lại")]
                ]
                reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
                
                await update.message.reply_text(
                    sources_text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown',
                    disable_web_page_preview=True
                )
                
            else:
                # Cleaner no sources message
                await update.message.reply_text(
                    "⚠️ **Không tìm thấy nguồn tin quốc tế**\n"
                    "📝 Tạo bài viết từ nguồn gốc"
                )
                
                # Proceed to generate post without sources
                await self._generate_final_post(update, context, user_id, [])
            
        except Exception as e:
            error_message = f"❌ **Lỗi tìm kiếm:** {str(e)}"
            safe_text, parse_mode = self._safe_markdown_message(error_message, use_markdown=False)
            await update.message.reply_text(safe_text, parse_mode=parse_mode)
            await self.logging_service.log_error("sources_search", str(e))

    async def handle_sources_review_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str):
        """Handle sources review decision from user"""
        user_id = update.effective_user.id
        
        if user_id not in self.user_sessions:
            await update.message.reply_text("❌ Phiên làm việc đã hết hạn. Gửi 'Start' để bắt đầu lại.")
            return
            
        session = self.user_sessions[user_id]
        
        if message_text == "✅ Có, sử dụng":
            await update.message.reply_text(
                "✅ **Nguồn đã xác nhận**\n📝 Đang tạo bài viết..."
            )
            # Generate post with verified international sources
            await self._generate_final_post(update, context, user_id, session.get('international_sources', []))
            
        elif message_text == "❌ Không, bỏ qua":
            await update.message.reply_text(
                "📝 **Đang tạo bài viết thông thường**\n🚫 Không sử dụng nguồn bổ sung"
            )
            # Generate post without sources
            await self._generate_final_post(update, context, user_id, [])
            
        elif message_text == "🔄 Tìm lại":
            await update.message.reply_text("🔄 **Đang tìm lại nguồn khác...**")
            # Retry searching for sources
            await self.generate_facebook_post(update, context, user_id)

    async def _generate_final_post(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, verified_international_sources: List[Dict]):
        """Generate final Facebook post with verified international sources and Facebook context"""
        try:
            session = self.user_sessions[user_id]
            selected_article = session['selected_article']
            expert_context = session.get('expert_context', {})
            facebook_context = session.get('facebook_context', {})
            
            # Generate post content using Gemini with international sources + Facebook context
            post_content = await self.ai_service.generate_expert_facebook_post(
                selected_article, verified_international_sources, expert_context, facebook_context
            )
            
            # Post-process to ensure word count and add source links
            post_content = await self.ai_service._post_process_facebook_post(
                post_content, verified_international_sources
            )
            
            # Generate contextual image prompt
            image_prompt = await self._generate_contextual_image_prompt(selected_article, expert_context)
            
            session['post_content'] = post_content
            session['verified_international_sources'] = verified_international_sources
            session['image_prompt'] = image_prompt
            session['step'] = 'post_approval'
            
            # Create approval buttons (reply keyboard)
            keyboard = [
                [KeyboardButton("✅ Duyệt bài")],
                [KeyboardButton("✏️ Chỉnh sửa")],
                [KeyboardButton("🔄 Làm lại")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            
            # Clean post display format
            header = "📝 **Bài viết đã tạo**"
            if verified_international_sources:
                source_names = ', '.join([s['source'] for s in verified_international_sources[:2]])
                header += f"\n🌍 Nguồn: {source_names}"
            
            await update.message.reply_text(
                f"{header}\n\n{post_content}\n\n👇 **Chọn hành động:**",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            # Log post generation
            await self.logging_service.log_post_generation(post_content)
            
        except Exception as e:
            error_message = f"❌ **Lỗi tạo bài:** {str(e)}"
            safe_text, parse_mode = self._safe_markdown_message(error_message, use_markdown=False)
            await update.message.reply_text(safe_text, parse_mode=parse_mode)
            await self.logging_service.log_error("final_post_generation", str(e))

    async def handle_post_approval_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str):
        """Handle post approval from reply keyboard text"""
        user_id = update.effective_user.id
        
        if user_id not in self.user_sessions:
            await update.message.reply_text("❌ Phiên làm việc đã hết hạn. Gửi 'Start' để bắt đầu lại.")
            return
            
        session = self.user_sessions[user_id]
        
        if message_text == "✅ Duyệt bài":
            session['step'] = 'generating_image'
            await update.message.reply_text("✅ Bài viết đã duyệt!\n🎨 Đang tạo hình ảnh...")
            
            # Generate image
            await self.generate_and_send_image(user_id, context, update.message.chat_id)
            
        elif message_text == "✏️ Chỉnh sửa":
            session['step'] = 'waiting_edit_feedback'
            await update.message.reply_text(
                "✏️ **Chỉnh sửa bài viết**\n\n"
                "📝 Gửi phản hồi để chỉnh sửa:\n\n"
                "💡 **Ví dụ:**\n"
                "• Viết ngắn gọn hơn\n"
                "• Thêm hashtag\n"
                "• Thay đổi tone giọng\n"
                "• Làm nổi bật ý chính"
            )

    async def handle_image_approval_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str):
        """Handle image approval from reply keyboard text"""
        user_id = update.effective_user.id
        
        if user_id not in self.user_sessions:
            await update.message.reply_text("❌ Phiên làm việc đã hết hạn. Gửi 'Start' để bắt đầu lại.")
            return
            
        session = self.user_sessions[user_id]
        
        if message_text == "✅ Duyệt ảnh":
            await update.message.reply_text("✅ Hình ảnh đã duyệt!\n📤 Đang đăng lên Facebook...")
            await self.publish_to_facebook(user_id, context, update.message.chat_id)
            
        elif message_text == "🔄 Tạo lại":
            await update.message.reply_text("🔄 Đang tạo lại hình ảnh...")
            await self.generate_and_send_image(user_id, context, update.message.chat_id)

    async def generate_and_send_image(self, user_id: int, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
        """🎨 Generate and send contextual image with expert Facebook profile integration"""
        try:
            session = self.user_sessions[user_id]
            article = session['selected_article']
            post_content = session['post_content']
            expert_context = session.get('expert_context', {})
            contextual_prompt = session.get('image_prompt', '')
            
            # Clean progress message
            progress_msg = await context.bot.send_message(
                chat_id=chat_id,
                text=f"🎨 **Đang tạo ảnh**\n\n"
                     f"👤 Expert: {expert_context.get('name', 'Ho Quoc Tuan')}\n"
                     f"🏢 Company: {expert_context.get('company', 'PioneerX')}\n"
                     f"🤖 Multiple AI APIs + Logo",
                parse_mode='Markdown'
            )
            
            # Use contextual prompt if available, otherwise generate one
            if contextual_prompt:
                image_path = await self.advanced_image_service.generate_image(
                    title=article.title,
                    content=contextual_prompt,
                    context={'expert_context': expert_context}
                )
            else:
                # Prepare article content for advanced image service with expert context
                article_content = f"{getattr(article, 'summary', '')} {getattr(article, 'content', '')}"
                
                # Use Advanced Image Service for intelligent generation
                image_path = await self.advanced_image_service.generate_image(
                    title=article.title,
                    content=article_content,
                    context={'expert_context': expert_context}
                )
            
            if image_path and os.path.exists(image_path):
                # Clean success message
                await progress_msg.edit_text(
                    f"✅ **Ảnh đã tạo thành công**\n\n"
                    f"👤 Expert: {expert_context.get('name', 'Ho Quoc Tuan')}\n"
                    f"🎨 AI tạo ảnh + PioneerX logo",
                    parse_mode='Markdown'
                )
                
                # Get generation stats
                stats = self.advanced_image_service.get_generation_stats()
                
                session['image_path'] = image_path
                session['step'] = 'image_approval'
                
                # Create image approval buttons (reply keyboard)
                keyboard = [
                    [KeyboardButton("✅ Duyệt ảnh")],
                    [KeyboardButton("🔄 Tạo lại")],
                    [KeyboardButton("🏠 Bắt đầu lại")]
                ]
                reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
                
                # Clean image caption
                caption = f"🎨 **Ảnh tạo bởi AI**\n\n"
                caption += f"👤 Expert: {expert_context.get('name', 'Ho Quoc Tuan')}\n"
                caption += f"📰 Chủ đề: {article.title[:40]}...\n"
                caption += f"📊 Tổng ảnh: {stats['total_images']}"
                
                # Send image with clean caption
                with open(image_path, 'rb') as photo:
                    await context.bot.send_photo(
                        chat_id=chat_id,
                        photo=photo,
                        caption=caption,
                        parse_mode='Markdown'
                    )
                
                # Send reply keyboard as separate message
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="👇 **Chọn hành động:**",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                
            else:
                await progress_msg.edit_text(
                    "⚠️ **Lỗi tạo ảnh AI**\n🔄 Đang dùng phương pháp dự phòng...",
                    parse_mode='Markdown'
                )
                
                # Fallback to original image service
                try:
                    image_path = await self.image_service.generate_image(article.title, post_content)
                    
                    if image_path and os.path.exists(image_path):
                        await progress_msg.edit_text(
                            "✅ **Ảnh dự phòng đã tạo**",
                            parse_mode='Markdown'
                        )
                        
                        session['image_path'] = image_path
                        session['step'] = 'image_approval'
                        
                        keyboard = [
                            [KeyboardButton("✅ Duyệt ảnh")],
                            [KeyboardButton("🔄 Tạo lại")],
                            [KeyboardButton("🏠 Bắt đầu lại")]
                        ]
                        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
                        
                        with open(image_path, 'rb') as photo:
                            await context.bot.send_photo(
                                chat_id=chat_id,
                                photo=photo,
                                caption="🎨 **Ảnh dự phòng**\n⚠️ AI APIs không khả dụng",
                                parse_mode='Markdown'
                            )
                    else:
                        await progress_msg.edit_text(
                            "❌ **Không thể tạo hình ảnh**\n\n"
                            "🔄 Tiếp tục với việc đăng bài không có ảnh",
                            parse_mode='Markdown'
                        )
                        await self.publish_to_facebook(user_id, context, chat_id)
                        
                except Exception as fallback_error:
                    error_message = f"❌ Lỗi tạo ảnh dự phòng: {str(fallback_error)}\n\n🔄 Tiếp tục đăng bài không có ảnh"
                    safe_text, parse_mode = self._safe_markdown_message(error_message, use_markdown=False)
                    
                    await progress_msg.edit_text(
                        safe_text,
                        parse_mode=parse_mode
                    )
                    await self.publish_to_facebook(user_id, context, chat_id)
                
        except Exception as e:
            error_message = f"❌ Lỗi khi tạo hình ảnh: {str(e)}\n\n🔄 Vui lòng thử lại hoặc liên hệ admin."
            safe_text, parse_mode = self._safe_markdown_message(error_message, use_markdown=False)
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=safe_text,
                parse_mode=parse_mode
            )

    async def publish_to_facebook(self, user_id: int, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
        """Publish final post to Facebook"""
        try:
            session = self.user_sessions[user_id]
            post_content = session['post_content']
            image_path = session.get('image_path')
            
            # Publish to Facebook
            result = await self.facebook_service.publish_post(post_content, image_path)
            
            if result['success']:
                # Create restart button
                keyboard = [[KeyboardButton("🏠 Bắt đầu lại")]]
                reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
                
                # Clean success message
                success_message = (
                    f"🎉 **Đăng Facebook thành công!**\n\n"
                    f"🔗 Post ID: {result.get('post_id', 'N/A')}\n"
                    f"✅ Quy trình hoàn tất"
                )
                
                safe_text, parse_mode = self._safe_markdown_message(success_message, use_markdown=False)
                
                await self._safe_send_message(
                    context=context,
                    chat_id=chat_id,
                    text=safe_text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
                
                # Log successful publication
                await self.logging_service.log_publication_success(result['post_id'])
                
            else:
                error_message = f"❌ **Lỗi đăng bài:** {result.get('error', 'Unknown error')}"
                safe_text, parse_mode = self._safe_markdown_message(error_message, use_markdown=False)
                
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=safe_text,
                    parse_mode=parse_mode
                )
            
            # Clean up session
            del self.user_sessions[user_id]
            
        except Exception as e:
            error_message = f"❌ **Lỗi Facebook:** {str(e)}"
            safe_text, parse_mode = self._safe_markdown_message(error_message, use_markdown=False)
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=safe_text,
                parse_mode=parse_mode
            )

    async def market_overview(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /market command - Market overview"""
        try:
            await update.message.reply_text("📊 Đang tải dữ liệu thị trường...")
            
            # Get comprehensive market data
            market_data = await self.market_service.get_comprehensive_market_data()
            
            if 'error' in market_data:
                await update.message.reply_text(f"❌ Lỗi khi lấy dữ liệu: {market_data['error']}")
                return
            
            # Format market overview
            overview = self._format_market_overview(market_data)
            
            # Create inline keyboard for more options
            keyboard = [
                [
                    InlineKeyboardButton("📈 Cổ phiếu VN", callback_data="market_vn_stocks"),
                    InlineKeyboardButton("🌍 Cổ phiếu QT", callback_data="market_global_stocks")
                ],
                [
                    InlineKeyboardButton("🥇 Giá vàng", callback_data="market_gold"),
                    InlineKeyboardButton("📰 Tin tức", callback_data="market_news")
                ],
                [
                    InlineKeyboardButton("🤖 AI Phân tích đầu tư", callback_data="ai_investment_analysis"),
                    InlineKeyboardButton("🎯 Portfolio AI", callback_data="ai_portfolio_recommend")
                ],
                [
                    InlineKeyboardButton("📊 Sentiment thị trường", callback_data="ai_market_sentiment"),
                    InlineKeyboardButton("📊 Báo cáo chi tiết", callback_data="market_detailed_report")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(overview, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"❌ Market overview error: {e}")
            await update.message.reply_text("❌ Không thể lấy dữ liệu thị trường. Vui lòng thử lại!")

    async def vietnamese_stocks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /stocks command - Vietnamese stocks"""
        try:
            # Parse symbols from command if provided
            symbols = context.args if context.args else None
            
            await update.message.reply_text("📈 Đang lấy dữ liệu cổ phiếu Việt Nam...")
            
            stocks = await self.market_service.get_vietnam_stocks(symbols)
            
            if not stocks:
                await update.message.reply_text("❌ Không thể lấy dữ liệu cổ phiếu!")
                return
            
            message = "📈 **CỔ PHIẾU VIỆT NAM**\n\n"
            
            for stock in stocks:
                change_icon = "📈" if stock.change >= 0 else "📉"
                message += f"{change_icon} **{stock.symbol}** ({stock.name})\n"
                message += f"💰 Giá: {stock.price:,.0f} VND\n"
                message += f"📊 Thay đổi: {stock.change:,.0f} ({stock.change_percent:+.1f}%)\n"
                message += f"📦 KL: {stock.volume:,}\n\n"
            
            message += f"⏰ Cập nhật: {datetime.now().strftime('%H:%M %d/%m/%Y')}"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"❌ Vietnamese stocks error: {e}")
            await update.message.reply_text("❌ Không thể lấy dữ liệu cổ phiếu!")

    async def global_stocks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /global command - Global stocks"""
        try:
            symbols = context.args if context.args else None
            
            await update.message.reply_text("🌍 Đang lấy dữ liệu cổ phiếu quốc tế...")
            
            stocks = await self.market_service.get_global_stocks(symbols)
            
            if not stocks:
                await update.message.reply_text("❌ Không thể lấy dữ liệu cổ phiếu!")
                return
            
            message = "🌍 **CỔ PHIẾU QUỐC TẾ**\n\n"
            
            for stock in stocks:
                change_icon = "📈" if stock.change >= 0 else "📉"
                message += f"{change_icon} **{stock.symbol}** ({stock.name})\n"
                message += f"💰 Giá: ${stock.price:.2f}\n"
                message += f"📊 Thay đổi: ${stock.change:+.2f} ({stock.change_percent:+.1f}%)\n"
                message += f"📦 KL: {stock.volume:,}\n\n"
            
            message += f"⏰ Cập nhật: {datetime.now().strftime('%H:%M %d/%m/%Y')}"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"❌ Global stocks error: {e}")
            await update.message.reply_text("❌ Không thể lấy dữ liệu cổ phiếu!")

    async def gold_prices(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /gold command - Gold prices"""
        try:
            await update.message.reply_text("🥇 Đang lấy giá vàng...")
            
            gold_data = await self.market_service.get_gold_prices()
            
            if not gold_data:
                await update.message.reply_text("❌ Không thể lấy giá vàng!")
                return
            
            change_icon = "📈" if gold_data.change >= 0 else "📉"
            
            message = f"""
🥇 **GIÁ VÀNG HIỆN TẠI**

{change_icon} **Giá vàng thế giới:**
💰 ${gold_data.price_usd:.2f}/oz
📊 Thay đổi: ${gold_data.change:+.2f} ({gold_data.change_percent:+.1f}%)

💎 **Giá vàng Việt Nam:**
💰 {gold_data.price_vnd:,.0f} VND/lượng
📊 Tương đương: ~{gold_data.price_vnd/37.5:,.0f} VND/chỉ

⏰ Cập nhật: {datetime.now().strftime('%H:%M %d/%m/%Y')}

📍 *Giá chỉ mang tính chất tham khảo*
            """
            
            await update.message.reply_text(message.strip(), parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"❌ Gold prices error: {e}")
            await update.message.reply_text("❌ Không thể lấy giá vàng!")

    async def market_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /report command - Generate market report"""
        try:
            # Parse report type from args
            report_type = context.args[0] if context.args else 'market_closing'
            
            if not self.market_scheduler:
                await update.message.reply_text("❌ Chức năng báo cáo chưa được kích hoạt!")
                return
            
            await update.message.reply_text("📊 Đang tạo báo cáo thị trường...")
            
            # Send manual report
            success = await self.market_scheduler.send_manual_report(
                report_type=report_type,
                chat_id=update.effective_chat.id
            )
            
            if not success:
                await update.message.reply_text("❌ Không thể tạo báo cáo. Vui lòng thử lại!")
            
        except Exception as e:
            logger.error(f"❌ Market report error: {e}")
            await update.message.reply_text("❌ Lỗi khi tạo báo cáo thị trường!")

    async def schedule_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /schedule command - Manage schedules"""
        try:
            if not self.market_scheduler:
                await update.message.reply_text("❌ Chức năng lên lịch chưa được kích hoạt!")
                return
            
            if not context.args:
                # Show schedule status
                status = self.market_scheduler.get_schedule_status()
                
                message = f"""
⏰ **TRẠNG THÁI LỊCH BÁO CÁO**

🟢 Trạng thái: {"Đang chạy" if status['running'] else "Đã dừng"}
📅 Số lịch: {status['job_count']}
👥 Người đăng ký: {status['subscriber_count']}

**📋 LỊCH SẮP TỚI:**
                """
                
                for job in status['next_jobs']:
                    message += f"• {job['id']}: {job['next_run']}\n"
                
                message += """
**⚙️ LỆNH QUẢN LÝ:**
• `/schedule` - Xem trạng thái
• `/schedule add "Tên" HH:MM` - Thêm lịch
• `/subscribe` - Đăng ký nhận báo cáo
• `/unsubscribe` - Hủy đăng ký
                """
                
                await update.message.reply_text(message.strip(), parse_mode='Markdown')
                
            elif context.args[0] == 'add' and len(context.args) >= 3:
                # Add custom schedule
                name = context.args[1].strip('"')
                schedule_time = context.args[2]
                
                success = self.market_scheduler.add_custom_schedule(
                    name=name,
                    schedule_time=schedule_time,
                    chat_id=update.effective_chat.id
                )
                
                if success:
                    await update.message.reply_text(f"✅ Đã thêm lịch: {name} lúc {schedule_time}")
                else:
                    await update.message.reply_text("❌ Không thể thêm lịch. Kiểm tra định dạng thời gian (HH:MM)!")
            
        except Exception as e:
            logger.error(f"❌ Schedule command error: {e}")
            await update.message.reply_text("❌ Lỗi khi quản lý lịch!")

    async def subscribe_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /subscribe command"""
        try:
            if not self.market_scheduler:
                await update.message.reply_text("❌ Chức năng đăng ký chưa được kích hoạt!")
                return
            
            # Parse schedule types from args
            schedules = context.args if context.args else None
            
            self.market_scheduler.subscribe_user(
                chat_id=update.effective_chat.id,
                schedules=schedules
            )
            
            message = "✅ **Đăng ký thành công!**\n\n"
            message += "Bạn sẽ nhận báo cáo thị trường tự động theo lịch:\n"
            message += "• 08:45 - Báo cáo mở cửa\n"
            message += "• 11:35 - Tổng kết buổi sáng\n"
            message += "• 12:55 - Dự báo buổi chiều\n"
            message += "• 15:05 - Báo cáo đóng cửa\n"
            message += "• 19:00 - Phân tích tối\n"
            message += "• 17:00 (T6) - Tổng kết tuần\n\n"
            message += "📱 Dùng `/unsubscribe` để hủy đăng ký"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"❌ Subscribe error: {e}")
            await update.message.reply_text("❌ Lỗi khi đăng ký!")

    async def unsubscribe_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /unsubscribe command"""
        try:
            if not self.market_scheduler:
                await update.message.reply_text("❌ Chức năng hủy đăng ký chưa được kích hoạt!")
                return
            
            self.market_scheduler.unsubscribe_user(update.effective_chat.id)
            
            await update.message.reply_text(
                "❌ **Đã hủy đăng ký**\n\n"
                "Bạn sẽ không còn nhận báo cáo thị trường tự động.\n"
                "📱 Dùng `/subscribe` để đăng ký lại.",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"❌ Unsubscribe error: {e}")
            await update.message.reply_text("❌ Lỗi khi hủy đăng ký!")

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command"""
        try:
            # Get system status
            market_status = {
                'vietnam_open': self.market_service.is_market_open('vietnam'),
                'us_open': self.market_service.is_market_open('us')
            }
            
            scheduler_status = self.market_scheduler.get_schedule_status() if self.market_scheduler else {
                'running': False,
                'job_count': 0,
                'subscriber_count': 0
            }
            
            message = f"""
🔧 **TRẠNG THÁI HỆ THỐNG**

📊 **Thị trường:**
• 🇻🇳 Việt Nam: {"🟢 Mở cửa" if market_status['vietnam_open'] else "🔴 Đóng cửa"}
• 🇺🇸 Mỹ: {"🟢 Mở cửa" if market_status['us_open'] else "🔴 Đóng cửa"}

⏰ **Lịch tự động:**
• Trạng thái: {"🟢 Hoạt động" if scheduler_status['running'] else "🔴 Dừng"}
• Số lịch: {scheduler_status['job_count']}
• Người đăng ký: {scheduler_status['subscriber_count']}

🤖 **Dịch vụ:**
• 📰 Tin tức: 🟢 Hoạt động
• 🧠 AI: 🟢 Hoạt động  
• 🎨 Tạo ảnh: 🟢 Hoạt động
• 📱 Facebook: 🟢 Hoạt động

⏰ Cập nhật: {datetime.now().strftime('%H:%M %d/%m/%Y')}
            """
            
            await update.message.reply_text(message.strip(), parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"❌ Status command error: {e}")
            await update.message.reply_text("❌ Lỗi khi kiểm tra trạng thái!")

    def _format_market_overview(self, market_data: dict) -> str:
        """Format market overview message"""
        try:
            vn_stocks = market_data.get('vietnam_stocks', [])[:5]
            global_stocks = market_data.get('global_stocks', [])[:4]
            gold_data = market_data.get('gold_data')
            market_status = market_data.get('market_status', {})
            
            message = "📊 **TỔNG QUAN THỊ TRƯỜNG**\n\n"
            
            # Market status
            vn_status = "🟢 Mở cửa" if market_status.get('vietnam_open') else "🔴 Đóng cửa"
            us_status = "🟢 Mở cửa" if market_status.get('us_open') else "🔴 Đóng cửa"
            message += f"🏛️ **Trạng thái:** VN {vn_status} | US {us_status}\n\n"
            
            # Vietnamese stocks
            message += "📈 **TOP CỔ PHIẾU VIỆT NAM:**\n"
            for stock in vn_stocks:
                icon = "📈" if stock.change >= 0 else "📉"
                message += f"{icon} {stock.symbol}: {stock.price:,.0f} ({stock.change_percent:+.1f}%)\n"
            
            # Global stocks
            message += "\n🌍 **CỔ PHIẾU QUỐC TẾ:**\n"
            for stock in global_stocks:
                icon = "📈" if stock.change >= 0 else "📉"
                message += f"{icon} {stock.symbol}: ${stock.price:.2f} ({stock.change_percent:+.1f}%)\n"
            
            # Gold prices
            if gold_data:
                icon = "📈" if gold_data.change >= 0 else "📉"
                message += f"\n🥇 **VÀNG:** {icon} ${gold_data.price_usd:.2f} ({gold_data.change_percent:+.1f}%)\n"
            
            message += f"\n⏰ {datetime.now().strftime('%H:%M %d/%m/%Y')}"
            
            return message
            
        except Exception as e:
            logger.error(f"❌ Format market overview error: {e}")
            return "❌ Lỗi định dạng dữ liệu thị trường"

    async def image_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /image command"""
        if not context.args:
            help_text = """
🎨 **HƯỚNG DẪN TẠO ẢNH AI**

**Cách sử dụng:**
`/image [mô tả ảnh]`

**Ví dụ:**
• `/image beautiful sunset landscape`
• `/image modern office building`
• `/image phong cảnh núi non Việt Nam`
• `/image business meeting professional`

**Nhà cung cấp:**
• 🚀 Stability AI (Premium - ưu tiên)
• 🤗 Hugging Face FLUX & SDXL
• 🔥 DeepAI
• 🌐 Web sources (fallback)

**Tính năng:**
• API key rotation tự động
• Chất lượng cao 1200x630
• Thêm logo tự động
• Hỗ trợ tiếng Việt & Anh
            """
            await update.message.reply_text(help_text, parse_mode='Markdown')
            return
        
        prompt = ' '.join(context.args)
        
        # Send initial message
        status_message = await update.message.reply_text(
            f"🎨 **Đang tạo ảnh:** {prompt[:50]}...\n\n"
            f"⏳ Đang xử lý với AI...",
            parse_mode='Markdown'
        )
        
        try:
            # Generate image
            image_path = await self.advanced_image_service.generate_image(
                title=prompt,
                content=prompt,
                context={'user_request': True}
            )
            
            if image_path and os.path.exists(image_path):
                # Update status
                await status_message.edit_text(
                    f"🎨 **Ảnh đã tạo thành công!**\n\n"
                    f"📝 Prompt: {prompt}\n"
                    f"📁 File: {os.path.basename(image_path)}",
                    parse_mode='Markdown'
                )
                
                # Send image
                with open(image_path, 'rb') as photo:
                    await update.message.reply_photo(
                        photo=photo,
                        caption=f"🎨 **Ảnh AI:** {prompt}\n\n"
                               f"🤖 Tạo bởi: Advanced AI Image Service\n"
                               f"📊 Xem trạng thái: /image_status",
                        parse_mode='Markdown'
                    )
            else:
                await status_message.edit_text(
                    f"❌ **Không thể tạo ảnh**\n\n"
                    f"📝 Prompt: {prompt}\n"
                    f"🔧 Thử lại hoặc kiểm tra /image_status",
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            await status_message.edit_text(
                f"❌ **Lỗi tạo ảnh:** {str(e)[:100]}...\n\n"
                f"🔧 Kiểm tra /status hoặc thử lại sau",
                parse_mode='Markdown'
            )
            logger.error(f"Image generation error: {e}")
    
    async def image_status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /image_status command"""
        try:
            status = self.advanced_image_service.get_api_status()
            
            status_text = "🎨 **TRẠNG THÁI TẠO ẢNH AI**\n\n"
            
            for api_name, api_status in status.items():
                status_emoji = {
                    'healthy': '✅',
                    'error': '❌',
                    'unknown': '❓'
                }.get(api_status['status'], '❓')
                
                enabled_emoji = '🟢' if api_status['enabled'] else '🔴'
                
                status_text += f"{status_emoji} **{api_name.upper()}** {enabled_emoji}\n"
                status_text += f"├ Keys: {api_status['keys_configured']}\n"
                status_text += f"├ Success: {api_status['success_count']}\n"
                status_text += f"├ Errors: {api_status['error_count']}\n"
                status_text += f"└ Usage: {api_status['usage_count']}\n\n"
            
            status_text += "📊 **Chú thích:**\n"
            status_text += "• ✅ Hoạt động tốt\n"
            status_text += "• ❌ Gặp lỗi\n" 
            status_text += "• 🟢 Đã bật\n"
            status_text += "• 🔴 Đã tắt\n\n"
            status_text += "💡 Sử dụng `/image [prompt]` để tạo ảnh!"
            
            await update.message.reply_text(status_text, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(
                f"❌ **Lỗi kiểm tra trạng thái:** {str(e)}\n\n"
                f"🔧 Thử lại sau hoặc liên hệ admin",
                parse_mode='Markdown'
            )
    
    async def api_health_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /api_health command"""
        try:
            # Get image service status
            image_status = self.advanced_image_service.get_api_status()
            
            # Get market data status (if available)
            market_status = {}
            if self.market_service:
                try:
                    # Test market API
                    test_data = await self.market_service.get_vietnamese_stocks(['VIC'])
                    market_status['vietnamese_stocks'] = '✅ OK' if test_data else '❌ Error'
                except:
                    market_status['vietnamese_stocks'] = '❌ Error'
            
            health_text = "🏥 **TÌNH TRẠNG SỨC KHỎE API**\n\n"
            
            # Image APIs
            health_text += "🎨 **IMAGE GENERATION:**\n"
            for api_name, status in image_status.items():
                emoji = '✅' if status['status'] == 'healthy' else '❌'
                health_text += f"{emoji} {api_name}: {status['success_count']}✅ {status['error_count']}❌\n"
            
            # Market APIs
            if market_status:
                health_text += "\n📊 **MARKET DATA:**\n"
                for api_name, status in market_status.items():
                    health_text += f"{status} {api_name}\n"
            
            # System info
            health_text += "\n🖥️ **SYSTEM:**\n"
            health_text += f"✅ Bot: Online\n"
            health_text += f"✅ AI Service: {self.ai_service is not None}\n"
            health_text += f"✅ Market Scheduler: {self.market_scheduler is not None}\n"
            
            # Recommendations
            health_text += "\n💡 **KHUYẾN NGHỊ:**\n"
            
            # Check for issues
            total_errors = sum(s['error_count'] for s in image_status.values())
            if total_errors > 10:
                health_text += "⚠️ Nhiều lỗi API - kiểm tra API keys\n"
            
            disabled_apis = [name for name, s in image_status.items() if not s['enabled']]
            if disabled_apis:
                health_text += f"⚠️ API tắt: {', '.join(disabled_apis)}\n"
            
            if not any(s['keys_configured'] > 0 for s in image_status.values()):
                health_text += "❌ Chưa cấu hình API keys tạo ảnh\n"
            
            if total_errors == 0:
                health_text += "✨ Tất cả API hoạt động tốt!\n"
            
            await update.message.reply_text(health_text, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(
                f"❌ **Lỗi kiểm tra sức khỏe API:** {str(e)}\n\n"
                f"🔧 Hệ thống có thể gặp sự cố",
                parse_mode='Markdown'
            )

    def _calculate_relevance_breakdown(self, article) -> float:
        """Calculate relevance score breakdown for display"""
        score = 0
        content_lower = (article.title + " " + article.content).lower()
        
        # Primary keywords from config (2 points each)
        if hasattr(self.news_service, 'config') and hasattr(self.news_service.config, 'RELEVANCE_KEYWORDS'):
            for keyword in self.news_service.config.RELEVANCE_KEYWORDS:
                if keyword.lower() in content_lower:
                    score += 2
        
        # Secondary keywords (1 point each)
        secondary_keywords = ["politics", "economy", "business", "international", "government", 
                              "trade", "diplomatic", "global", "market", "finance"]
        for keyword in secondary_keywords:
            if keyword.lower() in content_lower:
                score += 1
        
        return min(score, 6.0)  # Cap at 6 points
    
    def _calculate_appeal_breakdown(self, article) -> float:
        """Calculate appeal score breakdown for display"""
        score = 0
        content_lower = (article.title + " " + article.content).lower()
        
        # High appeal words (2 points each)
        high_appeal = ["breaking", "exclusive", "major", "crisis"]
        for word in high_appeal:
            if word in content_lower:
                score += 2
        
        # Medium appeal words (1 point each)
        medium_appeal = ["shocking", "urgent", "developing", "latest"]
        for word in medium_appeal:
            if word in content_lower:
                score += 1
        
        # Content quality indicators
        if len(article.content) > 1500:
            score += 1
        
        if len(article.title) > 50:
            score += 0.5
        
        # Time relevance
        if 'today' in content_lower or 'yesterday' in content_lower:
            score += 1
        
        return min(score, 4.0)  # Cap at 4 points

    async def _get_expert_facebook_context(self) -> dict:
        """Get expert context from Facebook profile"""
        try:
            expert_context = {
                'name': 'Ho Quoc Tuan',
                'profile_url': self.config.EXPERT_FACEBOOK_URL,
                'expertise': [
                    'Kinh doanh và Đầu tư',
                    'Công nghệ và AI', 
                    'Phân tích thị trường',
                    'Khởi nghiệp và Innovation',
                    'Tài chính cá nhân'
                ],
                'writing_style': 'Chuyên nghiệp, dễ hiểu, có tính thực tiễn cao',
                'focus_areas': [
                    'Xu hướng công nghệ mới',
                    'Cơ hội đầu tư',
                    'Phân tích kinh tế',
                    'Kỹ năng phát triển bản thân',
                    'Strategies kinh doanh'
                ],
                'company': 'PioneerX',
                'company_focus': 'Innovation và Technology Solutions'
            }
            
            # Future enhancement: Could scrape actual profile info here
            # For now, using predefined expert context
            
            return expert_context
            
        except Exception as e:
            # Fallback expert context
            return {
                'name': 'Ho Quoc Tuan',
                'profile_url': self.config.EXPERT_FACEBOOK_URL,
                'expertise': ['Business Analysis', 'Technology', 'Investment'],
                'writing_style': 'Professional and insightful',
                'company': 'PioneerX'
            }

    async def _generate_contextual_image_prompt(self, article, expert_context: dict) -> str:
        """Generate contextual image prompt based on news article and expert profile"""
        try:
            # Extract key themes from article
            article_themes = []
            title_lower = article.title.lower()
            content_lower = article.content.lower()
            
            # Business/Economic themes
            if any(keyword in title_lower or keyword in content_lower 
                   for keyword in ['business', 'economy', 'market', 'finance', 'trade', 'investment']):
                article_themes.append('business')
                
            # Technology themes  
            if any(keyword in title_lower or keyword in content_lower
                   for keyword in ['technology', 'ai', 'tech', 'digital', 'innovation', 'startup']):
                article_themes.append('technology')
                
            # Global/Political themes
            if any(keyword in title_lower or keyword in content_lower
                   for keyword in ['global', 'international', 'policy', 'government', 'political']):
                article_themes.append('global')
            
            # Create contextual prompt based on themes and expert profile
            company = expert_context.get('company', 'PioneerX')
            
            if 'technology' in article_themes:
                prompt = f"Professional tech innovation illustration representing {article.title[:50]}..., modern digital design, clean corporate style suitable for {company} technology company, business professional aesthetic, high quality, 16:9 aspect ratio"
            elif 'business' in article_themes:
                prompt = f"Professional business analysis visualization for {article.title[:50]}..., corporate design, financial charts and growth concepts, modern business aesthetic for {company}, professional consulting style, 16:9 aspect ratio"
            elif 'global' in article_themes:
                prompt = f"Professional global business illustration about {article.title[:50]}..., international connections, world map elements, corporate global perspective for {company}, professional news style, 16:9 aspect ratio"
            else:
                # Default professional news illustration
                prompt = f"Professional news illustration about {article.title[:50]}..., corporate design, modern business aesthetic, suitable for {company} news content, professional media style, clean and informative, 16:9 aspect ratio"
            
            return prompt
            
        except Exception as e:
            # Fallback prompt
            return f"Professional news illustration about {article.title[:50]}..., corporate design, modern business aesthetic, suitable for PioneerX company news content, 16:9 aspect ratio"

    # ===========================================
    # AI INVESTMENT ANALYSIS METHODS
    # ===========================================

    async def ai_investment_analysis_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /ai_analysis command - AI Stock Analysis"""
        try:
            # Parse symbols from command args
            symbols = context.args if context.args else None
            
            await update.message.reply_text("🤖 Đang thực hiện phân tích AI chuyên sâu...")
            
            # Get stock data
            if not self.market_service:
                await update.message.reply_text("❌ Dịch vụ thị trường chưa được kích hoạt!")
                return
            
            # Get Vietnamese stocks for analysis
            stocks_data = await self.market_service.get_vietnam_stocks(symbols)
            if not stocks_data:
                await update.message.reply_text("❌ Không thể lấy dữ liệu cổ phiếu!")
                return
            
            # Convert to dict format for AI service
            stock_dict = {
                'symbol': stocks_data[0].symbol,
                'price': stocks_data[0].price,
                'change_percent': stocks_data[0].change_percent,
                'volume': stocks_data[0].volume,
                'market_cap': getattr(stocks_data[0], 'market_cap', None)
            }
            
            # Get market context
            market_data = await self.market_service.get_comprehensive_market_data()
            
            # Perform AI analysis
            analysis = await self.ai_investment_service.analyze_stock_comprehensive_enhanced(
                symbol=stock_dict.get('symbol', 'UNKNOWN')
            )
            
            # Format analysis message
            message = self._format_ai_analysis(analysis)
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"❌ AI analysis command error: {e}")
            await update.message.reply_text("❌ Không thể thực hiện phân tích AI. Vui lòng thử lại!")

    async def ai_portfolio_recommendation_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /ai_portfolio command - AI Portfolio Recommendation"""
        try:
            await update.message.reply_text("🎯 Đang tạo khuyến nghị portfolio AI...")
            
            if not self.market_service:
                await update.message.reply_text("❌ Dịch vụ thị trường chưa được kích hoạt!")
                return
            
            # Get diverse stock data
            vn_stocks = await self.market_service.get_vietnam_stocks()
            global_stocks = await self.market_service.get_global_stocks()
            
            # Combine and convert to dict format
            all_stocks = []
            for stock in vn_stocks[:5]:  # Top 5 VN stocks
                all_stocks.append({
                    'symbol': stock.symbol,
                    'price': stock.price,
                    'change_percent': stock.change_percent,
                    'volume': stock.volume,
                    'market_cap': getattr(stock, 'market_cap', None)
                })
            
            for stock in global_stocks[:3]:  # Top 3 global stocks
                all_stocks.append({
                    'symbol': stock.symbol,
                    'price': stock.price,
                    'change_percent': stock.change_percent,
                    'volume': stock.volume,
                    'market_cap': getattr(stock, 'market_cap', None)
                })
            
            # Default user profile
            user_profile = {
                'risk_tolerance': 'moderate',
                'amount': 100000000,  # 100M VND
                'time_horizon': 'MEDIUM'
            }
            
            # Generate portfolio recommendation
            symbols = [stock['symbol'] for stock in all_stocks]
            portfolio = await self.ai_investment_service.generate_smart_portfolio_recommendation(symbols)
            
            # Format portfolio message
            message = self._format_portfolio_recommendation(portfolio)
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"❌ AI portfolio command error: {e}")
            await update.message.reply_text("❌ Không thể tạo khuyến nghị portfolio. Vui lòng thử lại!")

    async def ai_market_sentiment_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /ai_sentiment command - AI Market Sentiment Analysis"""
        try:
            await update.message.reply_text("📊 Đang phân tích sentiment thị trường...")
            
            if not self.market_service:
                await update.message.reply_text("❌ Dịch vụ thị trường chưa được kích hoạt!")
                return
            
            # Get market data
            market_data = await self.market_service.get_comprehensive_market_data()
            
            # Get recent market news
            news_data = []
            try:
                if hasattr(self.market_service, 'get_market_news'):
                    market_news = await self.market_service.get_market_news(5)
                    news_data = [{'title': news.title} for news in market_news]
            except:
                pass
            
            # Perform sentiment analysis
            sentiment = await self.ai_investment_service.analyze_market_sentiment_comprehensive()
            
            # Format sentiment message
            message = self._format_market_sentiment(sentiment)
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"❌ AI sentiment command error: {e}")
            await update.message.reply_text("❌ Không thể phân tích sentiment. Vui lòng thử lại!")

    def _format_ai_analysis(self, analysis) -> str:
        """Format AI investment analysis for display"""
        recommendation_emoji = {
            'BUY': '🟢',
            'SELL': '🔴', 
            'HOLD': '🟡'
        }
        
        risk_emoji = {
            'LOW': '🟢',
            'MEDIUM': '🟡',
            'HIGH': '🔴'
        }
        
        emoji = recommendation_emoji.get(analysis.recommendation, '🟡')
        risk_emoji_display = risk_emoji.get(analysis.risk_level, '🟡')
        
        message = f"""
🤖 **PHÂN TÍCH AI CHUYÊN SÂU**

📊 **Cổ phiếu:** {analysis.symbol}
💰 **Giá hiện tại:** {analysis.current_price:,.0f}

{emoji} **KHUYẾN NGHỊ:** {analysis.recommendation}
🎯 **Mức tin cậy:** {analysis.confidence_score:.0f}/100
💎 **Giá mục tiêu:** {analysis.target_price:,.0f}
{risk_emoji_display} **Mức rủi ro:** {analysis.risk_level}

📝 **TÓM TẮT PHÂN TÍCH:**
{analysis.analysis_summary}

🔍 **YẾU TỐ CHÍNH:**
"""
        
        for factor in analysis.key_factors:
            message += f"• {factor}\n"
        
        message += f"""
⏰ **Khung thời gian:** {analysis.time_horizon}
🕐 **Cập nhật:** {analysis.last_updated.strftime('%H:%M %d/%m/%Y')}

⚠️ *Đây là phân tích AI tham khảo. Không phải lời khuyên đầu tư.*
        """
        
        return message.strip()

    def _format_portfolio_recommendation(self, portfolio) -> str:
        """Format portfolio recommendation for display"""
        message = f"""
🎯 **KHUYẾN NGHỊ PORTFOLIO AI**

📊 **Điểm tổng:** {portfolio.total_score:.0f}/100
🛡️ **Đánh giá rủi ro:** {portfolio.risk_assessment}
📈 **Lợi nhuận kỳ vọng:** {portfolio.expected_return:.1f}%/năm
🎲 **Điểm đa dạng hóa:** {portfolio.diversification_score:.0f}/100

💼 **PHÂN BỔ ĐỀ XUẤT:**
"""
        
        for symbol, weight in portfolio.allocation.items():
            message += f"• **{symbol}:** {weight:.1f}%\n"
        
        message += f"""
💡 **KHUYẾN NGHỊ:**
"""
        
        for rec in portfolio.recommendations:
            message += f"• {rec}\n"
        
        message += f"""
⚠️ *Portfolio tham khảo cho nhà đầu tư có kinh nghiệm. Cân nhắc kỹ trước khi đầu tư.*
        """
        
        return message.strip()

    def _format_market_sentiment(self, sentiment) -> str:
        """Format market sentiment for display"""
        sentiment_emoji = {
            'BULLISH': '🐂',
            'BEARISH': '🐻',
            'NEUTRAL': '⚖️'
        }
        
        color_emoji = {
            'BULLISH': '🟢',
            'BEARISH': '🔴',
            'NEUTRAL': '🟡'
        }
        
        emoji = sentiment_emoji.get(sentiment.overall_sentiment, '⚖️')
        color = color_emoji.get(sentiment.overall_sentiment, '🟡')
        
        message = f"""
📊 **SENTIMENT THỊ TRƯỜNG AI**

{emoji} **Tổng quan:** {sentiment.overall_sentiment}
{color} **Điểm sentiment:** {sentiment.sentiment_score:+.1f}/100
🎯 **Mức tin cậy:** {sentiment.confidence:.0f}%

🔍 **ĐỘNG LỰC CHÍNH:**
"""
        
        for driver in sentiment.key_drivers:
            message += f"• {driver}\n"
        
        message += f"""
🔮 **TRIỂN VỌNG:**
{sentiment.outlook}

⚠️ *Phân tích dựa trên dữ liệu và tin tức hiện tại. Thị trường có thể thay đổi bất ngờ.*
        """
        
        return message.strip()

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle button callbacks from inline keyboards"""
        query = update.callback_query
        await query.answer()  # Acknowledge the callback
        
        callback_data = query.data
        
        try:
            # Handle workflow-specific callbacks
            if callback_data.startswith("select_article_"):
                # Handle article selection: select_article_{article_index}_{user_id}
                parts = callback_data.split("_")
                if len(parts) >= 4:
                    article_index = int(parts[2])
                    user_id = int(parts[3])
                    await self.workflow_service.handle_article_selection(user_id, article_index, context, query)
                return
            
            elif callback_data.startswith("approve_post_"):
                # Handle post approval: approve_post_{user_id}
                user_id = int(callback_data.split("_")[2])
                await self.workflow_service.handle_post_approval(user_id, 'approve', context, query)
                return
            
            elif callback_data.startswith("edit_post_"):
                # Handle post edit request: edit_post_{user_id}
                user_id = int(callback_data.split("_")[2])
                await self.workflow_service.handle_post_approval(user_id, 'edit', context, query)
                return
            
            elif callback_data.startswith("approve_image_"):
                # Handle image approval: approve_image_{user_id}
                user_id = int(callback_data.split("_")[2])
                await self.workflow_service.handle_image_approval(user_id, 'approve', context, query)
                return
            
            elif callback_data.startswith("regenerate_image_"):
                # Handle image regeneration: regenerate_image_{user_id}
                user_id = int(callback_data.split("_")[2])
                await self.workflow_service.handle_image_approval(user_id, 'regenerate', context, query)
                return
            if callback_data == "ai_investment_analysis":
                # Create a mock update object with message for AI analysis
                class MockUpdate:
                    def __init__(self, query):
                        self.callback_query = query
                        self.message = query.message
                        self.effective_chat = query.message.chat
                        self.effective_user = query.from_user
                
                mock_update = MockUpdate(query)
                await self.ai_investment_analysis_command(mock_update, context)
                
            elif callback_data == "ai_portfolio_recommend":
                # Create mock update for portfolio recommendation
                class MockUpdate:
                    def __init__(self, query):
                        self.callback_query = query
                        self.message = query.message
                        self.effective_chat = query.message.chat
                        self.effective_user = query.from_user
                
                mock_update = MockUpdate(query)
                await self.ai_portfolio_recommendation_command(mock_update, context)
                
            elif callback_data == "ai_market_sentiment":
                # Create mock update for sentiment analysis
                class MockUpdate:
                    def __init__(self, query):
                        self.callback_query = query
                        self.message = query.message
                        self.effective_chat = query.message.chat
                        self.effective_user = query.from_user
                
                mock_update = MockUpdate(query)
                await self.ai_market_sentiment_command(mock_update, context)
                
            elif callback_data == "market_vn_stocks":
                # Vietnamese stocks
                class MockUpdate:
                    def __init__(self, query):
                        self.callback_query = query
                        self.message = query.message
                        self.effective_chat = query.message.chat
                        self.effective_user = query.from_user
                
                mock_update = MockUpdate(query)
                await self.vietnamese_stocks(mock_update, context)
                
            elif callback_data == "market_global_stocks":
                # Global stocks
                class MockUpdate:
                    def __init__(self, query):
                        self.callback_query = query
                        self.message = query.message
                        self.effective_chat = query.message.chat
                        self.effective_user = query.from_user
                
                mock_update = MockUpdate(query)
                await self.global_stocks(mock_update, context)
                
            elif callback_data == "market_gold":
                # Gold prices
                class MockUpdate:
                    def __init__(self, query):
                        self.callback_query = query
                        self.message = query.message
                        self.effective_chat = query.message.chat
                        self.effective_user = query.from_user
                
                mock_update = MockUpdate(query)
                await self.gold_prices(mock_update, context)
                
            elif callback_data == "market_news":
                # Market news
                await query.edit_message_text("📰 Tính năng tin tức thị trường đang được phát triển...")
                
            elif callback_data == "market_detailed_report":
                # Detailed market report
                class MockUpdate:
                    def __init__(self, query):
                        self.callback_query = query
                        self.message = query.message
                        self.effective_chat = query.message.chat
                        self.effective_user = query.from_user
                
                mock_update = MockUpdate(query)
                await self.market_report(mock_update, context)
                
            else:
                await query.edit_message_text("❌ Lệnh không được hỗ trợ!")
                
        except Exception as e:
            logger.error(f"❌ Button callback error: {e}")
            try:
                await query.edit_message_text("❌ Có lỗi xảy ra. Vui lòng thử lại!")
            except:
                pass

    async def _generate_bullet_summary(self, article: Article) -> str:
        """Generate 3-4 bullet point summary using AI"""
        try:
            prompt = f"""
            Tạo tóm tắt ngắn gọn dưới dạng 3-4 gạch đầu dòng cho bài báo:
            
            Tiêu đề: {article.title}
            Nội dung: {article.content[:800]}...
            
            Yêu cầu:
            - 3-4 gạch đầu dòng ngắn gọn
            - Mỗi điểm tối đa 15 từ
            - Tập trung vào điểm chính và tác động
            - Format: • Điểm 1 • Điểm 2 • Điểm 3
            
            Chỉ trả về các gạch đầu dòng, không thêm gì khác.
            """
            
            # Use AI service to generate summary
            summary = await self.ai_service._make_gemini_request(prompt)
            
            # Clean up the response
            summary = summary.strip()
            if not summary.startswith('•'):
                # If AI doesn't format properly, add bullet points
                lines = summary.split('\n')
                summary = '\n'.join([f"• {line.strip()}" for line in lines[:4] if line.strip()])
            
            return summary
            
        except Exception as e:
            # Fallback to simple summary
            content_preview = article.content[:150].strip()
            if len(article.content) > 150:
                content_preview += "..."
            return f"• {content_preview}"

    async def handle_market_analysis(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle market analysis request"""
        try:
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id
            
            logger.info(f"📊 Market analysis requested by user {user_id}")
            
            # Send processing message
            processing_msg = await update.message.reply_text(
                "🔄 **ĐANG PHÂN TÍCH THỊ TRƯỜNG...**\n\n"
                "⏳ Đang thu thập dữ liệu từ RSS feeds real-time...\n"
                "🤖 AI đang phân tích xu hướng thị trường...\n"
                "📊 Tạo báo cáo chi tiết...",
                parse_mode='Markdown'
            )
            
            # Get market analysis
            market_summary = await self.financial_rss_service.get_real_time_market_summary()
            
            if market_summary.get('success'):
                # Format response
                response = await self._format_market_analysis_response(market_summary)
                
                # Update message
                await processing_msg.edit_text(response, parse_mode='Markdown')
                
                # Add keyboard for additional actions
                keyboard = [
                    ["📈 Phân tích cổ phiếu cụ thể", "💼 Tạo portfolio"],
                    ["🔄 Cập nhật thị trường", "🏠 Quay lại menu chính"]
                ]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                
                await update.message.reply_text(
                    "📋 **Chọn hành động tiếp theo:**",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                
            else:
                await processing_msg.edit_text(
                    f"❌ **LỖI PHÂN TÍCH THỊ TRƯỜNG**\n\n"
                    f"Không thể lấy dữ liệu thị trường: {market_summary.get('error', 'Unknown error')}\n\n"
                    f"Vui lòng thử lại sau.",
                    parse_mode='Markdown'
                )
            
        except Exception as e:
            logger.error(f"❌ Market analysis error: {e}")
            await update.message.reply_text(
                "❌ **LỖI HỆ THỐNG**\n\n"
                "Không thể thực hiện phân tích thị trường. Vui lòng thử lại sau.",
                parse_mode='Markdown'
            )

    async def handle_stock_analysis_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle stock analysis request"""
        try:
            user_id = update.effective_user.id
            
            # Show stock selection
            keyboard = [
                ["VIC - Vingroup", "VCB - Vietcombank", "BID - BIDV"],
                ["TCB - Techcombank", "VHM - Vinhomes", "HPG - Hoa Phat"],
                ["AAPL - Apple", "GOOGL - Google", "MSFT - Microsoft"],
                ["TSLA - Tesla", "NVDA - NVIDIA", "📝 Nhập mã khác"],
                ["🏠 Quay lại menu chính"]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            await update.message.reply_text(
                "📈 **CHỌN CỔ PHIẾU CẦN PHÂN TÍCH**\n\n"
                "🇻🇳 **Cổ phiếu Việt Nam:**\n"
                "• VIC, VCB, BID, TCB, VHM, HPG\n\n"
                "🌍 **Cổ phiếu Quốc tế:**\n"
                "• AAPL, GOOGL, MSFT, TSLA, NVDA\n\n"
                "Hoặc chọn '📝 Nhập mã khác' để nhập mã tùy chỉnh.",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            # Set state for stock analysis
            context.user_data['waiting_for_stock'] = True
            
        except Exception as e:
            logger.error(f"❌ Stock analysis request error: {e}")
            await update.message.reply_text(
                "❌ Lỗi khi khởi tạo phân tích cổ phiếu.",
                parse_mode='Markdown'
            )

    async def handle_portfolio_creation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle portfolio creation request"""
        try:
            user_id = update.effective_user.id
            
            # Show risk profile selection
            keyboard = [
                ["🛡️ Bảo thủ (Conservative)", "⚖️ Cân bằng (Moderate)"],
                ["🚀 Tích cực (Aggressive)", "🏠 Quay lại menu chính"]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            await update.message.reply_text(
                "💼 **TẠO PORTFOLIO ĐẦU TƯ THÔNG MINH**\n\n"
                "📊 Chọn hồ sơ rủi ro của bạn:\n\n"
                "🛡️ **Bảo thủ:** Ưu tiên bảo toàn vốn, rủi ro thấp\n"
                "⚖️ **Cân bằng:** Cân bằng rủi ro và lợi nhuận\n"
                "🚀 **Tích cực:** Chấp nhận rủi ro cao để có lợi nhuận cao\n\n"
                "AI sẽ phân tích và tạo portfolio tối ưu dựa trên dữ liệu real-time.",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            # Set state for portfolio creation
            context.user_data['waiting_for_risk_profile'] = True
            
        except Exception as e:
            logger.error(f"❌ Portfolio creation error: {e}")
            await update.message.reply_text(
                "❌ Lỗi khi khởi tạo tạo portfolio.",
                parse_mode='Markdown'
            )

    async def handle_risk_profile_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str):
        """Handle risk profile selection for portfolio creation"""
        try:
            user_id = update.effective_user.id
            
            # Clear the waiting flag
            context.user_data['waiting_for_risk_profile'] = False
            
            # Handle menu return
            if message_text == "🏠 Quay lại menu chính":
                await update.message.reply_text(
                    "🏠 **Quay lại menu chính**\n\n"
                    "💡 Gửi `/ai` để xem tất cả lệnh AI available",
                    reply_markup=ReplyKeyboardRemove(),
                    parse_mode='Markdown'
                )
                return
            
            # Map risk profile choices
            risk_profile_map = {
                "🛡️ Bảo thủ (Conservative)": "conservative",
                "⚖️ Cân bằng (Moderate)": "moderate", 
                "🚀 Tích cực (Aggressive)": "aggressive"
            }
            
            risk_profile = risk_profile_map.get(message_text)
            
            if not risk_profile:
                await update.message.reply_text(
                    "❌ **Lựa chọn không hợp lệ**\n\n"
                    "Vui lòng chọn một trong các hồ sơ rủi ro:\n"
                    "🛡️ Bảo thủ (Conservative)\n"
                    "⚖️ Cân bằng (Moderate)\n"
                    "🚀 Tích cực (Aggressive)",
                    parse_mode='Markdown'
                )
                # Reset the flag to try again
                context.user_data['waiting_for_risk_profile'] = True
                return
            
            # Show processing message
            processing_msg = await update.message.reply_text(
                f"🔄 **Đang tạo portfolio {message_text.split('(')[0].strip()}**\n\n"
                "🤖 AI đang phân tích thị trường và tối ưu hóa danh mục đầu tư...",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode='Markdown'
            )
            
            # Generate portfolio with selected risk profile
            if not self.ai_investment_service:
                await processing_msg.edit_text(
                    "❌ **LỖI HỆ THỐNG**\n\n"
                    "Dịch vụ AI chưa được khởi tạo. Vui lòng thử lại sau.",
                    parse_mode='Markdown'
                )
                return
            
            # Get sample symbols for portfolio
            symbols = ['VIC', 'VCB', 'AAPL', 'GOOGL', 'TSLA']
            
            # Generate portfolio recommendation with selected risk profile
            portfolio = await self.ai_investment_service.generate_smart_portfolio_recommendation(
                symbols=symbols,
                risk_profile=risk_profile,
                investment_amount=100000000  # 100M VND default
            )
            
            # Format and send portfolio response
            portfolio_message = self._format_portfolio_recommendation_with_risk(portfolio, risk_profile, message_text)
            
            # Try to edit message, fallback to new message if fails
            try:
                await processing_msg.edit_text(portfolio_message, parse_mode='Markdown')
            except Exception as edit_error:
                logger.warning(f"⚠️ Cannot edit message, sending new: {edit_error}")
                await update.message.reply_text(portfolio_message, parse_mode='Markdown')
            
            # Add follow-up keyboard
            keyboard = [
                ["📊 Phân tích chi tiết", "🔄 Thay đổi hồ sơ rủi ro"],
                ["🏠 Menu chính", "📞 Hỗ trợ"]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            await update.message.reply_text(
                "📋 **Bạn muốn làm gì tiếp theo?**",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"❌ Risk profile selection error: {e}")
            await update.message.reply_text(
                "❌ **LỖI TẠO PORTFOLIO**\n\n"
                f"Không thể tạo portfolio: {e}\n\n"
                "Vui lòng thử lại bằng cách gửi `/ai portfolio`",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode='Markdown'
            )

    def _format_portfolio_recommendation_with_risk(self, portfolio, risk_profile: str, selected_text: str) -> str:
        """Format portfolio recommendation with risk profile context"""
        
        risk_descriptions = {
            'conservative': {
                'emoji': '🛡️',
                'name': 'Bảo Thủ',
                'description': 'Ưu tiên bảo toàn vốn và thu nhập ổn định'
            },
            'moderate': {
                'emoji': '⚖️', 
                'name': 'Cân Bằng',
                'description': 'Cân bằng giữa tăng trưởng và bảo toàn vốn'
            },
            'aggressive': {
                'emoji': '🚀',
                'name': 'Tích Cực', 
                'description': 'Tối đa hóa tăng trưởng, chấp nhận rủi ro cao'
            }
        }
        
        risk_info = risk_descriptions.get(risk_profile, risk_descriptions['moderate'])
        
        message = f"""
{risk_info['emoji']} **PORTFOLIO {risk_info['name'].upper()}**

📋 **Hồ sơ rủi ro:** {selected_text}
💡 **Mô tả:** {risk_info['description']}

📊 **KẾT QUẢ PHÂN TÍCH AI:**
🎯 **Điểm tổng:** {portfolio.total_score:.0f}/100
🛡️ **Đánh giá rủi ro:** {portfolio.risk_assessment}
📈 **Lợi nhuận kỳ vọng:** {portfolio.expected_return:.1f}%/năm
⚖️ **Tỷ lệ Sharpe:** {portfolio.sharpe_ratio:.2f}
📉 **Max Drawdown:** {portfolio.max_drawdown:.1f}%
🎲 **Điểm đa dạng hóa:** {portfolio.diversification_score:.0f}/100

💼 **PHÂN BỔ ĐỀ XUẤT:**
"""
        
        for symbol, weight in portfolio.allocation.items():
            message += f"• **{symbol}:** {weight:.1f}%\n"
        
        if portfolio.sector_allocation:
            message += f"\n🏭 **PHÂN BỔ THEO NGÀNH:**\n"
            for sector, weight in portfolio.sector_allocation.items():
                message += f"• {sector}: {weight:.1f}%\n"
        
        message += f"""
💡 **KHUYẾN NGHỊ CHÍNH:**
"""
        
        for i, rec in enumerate(portfolio.recommendations[:3], 1):
            message += f"{i}. {rec}\n"
        
        message += f"""
🔄 **Tần suất cân bằng:** {portfolio.rebalancing_frequency}

⚠️ **LƯU Ý QUAN TRỌNG:**
• Portfolio được tối ưu hóa theo hồ sơ rủi ro {risk_info['name'].lower()}
• Dựa trên dữ liệu thị trường real-time và phân tích AI
• Chỉ mang tính chất tham khảo, không phải lời khuyên đầu tư
• Nên tham khảo ý kiến chuyên gia tài chính trước khi quyết định
        """
        
        return message.strip()

    async def _format_market_analysis_response(self, market_summary: dict) -> str:
        """Format market analysis response"""
        try:
            coverage = market_summary.get('coverage', {})
            analysis = market_summary.get('market_analysis', [])
            headlines = market_summary.get('top_headlines', [])
            
            response = "📊 **BÁO CÁO PHÂN TÍCH THỊ TRƯỜNG REAL-TIME**\n\n"
            
            # Data coverage
            response += f"📈 **TỔNG QUAN DỮ LIỆU:**\n"
            response += f"• Cổ phiếu VN: {coverage.get('vn_stocks', 0)} cập nhật\n"
            response += f"• Cổ phiếu Quốc tế: {coverage.get('global_stocks', 0)} cập nhật\n"
            response += f"• Giá vàng: {coverage.get('gold_updates', 0)} cập nhật\n"
            response += f"• Tỷ giá: {coverage.get('currency_updates', 0)} cập nhật\n"
            response += f"• Tổng tin tức: {coverage.get('total_news', 0)} bài\n\n"
            
            # AI Analysis
            if analysis:
                response += "🤖 **PHÂN TÍCH AI CHUYÊN SÂU:**\n"
                for i, report in enumerate(analysis[:3], 1):
                    trend_emoji = "📈" if report.get('trend') == 'BULLISH' else "📉" if report.get('trend') == 'BEARISH' else "➡️"
                    response += f"{trend_emoji} **{report.get('market_name', 'Unknown')}**\n"
                    response += f"   Xu hướng: {report.get('trend', 'N/A')} ({report.get('momentum', 'N/A')})\n"
                    response += f"   Khuyến nghị: {report.get('recommendation', 'N/A')}\n"
                    response += f"   Tin cậy: {report.get('confidence_score', 0):.0f}%\n\n"
            
            # Top headlines
            if headlines:
                response += "📰 **TIN TỨC NỔI BẬT:**\n"
                for i, news in enumerate(headlines[:5], 1):
                    title = news.get('title', 'No title')
                    source = news.get('source', 'Unknown')
                    sentiment = news.get('extracted_data', {}).get('sentiment', 'neutral')
                    sentiment_emoji = "😊" if sentiment == 'bullish' else "😰" if sentiment == 'bearish' else "😐"
                    
                    response += f"{sentiment_emoji} {title[:60]}...\n"
                    response += f"   📡 {source}\n\n"
            
            # Performance info
            performance = market_summary.get('performance', {})
            response += "⚡ **HIỆU SUẤT:**\n"
            response += f"• Nguồn dữ liệu: {performance.get('sources_fetched', 0)}\n"
            response += f"• Thời gian phản hồi: {performance.get('response_time', 'N/A')}\n"
            response += f"• Cập nhật: {market_summary.get('timestamp', datetime.now()).strftime('%H:%M %d/%m/%Y')}\n\n"
            
            response += "💡 *Dữ liệu được cập nhật real-time từ RSS feeds quốc tế*"
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Format market analysis error: {e}")
            return "❌ Lỗi định dạng báo cáo phân tích thị trường."

    async def _handle_stock_symbol_analysis(self, symbol: str, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle analysis for specific stock symbol"""
        try:
            user_id = update.effective_user.id
            
            # Send processing message
            processing_msg = await update.message.reply_text(
                f"🔄 **ĐANG PHÂN TÍCH CỔ PHIẾU {symbol}...**\n\n"
                "📊 Thu thập dữ liệu real-time...\n"
                "🤖 AI phân tích kỹ thuật & cơ bản...\n"
                "📈 Tạo khuyến nghị đầu tư...",
                parse_mode='Markdown'
            )
            
            # Get AI analysis
            analysis = await self.ai_investment_service.analyze_stock_comprehensive_enhanced(
                symbol=symbol,
                include_rss_data=True,
                analysis_depth="deep"
            )
            
            # Format response
            response = await self._format_stock_analysis_response(symbol, analysis)
            
            # Update message
            await processing_msg.edit_text(response, parse_mode='Markdown')
            
            # Clear state
            context.user_data.pop('waiting_for_stock', None)
            
        except Exception as e:
            logger.error(f"❌ Stock analysis error for {symbol}: {e}")
            await update.message.reply_text(
                f"❌ **LỖI PHÂN TÍCH {symbol}**\n\n"
                f"Không thể phân tích cổ phiếu. Vui lòng thử lại sau.",
                parse_mode='Markdown'
            )

    async def _format_stock_analysis_response(self, symbol: str, analysis) -> str:
        """Format stock analysis response"""
        try:
            response = f"📊 **PHÂN TÍCH AI CHO {symbol}**\n\n"
            
            # Basic info
            price_emoji = "📈" if analysis.recommendation == 'BUY' else "📉" if analysis.recommendation == 'SELL' else "➡️"
            response += f"{price_emoji} **GIÁ HIỆN TẠI:** {analysis.current_price:,.2f}\n"
            response += f"🎯 **GIÁ MỤC TIÊU:** {analysis.target_price:,.2f}\n"
            response += f"💡 **KHUYẾN NGHỊ:** {analysis.recommendation}\n"
            response += f"🔒 **ĐỘ TIN CẬY:** {analysis.confidence_score:.0f}%\n"
            response += f"⚠️ **RỦI RO:** {analysis.risk_level}\n"
            response += f"⏰ **KHUNG THỜI GIAN:** {analysis.time_horizon}\n\n"
            
            # Sentiment analysis
            sentiment = analysis.sentiment_analysis
            sentiment_emoji = "😊" if sentiment.get('overall_sentiment') == 'BULLISH' else "😰" if sentiment.get('overall_sentiment') == 'BEARISH' else "😐"
            response += f"📰 **SENTIMENT THỊ TRƯỜNG:**\n"
            response += f"{sentiment_emoji} {sentiment.get('overall_sentiment', 'NEUTRAL')} ({sentiment.get('sentiment_score', 50):.0f}/100)\n\n"
            
            # Technical indicators
            tech = analysis.technical_indicators
            if tech:
                momentum = tech.get('momentum_indicators', {})
                trend = tech.get('trend_indicators', {})
                response += f"📈 **CHỈ SỐ KỸ THUẬT:**\n"
                response += f"• RSI: {momentum.get('RSI', 'N/A')}\n"
                response += f"• SMA 20: {trend.get('SMA_20', 'N/A')}\n"
                response += f"• MACD: {trend.get('MACD', {}).get('value', 'N/A')}\n\n"
            
            # Key factors
            if analysis.key_factors:
                response += f"🔑 **YẾU TỐ CHÍNH:**\n"
                for i, factor in enumerate(analysis.key_factors[:3], 1):
                    response += f"{i}. {factor[:50]}...\n"
                response += "\n"
            
            # Market conditions
            market_conditions = analysis.market_conditions
            if market_conditions:
                response += f"🌍 **ĐIỀU KIỆN THỊ TRƯỜNG:**\n"
                response += f"• Giai đoạn: {market_conditions.get('market_phase', 'N/A')}\n"
                response += f"• Biến động: {market_conditions.get('volatility_regime', 'N/A')}\n\n"
            
            response += f"⏰ *Cập nhật: {analysis.last_updated.strftime('%H:%M %d/%m/%Y')}*\n"
            response += f"🤖 *Phân tích bởi AI với dữ liệu RSS real-time*"
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Format stock analysis error: {e}")
            return f"❌ Lỗi định dạng phân tích cổ phiếu {symbol}."

    async def ai_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /ai command with subcommands"""
        try:
            args = context.args
            if not args:
                # Show AI help
                help_text = """
🤖 **AI PHÂN TÍCH ĐẦU TƯ**

**📋 LỆNH AVAILABLE:**
• `/ai market` - Phân tích thị trường tổng quan
• `/ai stock VIC` - Phân tích cổ phiếu (VIC, AAPL, etc.)
• `/ai portfolio` - Tạo danh mục đầu tư thông minh
• `/ai gold` - Phân tích giá vàng và kim loại quý
• `/ai sentiment` - Phân tích sentiment thị trường

**💡 VÍ DỤ:**
• `/ai market` - Xem tổng quan thị trường
• `/ai stock AAPL` - Phân tích cổ phiếu Apple
• `/ai portfolio` - Tạo portfolio đầu tư
                """
                await update.message.reply_text(help_text, parse_mode='Markdown')
                return
            
            command = args[0].lower()
            
            if command == "market":
                await self.ai_market_command(update, context)
            elif command == "stock":
                await self.ai_stock_command(update, context, args[1:])
            elif command == "portfolio":
                await self.ai_portfolio_command(update, context)
            elif command == "gold":
                await self.ai_gold_command(update, context)
            elif command == "sentiment":
                await self.ai_sentiment_command(update, context)
            else:
                await update.message.reply_text(
                    f"❌ Lệnh không hợp lệ: `/ai {command}`\n\n"
                    "💡 Gửi `/ai` để xem danh sách lệnh"
                )
                
        except Exception as e:
            logger.error(f"❌ AI command error: {e}")
            await update.message.reply_text("❌ Lỗi xử lý lệnh AI. Vui lòng thử lại!")

    async def ai_market_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /ai market - Market analysis"""
        try:
            await update.message.reply_text("📊 Đang phân tích thị trường...")
            await self.handle_market_analysis(update, context)
        except Exception as e:
            logger.error(f"❌ AI market error: {e}")
            await update.message.reply_text("❌ Không thể phân tích thị trường!")

    async def ai_stock_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, args):
        """Handle /ai stock <symbol> - Stock analysis"""
        try:
            if not args:
                await update.message.reply_text(
                    "💡 **Cách dùng:** `/ai stock <mã_cổ_phiếu>`\n\n"
                    "**Ví dụ:**\n"
                    "• `/ai stock VIC` - Vingroup\n"
                    "• `/ai stock AAPL` - Apple\n"
                    "• `/ai stock GOOGL` - Google"
                )
                return
            
            symbol = args[0].upper()
            await update.message.reply_text(f"📈 Đang phân tích {symbol}...")
            await self._handle_stock_symbol_analysis(symbol, update, context)
            
        except Exception as e:
            logger.error(f"❌ AI stock error: {e}")
            await update.message.reply_text("❌ Không thể phân tích cổ phiếu!")

    async def ai_portfolio_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /ai portfolio - Portfolio creation"""
        try:
            await update.message.reply_text("💼 Đang tạo portfolio thông minh...")
            await self.handle_portfolio_creation(update, context)
        except Exception as e:
            logger.error(f"❌ AI portfolio error: {e}")
            await update.message.reply_text("❌ Không thể tạo portfolio!")

    async def ai_gold_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /ai gold - Gold price analysis"""
        try:
            await update.message.reply_text("🥇 Đang phân tích giá vàng...")
            
            # Get gold price data
            if self.market_service:
                gold_data = await self.market_service.get_gold_prices()
                
                # Enhanced analysis with AI
                analysis = await self.ai_investment_service.analyze_stock_comprehensive_enhanced("GOLD")
                
                # Access GoldData attributes directly, not using .get()
                usd_price = gold_data.price_usd if gold_data.price_usd else 0
                vnd_price = gold_data.price_vnd if gold_data.price_vnd else 0
                change_percent = gold_data.change_percent if gold_data.change_percent else 0
                
                message = f"""
🥇 **PHÂN TÍCH GIÁ VÀNG AI**

💰 **Giá hiện tại:** ${usd_price:.2f}/oz
💵 **VND:** {vnd_price:,.0f} VND/lượng
📈 **Thay đổi:** {change_percent:+.2f}%

🤖 **PHÂN TÍCH AI:**
📊 **Khuyến nghị:** {analysis.recommendation}
🎯 **Tin cậy:** {analysis.confidence_score:.0f}%
⚠️ **Rủi ro:** {analysis.risk_level}

📝 **Nhận định:** {analysis.analysis_summary}

⚠️ *Giá vàng biến động cao. Đầu tư thận trọng.*
                """
                
                await update.message.reply_text(message, parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ Dịch vụ market chưa sẵn sàng!")
                
        except Exception as e:
            logger.error(f"❌ AI gold error: {e}")
            await update.message.reply_text("❌ Không thể phân tích giá vàng!")

    async def ai_sentiment_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /ai sentiment - Market sentiment analysis"""
        try:
            await update.message.reply_text("📊 Đang phân tích sentiment thị trường...")
            
            sentiment = await self.ai_investment_service.analyze_market_sentiment_comprehensive()
            
            message = f"""
📊 **SENTIMENT THỊ TRƯỜNG AI**

⚖️ **Tổng quan:** {sentiment.overall_sentiment}
📈 **Điểm sentiment:** {sentiment.sentiment_score:+.1f}/100
🎯 **Tin cậy:** {sentiment.confidence:.0f}%
📰 **Số tin:** {sentiment.news_volume}

🔍 **Động lực chính:**
            """
            
            for driver in sentiment.key_drivers[:3]:
                message += f"• {driver}\n"
            
            message += f"""
🔮 **Triển vọng:** {sentiment.outlook}

⚠️ *Sentiment có thể thay đổi nhanh theo tin tức.*
            """
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"❌ AI sentiment error: {e}")
            await update.message.reply_text("❌ Không thể phân tích sentiment!")
