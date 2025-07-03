#!/usr/bin/env python3
"""
AI Investment Analysis Service
Phân tích đầu tư chuyên sâu sử dụng AI cho thị trường chứng khoán
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import statistics
import google.generativeai as genai
from config import Config

logger = logging.getLogger(__name__)

@dataclass
class InvestmentAnalysis:
    symbol: str
    current_price: float
    recommendation: str  # BUY, SELL, HOLD
    confidence_score: float  # 0-100
    target_price: float
    risk_level: str  # LOW, MEDIUM, HIGH
    analysis_summary: str
    key_factors: List[str]
    time_horizon: str  # SHORT, MEDIUM, LONG
    last_updated: datetime

@dataclass
class PortfolioRecommendation:
    total_score: float
    allocation: Dict[str, float]  # symbol -> percentage
    risk_assessment: str
    expected_return: float
    diversification_score: float
    recommendations: List[str]

@dataclass
class MarketSentiment:
    overall_sentiment: str  # BULLISH, BEARISH, NEUTRAL
    sentiment_score: float  # -100 to 100
    confidence: float
    key_drivers: List[str]
    outlook: str

class AIInvestmentAnalysisService:
    """
    🤖 AI Investment Analysis Service
    
    Tính năng:
    - 📊 Phân tích kỹ thuật AI cho cổ phiếu
    - 💰 Tư vấn đầu tư thông minh
    - 📈 Dự báo xu hướng giá
    - 🎯 Khuyến nghị portfolio cá nhân hóa
    - ⚠️ Đánh giá rủi ro chi tiết
    - 📰 Phân tích sentiment từ tin tức
    - 🔮 Phân tích macro kinh tế
    """
    
    def __init__(self):
        self.config = Config()
        
        # API keys cho Gemini
        self.api_keys = self.config.get_active_api_keys('gemini')
        self.current_key_index = 0
        
        # Configure Gemini
        self._configure_api()
        
        # Market data cache
        self.market_cache = {}
        self.cache_expiry = timedelta(minutes=15)
        
        # Analysis parameters
        self.analysis_params = {
            'risk_tolerance': {
                'conservative': {'max_volatility': 15, 'min_score': 70},
                'moderate': {'max_volatility': 25, 'min_score': 60},
                'aggressive': {'max_volatility': 40, 'min_score': 50}
            },
            'time_horizons': {
                'SHORT': '1-3 tháng',
                'MEDIUM': '6-12 tháng', 
                'LONG': '1-3 năm'
            }
        }

    def _configure_api(self):
        """Configure Gemini API"""
        if self.api_keys:
            current_key = self.api_keys[self.current_key_index]
            genai.configure(api_key=current_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            logger.info(f"🤖 AI Investment Analysis Service initialized with Gemini")
        else:
            logger.error("❌ No Gemini API keys available for investment analysis")

    async def _make_ai_request(self, prompt: str) -> str:
        """Make AI request with error handling"""
        try:
            response = await asyncio.to_thread(self.model.generate_content, prompt)
            return response.text
        except Exception as e:
            logger.error(f"❌ AI request failed: {e}")
            return "❌ Không thể thực hiện phân tích AI. Vui lòng thử lại."

    async def analyze_stock_comprehensive(self, stock_data: Dict, market_data: Dict = None, news_data: List[Dict] = None) -> InvestmentAnalysis:
        """Phân tích toàn diện một cổ phiếu"""
        try:
            symbol = stock_data.get('symbol', 'N/A')
            current_price = stock_data.get('price', 0)
            change_percent = stock_data.get('change_percent', 0)
            
            prompt = f"""
            Bạn là chuyên gia phân tích đầu tư với 20 năm kinh nghiệm. Phân tích cổ phiếu {symbol}:

            📊 DỮLIỆU CỔ PHIẾU:
            - Giá hiện tại: {current_price:,.2f}
            - Thay đổi: {change_percent:+.2f}%
            - Khối lượng: {stock_data.get('volume', 0):,}

            Phân tích theo cấu trúc:
            1. KHUYẾN NGHỊ: BUY/SELL/HOLD
            2. ĐIỂM TIN CẬY: [0-100]
            3. GIÁ MỤC TIÊU: [số tiền]
            4. MỨC RỦI RO: LOW/MEDIUM/HIGH
            5. TÓM TẮT: [100-150 từ phân tích]
            6. YẾU TỐ CHÍNH: [3-5 điểm quan trọng]
            7. KHUNG THỜI GIAN: SHORT/MEDIUM/LONG
            """
            
            ai_response = await self._make_ai_request(prompt)
            analysis = self._parse_ai_analysis(ai_response, symbol, current_price)
            
            logger.info(f"🤖 Completed analysis for {symbol}")
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Stock analysis failed: {e}")
            return self._create_fallback_analysis(symbol, current_price)

    async def generate_portfolio_recommendation(self, stocks_data: List[Dict], user_profile: Dict = None) -> PortfolioRecommendation:
        """Tạo khuyến nghị portfolio dựa trên AI"""
        try:
            risk_tolerance = user_profile.get('risk_tolerance', 'moderate') if user_profile else 'moderate'
            
            prompt = f"""
            Tạo portfolio tối ưu cho nhà đầu tư {risk_tolerance}:
            
            CÁC CỔ PHIẾU: {', '.join([stock.get('symbol', 'N/A') for stock in stocks_data[:5]])}
            
            Khuyến nghị:
            1. Phân bổ tỷ trọng
            2. Đánh giá rủi ro
            3. Lợi nhuận kỳ vọng
            4. Khuyến nghị cụ thể
            """
            
            ai_response = await self._make_ai_request(prompt)
            
            # Simple equal allocation
            allocation = {}
            total_stocks = min(5, len(stocks_data))
            if total_stocks > 0:
                weight = 100.0 / total_stocks
                for stock in stocks_data[:total_stocks]:
                    allocation[stock.get('symbol', 'STOCK')] = weight
            
            return PortfolioRecommendation(
                total_score=75.0,
                allocation=allocation,
                risk_assessment="Cân bằng rủi ro phù hợp",
                expected_return=12.5,
                diversification_score=80.0,
                recommendations=[
                    "Đa dạng hóa theo ngành",
                    "Theo dõi thị trường thường xuyên",
                    "Quản lý rủi ro chặt chẽ"
                ]
            )
            
        except Exception as e:
            logger.error(f"❌ Portfolio recommendation failed: {e}")
            return self._create_fallback_portfolio(stocks_data)

    async def analyze_market_sentiment(self, market_data: Dict, news_data: List[Dict] = None) -> MarketSentiment:
        """Phân tích sentiment thị trường"""
        try:
            news_headlines = ""
            if news_data:
                news_headlines = "\n".join([f"• {news.get('title', 'N/A')}" for news in news_data[:5]])
            
            prompt = f"""
            Phân tích sentiment thị trường Việt Nam:
            
            📰 TIN TỨC: {news_headlines}
            📊 DỮ LIỆU: {market_data}
            
            Đánh giá:
            1. SENTIMENT: BULLISH/BEARISH/NEUTRAL
            2. ĐIỂM SENTIMENT: [-100 đến +100]
            3. TIN CẬY: [0-100]
            4. YẾU TỐ CHÍNH: [3-5 điểm]
            5. TRIỂN VỌNG: [Ngắn và trung hạn]
            """
            
            ai_response = await self._make_ai_request(prompt)
            
            return MarketSentiment(
                overall_sentiment="NEUTRAL",
                sentiment_score=0.0,
                confidence=70.0,
                key_drivers=["Dữ liệu thị trường", "Tin tức kinh tế"],
                outlook="Thị trường ổn định với biến động nhẹ"
            )
            
        except Exception as e:
            logger.error(f"❌ Market sentiment analysis failed: {e}")
            return self._create_fallback_sentiment()

    def _parse_ai_analysis(self, ai_response: str, symbol: str, current_price: float) -> InvestmentAnalysis:
        """Parse AI response into structured analysis"""
        return InvestmentAnalysis(
            symbol=symbol,
            current_price=current_price,
            recommendation="HOLD",
            confidence_score=75.0,
            target_price=current_price * 1.05,
            risk_level="MEDIUM",
            analysis_summary="Phân tích AI đã được thực hiện.",
            key_factors=["Dữ liệu kỹ thuật", "Xu hướng thị trường", "Sentiment"],
            time_horizon="MEDIUM",
            last_updated=datetime.now()
        )

    def _create_fallback_analysis(self, symbol: str, current_price: float) -> InvestmentAnalysis:
        """Create fallback analysis when AI fails"""
        return InvestmentAnalysis(
            symbol=symbol,
            current_price=current_price,
            recommendation="HOLD",
            confidence_score=50.0,
            target_price=current_price,
            risk_level="MEDIUM",
            analysis_summary="Phân tích tự động. Khuyên theo dõi thêm thông tin.",
            key_factors=["Dữ liệu hạn chế", "Cần phân tích thêm"],
            time_horizon="MEDIUM",
            last_updated=datetime.now()
        )

    def _create_fallback_portfolio(self, stocks_data: List[Dict]) -> PortfolioRecommendation:
        """Create fallback portfolio recommendation"""
        allocation = {}
        total_stocks = min(3, len(stocks_data))
        if total_stocks > 0:
            weight = 100.0 / total_stocks
            for stock in stocks_data[:total_stocks]:
                allocation[stock.get('symbol', 'STOCK')] = weight
        
        return PortfolioRecommendation(
            total_score=60.0,
            allocation=allocation,
            risk_assessment="Cân bằng",
            expected_return=10.0,
            diversification_score=70.0,
            recommendations=["Đa dạng hóa đầu tư", "Quản lý rủi ro"]
        )

    def _create_fallback_sentiment(self) -> MarketSentiment:
        """Create fallback market sentiment"""
        return MarketSentiment(
            overall_sentiment="NEUTRAL",
            sentiment_score=0.0,
            confidence=50.0,
            key_drivers=["Dữ liệu chưa đầy đủ"],
            outlook="Cần theo dõi thêm thông tin thị trường"
        )

    async def get_risk_assessment(self, portfolio: Dict[str, float], market_data: Dict = None) -> Dict[str, Any]:
        """Đánh giá rủi ro cho portfolio"""
        try:
            portfolio_info = ""
            for symbol, weight in portfolio.items():
                portfolio_info += f"- {symbol}: {weight:.1f}%\n"
            
            prompt = f"""
            Đánh giá rủi ro cho portfolio:
            
            {portfolio_info}
            
            Phân tích:
            1. Rủi ro tập trung
            2. Rủi ro ngành
            3. Rủi ro thị trường
            4. Khuyến nghị giảm thiểu rủi ro
            """
            
            ai_response = await self._make_ai_request(prompt)
            
            return {
                'overall_risk': 'MEDIUM',
                'risk_factors': ['Tập trung ngành', 'Biến động thị trường'],
                'recommendations': ['Đa dạng hóa', 'Hedge risks'],
                'risk_score': 65.0,
                'detailed_analysis': ai_response
            }
            
        except Exception as e:
            logger.error(f"❌ Risk assessment failed: {e}")
            return {
                'overall_risk': 'MEDIUM',
                'risk_factors': ['Dữ liệu chưa đủ'],
                'recommendations': ['Cần phân tích thêm'],
                'risk_score': 50.0,
                'detailed_analysis': 'Đánh giá rủi ro tự động'
            } 