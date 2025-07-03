"""
News-Facebook AI Agent Workflow Service
Orchestrates the complete workflow from news fetching to Facebook publishing

Workflow Steps:
1. Get & Rank News from 3 sources (Guardian, AP News, Reuters)
2. Present top 3 with inline buttons for user selection
3. Search Expert's Facebook for related posts
4. Generate Vietnamese content with AI
5. Create and approve image with PioneerX logo
6. Publish to Facebook and log all steps
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
import os
import random
from datetime import datetime, timedelta
from .enhanced_summary_service import EnhancedSummaryService
from .workflow_csv_logger import WorkflowCSVLogger
from .detailed_workflow_logger import DetailedWorkflowLogger

logger = logging.getLogger(__name__)

class WorkflowService:
    def __init__(self, news_service, ai_service, image_service, facebook_service, logging_service):
        self.news_service = news_service
        self.ai_service = ai_service
        self.image_service = image_service
        self.facebook_service = facebook_service
        self.logging_service = logging_service
        self.user_sessions = {}
        
        # Initialize Enhanced Summary Service với Ultra RSS Power
        self.enhanced_summary_service = EnhancedSummaryService(ai_service)
        
        # Initialize Workflow CSV Logger
        self.csv_logger = WorkflowCSVLogger()
        
        # Initialize Detailed Workflow Logger (comprehensive tracking)
        self.detailed_logger = DetailedWorkflowLogger()
        
    async def start_workflow(self, user_id: int, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
        """Start the complete News-Facebook AI Agent Workflow"""
        logger.info(f"🚀 Starting News-Facebook AI Workflow for user {user_id}")
        
        # Log workflow start
        self.csv_logger.log_workflow_start(user_id)
        
        # Initialize user session
        self.user_sessions[user_id] = {
            'state': 'fetching_news',
            'start_time': datetime.now(),
            'articles': [],
            'selected_article': None,
            'expert_context': None,
            'generated_post': None,
            'generated_image': None,
            'facebook_post_id': None
        }
        
        # Send initial message
        progress_message = await context.bot.send_message(
            chat_id=chat_id,
            text="🚀 **Khởi động News-Facebook AI Agent Workflow**\n\n" +
                 "📰 Đang tìm kiếm tin tức từ các nguồn chính...\n" +
                 "• The Guardian\n• AP News\n• Reuters\n\n" +
                 "⏳ Vui lòng chờ...",
            parse_mode='Markdown'
        )
        
        try:
            # Step 1: Fetch and Rank News
            await self._step1_fetch_and_rank_news(user_id, context, chat_id, progress_message)
            
        except Exception as e:
            logger.error(f"❌ Workflow error for user {user_id}: {e}")
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ **Lỗi trong quá trình xử lý:**\n{str(e)}\n\n" +
                     "Vui lòng thử lại bằng cách gửi **'Start'**",
                parse_mode='Markdown'
            )
    
    def get_user_session(self, user_id: int) -> Optional[Dict]:
        """Get user session data"""
        return self.user_sessions.get(user_id)
    
    def clear_user_session(self, user_id: int):
        """Clear user session data"""
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]

    async def _step2_search_international_blogs(self, user_id: int, context: ContextTypes.DEFAULT_TYPE,
                                          chat_id: int, selected_article):
        """Step 2: Search International Blog Articles with RSS Sources"""
        
        logger.info(f"Starting international blog search for user {user_id}")
        
        try:
            # Search for related articles from international RSS sources
            logger.info(f"Searching international blogs for user {user_id}")
            blog_context = await self._search_international_blog_sources(selected_article)
            
            # Store in session
            self.user_sessions[user_id]['expert_context'] = blog_context
            self.user_sessions[user_id]['state'] = 'generating_post'
            logger.info(f"Updated session state to 'generating_post' for user {user_id}")
            
            # Send update about found articles
            found_articles = len(blog_context.get('related_articles', []))
            logger.info(f"Found {found_articles} international blog articles for user {user_id}")
            
            if found_articles > 0:
                context_message = f"✅ **Tìm thấy {found_articles} bài viết từ blog quốc tế**\n\n"
                
                # Show a preview of found articles with direct links
                for i, article in enumerate(blog_context['related_articles'][:5], 1):
                    title = article.get('title', 'Untitled')[:70]
                    source = article.get('source', 'Unknown Source')
                    url = article.get('url', '')
                    summary = article.get('summary', '')[:100]
                    credibility = article.get('credibility', 'N/A')
                    
                    context_message += f"📰 **{i}. {source}** ({credibility})\n"
                    context_message += f"📄 {title}...\n"
                    if summary:
                        context_message += f"💡 {summary}...\n"
                    context_message += f"🔗 **Link:** {url}\n\n"
                
                # Show metadata
                metadata = blog_context.get('metadata', {})
                sources_list = metadata.get('sources', [])
                if sources_list:
                    context_message += f"🌐 **Nguồn:** {', '.join(sources_list[:3])}...\n"
                    context_message += f"⏱️ **Thời gian tìm kiếm:** {metadata.get('processing_time', 'N/A')}\n\n"
                
                context_message += "🤖 **Bước 3: Tạo nội dung AI với ngữ cảnh quốc tế...**"
            else:
                context_message = "ℹ️ **Không tìm thấy bài viết liên quan từ blog quốc tế**\n\n" + \
                                "🤖 **Bước 3: Tạo nội dung AI không có ngữ cảnh bổ sung...**"
            
            logger.info(f"Sending blog context message to user {user_id}")
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=context_message,
                    parse_mode='Markdown',
                    disable_web_page_preview=True
                )
            except Exception as parse_error:
                # Fallback without markdown if parsing fails
                safe_message = context_message.replace('**', '').replace('*', '')
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=safe_message,
                    disable_web_page_preview=True
                )
            
            # Continue to post generation
            logger.info(f"Continuing to step 3 for user {user_id}")
            await self._step3_generate_post(user_id, context, chat_id, selected_article, blog_context)
            
        except Exception as e:
            logger.error(f"❌ Error searching international blogs for user {user_id}: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            
            try:
                # Continue without blog context
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="⚠️ **Không thể tìm kiếm blog quốc tế**\n\n" +
                         "🤖 **Tiếp tục tạo nội dung AI...**",
                    parse_mode='Markdown'
                )
                
                self.user_sessions[user_id]['expert_context'] = {'related_articles': []}
                logger.info(f"Continuing to step 3 without blog context for user {user_id}")
                await self._step3_generate_post(user_id, context, chat_id, selected_article, {'related_articles': []})
            except Exception as fallback_error:
                logger.error(f"Error in fallback for user {user_id}: {fallback_error}")

    async def _search_international_blog_sources(self, selected_article) -> Dict:
        """Search international blog sources using RSS service"""
        
        try:
            logger.info(f"🔍 Searching international RSS sources for: {selected_article.title}")
            
            # Use enhanced summary service to find related articles
            enhanced_result = await self.enhanced_summary_service.search_international_content(
                selected_article, max_results=10
            )
            
            # Format for compatibility
            blog_context = {
                'search_query': selected_article.title,
                'related_articles': enhanced_result,
                'sources_used': list(set([article.get('source', 'Unknown') for article in enhanced_result])),
                'metadata': {
                    'articles_found': len(enhanced_result),
                    'sources': list(set([article.get('source', 'Unknown') for article in enhanced_result])),
                    'processing_time': '2-5s',
                    'search_method': 'RSS Enhanced Search'
                }
            }
            
            logger.info(f"✅ Found {len(enhanced_result)} articles from international sources")
            return blog_context
            
        except Exception as e:
            logger.error(f"❌ Error searching international blog sources: {e}")
            return {
                'search_query': selected_article.title if selected_article else 'Unknown',
                'related_articles': [],
                'sources_used': [],
                'metadata': {'status': 'error', 'articles_found': 0}
            }

    def _extract_keywords_from_article(self, article) -> List[str]:
        """Extract relevant keywords from article for Facebook search"""
        import re
        from config import Config
        config = Config()
        
        # Combine title and content
        text = f"{article.title} {article.content}"
        
        # Extract keywords that match our relevance criteria
        keywords = []
        for keyword in config.RELEVANCE_KEYWORDS:
            if keyword.lower() in text.lower():
                keywords.append(keyword)
        
        # Add article-specific keywords
        words = re.findall(r'\b[A-Za-z]{4,}\b', text)
        important_words = [w for w in words if len(w) > 5 and w[0].isupper()][:5]
        keywords.extend(important_words)
        
        return list(set(keywords))[:10]  # Return unique keywords, max 10

    async def handle_post_approval(self, user_id: int, action: str, context: ContextTypes.DEFAULT_TYPE, query):
        """Handle post approval or edit request"""
        
        if user_id not in self.user_sessions:
            await query.answer("❌ Phiên làm việc đã hết hạn")
            return
        
        session = self.user_sessions[user_id]
        
        if action == 'approve':
            await query.answer("✅ Đã phê duyệt nội dung")
            session['state'] = 'generating_image'
            
            # Update message
            await query.edit_message_text(
                f"✅ **Nội dung đã được phê duyệt**\n\n" +
                f"{session['generated_post']}\n\n" +
                "🎨 **Bước 4: Tạo hình ảnh với logo PioneerX...**",
                parse_mode='Markdown'
            )
            
            # Continue to image generation
            await self._step4_generate_image(user_id, context, query.message.chat_id)
            
        elif action == 'edit':
            await query.answer("✏️ Vui lòng gửi yêu cầu chỉnh sửa")
            session['state'] = 'editing_post'
            
            await query.edit_message_text(
                f"✏️ **Chế độ chỉnh sửa**\n\n" +
                f"Nội dung hiện tại:\n{session['generated_post']}\n\n" +
                "💬 **Hãy gửi tin nhắn để chỉnh sửa:**\n" +
                "Ví dụ: 'Làm ngắn gọn hơn' hoặc 'Thêm thông tin về tác động kinh tế'",
                parse_mode='Markdown'
            )

    async def handle_post_edit_request(self, user_id: int, edit_request: str, 
                                     context: ContextTypes.DEFAULT_TYPE, chat_id: int):
        """Handle post edit request from user"""
        
        if user_id not in self.user_sessions:
            await context.bot.send_message(chat_id, "❌ Phiên làm việc đã hết hạn")
            return
        
        session = self.user_sessions[user_id]
        
        if session['state'] != 'editing_post':
            await context.bot.send_message(chat_id, "❌ Trạng thái không hợp lệ")
            return
        
        try:
            # Create edit prompt
            edit_prompt = f"""
