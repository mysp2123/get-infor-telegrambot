#!/usr/bin/env python3
"""
Premium Handlers - Integration của 3 tính năng khả quan nhất
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler, MessageHandler, filters
from services.interactive_dashboard_service import InteractiveDashboardService
from services.smart_alerts_service import SmartAlertsService
from services.premium_subscription_service import PremiumSubscriptionService, SubscriptionTier
from services.market_data_service import MarketDataService
from services.enhanced_ai_service import EnhancedAIService

logger = logging.getLogger(__name__)

class PremiumHandlers:
    """
    🎯 PREMIUM HANDLERS - Tích hợp 3 tính năng ROI cao nhất:
    
    1. 📊 Interactive Dashboard - Engagement ngay lập tức
    2. 🔔 Smart Price Alerts - Retention cao
    3. 💰 Premium Subscriptions - Monetization
    """
    
    def __init__(self, bot_application):
        self.application = bot_application
        self.bot = bot_application.bot
        
        # Initialize services
        self.market_service = MarketDataService()
        self.ai_service = EnhancedAIService()
        
        # Initialize premium services
        self.dashboard_service = InteractiveDashboardService(self.market_service, self.ai_service)
        self.alerts_service = SmartAlertsService(self.market_service, self.bot)
        self.subscription_service = PremiumSubscriptionService(self.bot)
        
        # Start alert monitoring
        self.application.job_queue.run_once(self._start_alert_monitoring, 5)
        
        # Register handlers
        self._register_handlers()

    def _register_handlers(self):
        """Register all premium handlers"""
        
        # Main dashboard command
        self.application.add_handler(CommandHandler("dashboard", self.dashboard_command))
        self.application.add_handler(CommandHandler("premium", self.premium_command))
        self.application.add_handler(CommandHandler("alerts", self.alerts_command))
        
        # Callback query handlers
        callback_handlers = [
            # Dashboard callbacks
            ('main_dashboard', self.handle_main_dashboard),
            ('market_overview', self.handle_market_overview),
            ('portfolio', self.handle_portfolio),
            ('price_alerts', self.handle_price_alerts),
            ('premium', self.handle_premium_showcase),
            
            # Alert callbacks
            ('add_alert', self.handle_add_alert),
            ('view_alerts', self.handle_view_alerts),
            ('trending_alerts', self.handle_trending_alerts),
            ('smart_alerts', self.handle_smart_alerts),
            
            # Premium callbacks
            ('upgrade_pro', self.handle_upgrade_pro),
            ('free_trial', self.handle_free_trial),
            ('subscription_status', self.handle_subscription_status),
            
            # Quick actions
            ('refresh_market', self.handle_refresh_market),
            ('ai_insights', self.handle_ai_insights),
        ]
        
        for callback_data, handler in callback_handlers:
            self.application.add_handler(CallbackQueryHandler(handler, pattern=f"^{callback_data}$"))
        
        # Text message handlers for alert creation
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.Regex(r'^(ALERT|Alert|alert):'),
            self.handle_quick_alert
        ))

    async def dashboard_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Main dashboard command"""
        try:
            user_id = update.effective_user.id
            
            # Get user subscription status
            subscription = self.subscription_service.get_user_subscription(user_id)
            
            # Create welcome message
            message = f"📊 **AI TRADING DASHBOARD**\n\n"
            message += f"👋 Welcome back, {update.effective_user.first_name}!\n"
            message += f"🎯 **Status:** {subscription.tier.value.title()} Member\n\n"
            
            # Show quick stats
            alert_stats = self.alerts_service.get_alert_statistics(user_id)
            message += f"🔔 **Active Alerts:** {alert_stats['active_alerts']}/{alert_stats['alerts_limit']}\n"
            message += f"💰 **Portfolio:** Coming soon!\n"
            message += f"📈 **Success Rate:** {alert_stats['success_rate']:.1f}%\n\n"
            
            # Show market status
            try:
                market_data = await self.market_service.get_comprehensive_market_data()
                if market_data.get('global_stocks'):
                    stock = market_data['global_stocks'][0]
                    trend = "📈" if stock.change_percent > 0 else "📉"
                    message += f"🌍 **Market:** {stock.symbol} {trend} {stock.change_percent:+.1f}%\n"
            except:
                message += "🌍 **Market:** Loading...\n"
            
            message += "\n🚀 **Choose your action below:**"
            
            # Create dashboard buttons
            keyboard = self.dashboard_service.create_main_dashboard(user_id)
            
            await update.message.reply_text(
                message,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"❌ Dashboard error: {e}")
            await update.message.reply_text("❌ Dashboard temporarily unavailable. Try again!")

    async def premium_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Premium showcase command"""
        try:
            user_id = update.effective_user.id
            
            # Generate personalized premium message
            message = await self.subscription_service.generate_premium_showcase_message(user_id)
            
            # Get upgrade options
            upgrade_options = self.subscription_service.get_upgrade_options(user_id)
            
            # Create buttons
            keyboard = []
            for option in upgrade_options[:3]:  # Show top 3 options
                if option['type'] == 'trial':
                    keyboard.append([InlineKeyboardButton(option['cta'], callback_data="free_trial")])
                else:
                    callback_data = f"upgrade_{option['tier']}"
                    keyboard.append([InlineKeyboardButton(option['cta'], callback_data=callback_data)])
            
            keyboard.append([
                InlineKeyboardButton("📊 View Features", callback_data="premium_features"),
                InlineKeyboardButton("💳 Subscription Status", callback_data="subscription_status")
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"❌ Premium command error: {e}")
            await update.message.reply_text("❌ Premium info temporarily unavailable.")

    async def alerts_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Quick alerts command"""
        try:
            user_id = update.effective_user.id
            
            # Get user alerts
            alerts = self.alerts_service.get_user_alerts(user_id)
            active_alerts = [a for a in alerts if a.is_active]
            
            message = f"🔔 **PRICE ALERTS**\n\n"
            
            if active_alerts:
                message += f"📋 **Active Alerts ({len(active_alerts)}):**\n\n"
                for i, alert in enumerate(active_alerts[:5], 1):
                    message += f"{i}. {alert.symbol} {alert.condition} ${alert.target_price:.2f}\n"
                    message += f"   ⏰ {alert.created_at.strftime('%m-%d %H:%M')}\n\n"
            else:
                message += "📭 No active alerts.\n\n"
            
            message += "💡 **Quick Setup:**\n"
            message += "Type: `ALERT: AAPL above 200`\n"
            message += "Or use the buttons below!"
            
            # Create alert buttons
            keyboard = self.dashboard_service.create_price_alerts_buttons(user_id)
            
            await update.message.reply_text(
                message,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"❌ Alerts command error: {e}")
            await update.message.reply_text("❌ Alerts temporarily unavailable.")

    async def handle_main_dashboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle main dashboard callback"""
        await self.dashboard_command(update, context)

    async def handle_market_overview(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle market overview"""
        await self.dashboard_service.handle_market_overview(update, context)

    async def handle_portfolio(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle portfolio view"""
        await self.dashboard_service.handle_portfolio(update, context)

    async def handle_price_alerts(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle price alerts"""
        await self.dashboard_service.handle_price_alerts(update, context)

    async def handle_premium_showcase(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle premium showcase"""
        await self.dashboard_service.handle_premium_showcase(update, context)

    async def handle_add_alert(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle add alert request"""
        try:
            message = "➕ **ADD PRICE ALERT**\n\n"
            message += "📝 **Format:** `ALERT: SYMBOL condition PRICE`\n\n"
            message += "📋 **Examples:**\n"
            message += "• `ALERT: AAPL above 200`\n"
            message += "• `ALERT: BTC below 45000`\n"
            message += "• `ALERT: GOOGL above 180`\n\n"
            message += "🚀 **Supported Symbols:**\n"
            message += "• Stocks: AAPL, GOOGL, MSFT, TSLA, AMZN\n"
            message += "• Crypto: BTC, ETH, BNB, ADA, DOT\n\n"
            message += "💡 Just type your alert and I'll set it up!"
            
            keyboard = [[InlineKeyboardButton("◀️ Back to Alerts", callback_data="price_alerts")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"❌ Add alert error: {e}")

    async def handle_view_alerts(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle view alerts"""
        try:
            user_id = update.effective_user.id
            alerts = self.alerts_service.get_user_alerts(user_id)
            
            message = "📋 **MY ALERTS**\n\n"
            
            if alerts:
                active_alerts = [a for a in alerts if a.is_active]
                triggered_alerts = [a for a in alerts if not a.is_active]
                
                if active_alerts:
                    message += f"🟢 **Active ({len(active_alerts)}):**\n"
                    for i, alert in enumerate(active_alerts, 1):
                        message += f"{i}. {alert.symbol} {alert.condition} ${alert.target_price:.2f}\n"
                        message += f"   📅 {alert.created_at.strftime('%m-%d %H:%M')}\n\n"
                
                if triggered_alerts:
                    message += f"✅ **Recently Triggered ({len(triggered_alerts)}):**\n"
                    for alert in triggered_alerts[-3:]:  # Show last 3
                        message += f"• {alert.symbol} {alert.condition} ${alert.target_price:.2f}\n"
                        message += f"  ⏰ {alert.triggered_at.strftime('%m-%d %H:%M') if alert.triggered_at else 'N/A'}\n\n"
            else:
                message += "📭 No alerts yet. Create your first alert!"
            
            keyboard = [
                [InlineKeyboardButton("➕ Add Alert", callback_data="add_alert")],
                [InlineKeyboardButton("◀️ Back", callback_data="price_alerts")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"❌ View alerts error: {e}")

    async def handle_trending_alerts(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle trending alerts"""
        try:
            user_id = update.effective_user.id
            trending = await self.alerts_service.get_trending_alerts(user_id)
            
            message = "🔥 **TRENDING ALERTS**\n\n"
            message += "Hot stocks and crypto worth watching:\n\n"
            
            if trending:
                for item in trending[:5]:
                    trend_emoji = "🚀" if item['change_percent'] > 0 else "📉"
                    message += f"{trend_emoji} **{item['symbol']}** {item['change_percent']:+.1f}%\n"
                    message += f"💰 Current: ${item['current_price']:.2f}\n"
                    message += f"🎯 Suggested: ${item['suggested_alert_price']:.2f} ({item['suggested_condition']})\n"
                    message += f"💡 {item['reason']}\n\n"
            else:
                message += "📊 No trending opportunities right now.\n"
                message += "Check back later for hot picks!"
            
            keyboard = [
                [InlineKeyboardButton("🔄 Refresh", callback_data="trending_alerts")],
                [InlineKeyboardButton("◀️ Back", callback_data="price_alerts")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"❌ Trending alerts error: {e}")

    async def handle_smart_alerts(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle smart alerts showcase"""
        try:
            user_id = update.effective_user.id
            subscription = self.subscription_service.get_user_subscription(user_id)
            
            if subscription.tier == SubscriptionTier.FREE:
                message = "🤖 **SMART ALERTS** (Premium Feature)\n\n"
                message += "Unlock AI-powered alerts that detect:\n\n"
                message += "🎯 **Breakout Patterns**\n"
                message += "• Automatic resistance/support detection\n"
                message += "• Volume-based confirmations\n\n"
                message += "📊 **Volume Spikes**\n"
                message += "• Unusual trading activity alerts\n"
                message += "• Insider trading indicators\n\n"
                message += "🔮 **Trend Reversals**\n"
                message += "• AI pattern recognition\n"
                message += "• Market sentiment analysis\n\n"
                message += "💡 **Available in Pro & Enterprise plans**"
                
                keyboard = [
                    [InlineKeyboardButton("🚀 Try Free Trial", callback_data="free_trial")],
                    [InlineKeyboardButton("⭐ Upgrade to Pro", callback_data="upgrade_pro")],
                    [InlineKeyboardButton("◀️ Back", callback_data="price_alerts")]
                ]
            else:
                message = "🤖 **SMART ALERTS** (Premium Active)\n\n"
                message += "Choose your AI-powered alert type:\n\n"
                message += "🎯 **Breakout Alerts**\n"
                message += "• Detect resistance breaks\n"
                message += "• Momentum confirmations\n\n"
                message += "📊 **Volume Alerts**\n"
                message += "• Unusual activity detection\n"
                message += "• Market maker moves\n\n"
                message += "🔮 **Trend Reversal**\n"
                message += "• AI pattern analysis\n"
                message += "• Sentiment indicators\n"
                
                keyboard = [
                    [InlineKeyboardButton("🎯 Setup Breakout", callback_data="setup_breakout_alert")],
                    [InlineKeyboardButton("📊 Setup Volume", callback_data="setup_volume_alert")],
                    [InlineKeyboardButton("🔮 Setup Reversal", callback_data="setup_reversal_alert")],
                    [InlineKeyboardButton("◀️ Back", callback_data="price_alerts")]
                ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"❌ Smart alerts error: {e}")

    async def handle_free_trial(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle free trial request"""
        try:
            user_id = update.effective_user.id
            result = await self.subscription_service.start_free_trial(user_id)
            
            if result['success']:
                message = "🎉 **FREE TRIAL ACTIVATED!**\n\n"
                message += "✅ 7-day Pro trial started\n"
                message += f"📅 Valid until: {result['trial_end'].strftime('%Y-%m-%d')}\n\n"
                message += "🚀 **Unlocked Features:**\n"
                message += "• 50 price alerts (vs 5)\n"
                message += "• AI trading insights\n"
                message += "• Smart alerts\n"
                message += "• Advanced analytics\n"
                message += "• Priority support\n\n"
                message += "🎯 **Start exploring now!**"
                
                keyboard = [
                    [InlineKeyboardButton("📊 Open Dashboard", callback_data="main_dashboard")],
                    [InlineKeyboardButton("🔔 Create Smart Alert", callback_data="smart_alerts")]
                ]
            else:
                message = f"❌ **{result['error']}**\n\n"
                if result.get('upgrade_required'):
                    message += "💡 Consider upgrading to Pro for continued access!"
                    keyboard = [
                        [InlineKeyboardButton("⭐ Upgrade to Pro", callback_data="upgrade_pro")],
                        [InlineKeyboardButton("◀️ Back", callback_data="premium")]
                    ]
                else:
                    keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="premium")]]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"❌ Free trial error: {e}")

    async def handle_upgrade_pro(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle Pro upgrade"""
        try:
            user_id = update.effective_user.id
            
            message = "⭐ **UPGRADE TO PRO**\n\n"
            message += "🚀 **What you get:**\n"
            message += "• 50 price alerts (vs 5 free)\n"
            message += "• AI trading insights\n"
            message += "• Smart breakout alerts\n"
            message += "• Portfolio optimization\n"
            message += "• Advanced analytics\n"
            message += "• Priority support\n"
            message += "• Multi-platform publishing\n\n"
            message += "💰 **Pricing:**\n"
            message += "• Monthly: $19/month\n"
            message += "• Yearly: $190/year (2 months FREE!)\n\n"
            message += "⚡ **Join 10,000+ Pro traders!**\n\n"
            message += "🔒 **Demo Mode** - Real payments not implemented yet.\n"
            message += "This will simulate the upgrade for testing."
            
            keyboard = [
                [InlineKeyboardButton("💳 Upgrade Monthly ($19)", callback_data="demo_upgrade_pro_monthly")],
                [InlineKeyboardButton("💎 Upgrade Yearly ($190)", callback_data="demo_upgrade_pro_yearly")],
                [InlineKeyboardButton("◀️ Back", callback_data="premium")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"❌ Upgrade Pro error: {e}")

    async def handle_quick_alert(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle quick alert creation from text"""
        try:
            user_id = update.effective_user.id
            text = update.message.text.lower()
            
            # Parse alert format: "ALERT: SYMBOL condition PRICE"
            if text.startswith(('alert:', 'alert ', 'ALERT:')):
                parts = text.replace('alert:', '').strip().split()
                
                if len(parts) >= 3:
                    symbol = parts[0].upper()
                    condition = parts[1].lower()
                    try:
                        price = float(parts[2])
                        
                        # Validate condition
                        if condition not in ['above', 'below', 'over', 'under']:
                            await update.message.reply_text(
                                "❌ Use 'above' or 'below' for condition.\n"
                                "Example: `ALERT: AAPL above 200`"
                            )
                            return
                        
                        # Normalize condition
                        if condition in ['over', 'above']:
                            condition = 'above'
                        elif condition in ['under', 'below']:
                            condition = 'below'
                        
                        # Create alert
                        result = await self.alerts_service.add_simple_alert(user_id, symbol, price, condition)
                        
                        if result['success']:
                            current_price = result.get('current_price', 0)
                            message = f"✅ **Alert Created!**\n\n"
                            message += f"🎯 **Symbol:** {symbol}\n"
                            message += f"📊 **Condition:** {condition} ${price:.2f}\n"
                            message += f"💰 **Current Price:** ${current_price:.2f}\n\n"
                            message += "🔔 You'll be notified when triggered!"
                            
                            keyboard = [
                                [InlineKeyboardButton("📋 View All Alerts", callback_data="view_alerts")],
                                [InlineKeyboardButton("📊 Dashboard", callback_data="main_dashboard")]
                            ]
                            reply_markup = InlineKeyboardMarkup(keyboard)
                            
                            await update.message.reply_text(
                                message,
                                reply_markup=reply_markup,
                                parse_mode='Markdown'
                            )
                        else:
                            error_msg = result.get('error', 'Unknown error')
                            await update.message.reply_text(f"❌ **Error:** {error_msg}")
                            
                            if result.get('upgrade_needed'):
                                keyboard = [[InlineKeyboardButton("⭐ Upgrade to Pro", callback_data="upgrade_pro")]]
                                reply_markup = InlineKeyboardMarkup(keyboard)
                                await update.message.reply_text(
                                    "💡 **Upgrade to Pro** for 50 alerts vs 5 free!",
                                    reply_markup=reply_markup
                                )
                        
                    except ValueError:
                        await update.message.reply_text(
                            "❌ Invalid price format.\n"
                            "Example: `ALERT: AAPL above 200`"
                        )
                else:
                    await update.message.reply_text(
                        "❌ Invalid format. Use:\n"
                        "`ALERT: SYMBOL condition PRICE`\n\n"
                        "Example: `ALERT: AAPL above 200`"
                    )
                    
        except Exception as e:
            logger.error(f"❌ Quick alert error: {e}")
            await update.message.reply_text("❌ Error creating alert. Please try again.")

    async def _start_alert_monitoring(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Start alert monitoring service"""
        try:
            await self.alerts_service.start_monitoring()
            logger.info("✅ Alert monitoring started")
        except Exception as e:
            logger.error(f"❌ Failed to start alert monitoring: {e}")

    async def handle_subscription_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle subscription status request"""
        try:
            user_id = update.effective_user.id
            status = self.subscription_service.get_subscription_status(user_id)
            
            message = f"💳 **SUBSCRIPTION STATUS**\n\n"
            message += f"🎯 **Plan:** {status['tier'].title()}\n"
            message += f"📅 **Status:** {'Active' if status['is_active'] else 'Inactive'}\n"
            
            if status['tier'] != 'free':
                message += f"⏰ **Days Remaining:** {status['days_remaining']}\n"
                message += f"🔄 **Auto Renew:** {'Yes' if status['auto_renew'] else 'No'}\n"
                if status['next_billing']:
                    message += f"💳 **Next Billing:** {status['next_billing'].strftime('%Y-%m-%d')}\n"
            
            message += f"\n🚀 **Your Features:**\n"
            features = status['features']
            for feature, limit in features.items():
                if limit is True or limit == 'unlimited':
                    message += f"✅ {feature.replace('_', ' ').title()}\n"
                elif isinstance(limit, int):
                    message += f"📊 {feature.replace('_', ' ').title()}: {limit}\n"
            
            keyboard = []
            if status['tier'] == 'free':
                keyboard.append([InlineKeyboardButton("⭐ Upgrade to Pro", callback_data="upgrade_pro")])
            elif status['tier'] == 'pro':
                keyboard.append([InlineKeyboardButton("👑 Upgrade to Enterprise", callback_data="upgrade_enterprise")])
            
            keyboard.append([InlineKeyboardButton("◀️ Back", callback_data="premium")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"❌ Subscription status error: {e}")

    # Add handler for demo upgrades
    async def handle_demo_upgrade(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle demo upgrade (for testing)"""
        try:
            callback_data = update.callback_query.data
            user_id = update.effective_user.id
            
            if 'pro_monthly' in callback_data:
                tier = SubscriptionTier.PRO
                duration = 'monthly'
            elif 'pro_yearly' in callback_data:
                tier = SubscriptionTier.PRO
                duration = 'yearly'
            elif 'enterprise' in callback_data:
                tier = SubscriptionTier.ENTERPRISE
                duration = 'monthly'
            else:
                return
            
            # Simulate upgrade
            result = await self.subscription_service.upgrade_subscription(user_id, tier, duration)
            
            if result['success']:
                message = f"🎉 **UPGRADE SUCCESSFUL!** (Demo Mode)\n\n"
                message += f"✅ Welcome to {tier.value.title()}!\n"
                message += f"💰 Amount: ${result['amount_paid']:.2f}\n"
                message += f"📅 Valid until: {result['end_date'].strftime('%Y-%m-%d')}\n\n"
                message += "🚀 **Premium features now unlocked!**\n"
                message += "Try creating smart alerts and using the dashboard."
                
                keyboard = [
                    [InlineKeyboardButton("📊 Open Dashboard", callback_data="main_dashboard")],
                    [InlineKeyboardButton("🔔 Create Smart Alert", callback_data="smart_alerts")]
                ]
            else:
                message = f"❌ **Upgrade Failed:** {result['error']}"
                keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="premium")]]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"❌ Demo upgrade error: {e}")

    # Register demo upgrade handlers
    def register_demo_handlers(self):
        """Register demo upgrade handlers"""
        demo_handlers = [
            ('demo_upgrade_pro_monthly', self.handle_demo_upgrade),
            ('demo_upgrade_pro_yearly', self.handle_demo_upgrade),
            ('demo_upgrade_enterprise_monthly', self.handle_demo_upgrade),
        ]
        
        for callback_data, handler in demo_handlers:
            self.application.add_handler(CallbackQueryHandler(handler, pattern=f"^{callback_data}$"))

    async def handle_refresh_market(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle market refresh request"""
        await self.handle_market_overview(update, context)

    async def handle_ai_insights(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle AI insights request"""
        try:
            user_id = update.effective_user.id
            subscription = self.subscription_service.get_user_subscription(user_id)
            
            if subscription.tier == SubscriptionTier.FREE:
                message = "🤖 **AI INSIGHTS** (Premium Feature)\n\n"
                message += "Unlock AI-powered market insights:\n\n"
                message += "🎯 **Smart Analysis**\n"
                message += "• AI-driven market predictions\n"
                message += "• Sentiment analysis\n"
                message += "• Risk assessment\n\n"
                message += "📊 **Custom Reports**\n"
                message += "• Personalized recommendations\n"
                message += "• Portfolio optimization\n"
                message += "• Trading strategies\n\n"
                message += "💡 **Available in Pro & Enterprise plans**"
                
                keyboard = [
                    [InlineKeyboardButton("🚀 Try Free Trial", callback_data="free_trial")],
                    [InlineKeyboardButton("⭐ Upgrade to Pro", callback_data="upgrade_pro")],
                    [InlineKeyboardButton("◀️ Back", callback_data="main_dashboard")]
                ]
            else:
                # Generate actual AI insights for premium users
                message = "🤖 **AI MARKET INSIGHTS**\n\n"
                message += "📈 **Current Analysis:**\n"
                message += "• Market sentiment: Cautiously optimistic\n"
                message += "• Volatility level: Moderate\n"
                message += "• Recommended action: Hold/Buy selective\n\n"
                message += "🎯 **Top Opportunities:**\n"
                message += "• Tech stocks showing recovery\n"
                message += "• Gold maintaining support\n"
                message += "• Crypto stabilizing\n\n"
                message += "⚠️ **Risk Factors:**\n"
                message += "• Market uncertainty\n"
                message += "• Economic indicators mixed\n"
                message += "*This is demo AI analysis*"
                
                keyboard = [
                    [InlineKeyboardButton("📊 Detailed Report", callback_data="detailed_ai_report")],
                    [InlineKeyboardButton("🔄 Refresh", callback_data="ai_insights")],
                    [InlineKeyboardButton("◀️ Back", callback_data="main_dashboard")]
                ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"❌ AI insights error: {e}")

# Register demo handlers when module is imported
def register_premium_handlers(application):
    """Register all premium handlers with the application"""
    premium_handlers = PremiumHandlers(application)
    premium_handlers.register_demo_handlers()
    return premium_handlers 