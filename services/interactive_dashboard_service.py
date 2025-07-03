#!/usr/bin/env python3
"""
Interactive Telegram Dashboard Service
High-impact feature that can be implemented immediately
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
import asyncio

logger = logging.getLogger(__name__)

class InteractiveDashboardService:
    """
    📊 INTERACTIVE TELEGRAM DASHBOARD
    
    Features có thể làm ngay:
    - 📈 Real-time market buttons
    - 🔔 Quick price alerts setup
    - 📊 Portfolio quick view
    - ⚙️ Settings panel
    - 🎯 Smart recommendations
    """
    
    def __init__(self, market_service, ai_service):
        self.market_service = market_service
        self.ai_service = ai_service
        
        # User preferences storage (simple dict, can upgrade to DB later)
        self.user_preferences = {}
        self.user_watchlists = {}
        self.price_alerts = {}

    def create_main_dashboard(self, user_id: int) -> InlineKeyboardMarkup:
        """Create main dashboard with interactive buttons"""
        keyboard = [
            [
                InlineKeyboardButton("📈 Market Overview", callback_data="market_overview"),
                InlineKeyboardButton("💰 My Portfolio", callback_data="portfolio")
            ],
            [
                InlineKeyboardButton("🔔 Price Alerts", callback_data="price_alerts"),
                InlineKeyboardButton("📰 News Feed", callback_data="news_feed")
            ],
            [
                InlineKeyboardButton("🎯 AI Insights", callback_data="ai_insights"),
                InlineKeyboardButton("⚙️ Settings", callback_data="settings")
            ],
            [
                InlineKeyboardButton("🚀 Premium Features", callback_data="premium"),
                InlineKeyboardButton("❓ Help", callback_data="help")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    def create_market_overview_buttons(self) -> InlineKeyboardMarkup:
        """Market overview với quick actions"""
        keyboard = [
            [
                InlineKeyboardButton("📊 VN Stocks", callback_data="vn_stocks"),
                InlineKeyboardButton("🌍 Global Stocks", callback_data="global_stocks")
            ],
            [
                InlineKeyboardButton("💰 Crypto", callback_data="crypto_prices"),
                InlineKeyboardButton("🥇 Gold/Metals", callback_data="metals_prices")
            ],
            [
                InlineKeyboardButton("📈 Top Gainers", callback_data="top_gainers"),
                InlineKeyboardButton("📉 Top Losers", callback_data="top_losers")
            ],
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="refresh_market"),
                InlineKeyboardButton("◀️ Back", callback_data="main_dashboard")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    def create_price_alerts_buttons(self, user_id: int) -> InlineKeyboardMarkup:
        """Price alerts management"""
        user_alerts = self.price_alerts.get(user_id, [])
        
        keyboard = [
            [
                InlineKeyboardButton("➕ Add Alert", callback_data="add_alert"),
                InlineKeyboardButton("📋 My Alerts", callback_data="view_alerts")
            ]
        ]
        
        # Show active alerts
        if user_alerts:
            keyboard.append([
                InlineKeyboardButton(f"🔔 {len(user_alerts)} Active Alerts", callback_data="manage_alerts")
            ])
        
        keyboard.extend([
            [
                InlineKeyboardButton("🎯 Smart Alerts", callback_data="smart_alerts"),
                InlineKeyboardButton("⚙️ Alert Settings", callback_data="alert_settings")
            ],
            [
                InlineKeyboardButton("◀️ Back", callback_data="main_dashboard")
            ]
        ])
        
        return InlineKeyboardMarkup(keyboard)

    def create_portfolio_buttons(self, user_id: int) -> InlineKeyboardMarkup:
        """Portfolio management dashboard"""
        keyboard = [
            [
                InlineKeyboardButton("➕ Add Stock", callback_data="add_to_portfolio"),
                InlineKeyboardButton("📊 Performance", callback_data="portfolio_performance")
            ],
            [
                InlineKeyboardButton("📈 P&L Today", callback_data="daily_pnl"),
                InlineKeyboardButton("📅 Monthly Report", callback_data="monthly_report")
            ],
            [
                InlineKeyboardButton("🎯 Rebalance", callback_data="rebalance_portfolio"),
                InlineKeyboardButton("💡 AI Suggestions", callback_data="ai_portfolio_tips")
            ],
            [
                InlineKeyboardButton("◀️ Back", callback_data="main_dashboard")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    def create_premium_features_buttons(self) -> InlineKeyboardMarkup:
        """Premium features showcase"""
        keyboard = [
            [
                InlineKeyboardButton("🤖 AI Trading Assistant", callback_data="ai_trading"),
                InlineKeyboardButton("📊 Advanced Analytics", callback_data="advanced_analytics")
            ],
            [
                InlineKeyboardButton("🔮 Price Predictions", callback_data="price_predictions"),
                InlineKeyboardButton("📱 Multi-Platform Publishing", callback_data="multi_platform")
            ],
            [
                InlineKeyboardButton("💳 Upgrade to Pro ($19/month)", callback_data="upgrade_pro"),
                InlineKeyboardButton("👑 Enterprise ($99/month)", callback_data="upgrade_enterprise")
            ],
            [
                InlineKeyboardButton("🆓 Try Premium Free", callback_data="free_trial"),
                InlineKeyboardButton("◀️ Back", callback_data="main_dashboard")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    async def handle_market_overview(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle market overview request"""
        try:
            # Fetch real market data
            market_data = await self.market_service.get_comprehensive_market_data()
            
            # Format message with current data
            message = "📊 **MARKET OVERVIEW**\n\n"
            
            # Global stocks
            global_stocks = market_data.get('global_stocks', [])
            if global_stocks:
                message += "🌍 **Global Stocks:**\n"
                for stock in global_stocks[:3]:
                    trend = "📈" if stock.change_percent > 0 else "📉"
                    message += f"{trend} {stock.symbol}: ${stock.price:.2f} ({stock.change_percent:+.2f}%)\n"
                message += "\n"
            
            # Crypto data
            crypto_data = market_data.get('cryptocurrencies', [])
            if crypto_data:
                message += "💰 **Cryptocurrencies:**\n"
                for crypto in crypto_data[:3]:
                    trend = "🚀" if crypto['change_percent_24h'] > 0 else "📉"
                    message += f"{trend} {crypto['symbol']}: ${crypto['price']:.2f} ({crypto['change_percent_24h']:+.2f}%)\n"
                message += "\n"
            
            # Gold price
            gold_data = market_data.get('gold_data')
            if gold_data:
                trend = "📈" if gold_data.change_percent > 0 else "📉"
                message += f"🥇 **Gold:** ${gold_data.price_usd:.2f} {trend} ({gold_data.change_percent:+.2f}%)\n\n"
            
            message += f"⏰ Updated: {datetime.now().strftime('%H:%M:%S')}"
            
            # Send with interactive buttons
            keyboard = self.create_market_overview_buttons()
            
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    message, 
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    message, 
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"❌ Market overview error: {e}")
            error_msg = "❌ Có lỗi khi tải dữ liệu thị trường. Vui lòng thử lại."
            
            if update.callback_query:
                await update.callback_query.edit_message_text(error_msg)
            else:
                await update.message.reply_text(error_msg)

    async def handle_price_alerts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle price alerts management"""
        user_id = update.effective_user.id
        user_alerts = self.price_alerts.get(user_id, [])
        
        message = "🔔 **PRICE ALERTS**\n\n"
        
        if user_alerts:
            message += f"📋 You have {len(user_alerts)} active alerts:\n\n"
            for i, alert in enumerate(user_alerts[:5], 1):
                status = "🟢" if alert['active'] else "🔴"
                message += f"{status} {i}. {alert['symbol']} {alert['condition']} ${alert['price']:.2f}\n"
        else:
            message += "📭 No active alerts. Create your first alert below!\n\n"
            message += "💡 **Tips:**\n"
            message += "• Set alerts for your favorite stocks\n"
            message += "• Get notified when prices hit your targets\n"
            message += "• Perfect for buying opportunities\n"
        
        keyboard = self.create_price_alerts_buttons(user_id)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                message, 
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                message, 
                reply_markup=keyboard,
                parse_mode='Markdown'
            )

    async def handle_portfolio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle portfolio view"""
        user_id = update.effective_user.id
        
        # Dummy portfolio data (can be replaced with real data)
        portfolio = self.user_watchlists.get(user_id, {
            'stocks': [
                {'symbol': 'AAPL', 'shares': 10, 'avg_price': 180.00},
                {'symbol': 'GOOGL', 'shares': 5, 'avg_price': 140.00},
                {'symbol': 'VIC', 'shares': 100, 'avg_price': 45000}
            ],
            'total_value': 5000,
            'daily_change': 2.5
        })
        
        message = "💰 **MY PORTFOLIO**\n\n"
        
        if portfolio['stocks']:
            total_value = portfolio['total_value']
            daily_change = portfolio['daily_change']
            change_symbol = "📈" if daily_change > 0 else "📉"
            
            message += f"💼 **Total Value:** ${total_value:,.2f}\n"
            message += f"{change_symbol} **Today:** {daily_change:+.2f}%\n\n"
            
            message += "📊 **Holdings:**\n"
            for stock in portfolio['stocks'][:5]:
                message += f"• {stock['symbol']}: {stock['shares']} shares @ ${stock['avg_price']:.2f}\n"
        else:
            message += "📭 Portfolio is empty. Add your first stock!\n\n"
            message += "💡 **Get Started:**\n"
            message += "• Track your investments\n"
            message += "• Monitor performance\n"
            message += "• Get AI recommendations\n"
        
        keyboard = self.create_portfolio_buttons(user_id)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                message, 
                reply_markup=keyboard,
                parse_mode='Markdown'
            )

    async def handle_premium_showcase(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show premium features"""
        message = "🚀 **PREMIUM FEATURES**\n\n"
        message += "Unlock the full power of AI News Bot:\n\n"
        
        message += "🤖 **AI Trading Assistant**\n"
        message += "• Personal AI mentor for trading\n"
        message += "• Smart buy/sell recommendations\n"
        message += "• Risk management advice\n\n"
        
        message += "📊 **Advanced Analytics**\n"
        message += "• Portfolio performance tracking\n"
        message += "• Custom reports & insights\n"
        message += "• Market sentiment analysis\n\n"
        
        message += "🔮 **AI Price Predictions**\n"
        message += "• Machine learning forecasts\n"
        message += "• Technical analysis automation\n"
        message += "• Market trend predictions\n\n"
        
        message += "💰 **Pricing:**\n"
        message += "• **Pro:** $19/month - All AI features\n"
        message += "• **Enterprise:** $99/month - Team features\n"
        message += "• **7-day free trial** available!\n"
        
        keyboard = self.create_premium_features_buttons()
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                message, 
                reply_markup=keyboard,
                parse_mode='Markdown'
            )

    def add_price_alert(self, user_id: int, symbol: str, price: float, condition: str = "above"):
        """Add a price alert for user"""
        if user_id not in self.price_alerts:
            self.price_alerts[user_id] = []
        
        alert = {
            'symbol': symbol,
            'price': price,
            'condition': condition,
            'active': True,
            'created_at': datetime.now()
        }
        
        self.price_alerts[user_id].append(alert)
        logger.info(f"📊 Added price alert for user {user_id}: {symbol} {condition} {price}")

    def add_to_watchlist(self, user_id: int, symbol: str, shares: int = 0, avg_price: float = 0):
        """Add stock to user watchlist/portfolio"""
        if user_id not in self.user_watchlists:
            self.user_watchlists[user_id] = {'stocks': [], 'total_value': 0, 'daily_change': 0}
        
        stock = {
            'symbol': symbol,
            'shares': shares,
            'avg_price': avg_price,
            'added_at': datetime.now()
        }
        
        self.user_watchlists[user_id]['stocks'].append(stock)
        logger.info(f"📊 Added {symbol} to watchlist for user {user_id}")

    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Get user statistics for dashboard"""
        alerts_count = len(self.price_alerts.get(user_id, []))
        portfolio_count = len(self.user_watchlists.get(user_id, {}).get('stocks', []))
        
        return {
            'alerts_count': alerts_count,
            'portfolio_count': portfolio_count,
            'is_premium': False,  # Can be upgraded with real subscription logic
            'join_date': datetime.now(),  # Can be real join date
            'total_interactions': 0  # Can track real interactions
        } 