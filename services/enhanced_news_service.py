"""
Enhanced News Service - Phiên bản nâng cấp toàn diện
- Nhiều nguồn tin tức quốc tế và Việt Nam
- Scraping hiện đại với retry mechanism
- Better error handling và logging
- User agent rotation
- Fallback methods
"""

import aiohttp
import asyncio
import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from config import Config
from models.article import Article
import hashlib
from bs4 import BeautifulSoup
import re
import logging
from urllib.parse import urljoin, urlparse
import feedparser
import time
import json

logger = logging.getLogger(__name__)

class EnhancedNewsService:
    def __init__(self):
        self.config = Config()
        
        # Multiple user agents to avoid blocking
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0'
        ]
        
        # International authoritative news sources focusing on economy, politics, and technology
        self.news_sources = {
            # Core International Economic & Political Sources (Priority 1)
            'reuters': {
                'name': 'Reuters',
                'rss_urls': [
                    'https://feeds.reuters.com/reuters/businessNews',  # Economics focus
                    'https://feeds.reuters.com/reuters/worldNews',    # International politics
                    'https://feeds.reuters.com/reuters/topNews',
                    'https://feeds.reuters.com/reuters/politicsNews'
                ],
                'priority': 1
            },
            'ap_news': {
                'name': 'Associated Press',
                'rss_urls': [
                    'https://feeds.apnews.com/rss/apf-businessnews',  # Economics focus
                    'https://feeds.apnews.com/rss/apf-worldnews',     # International politics
                    'https://feeds.apnews.com/rss/apf-politicsnews',
                    'https://feeds.apnews.com/rss/apf-topnews'
                ],
                'priority': 1
            },
            'bbc': {
                'name': 'BBC News',
                'rss_urls': [
                    'https://feeds.bbci.co.uk/news/business/rss.xml',  # Economics focus
                    'https://feeds.bbci.co.uk/news/world/rss.xml',     # International
                    'https://feeds.bbci.co.uk/news/politics/rss.xml',
                    'https://feeds.bbci.co.uk/news/rss.xml'
                ],
                'priority': 1
            },
            'guardian': {
                'name': 'The Guardian',
                'rss_urls': [
                    'https://www.theguardian.com/business/rss',        # Economics focus
                    'https://www.theguardian.com/world/rss',           # International
                    'https://www.theguardian.com/politics/rss',
                    'https://www.theguardian.com/us-news/rss'          # US politics (Trump)
                ],
                'priority': 1
            },
            
            # Secondary International Sources (Priority 2)
            'cnn': {
                'name': 'CNN',
                'rss_urls': [
                    'http://rss.cnn.com/rss/money_latest.rss',         # Economics
                    'http://rss.cnn.com/rss/edition_world.rss',        # International
                    'http://rss.cnn.com/rss/edition.rss'
                ],
                'priority': 2
            },
            'nikkei': {
                'name': 'Nikkei Asia',
                'rss_urls': [
                    'https://asia.nikkei.com/rss/feed/nar-business',   # Asian economics
                    'https://asia.nikkei.com/rss/feed/nar',
                    'https://asia.nikkei.com/rss/feed/nar-politics'
                ],
                'priority': 2
            },
            'scmp': {
                'name': 'South China Morning Post',
                'rss_urls': [
                    'https://www.scmp.com/rss/2/feed',                 # Business
                    'https://www.scmp.com/rss/4/feed',                 # China politics/economy
                    'https://www.scmp.com/rss/92/feed'                 # World
                ],
                'priority': 2
            },
            
            # Financial & Tech Sources (Priority 3) 
            'bloomberg': {
                'name': 'Bloomberg',
                'rss_urls': [
                    'https://feeds.bloomberg.com/markets/news.rss',
                    'https://feeds.bloomberg.com/politics/news.rss',
                    'https://feeds.bloomberg.com/economics/news.rss'
                ],
                'priority': 3
            },
            'wsj': {
                'name': 'Wall Street Journal',
                'rss_urls': [
                    'https://feeds.a.dj.com/rss/RSSWorldNews.xml',
                    'https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml'
                ],
                'priority': 3
            }
        }
        
        # Cache to avoid duplicate fetching
        self.cache = {}
        self.cache_duration = 300  # 5 minutes
        
        # User agent for web requests
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Economics & International Politics focused keywords
        self.relevance_keywords = [
            # Core political figures
            "Trump", "Biden", "Xi Jinping", "Putin", "Zelensky",
            
            # Countries & International relations
            "US", "USA", "America", "China", "Europe", "NATO", "UN", "G7", "G20",
            "international", "global", "world", "diplomatic", "foreign policy",
            
            # Economics & Trade
            "economy", "economic", "trade", "tariffs", "sanctions", "inflation", 
            "recession", "growth", "GDP", "stock market", "investment", "business",
            "supply chain", "commodities", "oil prices", "currency", "dollar", 
            "euro", "yuan", "interest rates", "central bank", "Fed", "ECB",
            
            # Government & Politics  
            "government", "politics", "policy", "election", "congress", "parliament",
            "legislation", "regulation", "budget", "deficit", "debt ceiling",
            
            # Corporate & Markets
            "corporate", "merger", "acquisition", "earnings", "IPO", "stocks",
            "bonds", "commodities", "forex", "crypto", "blockchain"
        ]
        
        self.appeal_keywords = [
            "breaking", "exclusive", "urgent", "major", "crisis", "emergency",
            "unprecedented", "historic", "dramatic", "surge", "crash", "collapse",
            "breakthrough", "deal", "agreement", "summit", "announcement"
        ]
    
    def get_random_headers(self) -> Dict[str, str]:
        """Get random headers to avoid blocking"""
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
    
    async def fetch_enhanced_news(self, limit: int = 20) -> List[Dict]:
        """Fetch news from multiple enhanced sources with priority ordering"""
        try:
            logger.info("🔍 Fetching enhanced news from multiple authoritative sources...")
            
            all_articles = []
            
            # Fetch from sources based on priority (International only)
            priority_1_sources = {k: v for k, v in self.news_sources.items() if v['priority'] == 1}
            priority_2_sources = {k: v for k, v in self.news_sources.items() if v['priority'] == 2}
            priority_3_sources = {k: v for k, v in self.news_sources.items() if v['priority'] == 3}
            
            # Fetch priority 1 sources first (Core International Economics & Politics)
            core_articles = await self._fetch_from_sources(priority_1_sources, limit // 2)
            all_articles.extend(core_articles)
            
            # Fetch priority 2 sources (Secondary International)
            secondary_articles = await self._fetch_from_sources(priority_2_sources, limit // 3)
            all_articles.extend(secondary_articles)
            
            # Fetch priority 3 sources (Financial/Specialized)
            financial_articles = await self._fetch_from_sources(priority_3_sources, limit // 6)
            all_articles.extend(financial_articles)
            
            # Remove duplicates and sort by recency
            unique_articles = self._remove_duplicates(all_articles)
            sorted_articles = self._sort_by_recency(unique_articles)
            
            logger.info(f"✅ Fetched {len(sorted_articles)} unique articles from enhanced sources")
            return sorted_articles[:limit]
            
        except Exception as e:
            logger.error(f"❌ Error fetching enhanced news: {e}")
            return []

    async def _fetch_from_sources(self, sources: Dict, limit: int) -> List[Dict]:
        """Fetch articles from a set of sources concurrently"""
        tasks = []
        
        for source_id, source_config in sources.items():
            for rss_url in source_config['rss_urls']:
                cache_key = f"{source_id}_{rss_url}"
                
                # Check cache first
                if cache_key in self.cache:
                    cached_time, cached_data = self.cache[cache_key]
                    if time.time() - cached_time < self.cache_duration:
                        continue
                
                task = self._fetch_from_rss(source_id, source_config['name'], rss_url)
                tasks.append(task)
        
        # Execute tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        articles = []
        for result in results:
            if isinstance(result, list):
                articles.extend(result)
        
        return articles[:limit] if articles else []

    async def _fetch_from_rss(self, source_id: str, source_name: str, rss_url: str) -> List[Dict]:
        """Fetch articles from a single RSS feed with enhanced error handling"""
        max_retries = 2
        
        for attempt in range(max_retries):
            try:
                cache_key = f"{source_id}_{rss_url}"
                
                # Check cache first
                if cache_key in self.cache:
                    cache_time, cached_articles = self.cache[cache_key]
                    if time.time() - cache_time < self.cache_duration:
                        return cached_articles
                
                # Add delay to avoid overwhelming servers
                await asyncio.sleep(random.uniform(0.2, 0.8))
                
                timeout = aiohttp.ClientTimeout(total=15)  # Increased timeout
                headers = self.get_random_headers()
                
                async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                    async with session.get(rss_url) as response:
                        if response.status == 200:
                            content = await response.text()
                            
                            # Parse RSS feed
                            feed = feedparser.parse(content)
                            
                            if not feed.entries:
                                logger.debug(f"⚠️ No entries in RSS feed: {source_name}")
                                return []
                                
                            articles = []
                            
                            for entry in feed.entries[:10]:  # Limit per RSS feed
                                try:
                                    title = self._clean_text(entry.get('title', ''))
                                    description = self._clean_text(entry.get('description', entry.get('summary', '')))
                                    
                                    # Skip if title is too short or contains spam indicators
                                    if len(title) < 10 or any(spam in title.lower() for spam in ['advertisement', 'sponsored']):
                                        continue
                                    
                                    article = {
                                        'title': title,
                                        'link': entry.get('link', ''),
                                        'description': description,
                                        'content': description,  # Use description as content for performance
                                        'published': self._parse_date(entry.get('published', entry.get('pubDate', ''))),
                                        'source': source_name,
                                        'source_id': source_id,
                                        'category': self._detect_category(title + ' ' + description),
                                        'fetch_time': datetime.now()
                                    }
                                    
                                    articles.append(article)
                                    
                                except Exception as e:
                                    logger.debug(f"Error parsing article from {source_name}: {e}")
                                    continue
                            
                            # Cache results
                            self.cache[cache_key] = (time.time(), articles)
                            
                            if articles:
                                logger.info(f"✅ {source_name}: {len(articles)} articles")
                            else:
                                logger.debug(f"⚠️ No valid articles from {source_name}")
                            return articles
                        
                        elif response.status == 404:
                            logger.debug(f"⚠️ RSS feed not found (404): {source_name}")
                            return []
                        elif response.status >= 500 and attempt < max_retries - 1:
                            logger.debug(f"⚠️ Server error {response.status} for {source_name}, retrying...")
                            await asyncio.sleep(2)
                            continue
                        else:
                            logger.debug(f"⚠️ HTTP {response.status} for {source_name}")
                            return []
                            
            except asyncio.TimeoutError:
                if attempt < max_retries - 1:
                    logger.debug(f"⚠️ Timeout for {source_name}, retrying...")
                    await asyncio.sleep(1)
                    continue
                else:
                    logger.debug(f"⚠️ Timeout for {source_name}")
                    return []
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.debug(f"⚠️ Error fetching from {source_name}, retrying: {e}")
                    await asyncio.sleep(1)
                    continue
                else:
                    logger.debug(f"⚠️ Error fetching from {source_name}: {e}")
                    return []
                    
        return []

    async def _extract_full_content(self, url: str) -> Optional[str]:
        """Extract full article content from URL"""
        try:
            timeout = aiohttp.ClientTimeout(total=8)
            async with aiohttp.ClientSession(timeout=timeout, headers=self.headers) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Remove script and style elements
                        for script in soup(["script", "style"]):
                            script.decompose()
                        
                        # Try common article selectors
                        content_selectors = [
                            'article', '.article-content', '.post-content', '.entry-content',
                            '.content', '.article-body', '.story-body', 'main', '.main-content'
                        ]
                        
                        for selector in content_selectors:
                            content_div = soup.select_one(selector)
                            if content_div:
                                text = content_div.get_text(strip=True)
                                if len(text) > 200:  # Ensure substantial content
                                    return self._clean_text(text)
                        
                        # Fallback: get all paragraph text
                        paragraphs = soup.find_all('p')
                        if paragraphs:
                            text = ' '.join([p.get_text(strip=True) for p in paragraphs])
                            return self._clean_text(text) if len(text) > 100 else None
                            
        except Exception as e:
            logger.debug(f"Could not extract content from {url}: {e}")
            return None

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        if not text:
            return ""
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove common unwanted patterns
        text = re.sub(r'Read more.*$', '', text, flags=re.IGNORECASE)
        text = re.sub(r'Continue reading.*$', '', text, flags=re.IGNORECASE)
        
        return text

    def _parse_date(self, date_str: str) -> datetime:
        """Parse various date formats"""
        if not date_str:
            return datetime.now()
        
        try:
            # Try feedparser's built-in parsing first
            parsed = feedparser._parse_date(date_str)
            if parsed:
                return datetime(*parsed[:6])
        except:
            pass
        
        # Fallback to current time
        return datetime.now()

    def _detect_category(self, text: str) -> str:
        """Detect article category based on content"""
        text_lower = text.lower()
        
        categories = {
            'technology': ['ai', 'artificial intelligence', 'tech', 'digital', 'startup', 'innovation', 'computer'],
            'business': ['business', 'economy', 'market', 'finance', 'trade', 'company', 'investment'],
            'politics': ['politics', 'government', 'election', 'policy', 'president', 'minister'],
            'health': ['health', 'medical', 'medicine', 'doctor', 'hospital', 'disease'],
            'environment': ['climate', 'environment', 'green', 'energy', 'pollution', 'sustainability'],
            'sports': ['sports', 'football', 'soccer', 'olympics', 'game', 'match', 'tournament'],
            'world': ['world', 'international', 'global', 'country', 'nation', 'war', 'conflict']
        }
        
        for category, keywords in categories.items():
            if any(keyword in text_lower for keyword in keywords):
                return category
        
        return 'general'

    def _remove_duplicates(self, articles: List[Dict]) -> List[Dict]:
        """Remove duplicate articles based on title similarity"""
        if not articles:
            return []
        
        unique_articles = []
        seen_titles = set()
        
        for article in articles:
            title = article.get('title', '').lower().strip()
            
            # Create a simplified version for comparison
            title_words = set(re.findall(r'\w+', title))
            
            # Check for substantial overlap with existing titles
            is_duplicate = False
            for seen_title in seen_titles:
                seen_words = set(re.findall(r'\w+', seen_title))
                
                if title_words and seen_words:
                    overlap = len(title_words & seen_words)
                    similarity = overlap / max(len(title_words), len(seen_words))
                    
                    if similarity > 0.7:  # 70% similarity threshold
                        is_duplicate = True
                        break
            
            if not is_duplicate and title:
                unique_articles.append(article)
                seen_titles.add(title)
        
        return unique_articles

    def _sort_by_recency(self, articles: List[Dict]) -> List[Dict]:
        """Sort articles by recency and relevance"""
        try:
            return sorted(articles, key=lambda x: x.get('published', datetime.min), reverse=True)
        except Exception as e:
            logger.warning(f"Error sorting articles: {e}")
            return articles

    async def fetch_news_with_keywords(self, keywords: List[str], limit: int = 10) -> List[Dict]:
        """Fetch news articles filtered by keywords"""
        try:
            logger.info(f"🔍 Searching for news with keywords: {keywords}")
            
            # First get regular news
            all_articles = await self.fetch_enhanced_news(limit * 3)  # Get more for filtering
            
            # Filter by keywords
            filtered_articles = []
            keywords_lower = [kw.lower() for kw in keywords]
            
            for article in all_articles:
                text_to_search = f"{article.get('title', '')} {article.get('description', '')} {article.get('content', '')}".lower()
                
                # Check if any keyword matches
                if any(keyword in text_to_search for keyword in keywords_lower):
                    # Calculate relevance score
                    score = sum(text_to_search.count(keyword) for keyword in keywords_lower)
                    article['relevance_score'] = score
                    filtered_articles.append(article)
            
            # Sort by relevance score
            filtered_articles.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
            
            logger.info(f"✅ Found {len(filtered_articles)} articles matching keywords")
            return filtered_articles[:limit]
            
        except Exception as e:
            logger.error(f"❌ Error searching news with keywords: {e}")
            return []

    def get_source_stats(self) -> Dict:
        """Get statistics about news sources"""
        total_sources = len(self.news_sources)
        core_sources = len([s for s in self.news_sources.values() if s['priority'] == 1])
        secondary_sources = len([s for s in self.news_sources.values() if s['priority'] == 2])
        financial_sources = len([s for s in self.news_sources.values() if s['priority'] == 3])
        
        return {
            'total_sources': total_sources,
            'core_international_sources': core_sources,
            'secondary_international_sources': secondary_sources,
            'financial_specialized_sources': financial_sources,
            'total_rss_feeds': sum(len(source['rss_urls']) for source in self.news_sources.values())
        } 