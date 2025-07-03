#!/usr/bin/env python3
"""
News → Facebook AI Agent Workflow
Main application entry point for the automated news-to-Facebook posting system

Key Features:
- Telegram bot with "Start" message trigger
- Multi-source news fetching with web scraping fallback
- AI-powered ranking and Vietnamese content generation using Gemini
- Advanced image generation with Stability AI and multiple providers
- Expert Facebook post integration (Ho Quoc Tuan)
- Automated Facebook publishing
- Market data & automated reporting
- Comprehensive logging with API key rotation
"""

import asyncio
import logging
import os
import sys
import signal
import platform
from datetime import datetime
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from config import Config
from bot.handlers import BotHandlers
from services.news_service import NewsService
from services.enhanced_ai_service import EnhancedAIService
from services.facebook_service import FacebookService
from services.image_service import ImageService
from services.advanced_image_service import AdvancedImageService
from services.market_data_service import MarketDataService
from services.market_scheduler import MarketScheduler
from services.logging_service import LoggingService
from services.detailed_workflow_logger import DetailedWorkflowLogger
from bot.premium_handlers import PremiumHandlers
from services.interactive_dashboard_service import InteractiveDashboardService
from services.smart_alerts_service import SmartAlertsService
from services.premium_subscription_service import PremiumSubscriptionService

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler()
    ]
)

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

class NewsBot:
    def __init__(self):
        self.config = Config()
        self.app = None
        
        # Validate required configuration
        self._validate_config()
        
        print("🔧 Initializing services...")
        
        # Initialize services with enhanced capabilities
        self.news_service = NewsService()
        self.ai_service = EnhancedAIService()
        self.facebook_service = FacebookService()
        self.image_service = ImageService()
        self.advanced_image_service = AdvancedImageService()
        self.market_service = MarketDataService()
        self.logging_service = LoggingService()
        
        # Initialize detailed workflow logger for comprehensive tracking
        self.detailed_logger = DetailedWorkflowLogger()
        
        # Market scheduler will be initialized later
        self.market_scheduler = None
        
        # Premium services will be initialized later
        self.premium_handlers = None
        self.smart_alerts_service = None
        
        print("✅ Services initialized successfully")
    
    def _validate_config(self):
        """Validate required configuration with enhanced checks"""
        # Check basic required config
        if not self.config.TELEGRAM_TOKEN:
            print("❌ Missing required environment variables:")
            print("- TELEGRAM_BOT_TOKEN (Telegram Bot Token)")
            print("\n📝 Please check SETUP_GUIDE.md for configuration instructions")
            sys.exit(1)
        
        # Check Gemini API keys using the get_active_api_keys method
        gemini_keys = self.config.get_active_api_keys('gemini')
        if not gemini_keys:
            print("❌ Missing required environment variables:")
            print("- GOOGLE_AI_API_KEY (Google AI (Gemini) API Key)")
            print("\n📝 Please check SETUP_GUIDE.md for configuration instructions")
            sys.exit(1)
        
        print(f"✅ Gemini AI: {len(gemini_keys)} API key(s) configured")
        
        optional_vars = {
            'FACEBOOK_ACCESS_TOKEN': 'Facebook Graph API Access Token',
            'FACEBOOK_PAGE_ID': 'Facebook Page ID for posting'
        }
        
        # Check optional Facebook config
        fb_missing = []
        for var, description in optional_vars.items():
            if not getattr(self.config, var, None):
                fb_missing.append(f"- {var} ({description})")
        
        if fb_missing:
            print("⚠️ Facebook automation not configured (optional):")
            print("\n".join(fb_missing))
            print("📝 Bot will work without Facebook posting")
        
        # Check API keys availability
        stability_keys = self.config.get_active_api_keys('stability')
        if stability_keys:
            print(f"✅ Stability AI: {len(stability_keys)} API key(s) configured")
        else:
            print("⚠️ No Stability AI keys configured - using free services")
            
        hf_keys = self.config.get_active_api_keys('huggingface')
        if hf_keys:
            print(f"✅ Hugging Face: {len(hf_keys)} API key(s) configured")
        else:
            print("⚠️ No Hugging Face keys - limited image generation")
        
        print("✅ Configuration validated successfully")
        
    async def setup_bot(self):
        """Setup Telegram bot with all handlers"""
        print("🤖 Setting up Telegram bot...")
        
        self.app = Application.builder().token(self.config.TELEGRAM_TOKEN).build()
        
        # Initialize market scheduler with bot
        self.market_scheduler = MarketScheduler(
            telegram_bot=self.app.bot,
            ai_service=self.ai_service
        )
        
        # Initialize bot handlers with all services
        self.handlers = BotHandlers(
            self.news_service,
            self.ai_service,
            self.advanced_image_service,
            self.facebook_service,
            self.logging_service,
            market_service=self.market_service,
            market_scheduler=self.market_scheduler
        )
        
        # 🎯 PREMIUM FEATURES INTEGRATION
        print("🎯 Initializing Premium Features...")
        
        # Initialize premium handlers
        self.premium_handlers = PremiumHandlers(self.app)
        self.premium_handlers.register_demo_handlers()
        print("✅ Premium handlers configured")
        
        # Get smart alerts service for monitoring
        self.smart_alerts_service = self.premium_handlers.alerts_service
        
        # Add command handlers
        self.app.add_handler(CommandHandler("start", self.handlers.start))
        self.app.add_handler(CommandHandler("help", self.handlers.help_command))
        
        # Image generation handlers (NEW)
        self.app.add_handler(CommandHandler("image", self.handlers.image_command))
        self.app.add_handler(CommandHandler("image_status", self.handlers.image_status_command))
        self.app.add_handler(CommandHandler("api_health", self.handlers.api_health_command))
        
        # Market command handlers
        self.app.add_handler(CommandHandler("market", self.handlers.market_overview))
        self.app.add_handler(CommandHandler("stocks", self.handlers.vietnamese_stocks))
        self.app.add_handler(CommandHandler("global", self.handlers.global_stocks))
        self.app.add_handler(CommandHandler("gold", self.handlers.gold_prices))
        self.app.add_handler(CommandHandler("report", self.handlers.market_report))
        
        # AI Investment Analysis command handlers (SIMPLE)
        self.app.add_handler(CommandHandler("ai", self.handlers.ai_command))
        self.app.add_handler(CommandHandler("ai_analysis", self.handlers.ai_investment_analysis_command))
        self.app.add_handler(CommandHandler("ai_portfolio", self.handlers.ai_portfolio_recommendation_command))
        self.app.add_handler(CommandHandler("ai_sentiment", self.handlers.ai_market_sentiment_command))
        
        # Schedule management handlers
        self.app.add_handler(CommandHandler("schedule", self.handlers.schedule_command))
        self.app.add_handler(CommandHandler("subscribe", self.handlers.subscribe_command))
        self.app.add_handler(CommandHandler("unsubscribe", self.handlers.unsubscribe_command))
        self.app.add_handler(CommandHandler("status", self.handlers.status_command))
        
        # Message handlers
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handlers.handle_text))
        self.app.add_handler(MessageHandler(filters.VOICE, self.handlers.handle_voice))
        
        # Callback query handler for buttons
        self.app.add_handler(CallbackQueryHandler(self.handlers.button_callback))
        
        print("✅ Bot handlers configured")
        
        # Start market scheduler
        print("⏰ Starting market scheduler...")
        self.market_scheduler.start_scheduler()
        print("✅ Market scheduler started")
        
        return self.app
    
    async def shutdown(self):
        """Gracefully shutdown bot and services"""
        print("🛑 Shutting down bot...")
        
        # Stop smart alerts monitoring
        if self.smart_alerts_service:
            await self.smart_alerts_service.stop_monitoring()
            print("✅ Smart alerts monitoring stopped")
        
        if self.market_scheduler:
            self.market_scheduler.stop_scheduler()
            print("✅ Market scheduler stopped")
        
        if self.app:
            await self.app.stop()
            await self.app.shutdown()
            print("✅ Bot stopped")