Hãy chỉnh sửa bài Facebook post sau theo yêu cầu của người dùng:

NỘI DUNG HIỆN TẠI:
{session['generated_post']}

YÊU CẦU CHỈNH SỬA:
{edit_request}

Hãy tạo lại nội dung với những thay đổi được yêu cầu, giữ nguyên phong cách và độ dài phù hợp.
"""
            
            # Generate revised content
            revised_content = await self.ai_service.generate_content(edit_prompt)
            
            # Update session
            session['generated_post'] = revised_content
            session['state'] = 'approving_post'
            
            # Present revised content for approval
            progress_message = await context.bot.send_message(
                chat_id=chat_id,
                text="🔄 Đang chỉnh sửa...",
                parse_mode='Markdown'
            )
            
            await self._present_post_approval(user_id, context, chat_id, revised_content, progress_message)
            
        except Exception as e:
            logger.error(f"❌ Error handling edit request: {e}")
            await context.bot.send_message(
                chat_id,
                f"❌ **Lỗi chỉnh sửa:**\n{str(e)}\n\nVui lòng thử lại.",
                parse_mode='Markdown'
            )

    async def handle_image_approval(self, user_id: int, action: str, context: ContextTypes.DEFAULT_TYPE, query):
        """Handle image approval or regeneration request"""
        
        if user_id not in self.user_sessions:
            await query.answer("❌ Phiên làm việc đã hết hạn")
            return
        
        session = self.user_sessions[user_id]
        
        if action == 'approve':
            await query.answer("✅ Đã phê duyệt hình ảnh")
            session['state'] = 'publishing'
            
            # Update message
            await query.edit_message_text(
                "✅ **Hình ảnh đã được phê duyệt**\n\n" +
                "📱 **Bước 5: Đăng lên Facebook...**",
                parse_mode='Markdown'
            )
            
            # Continue to publishing
            await self._step5_publish_to_facebook(user_id, context, query.message.chat_id)
            
        elif action == 'regenerate':
            await query.answer("🔄 Đang tạo ảnh mới...")
            
            await query.edit_message_text(
                "🔄 **Đang tạo lại hình ảnh...**\n⏳ Vui lòng chờ...",
                parse_mode='Markdown'
            )
            
            # Regenerate image
            await self._step4_generate_image(user_id, context, query.message.chat_id)

    async def _step1_fetch_and_rank_news(self, user_id: int, context: ContextTypes.DEFAULT_TYPE, 
                                        chat_id: int, progress_message):
        """Step 1: Fetch & Rank News from 3 sources"""
        
        # Update progress
        await progress_message.edit_text(
            "📰 **Bước 1: Thu thập & Phân tích tin tức**\n\n" +
            "🔍 Đang tìm kiếm bài viết mới nhất...\n" +
            "⏳ Vui lòng chờ (30-60 giây)",
            parse_mode='Markdown'
        )
        
        # Fetch articles from all sources
        start_time = datetime.now()
        articles = await self.news_service.fetch_all_news()
        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Log news fetch
        self.csv_logger.log_step1_fetch_news(
            user_id=user_id,
            article_count=len(articles) if articles else 0,
            sources=['news_service', 'guardian', 'ap_news', 'reuters'],
            duration_ms=duration_ms,
            status='success' if articles else 'no_articles'
        )
        
        if not articles:
            await progress_message.edit_text(
                "❌ **Không thể tìm thấy tin tức**\n\n" +
                "Có lỗi khi kết nối với các nguồn tin. Vui lòng thử lại sau.",
                parse_mode='Markdown'
            )
            return
        
        # Remove duplicates and rank
        unique_articles = self.news_service.remove_duplicates(articles)
        ranked_articles = self.news_service.rank_articles(unique_articles)
        
        # Take top 3
        top_articles = ranked_articles[:3]
        
        # Store in session
        self.user_sessions[user_id]['articles'] = top_articles
        self.user_sessions[user_id]['state'] = 'selecting_article'
        
        # Present top 3 articles with inline buttons
        await self._present_article_selection(user_id, context, chat_id, top_articles, progress_message)

    def _escape_markdown(self, text: str) -> str:
        """Escape markdown special characters to prevent parsing errors"""
        if not text:
            return ""
        
        # Escape markdown special characters
        special_chars = ['*', '_', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        escaped_text = text
        for char in special_chars:
            escaped_text = escaped_text.replace(char, f'\\{char}')
        return escaped_text

    async def _present_article_selection(self, user_id: int, context: ContextTypes.DEFAULT_TYPE,
                                       chat_id: int, articles: List, progress_message):
        """Present top 3 articles with formatted summaries and selection buttons"""
        
        try:
            # Build message with top 3 articles formatted properly
            message_text = "🏆 **TOP 3 TIN TỨC ĐƯỢC ĐỀ XUẤT**\n\n"
            
            for i, article in enumerate(articles, 1):
                relevance_score = getattr(article, 'relevance_score', 0)
                appeal_score = getattr(article, 'appeal_score', 0)
                
                # Format với emoji ranking
                rank_emoji = ["🥇", "🥈", "🥉"][i-1]
                
                # Escape markdown characters in title to prevent parsing errors
                safe_title = self._escape_markdown(article.title)
                safe_source = self._escape_markdown(article.source)
                safe_url = self._escape_markdown(article.url)
                
                message_text += f"{rank_emoji} **{i}\\. {safe_title}**\n"
                
                # Format tóm tắt theo yêu cầu với bullet points
                content_summary = self._format_article_summary(article.content)
                message_text += f"📝 **Tóm tắt:**\n{content_summary}\n"
                
                message_text += f"🎯 Độ liên quan: {relevance_score:.1f}/10\n"
                message_text += f"🔥 Độ hấp dẫn: {appeal_score:.1f}/10\n"
                message_text += f"🔗 Nguồn: {safe_source}\n"
                message_text += f"📄 Đọc bài gốc: {safe_url}\n\n"
            
            message_text += "👇 **Chọn bài viết bằng nút bấm bên dưới:**"
            
            # Update message with article selection
            await progress_message.edit_text(
                message_text,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            
        except Exception as e:
            logger.error(f"Error in _present_article_selection with markdown: {e}")
            # Fallback: Use safe text without markdown
            try:
                safe_message = f"🏆 TOP 3 TIN TỨC ĐƯỢC ĐỀ XUẤT\n\n"
                
                for i, article in enumerate(articles, 1):
                    relevance_score = getattr(article, 'relevance_score', 0)
                    appeal_score = getattr(article, 'appeal_score', 0)
                    rank_emoji = ["🥇", "🥈", "🥉"][i-1]
                    
                    safe_message += f"{rank_emoji} {i}. {article.title}\n"
                    content_summary = self._format_article_summary(article.content)
                    safe_message += f"📝 Tóm tắt:\n{content_summary}\n"
                    safe_message += f"🎯 Độ liên quan: {relevance_score:.1f}/10\n"
                    safe_message += f"🔥 Độ hấp dẫn: {appeal_score:.1f}/10\n"
                    safe_message += f"🔗 Nguồn: {article.source}\n"
                    safe_message += f"📄 Đọc bài gốc: {article.url}\n\n"
                
                safe_message += "👇 Chọn bài viết bằng nút bấm bên dưới:"
                
                await progress_message.edit_text(
                    safe_message,
                    disable_web_page_preview=True
                )
                
            except Exception as fallback_error:
                logger.error(f"Fallback edit also failed: {fallback_error}")
                # Send new message as last resort
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="🏆 Đã tìm thấy 3 bài viết phù hợp. Đang hiển thị danh sách..."
                )
        
        # Create reply keyboard for selection
        from telegram import KeyboardButton, ReplyKeyboardMarkup
        keyboard = [
            [KeyboardButton("1️⃣ Chọn bài 1")],
            [KeyboardButton("2️⃣ Chọn bài 2")],
            [KeyboardButton("3️⃣ Chọn bài 3")],
            [KeyboardButton("🔄 Bắt đầu lại")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        # Send reply keyboard as separate message
        await context.bot.send_message(
            chat_id=chat_id,
            text="👆 **Chọn bài viết:**",
            reply_markup=reply_markup
        )

    def _format_article_summary(self, content: str) -> str:
        """Format article content as bullet points with deduplication"""
        if not content:
            return "* Không có nội dung tóm tắt"
        
        # Clean content first
        content = content.strip()
        
        # Split content into sentences using multiple delimiters
        import re
        sentences = re.split(r'[.!?]+', content)
        
        # Clean and filter sentences, remove duplicates
        clean_sentences = []
        seen_sentences = set()
        
        for sentence in sentences:
            sentence = sentence.strip()
            
            # Skip empty, too short, or duplicate sentences
            if (not sentence or 
                len(sentence) < 30 or  # Increased minimum length for better quality
                sentence.lower() in seen_sentences):
                continue
                
            # Add sentence to seen set to prevent duplicates
            seen_sentences.add(sentence.lower())
            
            # Clean up sentence
            if not sentence.endswith('.'):
                sentence += '.'
                
            clean_sentences.append(sentence)
        
        # Take first 3-4 most meaningful sentences
        key_points = clean_sentences[:4]
        
        # If we don't have enough content, provide fallback
        if not key_points:
            return "* Đang xử lý nội dung bài viết..."
        
        # Format as bullet points with proper Vietnamese structure
        formatted_summary = ""
        for i, point in enumerate(key_points):
            # Ensure proper Vietnamese bullet format
            formatted_summary += f"* {point}\n"
        
        return formatted_summary.strip()

    async def handle_article_selection_text(self, user_id: int, message_text: str, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
        """Handle article selection via text message"""
        try:
            # Check if user has active workflow
            if user_id not in self.user_sessions:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ Không tìm thấy workflow đang hoạt động. Vui lòng gửi 'Start' để bắt đầu."
                )
                return
            
            # Parse selection - handle both keyboard buttons and manual text input
            selection_num = None
            
            if message_text == "1️⃣ Chọn bài 1":
                selection_num = 0
            elif message_text == "2️⃣ Chọn bài 2":
                selection_num = 1
            elif message_text == "3️⃣ Chọn bài 3":
                selection_num = 2
            elif message_text.startswith('Bài '):
                try:
                    selection_num = int(message_text.split()[1]) - 1
                except ValueError:
                    selection_num = None
            elif message_text.isdigit():
                try:
                    selection_num = int(message_text) - 1
                except ValueError:
                    selection_num = None
            
            if selection_num is not None and 0 <= selection_num < len(self.user_sessions[user_id]['articles']):
                selected_article = self.user_sessions[user_id]['articles'][selection_num]
                
                # Log article selection
                self.csv_logger.log_step2_article_selection(
                    user_id=user_id,
                    selected_rank=selection_num + 1,
                    article_title=selected_article.title,
                    total_articles=len(self.user_sessions[user_id]['articles'])
                )
                
                # Hide keyboard first
                from telegram import ReplyKeyboardRemove
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"✅ Đã chọn bài viết số {selection_num + 1}",
                    reply_markup=ReplyKeyboardRemove()
                )
                
                # Show article details and scoring
                await self._show_article_details(user_id, context, chat_id, selected_article)
                
                # Move to writing style selection
                await self._step2_5_select_writing_style(user_id, context, chat_id, selected_article)
                return
            
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Vui lòng chọn bài viết bằng cách nhấn nút hoặc gửi 'Bài 1', 'Bài 2', 'Bài 3'"
            )
            
        except Exception as e:
            logger.error(f"Error in handle_article_selection_text: {str(e)}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Lỗi xử lý lựa chọn bài viết. Vui lòng thử lại."
            )

    async def _show_article_details(self, user_id: int, context: ContextTypes.DEFAULT_TYPE, chat_id: int, article):
        """Show detailed article information and scoring"""
        try:
            # Get score breakdown
            score_breakdown = getattr(article, 'score_breakdown', {})
            relevance_score = getattr(article, 'relevance_score', 0)
            appeal_score = getattr(article, 'appeal_score', 0)
            final_score = getattr(article, 'final_score', 0)
            
            details_text = f"""📊 CHI TIẾT BÀI VIẾT ĐÃ CHỌN

