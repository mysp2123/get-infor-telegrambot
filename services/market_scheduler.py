import os
import logging
import asyncio
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Callable, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
import pytz
from dataclasses import dataclass

from services.market_data_service import MarketDataService
from services.enhanced_ai_service import EnhancedAIService

logger = logging.getLogger(__name__)

@dataclass
class ScheduleConfig:
    name: str
    schedule_time: str  # HH:MM format
    enabled: bool = True
    description: str = ""
    chat_id: Optional[int] = None

@dataclass
class MarketReport:
    title: str
    content: str
    image_path: Optional[str] = None
    report_type: str = "daily"
    generated_at: datetime = None

class MarketScheduler:
    """
    ⏰ MARKET SCHEDULER SERVICE
    
    Features:
    - 📅 Automated daily market reports
    - ⏰ Customizable schedule (open/close times)
    - 🇻🇳 Vietnam market focus (GMT+7)
    - 🌍 Global market coverage
    - 📊 AI-generated market analysis
    - 📱 Telegram integration
    - 🔔 Smart notifications
    """
    
    def __init__(self, telegram_bot=None, ai_service: EnhancedAIService = None):
        self.scheduler = AsyncIOScheduler(timezone=pytz.timezone('Asia/Ho_Chi_Minh'))
        self.market_service = MarketDataService()
        self.ai_service = ai_service or EnhancedAIService()
        self.telegram_bot = telegram_bot
        
        # Default schedules
        self.default_schedules = {
            'market_opening': ScheduleConfig(
                name='Báo cáo mở cửa thị trường',
                schedule_time='08:45',  # 15 minutes before VN market opens
                description='Báo cáo trước khi thị trường mở cửa'
            ),
            'lunch_summary': ScheduleConfig(
                name='Tổng kết buổi sáng',
                schedule_time='11:35',  # 5 minutes after morning session
                description='Tổng kết phiên giao dịch buổi sáng'
            ),
            'afternoon_preview': ScheduleConfig(
                name='Dự báo buổi chiều',
                schedule_time='12:55',  # 5 minutes before afternoon session
                description='Dự báo thị trường buổi chiều'
            ),
            'market_closing': ScheduleConfig(
                name='Báo cáo đóng cửa thị trường',
                schedule_time='15:05',  # 5 minutes after VN market closes
                description='Tổng kết phiên giao dịch cả ngày'
            ),
            'evening_analysis': ScheduleConfig(
                name='Phân tích tối',
                schedule_time='19:00',  # Evening analysis
                description='Phân tích sâu và dự báo ngày mai'
            ),
            'weekend_review': ScheduleConfig(
                name='Tổng kết tuần',
                schedule_time='17:00',  # Friday evening
                description='Tổng kết tuần và dự báo tuần tới'
            )
        }
        
        # Subscriber management
        self.subscribers = {}  # chat_id -> schedule preferences
        self.active_schedules = {}
        
        # Vietnam timezone
        self.vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
        
    def start_scheduler(self):
        """🚀 Start the market scheduler"""
        try:
            if not self.scheduler.running:
                self.scheduler.start()
                logger.info("⏰ Market scheduler started successfully")
                
                # Add default schedules
                self._setup_default_schedules()
                
            else:
                logger.warning("⚠️ Scheduler is already running")
                
        except Exception as e:
            logger.error(f"❌ Failed to start scheduler: {e}")

    def stop_scheduler(self):
        """🛑 Stop the market scheduler"""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown(wait=False)
                logger.info("⏹️ Market scheduler stopped")
            else:
                logger.warning("⚠️ Scheduler is not running")
                
        except Exception as e:
            logger.error(f"❌ Failed to stop scheduler: {e}")

    def _setup_default_schedules(self):
        """Setup default market schedules"""
        try:
            # Daily market schedules (Monday to Friday)
            for schedule_key, config in self.default_schedules.items():
                if schedule_key == 'weekend_review':
                    # Friday only
                    self.scheduler.add_job(
                        self._generate_and_send_report,
                        CronTrigger(
                            day_of_week='fri',
                            hour=int(config.schedule_time.split(':')[0]),
                            minute=int(config.schedule_time.split(':')[1]),
                            timezone=self.vn_tz
                        ),
                        id=f"schedule_{schedule_key}",
                        args=[schedule_key, config],
                        max_instances=1,
                        coalesce=True
                    )
                else:
                    # Monday to Friday
                    self.scheduler.add_job(
                        self._generate_and_send_report,
                        CronTrigger(
                            day_of_week='mon-fri',
                            hour=int(config.schedule_time.split(':')[0]),
                            minute=int(config.schedule_time.split(':')[1]),
                            timezone=self.vn_tz
                        ),
                        id=f"schedule_{schedule_key}",
                        args=[schedule_key, config],
                        max_instances=1,
                        coalesce=True
                    )
            
            logger.info(f"📅 Added {len(self.default_schedules)} default schedules")
            
        except Exception as e:
            logger.error(f"❌ Failed to setup default schedules: {e}")

    async def _generate_and_send_report(self, schedule_key: str, config: ScheduleConfig):
        """📊 Generate and send market report"""
        try:
            logger.info(f"📊 Generating {config.name} report...")
            
            # Get current market data
            market_data = await self.market_service.get_comprehensive_market_data()
            
            # Generate AI report based on schedule type
            report = await self._generate_market_report(schedule_key, market_data, config)
            
            if not report:
                logger.warning(f"⚠️ Failed to generate report for {schedule_key}")
                return
            
            # Send to all subscribers (or default chat)
            await self._send_report_to_subscribers(report, config)
            
            logger.info(f"✅ {config.name} report sent successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to generate/send report for {schedule_key}: {e}")

    async def _generate_market_report(self, schedule_key: str, market_data: Dict, config: ScheduleConfig) -> Optional[MarketReport]:
        """🤖 Generate AI market report based on schedule type"""
        try:
            # Create context-specific prompts
            prompt_templates = {
                'market_opening': """
🌅 TẠO BÁO CÁO MỞ CỬA THỊ TRƯỜNG CHỨNG KHOÁN

Dựa trên dữ liệu thị trường sau, hãy tạo báo cáo mở cửa thị trường:

📈 CỔ PHIẾU VIỆT NAM: {vn_stocks_summary}
🌍 CỔ PHIẾU QUỐC TẾ: {global_stocks_summary}  
🥇 GIÁ VÀNG: {gold_summary}
📰 TIN TỨC QUAN TRỌNG: {news_summary}

Yêu cầu báo cáo:
- Dự báo xu hướng thị trường hôm nay
- Điểm nhấn các cổ phiếu đáng chú ý
- Khuyến nghị đầu tư ngắn hạn
- Độ dài: 300-400 từ
- Tone: Chuyên nghiệp, tích cực, hướng dẫn
""",
                'lunch_summary': """
🍽️ TẠO BÁO CÁO TỔNG KẾT BUỔI SÁNG

Tạo báo cáo tổng kết phiên giao dịch buổi sáng:

📊 HIỆU SUẤT BUỔI SÁNG: {market_performance}
🔥 CỔ PHIẾU NỔI BẬT: {top_performers}
📉 CỔ PHIẾU GIẢM MẠNH: {declining_stocks}
💰 THANH KHOẢN: {volume_analysis}

Yêu cầu:
- Phân tích các diễn biến chính buổi sáng
- Đánh giá tâm lý nhà đầu tư
- Dự báo cho phiên chiều
- Độ dài: 250-350 từ
""",
                'afternoon_preview': """
🌤️ TẠO DỰ BÁO THỊ TRƯỜNG BUỔI CHIỀU

Dự báo thị trường cho phiên giao dịch buổi chiều:

📈 XU HƯỚNG HIỆN TẠI: {current_trends}
🎯 CỔ PHIẾU ĐÁNG CHÚ Ý: {watchlist}
📊 PHÂN TÍCH KỸ THUẬT: {technical_analysis}
🌍 ẢNH HƯỞNG QUỐC TẾ: {international_factors}

Yêu cầu:
- Dự báo xu hướng buổi chiều
- Khuyến nghị trading ngắn hạn
- Mức hỗ trợ/kháng cự quan trọng
- Độ dài: 250-300 từ
""",
                'market_closing': """
🌅 TẠO BÁO CÁO ĐÓNG CỬA THỊ TRƯỜNG

Tổng kết toàn diện phiên giao dịch hôm nay:

📊 TỔNG QUAN PHIÊN: {session_overview}
🏆 TOP WINNERS: {top_gainers}
📉 TOP LOSERS: {top_losers}
💎 ĐIỂM NHẤN: {key_highlights}
📈 CHỈ SỐ CHÍNH: {main_indices}

Yêu cầu:
- Đánh giá tổng thể phiên giao dịch
- Phân tích nguyên nhân biến động
- Dự báo cho phiên kế tiếp
- Khuyến nghị cho nhà đầu tư
- Độ dài: 400-500 từ
""",
                'evening_analysis': """
🌙 TẠO PHÂN TÍCH THỊ TRƯỜNG TỐI

Phân tích sâu thị trường và dự báo ngày mai:

🔍 PHÂN TÍCH SÂU: {deep_analysis}
📈 XU HƯỚNG DÀI HẠN: {long_term_trends}
🎯 CƠ HỘI ĐẦU TƯ: {investment_opportunities}
⚠️ RỦI RO CẦN LƯU Ý: {risk_factors}
🔮 DỰ BÁO NGÀY MAI: {tomorrow_outlook}

Yêu cầu:
- Phân tích chuyên sâu các yếu tố ảnh hưởng
- Đưa ra khuyến nghị đầu tư cụ thể
- Dự báo chi tiết cho ngày hôm sau
- Độ dài: 500-600 từ
- Tone: Chuyên nghiệp, phân tích sâu
""",
                'weekend_review': """
📅 TẠO BÁO CÁO TỔNG KẾT TUẦN

Tổng kết toàn diện tuần giao dịch và dự báo tuần tới:

📊 HIỆU SUẤT TUẦN: {weekly_performance}
🔥 SỰ KIỆN NỔ BẬT: {week_highlights}
📈 XU HƯỚNG CHỦ ĐẠO: {dominant_trends}
💰 DÒNG TIỀN: {money_flow}
🔮 DỰ BÁO TUẦN TỚI: {next_week_outlook}

Yêu cầu:
- Tổng kết đầy đủ tuần giao dịch
- Phân tích các sự kiện quan trọng
- Dự báo chi tiết cho tuần tới
- Chiến lược đầu tư tuần
- Độ dài: 600-700 từ
"""
            }
            
            # Prepare data summaries
            vn_stocks_summary = self._format_stocks_summary(market_data.get('vietnam_stocks', []))
            global_stocks_summary = self._format_stocks_summary(market_data.get('global_stocks', []))
            gold_summary = self._format_gold_summary(market_data.get('gold_data'))
            news_summary = self._format_news_summary(market_data.get('market_news', []))
            
            # Get the appropriate prompt
            prompt_template = prompt_templates.get(schedule_key, prompt_templates['market_closing'])
            
            # Format the prompt with actual data
            prompt = prompt_template.format(
                vn_stocks_summary=vn_stocks_summary,
                global_stocks_summary=global_stocks_summary,
                gold_summary=gold_summary,
                news_summary=news_summary,
                market_performance=vn_stocks_summary,  # Reuse for simplicity
                top_performers=vn_stocks_summary,
                declining_stocks=global_stocks_summary,
                volume_analysis="Thanh khoản ở mức trung bình",
                current_trends="Xu hướng tăng nhẹ",
                watchlist=vn_stocks_summary,
                technical_analysis="Chỉ báo kỹ thuật tích cực",
                international_factors=global_stocks_summary,
                session_overview="Phiên giao dịch diễn ra ổn định",
                top_gainers=vn_stocks_summary,
                top_losers=global_stocks_summary,
                key_highlights="Các cổ phiếu ngân hàng tăng mạnh",
                main_indices="VN-Index tăng 0.5%",
                deep_analysis="Thị trường đang trong xu hướng tích cực",
                long_term_trends="Triển vọng dài hạn khả quan",
                investment_opportunities=vn_stocks_summary,
                risk_factors="Rủi ro thấp trong ngắn hạn",
                tomorrow_outlook="Dự báo tích cực cho ngày mai",
                weekly_performance="Tuần tăng điểm tích cực",
                week_highlights="Nhiều tin tích cực từ doanh nghiệp",
                dominant_trends="Xu hướng tăng trưởng bền vững",
                money_flow="Dòng tiền vào ổn định",
                next_week_outlook="Tuần tới tiếp tục tích cực"
            )
            
            # Generate AI content
            ai_content = await self.ai_service.generate_content(prompt)
            
            if not ai_content:
                logger.warning(f"⚠️ AI content generation failed for {schedule_key}")
                ai_content = self._create_fallback_report(schedule_key, market_data, config)
            
            # Create report
            report = MarketReport(
                title=f"📊 {config.name} - {datetime.now().strftime('%d/%m/%Y')}",
                content=ai_content,
                report_type=schedule_key,
                generated_at=datetime.now()
            )
            
            return report
            
        except Exception as e:
            logger.error(f"❌ Failed to generate market report: {e}")
            # Return fallback report
            return MarketReport(
                title=f"📊 {config.name} - {datetime.now().strftime('%d/%m/%Y')}",
                content=self._create_fallback_report(schedule_key, market_data, config),
                report_type=schedule_key,
                generated_at=datetime.now()
            )

    def _format_stocks_summary(self, stocks: List) -> str:
        """Format stocks data for AI prompt"""
        if not stocks:
            return "Không có dữ liệu cổ phiếu"
        
        summary_parts = []
        for stock in stocks[:5]:  # Top 5 stocks
            change_icon = "📈" if stock.change >= 0 else "📉"
            summary_parts.append(
                f"{change_icon} {stock.symbol} ({stock.name}): {stock.price:.0f} "
                f"({stock.change_percent:+.1f}%)"
            )
        
        return " | ".join(summary_parts)

    def _format_gold_summary(self, gold_data) -> str:
        """Format gold data for AI prompt"""
        if not gold_data:
            return "Không có dữ liệu giá vàng"
        
        change_icon = "📈" if gold_data.change >= 0 else "📉"
        return (f"{change_icon} Vàng: ${gold_data.price_usd:.0f}/oz "
                f"({gold_data.change_percent:+.1f}%) | "
                f"~{gold_data.price_vnd:,.0f} VND/lượng")

    def _format_news_summary(self, news: List) -> str:
        """Format news data for AI prompt"""
        if not news:
            return "Không có tin tức mới"
        
        news_parts = []
        for item in news[:3]:  # Top 3 news
            news_parts.append(f"• {item.title[:100]}...")
        
        return " | ".join(news_parts)

    def _create_fallback_report(self, schedule_key: str, market_data: Dict, config: ScheduleConfig) -> str:
        """Create fallback report when AI fails"""
        current_time = datetime.now().strftime('%H:%M %d/%m/%Y')
        
        fallback_content = f"""
📊 **{config.name}**
⏰ Thời gian: {current_time}

📈 **TÌNH HÌNH THỊ TRƯỜNG**
• Thị trường Việt Nam: {"Đang mở cửa" if self.market_service.is_market_open('vietnam') else "Đã đóng cửa"}
• Thị trường Mỹ: {"Đang mở cửa" if self.market_service.is_market_open('us') else "Đã đóng cửa"}

🏦 **CỔ PHIẾU VIỆT NAM**
{self._format_stocks_summary(market_data.get('vietnam_stocks', []))}

🌍 **CỔ PHIẾU QUỐC TẾ**  
{self._format_stocks_summary(market_data.get('global_stocks', []))}

🥇 **GIÁ VÀNG**
{self._format_gold_summary(market_data.get('gold_data'))}

📰 **TIN TỨC NỔI BẬT**
{self._format_news_summary(market_data.get('market_news', []))}

---
🤖 Báo cáo được tạo tự động bởi Market AI Bot
📱 Để cập nhật lịch báo cáo, gửi /schedule
        """
        
        return fallback_content.strip()

    async def _send_report_to_subscribers(self, report: MarketReport, config: ScheduleConfig):
        """📱 Send report to Telegram subscribers"""
        try:
            if not self.telegram_bot:
                logger.warning("⚠️ Telegram bot not configured")
                return
            
            # Get default chat ID from environment or config
            default_chat_id = config.chat_id or os.getenv('DEFAULT_CHAT_ID')
            
            if not default_chat_id and not self.subscribers:
                logger.warning("⚠️ No subscribers or default chat configured")
                return
            
            # Send to subscribers or default chat
            recipients = list(self.subscribers.keys()) if self.subscribers else [int(default_chat_id)] if default_chat_id else []
            
            for chat_id in recipients:
                try:
                    # Send the report
                    await self.telegram_bot.send_message(
                        chat_id=chat_id,
                        text=f"**{report.title}**\n\n{report.content}",
                        parse_mode='Markdown'
                    )
                    
                    logger.info(f"📤 Report sent to chat {chat_id}")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to send report to {chat_id}: {e}")
            
        except Exception as e:
            logger.error(f"❌ Failed to send reports: {e}")

    def add_custom_schedule(self, name: str, schedule_time: str, chat_id: int = None, description: str = "") -> bool:
        """➕ Add custom market schedule"""
        try:
            # Validate time format
            time_parts = schedule_time.split(':')
            if len(time_parts) != 2:
                return False
            
            hour, minute = int(time_parts[0]), int(time_parts[1])
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                return False
            
            # Create schedule config
            config = ScheduleConfig(
                name=name,
                schedule_time=schedule_time,
                description=description,
                chat_id=chat_id
            )
            
            # Add to scheduler
            job_id = f"custom_{name.lower().replace(' ', '_')}"
            self.scheduler.add_job(
                self._generate_and_send_report,
                CronTrigger(
                    day_of_week='mon-fri',
                    hour=hour,
                    minute=minute,
                    timezone=self.vn_tz
                ),
                id=job_id,
                args=['market_closing', config],  # Use default report type
                max_instances=1,
                coalesce=True,
                replace_existing=True
            )
            
            # Save to active schedules
            self.active_schedules[job_id] = config
            
            logger.info(f"➕ Added custom schedule: {name} at {schedule_time}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to add custom schedule: {e}")
            return False

    def remove_schedule(self, job_id: str) -> bool:
        """➖ Remove a schedule"""
        try:
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                self.active_schedules.pop(job_id, None)
                logger.info(f"➖ Removed schedule: {job_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"❌ Failed to remove schedule: {e}")
            return False

    def subscribe_user(self, chat_id: int, schedules: List[str] = None):
        """👤 Subscribe user to market reports"""
        if schedules is None:
            schedules = list(self.default_schedules.keys())
        
        self.subscribers[chat_id] = {
            'schedules': schedules,
            'subscribed_at': datetime.now(),
            'active': True
        }
        
        logger.info(f"👤 User {chat_id} subscribed to {len(schedules)} schedules")

    def unsubscribe_user(self, chat_id: int):
        """❌ Unsubscribe user from market reports"""
        if chat_id in self.subscribers:
            del self.subscribers[chat_id]
            logger.info(f"❌ User {chat_id} unsubscribed")

    def get_schedule_status(self) -> Dict[str, Any]:
        """📋 Get scheduler status"""
        return {
            'running': self.scheduler.running,
            'job_count': len(self.scheduler.get_jobs()),
            'subscriber_count': len(self.subscribers),
            'active_schedules': list(self.active_schedules.keys()),
            'next_jobs': [
                {
                    'id': job.id,
                    'next_run': job.next_run_time.strftime('%H:%M %d/%m/%Y') if job.next_run_time else None
                }
                for job in self.scheduler.get_jobs()[:5]
            ]
        }

    async def send_manual_report(self, report_type: str = 'market_closing', chat_id: int = None) -> bool:
        """📤 Send manual market report"""
        try:
            config = self.default_schedules.get(
                report_type, 
                self.default_schedules['market_closing']
            )
            
            if chat_id:
                config.chat_id = chat_id
            
            await self._generate_and_send_report(report_type, config)
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send manual report: {e}")
            return False 