async def main():
    """Main application entry point with proper error handling"""
    print("🤖 News → Facebook AI Agent Starting...")
    print("📰 Multi-source news fetching with web scraping")
    print("🧠 Gemini 1.5 Flash AI integration")
    print("🎨 Stability AI + multiple image providers")
    print("🔄 API key rotation & fallback systems")
    print("📱 Facebook auto-publishing")
    print("📊 Market data & automated reports")
    print("⏰ Scheduled market analysis")
    print("=" * 50)
    
    bot = None
    
    try:
        bot = NewsBot()
        app = await bot.setup_bot()
        
        print("✅ Bot initialized successfully")
        print("🚀 Ready to receive messages...")
        print("💡 Send '/start' to see all available commands")
        print("📊 Market reports will be sent automatically")
        print("🔍 Enhanced image generation with multiple providers")
        print("")
        print("🎯 PREMIUM FEATURES AVAILABLE:")
        print("   • /dashboard - Interactive Trading Dashboard")
        print("   • /alerts - Smart Price Alerts System") 
        print("   • /premium - Premium Subscription Features")
        print("   • ALERT: SYMBOL above/below PRICE - Quick alerts")
        print("=" * 50)
        
        # Initialize and start the application manually
        await app.initialize()
        await app.start()
        
        # Start polling manually to avoid event loop conflicts
        updater = app.updater
        await updater.start_polling(drop_pending_updates=True)
        
        print("🔄 Bot is now polling for updates...")
        
        # Keep the application running
        try:
            # Wait indefinitely
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 Received interrupt signal")
        
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"❌ Bot failed to start: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if bot and bot.app:
            print("🛑 Shutting down bot...")
            try:
                # Stop polling
                if hasattr(bot.app, 'updater'):
                    await bot.app.updater.stop()
                
                # Stop the application
                await bot.app.stop()
                await bot.app.shutdown()
                print("✅ Bot stopped cleanly")
            except Exception as e:
                print(f"⚠️ Error during shutdown: {e}")
        
        if bot and bot.market_scheduler:
            try:
                bot.market_scheduler.stop_scheduler()
                print("✅ Market scheduler stopped")
            except Exception as e:
                print(f"⚠️ Error stopping scheduler: {e}")

def run_bot():
    """Run bot with proper event loop handling for all platforms"""
    try:
        # Fix for different platforms
        if platform.system() == 'Windows':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        # Always create a new event loop to avoid conflicts
        print("🆕 Creating clean event loop")
        
        # Close any existing event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.close()
        except:
            pass
        
        # Create fresh event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Run the main function
            loop.run_until_complete(main())
        finally:
            # Clean shutdown
            try:
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except:
                pass
            finally:
                loop.close()
            
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"❌ Bot startup failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    run_bot()