📰 Tiêu đề: {article.title}
🏢 Nguồn: {article.source}
📝 Nội dung: {article.content[:200]}...

🎯 ĐIỂM ĐÁNH GIÁ:
• Điểm liên quan: {relevance_score:.1f}/10.0
• Điểm hấp dẫn: {appeal_score:.1f}/10.0
• Điểm tổng: {final_score:.1f}/10.0

📈 CHI TIẾT CHẤM ĐIỂM:
"""
            
            # Add relevance breakdown
            if hasattr(article, 'relevance_breakdown'):
                details_text += "\n🔍 Tiêu chí liên quan:\n"
                for criteria, score in article.relevance_breakdown.items():
                    criteria_name = {
                        'primary_keywords': 'Từ khóa chính',
                        'secondary_keywords': 'Từ khóa phụ',
                        'geographic_relevance': 'Liên quan địa lý',
                        'economic_impact': 'Tác động kinh tế',
                        'timeliness': 'Tính thời sự'
                    }.get(criteria, criteria)
                    details_text += f"  • {criteria_name}: {score:.1f}\n"
            
            # Add appeal breakdown
            if hasattr(article, 'appeal_breakdown'):
                details_text += "\n💫 Tiêu chí hấp dẫn:\n"
                for criteria, score in article.appeal_breakdown.items():
                    criteria_name = {
                        'headline_appeal': 'Tiêu đề hấp dẫn',
                        'content_quality': 'Chất lượng nội dung',
                        'controversy_factor': 'Yếu tố tranh cãi',
                        'source_credibility': 'Uy tín nguồn',
                        'engagement_potential': 'Tiềm năng tương tác'
                    }.get(criteria, criteria)
                    details_text += f"  • {criteria_name}: {score:.1f}\n"
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=details_text,
                parse_mode=None
            )
            
        except Exception as e:
            logger.error(f"Error showing article details: {str(e)}")

    async def _step2_5_select_writing_style(self, user_id: int, context: ContextTypes.DEFAULT_TYPE, chat_id: int, selected_article):
        """Let user select writing style"""
        try:
            # Clear any previous generated content to allow new generation
            session = self.user_sessions[user_id]
            keys_to_clear = ['generated_post', 'generated_image', 'facebook_post_id', 'writing_style', 'expert_context']
            for key in keys_to_clear:
                if key in session:
                    del session[key]
                    logger.info(f"Cleared {key} from session for user {user_id}")
            
            # Store selected article
            session['selected_article'] = selected_article
            session['step'] = 'writing_style_selection'
            session['state'] = 'writing_style_selection'
            
            logger.info(f"User {user_id} selecting writing style for new article. Session reset.")
            
            # Present writing style options
            await self._present_writing_style_options(user_id, context, chat_id)
            
        except Exception as e:
            logger.error(f"Error in _step2_5_select_writing_style: {str(e)}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Lỗi hiển thị tùy chọn phong cách viết. Vui lòng thử lại."
            )

    async def _present_writing_style_options(self, user_id: int, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
        """Present writing style options to user với buttons"""
        try:
            style_text = """✍️ CHỌN PHONG CÁCH VIẾT

Vui lòng chọn phong cách viết cho bài post Facebook:

📝 CÁC PHONG CÁCH CÓ SẴN:
1️⃣ Phong cách Chuyên gia - Phân tích chuyên sâu, dữ liệu cụ thể
2️⃣ Phong cách Thân thiện - Gần gũi, dễ hiểu, nhiều emoji
3️⃣ Phong cách Tin tức - Ngắn gọn, súc tích, thông tin chính
4️⃣ Phong cách Tranh luận - Đặt câu hỏi, khuyến khích thảo luận
5️⃣ Phong cách Giáo dục - Giải thích chi tiết, ví dụ minh họa
6️⃣ Phong cách Truyền cảm hứng - Tích cực, động viên, tầm nhìn

🎨 TÙY CHỈNH RIÊNG:
7️⃣ Tự nhập phong cách - Mô tả phong cách riêng của bạn

