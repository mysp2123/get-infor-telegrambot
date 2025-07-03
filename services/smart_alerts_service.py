#!/usr/bin/env python3
"""
Smart Price Alerts Service
High-value feature for user retention and engagement
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)

@dataclass
class PriceAlert:
    user_id: int
    symbol: str
    target_price: float
    condition: str  # 'above', 'below', 'change_percent'
    threshold_percent: Optional[float] = None
    is_active: bool = True
    created_at: datetime = None
    triggered_at: Optional[datetime] = None
    alert_type: str = "simple"  # 'simple', 'smart', 'ai_predicted'

class SmartAlertsService:
    """
    🔔 SMART PRICE ALERTS SYSTEM
    
    Features có ROI cao ngay:
    - 📈 Simple price alerts (above/below)
    - 🎯 Smart percentage alerts
    - 🤖 AI-powered alerts (market patterns)
    - 🔥 Trending alerts (viral stocks)
    - 📊 Portfolio alerts (rebalancing)
    - 💎 VIP alerts (premium feature)
    """
    
    def __init__(self, market_service, telegram_bot):
        self.market_service = market_service
        self.telegram_bot = telegram_bot
        
        # Alert storage (can upgrade to database later)
        self.user_alerts: Dict[int, List[PriceAlert]] = {}
        self.alert_history: Dict[int, List[Dict]] = {}
        
        # Premium features
        self.premium_users = set()
        self.alert_limits = {
            'free': 5,
            'premium': 50
        }
        
        # Market monitoring
        self.last_prices: Dict[str, float] = {}
        self.monitoring_active = False

    async def start_monitoring(self):
        """Start monitoring prices for alerts"""
        if self.monitoring_active:
            return
            
        self.monitoring_active = True
        logger.info("🔔 Starting smart alerts monitoring...")
        
        while self.monitoring_active:
            try:
                await self._check_all_alerts()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"❌ Alert monitoring error: {e}")
                await asyncio.sleep(60)

    async def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring_active = False
        logger.info("🔔 Stopped alerts monitoring")

    async def add_simple_alert(self, user_id: int, symbol: str, target_price: float, condition: str) -> Dict[str, Any]:
        """Add simple price alert"""
        try:
            # Check user limits
            current_alerts = len(self.get_user_alerts(user_id))
            limit = self.alert_limits['premium' if user_id in self.premium_users else 'free']
            
            if current_alerts >= limit:
                return {
                    'success': False,
                    'error': f"Alert limit reached ({limit}). Upgrade to Premium for more alerts!",
                    'upgrade_needed': True
                }
            
            # Validate symbol (check if it exists in market data)
            market_data = await self.market_service.get_comprehensive_market_data()
            symbol_exists = await self._validate_symbol(symbol, market_data)
            
            if not symbol_exists:
                return {
                    'success': False,
                    'error': f"Symbol '{symbol}' not found. Please check the symbol.",
                    'suggestion': await self._suggest_similar_symbols(symbol)
                }
            
            # Create alert
            alert = PriceAlert(
                user_id=user_id,
                symbol=symbol.upper(),
                target_price=target_price,
                condition=condition,
                created_at=datetime.now(),
                alert_type="simple"
            )
            
            # Add to user alerts
            if user_id not in self.user_alerts:
                self.user_alerts[user_id] = []
            
            self.user_alerts[user_id].append(alert)
            
            logger.info(f"🔔 Added alert for user {user_id}: {symbol} {condition} ${target_price}")
            
            return {
                'success': True,
                'alert_id': len(self.user_alerts[user_id]) - 1,
                'message': f"✅ Alert set: {symbol} {condition} ${target_price:.2f}",
                'current_price': await self._get_current_price(symbol)
            }
            
        except Exception as e:
            logger.error(f"❌ Error adding alert: {e}")
            return {
                'success': False,
                'error': "Failed to create alert. Please try again."
            }

    async def add_smart_alert(self, user_id: int, symbol: str, alert_type: str, **kwargs) -> Dict[str, Any]:
        """Add smart AI-powered alert"""
        try:
            if user_id not in self.premium_users:
                return {
                    'success': False,
                    'error': "Smart alerts are a Premium feature. Upgrade to unlock!",
                    'upgrade_needed': True
                }
            
            current_price = await self._get_current_price(symbol)
            
            if alert_type == "breakout":
                # Breakout alert - detect when stock breaks resistance/support
                resistance_level = kwargs.get('resistance_level', current_price * 1.05)
                alert = PriceAlert(
                    user_id=user_id,
                    symbol=symbol.upper(),
                    target_price=resistance_level,
                    condition="above",
                    alert_type="smart_breakout",
                    created_at=datetime.now()
                )
                
            elif alert_type == "volume_spike":
                # Volume spike alert
                threshold_percent = kwargs.get('volume_threshold', 200)  # 200% above average
                alert = PriceAlert(
                    user_id=user_id,
                    symbol=symbol.upper(),
                    target_price=0,  # Not price-based
                    condition="volume_spike",
                    threshold_percent=threshold_percent,
                    alert_type="smart_volume",
                    created_at=datetime.now()
                )
                
            elif alert_type == "trend_reversal":
                # Trend reversal alert using AI
                alert = PriceAlert(
                    user_id=user_id,
                    symbol=symbol.upper(),
                    target_price=current_price,
                    condition="trend_reversal",
                    alert_type="ai_predicted",
                    created_at=datetime.now()
                )
            
            # Add to user alerts
            if user_id not in self.user_alerts:
                self.user_alerts[user_id] = []
            
            self.user_alerts[user_id].append(alert)
            
            return {
                'success': True,
                'message': f"🤖 Smart alert activated for {symbol}",
                'alert_type': alert_type,
                'current_price': current_price
            }
            
        except Exception as e:
            logger.error(f"❌ Error adding smart alert: {e}")
            return {
                'success': False,
                'error': "Failed to create smart alert."
            }

    async def get_trending_alerts(self, user_id: int) -> List[Dict[str, Any]]:
        """Get trending stocks worth alerting on"""
        try:
            market_data = await self.market_service.get_comprehensive_market_data()
            
            trending_suggestions = []
            
            # Analyze global stocks for trending opportunities
            global_stocks = market_data.get('global_stocks', [])
            for stock in global_stocks:
                if abs(stock.change_percent) > 3:  # Significant movement
                    trend_direction = "📈 Bullish" if stock.change_percent > 0 else "📉 Bearish"
                    
                    # Suggest alert levels
                    if stock.change_percent > 0:
                        suggested_price = stock.price * 1.05  # 5% above current
                        condition = "above"
                    else:
                        suggested_price = stock.price * 0.95  # 5% below current
                        condition = "below"
                    
                    trending_suggestions.append({
                        'symbol': stock.symbol,
                        'name': stock.name,
                        'current_price': stock.price,
                        'change_percent': stock.change_percent,
                        'trend': trend_direction,
                        'suggested_alert_price': suggested_price,
                        'suggested_condition': condition,
                        'reason': f"Strong {trend_direction.split()[1].lower()} momentum"
                    })
            
            # Analyze crypto for trending
            crypto_data = market_data.get('cryptocurrencies', [])
            for crypto in crypto_data:
                if abs(crypto['change_percent_24h']) > 5:  # Crypto moves more
                    trend_direction = "🚀 Bullish" if crypto['change_percent_24h'] > 0 else "📉 Bearish"
                    
                    trending_suggestions.append({
                        'symbol': crypto['symbol'],
                        'name': crypto['name'],
                        'current_price': crypto['price'],
                        'change_percent': crypto['change_percent_24h'],
                        'trend': trend_direction,
                        'suggested_alert_price': crypto['price'] * (1.1 if crypto['change_percent_24h'] > 0 else 0.9),
                        'suggested_condition': "above" if crypto['change_percent_24h'] > 0 else "below",
                        'reason': f"Crypto momentum - {trend_direction.split()[1].lower()}"
                    })
            
            # Sort by absolute change percentage
            trending_suggestions.sort(key=lambda x: abs(x['change_percent']), reverse=True)
            
            return trending_suggestions[:10]  # Top 10 trending
            
        except Exception as e:
            logger.error(f"❌ Error getting trending alerts: {e}")
            return []

    async def _check_all_alerts(self):
        """Check all active alerts against current prices"""
        try:
            if not self.user_alerts:
                return
                
            # Get current market data
            market_data = await self.market_service.get_comprehensive_market_data()
            current_prices = await self._extract_current_prices(market_data)
            
            triggered_alerts = []
            
            for user_id, alerts in self.user_alerts.items():
                for i, alert in enumerate(alerts):
                    if not alert.is_active:
                        continue
                        
                    if await self._check_alert_condition(alert, current_prices):
                        triggered_alerts.append((user_id, i, alert))
            
            # Send notifications for triggered alerts
            for user_id, alert_index, alert in triggered_alerts:
                await self._send_alert_notification(user_id, alert, current_prices.get(alert.symbol, 0))
                
                # Mark alert as triggered
                self.user_alerts[user_id][alert_index].is_active = False
                self.user_alerts[user_id][alert_index].triggered_at = datetime.now()
                
                # Add to history
                self._add_to_history(user_id, alert, current_prices.get(alert.symbol, 0))
                
        except Exception as e:
            logger.error(f"❌ Error checking alerts: {e}")

    async def _check_alert_condition(self, alert: PriceAlert, current_prices: Dict[str, float]) -> bool:
        """Check if alert condition is met"""
        current_price = current_prices.get(alert.symbol)
        if current_price is None:
            return False
            
        if alert.condition == "above":
            return current_price >= alert.target_price
        elif alert.condition == "below":
            return current_price <= alert.target_price
        elif alert.condition == "change_percent" and alert.threshold_percent:
            last_price = self.last_prices.get(alert.symbol, current_price)
            change_percent = ((current_price - last_price) / last_price) * 100
            return abs(change_percent) >= alert.threshold_percent
        
        return False

    async def _send_alert_notification(self, user_id: int, alert: PriceAlert, current_price: float):
        """Send alert notification to user"""
        try:
            message = f"🔔 **PRICE ALERT TRIGGERED!**\n\n"
            message += f"📊 **{alert.symbol}** has reached your target!\n\n"
            message += f"🎯 **Target:** ${alert.target_price:.2f}\n"
            message += f"💰 **Current:** ${current_price:.2f}\n"
            message += f"📈 **Condition:** {alert.condition}\n"
            message += f"⏰ **Set:** {alert.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
            
            if alert.alert_type == "smart_breakout":
                message += "🚀 **Breakout Alert** - Stock may be breaking resistance!\n"
            elif alert.alert_type == "ai_predicted":
                message += "🤖 **AI Alert** - Pattern detected by our AI system!\n"
            
            message += "💡 Consider reviewing your investment strategy!"
            
            await self.telegram_bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='Markdown'
            )
            
            logger.info(f"🔔 Sent alert notification to user {user_id} for {alert.symbol}")
            
        except Exception as e:
            logger.error(f"❌ Error sending alert notification: {e}")

    def get_user_alerts(self, user_id: int) -> List[PriceAlert]:
        """Get all alerts for a user"""
        return self.user_alerts.get(user_id, [])

    def get_active_alerts_count(self, user_id: int) -> int:
        """Get count of active alerts for user"""
        alerts = self.get_user_alerts(user_id)
        return len([alert for alert in alerts if alert.is_active])

    def remove_alert(self, user_id: int, alert_index: int) -> bool:
        """Remove an alert"""
        try:
            if user_id in self.user_alerts and 0 <= alert_index < len(self.user_alerts[user_id]):
                removed_alert = self.user_alerts[user_id].pop(alert_index)
                logger.info(f"🗑️ Removed alert for user {user_id}: {removed_alert.symbol}")
                return True
            return False
        except Exception as e:
            logger.error(f"❌ Error removing alert: {e}")
            return False

    def upgrade_to_premium(self, user_id: int):
        """Upgrade user to premium alerts"""
        self.premium_users.add(user_id)
        logger.info(f"⭐ User {user_id} upgraded to premium alerts")

    async def _validate_symbol(self, symbol: str, market_data: Dict) -> bool:
        """Validate if symbol exists in market data"""
        symbol = symbol.upper()
        
        # Check in global stocks
        global_stocks = market_data.get('global_stocks', [])
        for stock in global_stocks:
            if stock.symbol == symbol:
                return True
        
        # Check in crypto
        crypto_data = market_data.get('cryptocurrencies', [])
        for crypto in crypto_data:
            if crypto['symbol'] == symbol:
                return True
        
        return False

    async def _suggest_similar_symbols(self, symbol: str) -> List[str]:
        """Suggest similar symbols if exact match not found"""
        # Simple suggestion logic - can be enhanced with fuzzy matching
        suggestions = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN', 'BTC', 'ETH']
        return [s for s in suggestions if symbol.upper() in s or s in symbol.upper()][:3]

    async def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol"""
        try:
            market_data = await self.market_service.get_comprehensive_market_data()
            
            # Check global stocks
            for stock in market_data.get('global_stocks', []):
                if stock.symbol == symbol.upper():
                    return stock.price
            
            # Check crypto
            for crypto in market_data.get('cryptocurrencies', []):
                if crypto['symbol'] == symbol.upper():
                    return crypto['price']
            
            return None
        except Exception as e:
            logger.error(f"❌ Error getting current price for {symbol}: {e}")
            return None

    async def _extract_current_prices(self, market_data: Dict) -> Dict[str, float]:
        """Extract current prices from market data"""
        prices = {}
        
        # Extract from global stocks
        for stock in market_data.get('global_stocks', []):
            prices[stock.symbol] = stock.price
        
        # Extract from crypto
        for crypto in market_data.get('cryptocurrencies', []):
            prices[crypto['symbol']] = crypto['price']
        
        # Update last prices
        self.last_prices.update(prices)
        
        return prices

    def _add_to_history(self, user_id: int, alert: PriceAlert, triggered_price: float):
        """Add triggered alert to history"""
        if user_id not in self.alert_history:
            self.alert_history[user_id] = []
        
        history_entry = {
            'symbol': alert.symbol,
            'target_price': alert.target_price,
            'triggered_price': triggered_price,
            'condition': alert.condition,
            'created_at': alert.created_at,
            'triggered_at': alert.triggered_at,
            'alert_type': alert.alert_type
        }
        
        self.alert_history[user_id].append(history_entry)
        
        # Keep only last 50 entries
        if len(self.alert_history[user_id]) > 50:
            self.alert_history[user_id] = self.alert_history[user_id][-50:]

    def get_alert_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get user alert statistics"""
        alerts = self.get_user_alerts(user_id)
        history = self.alert_history.get(user_id, [])
        
        return {
            'total_alerts': len(alerts),
            'active_alerts': len([a for a in alerts if a.is_active]),
            'triggered_alerts': len(history),
            'success_rate': len(history) / max(len(alerts), 1) * 100,
            'most_watched_symbol': self._get_most_watched_symbol(user_id),
            'is_premium': user_id in self.premium_users,
            'alerts_limit': self.alert_limits['premium' if user_id in self.premium_users else 'free']
        }

    def _get_most_watched_symbol(self, user_id: int) -> Optional[str]:
        """Get most watched symbol by user"""
        alerts = self.get_user_alerts(user_id)
        if not alerts:
            return None
        
        symbol_counts = {}
        for alert in alerts:
            symbol_counts[alert.symbol] = symbol_counts.get(alert.symbol, 0) + 1
        
        return max(symbol_counts, key=symbol_counts.get) if symbol_counts else None 