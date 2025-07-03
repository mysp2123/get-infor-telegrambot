#!/usr/bin/env python3
"""
Premium Subscription Service
Immediate monetization with high-value features
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json

logger = logging.getLogger(__name__)

class SubscriptionTier(Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"

@dataclass
class Subscription:
    user_id: int
    tier: SubscriptionTier
    start_date: datetime
    end_date: datetime
    is_active: bool = True
    trial_used: bool = False
    auto_renew: bool = True
    payment_method: Optional[str] = None

class PremiumSubscriptionService:
    """
    💰 PREMIUM SUBSCRIPTION SYSTEM
    
    Monetization strategy với value ngay:
    
    FREE TIER:
    - 5 price alerts
    - Basic market data
    - Daily news summary
    - Community features
    
    PRO TIER ($19/month):
    - 50 price alerts
    - AI trading insights
    - Advanced analytics
    - Priority support
    - Multi-platform publishing
    - Portfolio optimization
    
    ENTERPRISE ($99/month):
    - Unlimited alerts
    - Custom AI models  
    - Team collaboration
    - API access
    - White-label options
    - Dedicated support
    """
    
    def __init__(self, telegram_bot):
        self.telegram_bot = telegram_bot
        
        # Subscription storage
        self.subscriptions: Dict[int, Subscription] = {}
        self.payment_history: Dict[int, List[Dict]] = {}
        
        # Feature limits by tier
        self.tier_limits = {
            SubscriptionTier.FREE: {
                'alerts': 5,
                'portfolio_stocks': 10,
                'ai_requests_daily': 10,
                'news_categories': 3,
                'export_data': False,
                'priority_support': False,
                'multi_platform': False,
                'advanced_analytics': False
            },
            SubscriptionTier.PRO: {
                'alerts': 50,
                'portfolio_stocks': 100,
                'ai_requests_daily': 100,
                'news_categories': 'unlimited',
                'export_data': True,
                'priority_support': True,
                'multi_platform': True,
                'advanced_analytics': True
            },
            SubscriptionTier.ENTERPRISE: {
                'alerts': 'unlimited',
                'portfolio_stocks': 'unlimited',
                'ai_requests_daily': 'unlimited',
                'news_categories': 'unlimited',
                'export_data': True,
                'priority_support': True,
                'multi_platform': True,
                'advanced_analytics': True,
                'custom_ai': True,
                'api_access': True,
                'team_features': True
            }
        }
        
        # Pricing
        self.pricing = {
            SubscriptionTier.PRO: {
                'monthly': 19.00,
                'yearly': 190.00,  # 2 months free
                'currency': 'USD'
            },
            SubscriptionTier.ENTERPRISE: {
                'monthly': 99.00,
                'yearly': 990.00,  # 2 months free
                'currency': 'USD'
            }
        }

    def get_user_subscription(self, user_id: int) -> Subscription:
        """Get user's current subscription"""
        if user_id not in self.subscriptions:
            # Create free tier subscription
            self.subscriptions[user_id] = Subscription(
                user_id=user_id,
                tier=SubscriptionTier.FREE,
                start_date=datetime.now(),
                end_date=datetime.now() + timedelta(days=365*10),  # Free tier never expires
                is_active=True
            )
        
        subscription = self.subscriptions[user_id]
        
        # Check if subscription expired
        if subscription.end_date < datetime.now() and subscription.tier != SubscriptionTier.FREE:
            subscription.is_active = False
            # Downgrade to free
            subscription.tier = SubscriptionTier.FREE
            logger.info(f"💳 User {user_id} subscription expired, downgraded to FREE")
        
        return subscription

    def get_tier_features(self, tier: SubscriptionTier) -> Dict[str, Any]:
        """Get features available for a tier"""
        return self.tier_limits.get(tier, self.tier_limits[SubscriptionTier.FREE])

    def can_use_feature(self, user_id: int, feature: str, current_usage: int = 0) -> Dict[str, Any]:
        """Check if user can use a feature"""
        subscription = self.get_user_subscription(user_id)
        tier_limits = self.get_tier_features(subscription.tier)
        
        feature_limit = tier_limits.get(feature)
        
        if feature_limit is True or feature_limit == 'unlimited':
            return {'allowed': True, 'remaining': 'unlimited'}
        elif feature_limit is False:
            return {'allowed': False, 'reason': 'Not available in your plan', 'upgrade_required': True}
        elif isinstance(feature_limit, int):
            remaining = feature_limit - current_usage
            return {
                'allowed': remaining > 0,
                'remaining': remaining,
                'limit': feature_limit,
                'upgrade_required': remaining <= 0
            }
        
        return {'allowed': False, 'reason': 'Feature not found'}

    async def start_free_trial(self, user_id: int) -> Dict[str, Any]:
        """Start 7-day free trial for Pro features"""
        subscription = self.get_user_subscription(user_id)
        
        if subscription.trial_used:
            return {
                'success': False,
                'error': 'Free trial already used. Upgrade to Pro to continue using premium features.'
            }
        
        if subscription.tier != SubscriptionTier.FREE:
            return {
                'success': False,
                'error': 'You already have a premium subscription!'
            }
        
        # Start trial
        trial_subscription = Subscription(
            user_id=user_id,
            tier=SubscriptionTier.PRO,
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=7),
            is_active=True,
            trial_used=True
        )
        
        self.subscriptions[user_id] = trial_subscription
        
        # Send welcome message
        await self._send_trial_welcome_message(user_id)
        
        logger.info(f"🆓 Started free trial for user {user_id}")
        
        return {
            'success': True,
            'message': '🎉 7-day Pro trial activated!',
            'trial_end': trial_subscription.end_date,
            'features_unlocked': list(self.tier_limits[SubscriptionTier.PRO].keys())
        }

    async def upgrade_subscription(self, user_id: int, tier: SubscriptionTier, duration: str = 'monthly') -> Dict[str, Any]:
        """Upgrade user subscription"""
        try:
            current_subscription = self.get_user_subscription(user_id)
            
            if tier == SubscriptionTier.FREE:
                return {'success': False, 'error': 'Cannot upgrade to free tier'}
            
            # Calculate end date
            if duration == 'monthly':
                end_date = datetime.now() + timedelta(days=30)
                price = self.pricing[tier]['monthly']
            elif duration == 'yearly':
                end_date = datetime.now() + timedelta(days=365)
                price = self.pricing[tier]['yearly']
            else:
                return {'success': False, 'error': 'Invalid duration'}
            
            # Create new subscription
            new_subscription = Subscription(
                user_id=user_id,
                tier=tier,
                start_date=datetime.now(),
                end_date=end_date,
                is_active=True,
                trial_used=current_subscription.trial_used
            )
            
            self.subscriptions[user_id] = new_subscription
            
            # Record payment (mock - integrate with real payment processor)
            await self._record_payment(user_id, tier, duration, price)
            
            # Send confirmation
            await self._send_upgrade_confirmation(user_id, tier, end_date, price)
            
            logger.info(f"⭐ User {user_id} upgraded to {tier.value} ({duration})")
            
            return {
                'success': True,
                'message': f'🎉 Upgraded to {tier.value.title()}!',
                'tier': tier.value,
                'end_date': end_date,
                'amount_paid': price
            }
            
        except Exception as e:
            logger.error(f"❌ Error upgrading subscription: {e}")
            return {'success': False, 'error': 'Failed to process upgrade'}

    def get_subscription_status(self, user_id: int) -> Dict[str, Any]:
        """Get detailed subscription status"""
        subscription = self.get_user_subscription(user_id)
        
        return {
            'tier': subscription.tier.value,
            'is_active': subscription.is_active,
            'start_date': subscription.start_date,
            'end_date': subscription.end_date,
            'days_remaining': (subscription.end_date - datetime.now()).days if subscription.is_active else 0,
            'trial_used': subscription.trial_used,
            'auto_renew': subscription.auto_renew,
            'features': self.get_tier_features(subscription.tier),
            'next_billing': subscription.end_date if subscription.is_active and subscription.tier != SubscriptionTier.FREE else None
        }

    def get_upgrade_options(self, user_id: int) -> List[Dict[str, Any]]:
        """Get available upgrade options for user"""
        current_subscription = self.get_user_subscription(user_id)
        options = []
        
        if current_subscription.tier == SubscriptionTier.FREE:
            if not current_subscription.trial_used:
                options.append({
                    'type': 'trial',
                    'title': '🆓 7-Day Pro Trial',
                    'description': 'Try all Pro features free for 7 days',
                    'price': 0,
                    'features': ['50 price alerts', 'AI insights', 'Advanced analytics', 'Multi-platform publishing'],
                    'cta': 'Start Free Trial'
                })
            
            options.extend([
                {
                    'type': 'subscription',
                    'tier': 'pro',
                    'title': '⭐ Pro Monthly',
                    'description': 'Perfect for active traders',
                    'price': self.pricing[SubscriptionTier.PRO]['monthly'],
                    'duration': 'monthly',
                    'features': ['50 price alerts', 'AI trading insights', 'Portfolio optimization', 'Priority support'],
                    'cta': 'Upgrade to Pro'
                },
                {
                    'type': 'subscription',
                    'tier': 'pro',
                    'title': '⭐ Pro Yearly',
                    'description': '2 months FREE!',
                    'price': self.pricing[SubscriptionTier.PRO]['yearly'],
                    'duration': 'yearly',
                    'savings': self.pricing[SubscriptionTier.PRO]['monthly'] * 2,
                    'features': ['All Pro features', 'Best value', '2 months free'],
                    'cta': 'Get Pro Yearly',
                    'popular': True
                },
                {
                    'type': 'subscription',
                    'tier': 'enterprise',
                    'title': '👑 Enterprise',
                    'description': 'For teams and power users',
                    'price': self.pricing[SubscriptionTier.ENTERPRISE]['monthly'],
                    'duration': 'monthly',
                    'features': ['Unlimited everything', 'Team features', 'API access', 'Custom AI'],
                    'cta': 'Go Enterprise'
                }
            ])
        
        elif current_subscription.tier == SubscriptionTier.PRO:
            options.append({
                'type': 'subscription',
                'tier': 'enterprise',
                'title': '👑 Upgrade to Enterprise',
                'description': 'Unlock unlimited power',
                'price': self.pricing[SubscriptionTier.ENTERPRISE]['monthly'],
                'duration': 'monthly',
                'features': ['Unlimited alerts', 'Team collaboration', 'API access', 'Custom AI models'],
                'cta': 'Upgrade to Enterprise'
            })
        
        return options

    async def generate_premium_showcase_message(self, user_id: int) -> str:
        """Generate personalized premium showcase message"""
        subscription = self.get_user_subscription(user_id)
        
        if subscription.tier == SubscriptionTier.FREE:
            message = "🚀 **UNLOCK PREMIUM FEATURES**\n\n"
            message += "Transform your trading with AI-powered insights:\n\n"
            
            message += "🎯 **What you're missing:**\n"
            message += "• 45 more price alerts (currently 5/5 used)\n"
            message += "• AI trading recommendations\n"
            message += "• Advanced portfolio analytics\n"
            message += "• Multi-platform publishing\n"
            message += "• Priority support\n\n"
            
            if not subscription.trial_used:
                message += "🆓 **7-DAY FREE TRIAL AVAILABLE**\n"
                message += "Try all Pro features risk-free!\n\n"
            
            message += "💰 **Pricing:**\n"
            message += f"• Pro: ${self.pricing[SubscriptionTier.PRO]['monthly']}/month\n"
            message += f"• Pro Yearly: ${self.pricing[SubscriptionTier.PRO]['yearly']}/year (2 months FREE!)\n"
            message += f"• Enterprise: ${self.pricing[SubscriptionTier.ENTERPRISE]['monthly']}/month\n\n"
            
            message += "⚡ **Join 10,000+ premium users** making smarter trades!"
            
        elif subscription.tier == SubscriptionTier.PRO:
            days_remaining = (subscription.end_date - datetime.now()).days
            message = f"⭐ **PRO MEMBER** ({days_remaining} days left)\n\n"
            message += "🎉 You're using premium features! Consider:\n\n"
            message += "👑 **Enterprise Upgrade:**\n"
            message += "• Unlimited everything\n"
            message += "• Team collaboration tools\n"
            message += "• Custom AI models\n"
            message += "• API access for automation\n"
            message += f"• Only ${self.pricing[SubscriptionTier.ENTERPRISE]['monthly']}/month\n"
            
        else:  # Enterprise
            message = "👑 **ENTERPRISE MEMBER**\n\n"
            message += "🔥 You have access to all premium features!\n\n"
            message += "💡 **Pro Tips:**\n"
            message += "• Use API access for automated trading\n"
            message += "• Set up team collaboration\n"
            message += "• Customize AI models for your strategy\n"
            message += "• Contact support for advanced features\n"
        
        return message

    async def _send_trial_welcome_message(self, user_id: int):
        """Send welcome message for trial users"""
        message = "🎉 **WELCOME TO PRO TRIAL!**\n\n"
        message += "Your 7-day Pro trial is now active!\n\n"
        message += "🚀 **Unlocked Features:**\n"
        message += "• 50 price alerts (vs 5 free)\n"
        message += "• AI trading insights\n"
        message += "• Advanced portfolio analytics\n"
        message += "• Multi-platform publishing\n"
        message += "• Priority support\n\n"
        message += "💡 **Get Started:**\n"
        message += "• Set up smart price alerts\n"
        message += "• Try AI portfolio optimization\n"
        message += "• Explore advanced analytics\n\n"
        message += "⏰ **Trial ends in 7 days**\n"
        message += "We'll remind you before it expires!"
        
        try:
            await self.telegram_bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"❌ Error sending trial welcome: {e}")

    async def _send_upgrade_confirmation(self, user_id: int, tier: SubscriptionTier, end_date: datetime, amount: float):
        """Send upgrade confirmation message"""
        message = f"✅ **UPGRADE SUCCESSFUL!**\n\n"
        message += f"🎉 Welcome to {tier.value.title()}!\n\n"
        message += f"💳 **Payment:** ${amount:.2f}\n"
        message += f"📅 **Valid until:** {end_date.strftime('%Y-%m-%d')}\n\n"
        message += "🚀 **Your Premium Features:**\n"
        
        features = self.get_tier_features(tier)
        for feature, value in features.items():
            if value is True or value == 'unlimited':
                message += f"✅ {feature.replace('_', ' ').title()}\n"
        
        message += "\n🎯 **Start using your premium features now!**"
        
        try:
            await self.telegram_bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"❌ Error sending upgrade confirmation: {e}")

    async def _record_payment(self, user_id: int, tier: SubscriptionTier, duration: str, amount: float):
        """Record payment in history"""
        if user_id not in self.payment_history:
            self.payment_history[user_id] = []
        
        payment_record = {
            'date': datetime.now(),
            'tier': tier.value,
            'duration': duration,
            'amount': amount,
            'currency': 'USD',
            'status': 'completed',
            'transaction_id': f"txn_{user_id}_{int(datetime.now().timestamp())}"
        }
        
        self.payment_history[user_id].append(payment_record)
        logger.info(f"💳 Recorded payment for user {user_id}: ${amount} for {tier.value} {duration}")

    def get_payment_history(self, user_id: int) -> List[Dict[str, Any]]:
        """Get user's payment history"""
        return self.payment_history.get(user_id, [])

    def get_subscription_analytics(self) -> Dict[str, Any]:
        """Get subscription analytics for admin"""
        total_users = len(self.subscriptions)
        free_users = sum(1 for s in self.subscriptions.values() if s.tier == SubscriptionTier.FREE)
        pro_users = sum(1 for s in self.subscriptions.values() if s.tier == SubscriptionTier.PRO and s.is_active)
        enterprise_users = sum(1 for s in self.subscriptions.values() if s.tier == SubscriptionTier.ENTERPRISE and s.is_active)
        
        # Calculate MRR (Monthly Recurring Revenue)
        mrr = (pro_users * self.pricing[SubscriptionTier.PRO]['monthly'] + 
               enterprise_users * self.pricing[SubscriptionTier.ENTERPRISE]['monthly'])
        
        return {
            'total_users': total_users,
            'free_users': free_users,
            'pro_users': pro_users,
            'enterprise_users': enterprise_users,
            'conversion_rate': ((pro_users + enterprise_users) / max(total_users, 1)) * 100,
            'monthly_recurring_revenue': mrr,
            'annual_recurring_revenue': mrr * 12
        } 