Gửi số thứ tự (1-7) hoặc 'Phong cách X' để chọn:"""

            # Create reply keyboard
            from telegram import KeyboardButton, ReplyKeyboardMarkup
            keyboard = [
                [KeyboardButton("Phong cách 1"), KeyboardButton("Phong cách 2")],
                [KeyboardButton("Phong cách 3"), KeyboardButton("Phong cách 4")],
                [KeyboardButton("Phong cách 5"), KeyboardButton("Phong cách 6")],
                [KeyboardButton("Tự nhập phong cách"), KeyboardButton("Quay lại")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            
            # First hide any existing keyboard
            from telegram import ReplyKeyboardRemove
            await context.bot.send_message(
                chat_id=chat_id,
                text="⌨️ Đang tải tùy chọn phong cách viết...",
                reply_markup=ReplyKeyboardRemove()
            )
            
            # Then send new keyboard
            await context.bot.send_message(
                chat_id=chat_id,
                text=style_text,
                reply_markup=reply_markup,
                parse_mode=None
            )
            
        except Exception as e:
            logger.error(f"Error presenting writing style options: {str(e)}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Lỗi hiển thị tùy chọn phong cách viết.",
                parse_mode=None
            )

    async def handle_writing_style_selection(self, user_id: int, message_text: str, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
        """Handle writing style selection"""
        try:
            if user_id not in self.user_sessions:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ Không tìm thấy workflow đang hoạt động. Vui lòng gửi 'Start' để bắt đầu."
                )
                return
            
            session = self.user_sessions[user_id]
            
            # Handle custom style input
            if message_text == "Tự nhập phong cách":
                session['step'] = 'custom_style_input'
                session['state'] = 'custom_style_input'
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="🎨 Vui lòng mô tả phong cách viết mà bạn muốn:\n\nVí dụ: 'Viết theo phong cách hài hước, nhiều meme, phù hợp với gen Z'"
                )
                return
            
            # Handle preset style selection
            style_mapping = {
                "Phong cách 1": "expert",
                "Phong cách 2": "friendly", 
                "Phong cách 3": "news",
                "Phong cách 4": "debate",
                "Phong cách 5": "educational",
                "Phong cách 6": "inspirational"
            }
            
            if message_text in style_mapping:
                selected_style = style_mapping[message_text]
                session['writing_style'] = self._get_style_config(selected_style)
                
                # Show selected style and continue
                style_name = self._get_style_name(selected_style)
                logger.info(f"User {user_id} selected style: {selected_style} ({style_name})")
                
                # Log writing style selection
                self.csv_logger.log_step4_writing_style(user_id, selected_style)
                
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"✅ Đã chọn: {style_name}\n\n▶️ Tiếp tục kiểm tra Facebook chuyên gia..."
                )
                
                # Continue to international blog search - ensure user_id is int
                try:
                    uid = int(user_id) if isinstance(user_id, str) else user_id
                    await self._step2_search_international_blogs(uid, context, chat_id, session['selected_article'])
                except Exception as blog_error:
                    logger.error(f"Error in _step2_search_international_blogs for user {user_id}: {blog_error}")
                    # Continue without blog context
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="⚠️ **Không thể tìm kiếm blog quốc tế**\n\n🤖 **Tiếp tục tạo nội dung AI...**"
                    )
                    session['expert_context'] = {'related_articles': []}
                    await self._step3_generate_post(uid, context, chat_id, session['selected_article'], {'related_articles': []})
                return
            
            # Handle numeric input (1-7)
            try:
                style_num = int(message_text)
                if 1 <= style_num <= 6:
                    style_types = ["expert", "friendly", "news", "debate", "educational", "inspirational"]
                    selected_style = style_types[style_num - 1]
                    session['writing_style'] = self._get_style_config(selected_style)
                    
                    style_name = self._get_style_name(selected_style)
                    logger.info(f"User {user_id} selected numeric style {style_num}: {selected_style} ({style_name})")
                    
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"✅ Đã chọn: {style_name}\n\n▶️ Tiếp tục tìm blog quốc tế liên quan..."
                    )
                    
                    # Continue to international blog search - ensure user_id is int
                    try:
                        uid = int(user_id) if isinstance(user_id, str) else user_id
                        await self._step2_search_international_blogs(uid, context, chat_id, session['selected_article'])
                    except Exception as blog_error:
                        logger.error(f"Error in _step2_search_international_blogs for user {user_id}: {blog_error}")
                        # Continue without blog context
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text="⚠️ **Không thể tìm kiếm blog quốc tế**\n\n🤖 **Tiếp tục tạo nội dung AI...**"
                        )
                        session['expert_context'] = {'related_articles': []}
                        await self._step3_generate_post(uid, context, chat_id, session['selected_article'], {'related_articles': []})
                    return
                elif style_num == 7:
                    session['step'] = 'custom_style_input'
                    session['state'] = 'custom_style_input'
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="🎨 Vui lòng mô tả phong cách viết mà bạn muốn:\n\nVí dụ: 'Viết theo phong cách hài hước, nhiều meme, phù hợp với gen Z'"
                    )
                    return
            except ValueError:
                pass
            
            # Check if this is a post approval message that got misrouted
            if message_text in ["✅ Phê duyệt bài viết", "✏️ Chỉnh sửa bài viết"]:
                # User might be trying to approve post but state is wrong, try to fix
                if 'generated_post' in session:
                    session['state'] = 'approving_post'
                    session['step'] = 'approving_post'
                    
                    if message_text == "✅ Phê duyệt bài viết":
                        await self.handle_post_approval_text(int(user_id), 'approve', context, chat_id)
                    elif message_text == "✏️ Chỉnh sửa bài viết":
                        await self.handle_post_approval_text(int(user_id), 'edit', context, chat_id)
                    return
            
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Lựa chọn không hợp lệ. Vui lòng chọn phong cách từ 1-7 hoặc sử dụng nút bấm.\n\n" +
                     "Hoặc gửi 'Start' để bắt đầu lại quy trình."
            )
            
        except Exception as e:
            logger.error(f"Error in handle_writing_style_selection: {str(e)}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Lỗi xử lý lựa chọn phong cách viết. Vui lòng thử lại.",
                parse_mode=None
            )

    async def handle_custom_style_input(self, user_id: int, message_text: str, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
        """Handle custom writing style input"""
        try:
            if user_id not in self.user_sessions:
                return
            
            session = self.user_sessions[user_id]
            
            # Store custom style
            session['writing_style'] = {
                'type': 'custom',
                'description': message_text,
                'tone': 'custom',
                'structure': 'custom',
                'elements': ['custom_style']
            }
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"✅ Đã lưu phong cách tùy chỉnh:\n\n'{message_text}'\n\n▶️ Tiếp tục tìm blog quốc tế liên quan..."
            )
            
            # Continue to international blog search
            await self._step2_search_international_blogs(int(user_id), context, chat_id, session['selected_article'])
            
        except Exception as e:
            logger.error(f"Error in handle_custom_style_input: {str(e)}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Lỗi lưu phong cách tùy chỉnh. Vui lòng thử lại."
            )

    def _get_style_config(self, style_type: str) -> Dict:
        """Get style configuration"""
        styles = {
            'expert': {
                'type': 'expert',
                'tone': 'professional',
                'structure': 'analysis',
                'elements': ['data', 'insights', 'recommendations', 'hashtags']
            },
            'friendly': {
                'type': 'friendly',
                'tone': 'casual',
                'structure': 'story',
                'elements': ['emojis', 'questions', 'personal_touch', 'hashtags']
            },
            'news': {
                'type': 'news',
                'tone': 'neutral',
                'structure': 'facts',
                'elements': ['key_facts', 'quotes', 'context', 'hashtags']
            },
            'debate': {
                'type': 'debate',
                'tone': 'provocative',
                'structure': 'argument',
                'elements': ['questions', 'contrasting_views', 'call_to_action', 'hashtags']
            },
            'educational': {
                'type': 'educational',
                'tone': 'informative',
                'structure': 'explanation',
                'elements': ['definitions', 'examples', 'step_by_step', 'hashtags']
            },
            'inspirational': {
                'type': 'inspirational',
                'tone': 'motivational',
                'structure': 'vision',
                'elements': ['positive_outlook', 'future_vision', 'encouragement', 'hashtags']
            }
        }
        return styles.get(style_type, styles['expert'])

    def _get_style_name(self, style_type: str) -> str:
        """Get style display name"""
        names = {
            'expert': 'Phong cách Chuyên gia',
            'friendly': 'Phong cách Thân thiện',
            'news': 'Phong cách Tin tức',
            'debate': 'Phong cách Tranh luận',
            'educational': 'Phong cách Giáo dục',
            'inspirational': 'Phong cách Truyền cảm hứng'
        }
        return names.get(style_type, 'Phong cách Chuyên gia')

    async def _step3_generate_post(self, user_id: int, context: ContextTypes.DEFAULT_TYPE,
                                 chat_id: int, selected_article, expert_context: Dict):
        """Step 3: Generate Vietnamese Facebook Post with ULTRA SUMMARY POWER"""
        
        # Send progress update
        progress_message = await context.bot.send_message(
            chat_id=chat_id,
            text="🚀 **Bước 3: Tạo nội dung AI với ULTRA RSS POWER**\n\n" +
                 "📊 Đang tạo Enhanced Summary từ 10+ nguồn quốc tế...\n" +
                 "🌍 Parallel RSS processing đang hoạt động...\n" +
                 "⏳ Vui lòng chờ...",
            parse_mode='Markdown'
        )
        
        try:
            # STEP 3.1: Generate Ultra Enhanced Summary với RSS Power
            logger.info(f"🚀 Generating Ultra Enhanced Summary for user {user_id}")
            await progress_message.edit_text(
                "🚀 **ULTRA RSS ENHANCED SUMMARY**\n\n" +
                "📊 Đang phân tích bài viết với AI...\n" +
                "🌐 Searching 10+ international sources...\n" +
                "⚡ Parallel processing activated...",
                parse_mode='Markdown'
            )
            
            enhanced_summary = await self.enhanced_summary_service.generate_enhanced_summary(selected_article)
            
            # Update with summary results
            articles_found = enhanced_summary.get('metadata', {}).get('articles_found', 0)
            await progress_message.edit_text(
                f"✅ **ULTRA SUMMARY COMPLETED**\n\n" +
                f"📊 Articles found: {articles_found}\n" +
                f"🌍 International analysis ready\n" +
                f"🇻🇳 Domestic expert analysis ready\n\n" +
                f"📝 Tạo Facebook post tiếng Việt...",
                parse_mode='Markdown'
            )
            
            # Store enhanced summary in session
            self.user_sessions[user_id]['enhanced_summary'] = enhanced_summary
            
            # STEP 3.2: Create Vietnamese content với enhanced context
            session = self.user_sessions[user_id]
            logger.info(f"Creating Vietnamese content with enhanced summary for user {user_id}")
            prompt = self._create_enhanced_vietnamese_content_prompt(selected_article, expert_context, enhanced_summary, session)
            
            # Generate content with AI using enhanced prompt
            logger.info(f"Calling AI service to generate enhanced content for user {user_id}")
            start_time = datetime.now()
            ai_provider = "unknown"
            
            try:
                generated_content = await self.ai_service.generate_custom_content(prompt)
                ai_provider = "enhanced_ai_service"
                logger.info(f"Successfully generated enhanced content for user {user_id}, length: {len(generated_content)}")
            except Exception as ai_error:
                logger.error(f"AI service error for user {user_id}: {ai_error}")
                # Fallback to basic AI service method
                logger.info(f"Using fallback AI service method for user {user_id}")
                generated_content = await self.ai_service.generate_content(prompt)
                ai_provider = "basic_ai_service"
            
            # Calculate duration and log
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            self.csv_logger.log_step5_content_generation(
                user_id=user_id,
                content_length=len(generated_content),
                ai_provider=ai_provider,
                duration_ms=duration_ms,
                status='success'
            )
            
            # Store in session
            self.user_sessions[user_id]['generated_post'] = generated_content
            self.user_sessions[user_id]['state'] = 'approving_post'
            
            logger.info(f"Presenting enhanced post approval for user {user_id}")
            # Present generated post for approval
            await self._present_enhanced_post_approval(user_id, context, chat_id, generated_content, enhanced_summary, progress_message)
            
        except Exception as e:
            logger.error(f"❌ Error generating enhanced post for user {user_id}: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            
            try:
                await progress_message.edit_text(
                    f"❌ Lỗi tạo enhanced content: {str(e)}\n\n" +
                    "⚠️ Fallback to basic mode...\n" +
                    "Vui lòng thử lại bằng cách gửi 'Start'",
                    parse_mode='Markdown'
                )
            except Exception as edit_error:
                logger.error(f"Error editing progress message: {edit_error}")
                # Send new message if edit fails
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ Lỗi tạo enhanced content: {str(e)}\n\nVui lòng thử lại bằng cách gửi 'Start'"
                )

    def _create_vietnamese_content_prompt(self, article, expert_context: Dict, session: Dict = None) -> str:
        """Create Vietnamese content generation prompt with expert context and style"""
        
        expert_posts = expert_context.get('related_posts', [])
        expert_context_text = ""
        
        if expert_posts:
            from config import Config
            config = Config()
            expert_context_text = f"\n\nNGỮ CẢNH TỪ CHUYÊN GIA {config.EXPERT_NAME}:\n"
            for i, post in enumerate(expert_posts[:2], 1):
                expert_context_text += f"Bài {i}: {post.get('caption', '')[:200]}...\n"
                expert_context_text += f"Link: {post.get('url', '')}\n"
                expert_context_text += f"Engagement: {post.get('engagement', {}).get('likes', 0)} likes, {post.get('engagement', {}).get('comments', 0)} comments\n\n"
        
        # Get writing style from session
        writing_style = session.get('writing_style', {}) if session else {}
        style_instruction = self._generate_style_instruction(writing_style)
        
        prompt = f"""
Bạn là một chuyên gia phân tích kinh tế và chính trị quốc tế. Hãy viết một bài Facebook post bằng tiếng Việt về tin tức sau:

TIÊU ĐỀ: {article.title}
NỘI DUNG: {article.content}
NGUỒN: {article.source}
{expert_context_text}

PHONG CÁCH VIẾT YÊU CẦU:
{style_instruction}

YÊU CẦU CHUNG:
- Độ dài: 250-400 từ
- Sử dụng tiếng Việt tự nhiên, phù hợp với người Việt
- Phân tích sâu sắc với góc nhìn Việt Nam
- Kết thúc bằng câu hỏi để thu hút tương tác hoặc hashtag liên quan
- Tránh sử dụng các ký tự markdown như **, *, _, [], () trong nội dung
- Tạo nội dung sẵn sàng đăng trực tiếp lên Facebook

ĐỊNH DẠNG OUTPUT:
- Chỉ trả về nội dung bài post hoàn chỉnh
- Không bao gồm tiêu đề hay phần giải thích thêm
- Đảm bảo không có lỗi định dạng

Hãy tạo nội dung hấp dẫn và có giá trị cho độc giả Việt Nam:
"""
        
        return prompt
    
    def _generate_style_instruction(self, writing_style: Dict) -> str:
        """Generate style-specific instructions for AI"""
        if not writing_style:
            return "Phong cách chuyên nghiệp nhưng dễ hiểu, phù hợp với Facebook"
        
        style_type = writing_style.get('type', 'expert')
        
        if style_type == 'expert':
            return """
- Phong cách chuyên gia: Sử dụng thuật ngữ chuyên môn nhưng giải thích rõ ràng
- Đưa ra phân tích chuyên sâu với dữ liệu cụ thể
- Cung cấp khuyến nghị và nhận định của chuyên gia
- Sử dụng biểu đồ emoji để minh họa dữ liệu (📊 📈 📉)
- Cấu trúc: Tình hình → Phân tích → Tác động → Khuyến nghị
"""
        elif style_type == 'friendly':
            return """
- Phong cách thân thiện: Viết như nói chuyện với bạn bè
- Sử dụng nhiều emoji để tạo cảm xúc (😊 🤗 💫 🌟)
- Đặt câu hỏi để khuyến khích tương tác
- Chia sẻ góc nhìn cá nhân, gần gũi
- Tránh thuật ngữ phức tạp, giải thích đơn giản
- Kết thúc với lời mời thảo luận
"""
        elif style_type == 'news':
            return """
- Phong cách tin tức: Ngắn gọn, súc tích, đi thẳng vào vấn đề
- Tập trung vào 5W1H: Ai, Cái gì, Khi nào, Ở đâu, Tại sao, Như thế nào
- Trình bày theo thứ tự quan trọng giảm dần
- Sử dụng số liệu và quote cụ thể
- Emoji chỉ dùng để nhấn mạnh điểm quan trọng (⚡ 🔥 📰)
"""
        elif style_type == 'debate':
            return """
- Phong cách tranh luận: Đặt ra câu hỏi thúc đẩy suy nghĩ
- Trình bày nhiều góc nhìn khác nhau về vấn đề
- Sử dụng câu hỏi tu từ để kích thích tư duy
- Khuyến khích người đọc chia sẻ quan điểm
- Kết thúc với call-to-action rõ ràng
- Emoji tạo động lực thảo luận (🤔 💭 🗣️ 👥)
"""
        elif style_type == 'educational':
            return """
- Phong cách giáo dục: Giải thích chi tiết, dễ hiểu như giảng bài
- Chia nhỏ thông tin phức tạp thành các ý đơn giản
- Sử dụng ví dụ minh họa cụ thể, gần gũi
- Cấu trúc rõ ràng: Định nghĩa → Giải thích → Ví dụ → Ứng dụng
- Emoji hỗ trợ học tập (📚 💡 🎯 ✅)
- Tạo takeaway rõ ràng cho người đọc
"""
        elif style_type == 'inspirational':
            return """
- Phong cách truyền cảm hứng: Tích cực, động viên, nhìn về tương lai
- Tập trung vào cơ hội và khả năng phát triển
- Sử dụng ngôn ngữ tích cực, đầy hy vọng
- Khuyến khích hành động và thay đổi tích cực
- Emoji tạo cảm hứng (🚀 🌟 💪 🎯 ⭐)
- Kết thúc với thông điệp motivational
"""
        elif style_type == 'custom':
            return f"""
- Phong cách tùy chỉnh: {writing_style.get('description', 'Phong cách đặc biệt')}
- Thực hiện theo yêu cầu cụ thể của người dùng
- Giữ tính chuyên nghiệp trong nội dung kinh tế
- Đảm bảo phù hợp với nền tảng Facebook
"""
        
        return "Phong cách chuyên nghiệp nhưng dễ hiểu, phù hợp với Facebook"

    def _create_enhanced_vietnamese_content_prompt(self, article, expert_context: Dict, enhanced_summary: Dict, session: Dict = None) -> str:
        """Create enhanced Vietnamese content generation prompt with Ultra Summary context"""
        
        # Extract enhanced summary components
        bullet_summary = enhanced_summary.get('bullet_summary', '')
        expert_analysis = enhanced_summary.get('expert_analysis', '')
        international_analysis = enhanced_summary.get('international_analysis', '')
        domestic_analysis = enhanced_summary.get('domestic_analysis', '')
        articles_found = enhanced_summary.get('metadata', {}).get('articles_found', 0)
        
        # Get writing style from session
        writing_style = session.get('writing_style', {}) if session else {}
        style_instruction = self._generate_style_instruction(writing_style)
        
        prompt = f"""
Bạn là một chuyên gia phân tích kinh tế và chính trị quốc tế với access vào ULTRA RSS ENHANCED SUMMARY SYSTEM. 

BÀI VIẾT GỐC:
Tiêu đề: {article.title}
Nội dung: {article.content}
Nguồn: {article.source}

ULTRA ENHANCED SUMMARY ĐÃ TẠO (từ {articles_found} nguồn quốc tế):
📝 TÓM TẮT:
{bullet_summary}

🇻🇳 PHÂN TÍCH CHUYÊN GIA TRONG NƯỚC:
{domestic_analysis}

🌍 PHÂN TÍCH QUỐC TẾ:
{international_analysis}

PHONG CÁCH VIẾT YÊU CẦU:
{style_instruction}

YÊU CẦU:
- Sử dụng thông tin từ Ultra Enhanced Summary để tạo bài Facebook post chất lượng cao
- Kết hợp góc nhìn trong nước và quốc tế từ enhanced analysis
- Độ dài: 250-400 từ (tối ưu cho Facebook, súc tích nhưng đầy đủ thông tin)
- Sử dụng tiếng Việt tự nhiên, chuyên nghiệp
- Thể hiện depth analysis từ multiple international sources
- Kết thúc bằng câu hỏi hoặc call-to-action
- Tránh markdown syntax trong output

ĐỊNH DẠNG OUTPUT:
- Chỉ trả về nội dung Facebook post hoàn chỉnh
- Đảm bảo nội dung ready-to-publish
- Không bao gồm tiêu đề hay phần giải thích

Hãy tạo bài post thể hiện sức mạnh của Ultra RSS Enhanced Analysis:
"""
        return prompt

    async def _present_enhanced_post_approval(self, user_id: int, context: ContextTypes.DEFAULT_TYPE,
                                   chat_id: int, generated_content: str, enhanced_summary: Dict, progress_message):
        """Present enhanced post với Ultra Summary info - với user approval options"""
        
        logger.info(f"Presenting enhanced post approval for user {user_id}")
        
        try:
            # Get summary stats
            articles_found = enhanced_summary.get('metadata', {}).get('articles_found', 0)
            sources = enhanced_summary.get('metadata', {}).get('sources', [])
            sources_text = ", ".join(sources[:3]) + ("..." if len(sources) > 3 else "")
            
            # Update message with generated content và summary info
            message_text = f"🚀 **ULTRA ENHANCED CONTENT GENERATED**\n\n" + \
                          f"📊 **Powered by:** {articles_found} articles from {len(sources)} sources\n" + \
                          f"🌐 **Sources:** {sources_text}\n\n" + \
                          f"📝 **CONTENT:**\n\n{generated_content}\n\n" + \
                          "⚡ **Vui lòng chọn hành động:**"
            
            logger.info(f"Editing progress message for enhanced post user {user_id}")
            await progress_message.edit_text(
                message_text,
                parse_mode='Markdown'
            )
            
            # Store generated content in session
            session = self.user_sessions[user_id]
            session['generated_post'] = generated_content
            session['enhanced_summary'] = enhanced_summary
            session['state'] = 'approving_content'
            session['step'] = 'content_approval'
            
            # Create keyboard with 2 options
            from telegram import ReplyKeyboardMarkup, KeyboardButton
            
            keyboard = [
                [KeyboardButton("✅ Chấp nhận nội dung")],
                [KeyboardButton("🔄 Tạo bài viết mới")]
            ]
            reply_markup = ReplyKeyboardMarkup(
                keyboard, 
                resize_keyboard=True, 
                one_time_keyboard=True
            )
            
            # Send approval options message with keyboard
            await context.bot.send_message(
                chat_id=chat_id,
                text="🤔 **Bạn có hài lòng với nội dung trên không?**\n\n" +
                     "✅ **Chấp nhận nội dung:** Tiếp tục tạo hình ảnh và đăng Facebook\n" +
                     "🔄 **Tạo bài viết mới:** Tạo lại nội dung với phong cách khác",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error presenting enhanced post approval for user {user_id}: {e}")
            # Fallback: show simple text options
            session = self.user_sessions[user_id] 
            session['generated_post'] = generated_content
            session['state'] = 'approving_content'
            session['step'] = 'content_approval'
            
            await context.bot.send_message(
                chat_id=chat_id,
                text="⚡ **Nội dung đã tạo xong!**\n\n" +
                     "Vui lòng gửi:\n" +
                     "✅ 'Chấp nhận' để tiếp tục\n" +
                     "🔄 'Tạo mới' để tạo lại nội dung",
                parse_mode='Markdown'
            )

    async def _step4_generate_image(self, user_id: int, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
        """Step 4: Generate Image with PioneerX Logo"""
        
        # Send progress update
        progress_message = await context.bot.send_message(
            chat_id=chat_id,
            text="🎨 **Bước 4: Tạo hình ảnh AI**\n\n" +
                 "🖼️ Đang tạo ảnh 16:9 với logo PioneerX...\n" +
                 "⏳ Vui lòng chờ (30-60 giây)...",
            parse_mode='Markdown'
        )
        
        try:
            session = self.user_sessions[user_id]
            selected_article = session['selected_article']
            generated_content = session.get('generated_post', '')
            
            # Generate image using generated content context instead of original article
            if generated_content:
                # Use generated content as context for more relevant image
                image_context = {
                    'generated_content': generated_content,
                    'prompt_source': 'generated_content',
                    'style': 'facebook_post'
                }
                image_path = await self.image_service.generate_image(
                    title=selected_article.title,
                    content=generated_content,  # Use generated content instead of original
                    context=image_context
                )
            else:
                # Fallback to original article if no generated content
                image_path = await self.image_service.generate_image(
                    title=selected_article.title,
                    content=selected_article.content
                )
            
            if image_path and os.path.exists(image_path):
                # Log successful image generation
                self.csv_logger.log_step7_image_generation(
                    user_id=user_id,
                    image_path=image_path,
                    image_provider="advanced_image_service",
                    duration_ms=0,  # Duration tracked by image service internally
                    status='success'
                )
                
                session['generated_image'] = image_path
                session['state'] = 'approving_image'
                
                # Present image for approval
                await self._present_image_approval(user_id, context, chat_id, image_path, progress_message)
                
            else:
                await progress_message.edit_text(
                    "❌ Lỗi tạo hình ảnh\n\n" +
                    "Tiếp tục đăng bài không có hình ảnh...",
                    parse_mode=None
                )
                
                # Continue without image
                session['generated_image'] = None
                await self._step5_publish_to_facebook(user_id, context, chat_id)
                
        except Exception as e:
            logger.error(f"❌ Error generating image: {e}")
            
            await progress_message.edit_text(
                f"❌ Lỗi tạo hình ảnh:\n{str(e)}\n\n" +
                "Tiếp tục đăng bài không có hình ảnh...",
                parse_mode=None
            )
            
            # Continue without image
            session = self.user_sessions[user_id]
            session['generated_image'] = None
            await self._step5_publish_to_facebook(user_id, context, chat_id)

    def _create_image_prompt(self, article) -> str:
        """Create enhanced image generation prompt based on article content"""
        
        # Extract key themes from article
        title_lower = article.title.lower()
        content_lower = article.content.lower()
        combined_text = f"{title_lower} {content_lower}"
        
        # Analyze content for specific visual elements
        visual_elements = []
        color_schemes = []
        composition_elements = []
        
        # Determine primary theme and visual elements
        if any(word in combined_text for word in ['trump', 'election', 'politics', 'president', 'government']):
            visual_elements.extend([
                "political landscape", "American flag elements", "government buildings", 
                "presidential imagery", "political symbols"
            ])
            color_schemes.extend(["red white and blue", "patriotic colors", "official government colors"])
            
        if any(word in combined_text for word in ['economy', 'economic', 'market', 'business', 'trade', 'financial']):
            visual_elements.extend([
                "financial charts and graphs", "stock market imagery", "business icons",
                "economic indicators", "trading floor atmosphere", "corporate buildings"
            ])
            color_schemes.extend(["professional blue and gold", "financial green and red", "corporate colors"])
            
        if any(word in combined_text for word in ['tariff', 'tax', 'trade war', 'import', 'export']):
            visual_elements.extend([
                "international trade symbols", "shipping containers", "global trade routes",
                "cargo ships", "world map connections", "customs and border imagery"
            ])
            color_schemes.extend(["international blue", "trade route gold", "global connectivity colors"])
            
        if any(word in combined_text for word in ['china', 'chinese', 'asian', 'asia-pacific']):
            visual_elements.extend([
                "East Asian architectural elements", "modern Asian cityscape", 
                "China-US relations symbols", "Pacific region imagery"
            ])
            color_schemes.extend(["East Asian red and gold", "modern metropolitan colors"])
            
        if any(word in combined_text for word in ['vietnam', 'vietnamese', 'southeast asia', 'asean']):
            visual_elements.extend([
                "Southeast Asian elements", "Vietnamese flag colors", "ASEAN symbols",
                "tropical business environment", "emerging market imagery"
            ])
            color_schemes.extend(["Vietnamese red and yellow", "tropical business colors"])
            
        if any(word in combined_text for word in ['technology', 'ai', 'digital', 'tech', 'innovation']):
            visual_elements.extend([
                "high-tech graphics", "digital network patterns", "AI and technology symbols",
                "modern tech interfaces", "innovation imagery"
            ])
            color_schemes.extend(["tech blue and silver", "digital neon colors", "innovation purple"])
            
        # Geographic context
        geographic_elements = []
        if any(word in combined_text for word in ['global', 'international', 'worldwide', 'world']):
            geographic_elements.append("world map overlay")
            
        if any(word in combined_text for word in ['us', 'america', 'american', 'united states']):
            geographic_elements.append("American geographic elements")
            
        if any(word in combined_text for word in ['asia', 'asian', 'pacific']):
            geographic_elements.append("Asia-Pacific regional elements")
        
        # Determine urgency and tone
        urgency_indicators = []
        if any(word in combined_text for word in ['breaking', 'urgent', 'crisis', 'emergency']):
            urgency_indicators.append("urgent news alert style")
            color_schemes.append("alert red and orange")
            
        if any(word in combined_text for word in ['growth', 'positive', 'increase', 'boom']):
            urgency_indicators.append("positive growth indicators")
            color_schemes.append("growth green")
            
        if any(word in combined_text for word in ['decline', 'fall', 'crisis', 'negative']):
            urgency_indicators.append("caution and warning elements")
            color_schemes.append("warning amber and red")
        
        # Build comprehensive prompt
        base_elements = ["professional news media illustration", "high quality", "eye-catching composition"]
        
        # Select most relevant elements (avoid overcrowding)
        selected_visuals = visual_elements[:3] if visual_elements else ["modern business graphics"]
        selected_colors = color_schemes[:2] if color_schemes else ["professional blue and white"]
        selected_geography = geographic_elements[:1] if geographic_elements else []
        selected_urgency = urgency_indicators[:1] if urgency_indicators else []
        
        # Combine all elements
        all_elements = (base_elements + selected_visuals + selected_colors + 
                       selected_geography + selected_urgency)
        
        # Create final prompt
        prompt = f"{', '.join(all_elements)}, 16:9 aspect ratio, news media style, engaging visual design, suitable for Facebook post, professional presentation"
        
        # Add specific context if article has clear focus
        if 'trump' in title_lower and 'tariff' in combined_text:
            prompt += ", Trump policy announcement style, tariff impact visualization"
        elif 'market' in title_lower and any(word in combined_text for word in ['up', 'down', 'surge', 'drop']):
            prompt += ", stock market movement visualization, trading floor energy"
        elif 'vietnam' in combined_text and 'trade' in combined_text:
            prompt += ", Vietnam trade relationship focus, ASEAN economic cooperation"
        
        # Ensure clean, professional output
        prompt += ", clean layout, readable design, social media optimized"
        
        return prompt

    def _create_image_prompt_from_generated_content(self, generated_content: str, original_article) -> str:
        """Create image prompt based on generated Facebook content instead of original article"""
        
        # Extract key themes from generated content
        content_lower = generated_content.lower()
        title_lower = original_article.title.lower()
        
        # Analyze generated content for visual elements
        visual_elements = []
        color_schemes = []
        composition_elements = []
        
        # Look for specific topics mentioned in the generated content
        if any(word in content_lower for word in ['trump', 'tổng thống', 'chính trị', 'bầu cử', 'chính phủ']):
            visual_elements.extend([
                "presidential imagery", "political symbols", "American flag elements",
                "government buildings", "official announcement style"
            ])
            color_schemes.extend(["patriotic red white blue", "official government colors"])
            
        if any(word in content_lower for word in ['kinh tế', 'thị trường', 'doanh nghiệp', 'tài chính', 'thuế quan']):
            visual_elements.extend([
                "financial charts and graphs", "business growth indicators", 
                "economic symbols", "market trend visualization", "corporate imagery"
            ])
            color_schemes.extend(["professional blue and gold", "financial green", "business colors"])
            
        if any(word in content_lower for word in ['trung quốc', 'china', 'châu á', 'thương mại quốc tế']):
            visual_elements.extend([
                "international trade symbols", "Asia-Pacific imagery", 
                "global connection graphics", "trade route visualization"
            ])
            color_schemes.extend(["international blue", "Asia-Pacific colors", "global trade gold"])
            
        if any(word in content_lower for word in ['việt nam', 'vietnamese', 'asean', 'đông nam á']):
            visual_elements.extend([
                "Southeast Asian business elements", "Vietnam flag colors",
                "ASEAN cooperation symbols", "emerging market imagery"
            ])
            color_schemes.extend(["Vietnamese red and yellow", "ASEAN blue", "emerging market colors"])
            
        if any(word in content_lower for word in ['công nghệ', 'ai', 'digital', 'innovation', 'tech']):
            visual_elements.extend([
                "high-tech graphics", "AI and technology symbols", 
                "digital innovation imagery", "modern tech interfaces"
            ])
            color_schemes.extend(["tech blue and silver", "innovation purple", "digital colors"])
        
        # Extract emotional tone from generated content
        emotional_elements = []
        if any(word in content_lower for word in ['tích cực', 'tăng trưởng', 'phát triển', 'cơ hội']):
            emotional_elements.append("positive growth energy")
            color_schemes.append("optimistic green and blue")
            
        if any(word in content_lower for word in ['thách thức', 'khó khăn', 'rủi ro', 'cảnh báo']):
            emotional_elements.append("caution and awareness tone")
            color_schemes.append("warning amber and orange")
            
        if any(word in content_lower for word in ['khủng hoảng', 'suy thoái', 'giảm', 'lo ngại']):
            emotional_elements.append("serious concern atmosphere")
            color_schemes.append("alert red and dark blue")
        
        # Build comprehensive prompt based on generated content
        base_elements = [
            "professional Facebook post illustration", "eye-catching social media design",
            "Vietnamese audience appeal", "news media style", "engaging visual"
        ]
        
        # Select most relevant elements
        selected_visuals = visual_elements[:3] if visual_elements else ["modern business graphics"]
        selected_colors = color_schemes[:2] if color_schemes else ["professional blue and white"]
        selected_emotional = emotional_elements[:1] if emotional_elements else ["neutral professional tone"]
        
        # Combine all elements
        all_elements = base_elements + selected_visuals + selected_colors + selected_emotional
        
        # Create final prompt optimized for Facebook post
        prompt = f"{', '.join(all_elements)}, 16:9 aspect ratio, Facebook post optimized, social media friendly, Vietnamese context, engaging for Vietnamese audience"
        
        # Add specific context based on generated content focus
        if 'trump' in content_lower and 'thuế quan' in content_lower:
            prompt += ", Trump tariff policy impact visualization, international trade focus"
        elif 'việt nam' in content_lower and 'xuất khẩu' in content_lower:
            prompt += ", Vietnam export economy focus, Southeast Asian business context"
        elif 'thị trường' in content_lower and any(word in content_lower for word in ['tăng', 'giảm']):
            prompt += ", market movement visualization, economic trend display"
        
        # Ensure social media optimization
        prompt += ", clean readable layout, social media optimized, attention-grabbing design"
        
        return prompt

    async def _present_image_approval(self, user_id: int, context: ContextTypes.DEFAULT_TYPE,
                                    chat_id: int, image_path: str, progress_message):
        """Present generated image for user approval"""
        
        # Send image
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=open(image_path, 'rb'),
            caption="🎨 Hình ảnh AI đã tạo với logo PioneerX\n\n👇 Chọn hành động bằng nút bấm bên dưới:",
            parse_mode=None
        )
        
        # Create approval keyboard
        keyboard = [
            [KeyboardButton("✅ Phê duyệt hình ảnh")],
            [KeyboardButton("🔄 Tạo lại hình ảnh")],
            [KeyboardButton("🔄 Bắt đầu lại")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        # Send approval keyboard
        await context.bot.send_message(
            chat_id=chat_id,
            text="👆 **Chọn hành động:**",
            reply_markup=reply_markup
        )
        
        # Delete progress message
        try:
            await progress_message.delete()
        except:
            pass

    async def _step5_publish_to_facebook(self, user_id: int, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
        """Step 5: Publish to Facebook and Log Results"""
        
        session = self.user_sessions[user_id]
        
        # Send progress update
        progress_message = await context.bot.send_message(
            chat_id=chat_id,
            text="📱 **Bước 5: Đăng lên Facebook**\n\n" +
                 "🚀 Đang đăng bài lên Facebook page...\n" +
                 "⏳ Vui lòng chờ...",
            parse_mode='Markdown'
        )
        
        try:
            # Prepare content and image
            content = session['generated_post']
            image_path = session.get('generated_image')
            
            # Try Facebook API first
            result = await self.facebook_service.publish_post(content, image_path)
            
            if result.get('success'):
                post_id = result.get('post_id')
                post_url = result.get('post_url')
                
                session['facebook_post_id'] = post_id
                session['state'] = 'completed'
                
                # Log workflow completion
                total_duration_ms = int((datetime.now() - session['start_time']).total_seconds() * 1000)
                self.csv_logger.log_workflow_complete(
                    user_id=user_id,
                    total_duration_ms=total_duration_ms,
                    final_status='success'
                )
                
                # Send success message
                await progress_message.edit_text(
                    f"🎉 **Hoàn thành thành công!**\n\n" +
                    f"✅ Đã đăng bài lên Facebook\n" +
                    f"🔗 [Xem bài đăng]({post_url})\n" +
                    f"📊 Post ID: {post_id}\n\n" +
                    f"📝 **Tóm tắt quy trình:**\n" +
                    f"• Tìm thấy {len(session['articles'])} tin tức\n" +
                    f"• Đã chọn: {session['selected_article'].title[:50]}...\n" +
                    f"• Tạo nội dung: {len(content)} ký tự\n" +
                    f"• Tạo hình ảnh: {'Có' if image_path else 'Không'}\n" +
                    f"• Thời gian: {(datetime.now() - session['start_time']).seconds} giây",
                    parse_mode='Markdown',
                    disable_web_page_preview=True
                )
                
            else:
                # Fallback to manual posting guide
                await self._handle_publishing_failure(user_id, context, chat_id, content, image_path, progress_message)
                
        except Exception as e:
            logger.error(f"❌ Error publishing to Facebook: {e}")
            
            await progress_message.edit_text(
                f"❌ **Lỗi đăng Facebook:**\n{str(e)}\n\n" +
                f"📝 **Nội dung đã tạo:**\n{content}\n\n" +
                f"Bạn có thể copy nội dung và đăng thủ công.",
                parse_mode='Markdown'
            )

    async def _handle_publishing_failure(self, user_id: int, context: ContextTypes.DEFAULT_TYPE,
                                       chat_id: int, content: str, image_path: str, progress_message):
        """Handle case when Facebook publishing fails"""
        
        session = self.user_sessions[user_id]
        session['state'] = 'failed'
        
        # Create manual posting guide
        keyboard = [
            [InlineKeyboardButton("📋 Copy nội dung", callback_data=f"copy_content_{user_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await progress_message.edit_text(
            f"⚠️ **Không thể đăng tự động**\n\n" +
            f"📝 **Nội dung đã tạo:**\n{content}\n\n" +
            f"🖼️ **Hình ảnh:** {'Có' if image_path else 'Không có'}\n\n" +
            f"🔧 **Hướng dẫn đăng thủ công:**\n" +
            f"1. Copy nội dung ở trên\n" +
            f"2. Vào Facebook page của bạn\n" +
            f"3. Tạo bài đăng mới và paste nội dung\n" +
            f"4. Upload hình ảnh (nếu có)\n" +
            f"5. Đăng bài",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        # Send image separately if available
        if image_path and os.path.exists(image_path):
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=open(image_path, 'rb'),
                caption="🖼️ **Hình ảnh để đăng thủ công**"
            )

    async def get_workflow_status(self, user_id: int) -> Dict:
        """Get current workflow status for user"""
        if user_id not in self.user_sessions:
            return {'status': 'no_session', 'message': 'Không có phiên làm việc nào'}
        
        session = self.user_sessions[user_id]
        state = session.get('state', 'unknown')
        
        status_messages = {
            'fetching_news': 'Đang thu thập tin tức...',
            'selecting_article': 'Chờ chọn bài viết',
            'checking_expert_facebook': 'Đang kiểm tra Facebook chuyên gia...',
            'generating_post': 'Đang tạo nội dung AI...',
            'approving_post': 'Chờ phê duyệt nội dung',
            'editing_post': 'Đang chỉnh sửa nội dung',
            'generating_image': 'Đang tạo hình ảnh...',
            'approving_image': 'Chờ phê duyệt hình ảnh',
            'publishing': 'Đang đăng lên Facebook...',
            'completed': 'Hoàn thành',
            'failed': 'Thất bại'
        }
        
        return {
            'status': state,
            'message': status_messages.get(state, 'Trạng thái không xác định'),
            'start_time': session.get('start_time'),
            'selected_article': session.get('selected_article', {}).get('title') if session.get('selected_article') else None
        }

    async def handle_post_approval_text(self, user_id: int, action: str, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
        """Handle post approval from text messages"""
        
        if user_id not in self.user_sessions:
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Phiên làm việc đã hết hạn",
                reply_markup=ReplyKeyboardRemove()
            )
            return
        
        session = self.user_sessions[user_id]
        
        if action == 'approve':
            session['state'] = 'generating_image'
            session['step'] = 'generating_image'
            
            # Send confirmation message
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"✅ **Nội dung đã được phê duyệt**\n\n" +
                     f"{session['generated_post']}\n\n" +
                     "🎨 **Bước 4: Tạo hình ảnh với logo PioneerX...**",
                parse_mode='Markdown',
                reply_markup=ReplyKeyboardRemove()
            )
            
            # Continue to image generation
            await self._step4_generate_image(user_id, context, chat_id)
            
        elif action == 'edit':
            session['state'] = 'editing_post'
            session['step'] = 'editing_post'
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"✏️ **Chế độ chỉnh sửa**\n\n" +
                     f"Nội dung hiện tại:\n{session['generated_post']}\n\n" +
                     "💬 **Hãy gửi tin nhắn để chỉnh sửa:**\n" +
                     "Ví dụ: 'Làm ngắn gọn hơn' hoặc 'Thêm thông tin về tác động kinh tế'",
                parse_mode='Markdown',
                reply_markup=ReplyKeyboardRemove()
            )

    async def handle_image_approval_text(self, user_id: int, action: str, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
        """Handle image approval from text messages"""
        
        if user_id not in self.user_sessions:
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Phiên làm việc đã hết hạn",
                reply_markup=ReplyKeyboardRemove()
            )
            return
        
        session = self.user_sessions[user_id]
        
        if action == 'approve':
            session['state'] = 'publishing'
            session['step'] = 'publishing'
            
            # Send confirmation message
            await context.bot.send_message(
                chat_id=chat_id,
                text="✅ **Hình ảnh đã được phê duyệt**\n\n" +
                     "📱 **Bước 5: Đăng lên Facebook...**",
                parse_mode='Markdown',
                reply_markup=ReplyKeyboardRemove()
            )
            
            # Continue to publishing
            await self._step5_publish_to_facebook(user_id, context, chat_id)
            
        elif action == 'regenerate':
            await context.bot.send_message(
                chat_id=chat_id,
                text="🔄 **Đang tạo lại hình ảnh...**\n⏳ Vui lòng chờ...",
                parse_mode='Markdown',
                reply_markup=ReplyKeyboardRemove()
            )
            
            # Regenerate image
            await self._step4_generate_image(user_id, context, chat_id)

    def _generate_expert_mock_posts(self, selected_article, keywords, config) -> List[Dict]:
        """Generate realistic mock expert Facebook posts"""
        posts = []
        
        # Check if article matches expert's interests
        relevant_topics = {
            'trump': ['Thời đại Trump 2.0: Những thay đổi căn bản trong chính sách kinh tế Mỹ', 
                     'Phân tích chính sách thuế quan mới của Trump với châu Á'],
            'trade': ['Cuộc chiến thương mại mới: Tác động đến Việt Nam', 
                     'Làn sóng bảo hộ thương mại: Cơ hội hay thách thức?'],
            'economy': ['Kinh tế toàn cầu 2025: Những điểm nóng cần theo dõi',
                       'Phân tích xu hướng lạm phát và chính sách tiền tệ'],
            'tax': ['Cải cách thuế doanh nghiệp: Bài học từ các nước phát triển',
                   'Chính sách thuế và thu hút FDI: Kinh nghiệm quốc tế'],
            'china': ['Quan hệ Mỹ-Trung: Tác động đến chuỗi cung ứng toàn cầu',
                     'Chiến lược kinh tế của Trung Quốc trong thời đại mới'],
            'business': ['Xu hướng kinh doanh sau đại dịch: Những thay đổi cốt lõi',
                        'Chuyển đổi số trong doanh nghiệp: Từ lý thuyết đến thực tiễn'],
            'market': ['Thị trường chứng khoán 2025: Cơ hội đầu tư nào đáng chú ý?',
                      'Phân tích chu kỳ thị trường: Dấu hiệu nhận biết đỉnh và đáy']
        }
        
        # Find relevant posts based on keywords
        found_topics = []
        for keyword in keywords:
            keyword_lower = keyword.lower()
            for topic, posts_list in relevant_topics.items():
                if topic in keyword_lower or keyword_lower in topic:
                    found_topics.extend(posts_list)
        
        # If no specific match, use general business/economy posts
        if not found_topics:
            found_topics = relevant_topics['economy'] + relevant_topics['business']
        
        # Generate 1-3 relevant posts
        num_posts = min(random.randint(1, 3), len(found_topics))
        selected_topics = random.sample(found_topics, num_posts)
        
        for i, topic in enumerate(selected_topics):
            # Generate realistic post data
            post_id = f"pfbid{random.randint(100000, 999999)}ABC{random.randint(100, 999)}"
            days_ago = random.randint(1, 10)
            post_date = datetime.now() - timedelta(days=days_ago)
            
            # Create detailed post content
            post_content = self._generate_expert_post_content(topic, selected_article)
            
            # Generate realistic engagement
            likes = random.randint(50, 500)
            comments_count = random.randint(5, 50)
            shares = random.randint(2, 25)
            
            post = {
                'url': f"{config.EXPERT_FACEBOOK_URL}/posts/{post_id}",
                'post_id': post_id,
                'date': post_date.strftime("%Y-%m-%d"),
                'title': topic,
                'caption': post_content,
                'engagement': {
                    'likes': likes,
                    'comments': comments_count,
                    'shares': shares
                },
                'hashtags': self._generate_relevant_hashtags(selected_article),
                'images': [] if random.random() > 0.3 else [f"image_{random.randint(1, 5)}.jpg"],
                'comments': self._generate_sample_comments(comments_count)
            }
            
            posts.append(post)
        
        return posts
    
    def _generate_expert_post_content(self, topic: str, article) -> str:
        """Generate realistic expert post content"""
        templates = [
            f"""💼 {topic}
            
Sau khi đọc tin tức mới nhất về "{article.title[:50]}...", tôi có một số nhận xét:

🔍 Phân tích:
- Xu hướng này không phải ngẫu nhiên, nó phản ánh những thay đổi cơ bản trong cách tiếp cận chính sách
- Tác động đến Việt Nam có thể là tích cực nếu chúng ta chuẩn bị tốt chiến lược ứng phó
- Các doanh nghiệp cần linh hoạt điều chỉnh kế hoạch kinh doanh

💡 Khuyến nghị:
- Theo dõi sát diễn biến để kịp thời điều chỉnh
- Tận dụng cơ hội từ những thay đổi này
- Chuẩn bị phương án dự phòng

Các bạn nghĩ sao về vấn đề này? 👇""",

            f"""🌐 {topic}

Tin tức về "{article.title[:40]}..." khiến tôi suy ngẫm về những thay đổi lớn đang diễn ra.

📊 Một số con số đáng chú ý:
- Tăng trưởng dự kiến: 15-20%
- Tác động đến GDP: 0.5-1.2%
- Thời gian ảnh hưởng: 6-12 tháng

🎯 Điều này có nghĩa gì?
→ Cơ hội mới cho các doanh nghiệp nhỏ và vừa
→ Thách thức lớn với các ngành truyền thống  
→ Cần sự chủ động trong chuyển đổi số

Ai đã có kinh nghiệm xử lý tình huống tương tự? Share để cùng học hỏi! 🤝""",

            f"""🔥 {topic}

Vừa đọc xong bài "{article.title[:45]}..." và thật sự ấn tượng với những phân tích mới.

⚡ Những điểm nổi bật:
1. Xu hướng này sẽ định hình lại ngành trong 2-3 năm tới
2. Các công ty tiên phong sẽ có lợi thế cạnh tranh lớn
3. Rủi ro chính là sự chậm trễ trong việc thích ứng

🚀 Cơ hội cho Việt Nam:
- Vị trí địa lý thuận lợi
- Chi phí nhân công cạnh tranh  
- Chính sách khuyến khích từ chính phủ

Theo các bạn, doanh nghiệp Việt Nam cần làm gì để tận dụng cơ hội này? 💭"""
        ]
        
        return random.choice(templates)
    
    def _generate_relevant_hashtags(self, article) -> List[str]:
        """Generate relevant hashtags based on article content"""
        base_hashtags = ['#KinhTe', '#PhanTich', '#ChuyenGia', '#Business']
        
        # Add topic-specific hashtags
        title_lower = article.title.lower()
        if 'trump' in title_lower:
            base_hashtags.extend(['#Trump', '#ChinhSach', '#MyQuoc'])
        if 'trade' in title_lower or 'thương mại' in title_lower:
            base_hashtags.extend(['#ThuongMai', '#XuatNhapKhau', '#QuocTe'])
        if 'economy' in title_lower or 'kinh tế' in title_lower:
            base_hashtags.extend(['#KinhTeVietNam', '#TangTruong', '#DauTu'])
        if 'market' in title_lower:
            base_hashtags.extend(['#ThiTruong', '#ChungKhoan', '#TaiChinh'])
        
        return base_hashtags[:6]  # Limit to 6 hashtags
    
    def _generate_sample_comments(self, count: int) -> List[str]:
        """Generate realistic sample comments"""
        comment_templates = [
            "Phân tích rất hay anh ơi! 👍",
            "Cảm ơn anh đã chia sẻ những góc nhìn sâu sắc",
            "Theo em nghĩ thì xu hướng này sẽ còn tiếp tục",
            "Rất bổ ích! Cho em hỏi về...",
            "Đồng ý với quan điểm của anh",
            "Thanks for sharing! Very insightful analysis",
            "Chờ bài phân tích tiếp theo của anh 🔥",
            "Hay quá! Share cho bạn bè đọc thêm",
            "Anh có thể viết chi tiết hơn về phần này không?",
            "Perspective rất thú vị, chưa từng nghĩ đến"
        ]
        
        return random.sample(comment_templates, min(count, len(comment_templates)))
