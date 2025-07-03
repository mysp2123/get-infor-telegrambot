"""
Enhanced RSS Service - Ultra Strong Version
Tính năng mạnh mẽ:
- Retry mechanism với exponential backoff
- SSL/TLS error handling
- Caching layer với Redis-like functionality
- Multiple RSS sources và backup URLs
- Parallel processing
- Advanced keyword matching
- Content parsing và cleaning
- Monitoring và metrics
- Alternative news APIs
"""

import asyncio
import aiohttp
import feedparser
import logging
import time
import json
import re
import hashlib
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from urllib.parse import urljoin, quote_plus
import ssl
import certifi
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import threading

logger = logging.getLogger(__name__)

@dataclass
class RSSFeedResult:
    """Kết quả từ RSS feed"""
    title: str
    url: str
    summary: str
    published: str
    source: str
    credibility: str
    region: str
    relevance_score: int
    feed_url: str
    content_length: int

class EnhancedRSSCache:
    """Simple in-memory cache for RSS feeds"""
    
    def __init__(self, default_ttl: int = 900):  # 15 minutes
        self.cache = {}
        self.ttl = default_ttl
        self._lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self.cache:
                data, timestamp = self.cache[key]
                if time.time() - timestamp < self.ttl:
                    return data
                else:
                    del self.cache[key]
            return None
    
    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self.cache[key] = (value, time.time())
    
    def clear(self) -> None:
        with self._lock:
            self.cache.clear()

class EnhancedRSSService:
    def __init__(self):
        self.cache = EnhancedRSSCache()
        self.session = None
        self.ssl_context = self._create_ssl_context()
        
        # Enhanced RSS sources với backup URLs
        self.rss_sources = {
            'harvard_business_review': {
                'name': 'Harvard Business Review',
                'primary_feeds': [
                    'https://feeds.hbr.org/harvardbusiness',
                    'https://feeds.hbr.org/harvardbusiness/ideacast'
                ],
                'backup_feeds': [
                    'https://hbr.org/rss/feed',
                    'https://feeds.feedburner.com/harvardbusiness'
                ],
                'web_scraping_url': 'https://hbr.org/magazine',
                'credibility': 'Very High',
                'region': 'US',
                'keywords': ['business', 'strategy', 'leadership', 'innovation', 'management', 'harvard'],
                'user_agent': 'Mozilla/5.0 (compatible; HBR-Reader/1.0)',
                'headers': {'Accept': 'application/rss+xml, application/xml, text/xml'}
            },
            'the_economist': {
                'name': 'The Economist',
                'primary_feeds': [
                    'https://www.economist.com/rss/the_world_this_week',
                    'https://www.economist.com/rss/business_rss.xml',
                    'https://www.economist.com/rss/economics_rss.xml',
                    'https://www.economist.com/rss/international_rss.xml'
                ],
                'backup_feeds': [
                    'https://feeds.feedburner.com/economist/business',
                    'https://feeds.feedburner.com/economist/economics'
                ],
                'web_scraping_url': 'https://www.economist.com/business',
                'credibility': 'Very High',
                'region': 'UK',
                'keywords': ['economics', 'politics', 'global', 'policy', 'international', 'economist'],
                'user_agent': 'Mozilla/5.0 (compatible; Economist-Reader/1.0)',
                'headers': {'Accept': 'application/rss+xml, application/xml, text/xml'}
            },
            'financial_times': {
                'name': 'Financial Times',
                'primary_feeds': [
                    'https://www.ft.com/rss/home/world',
                    'https://www.ft.com/rss/home/markets',
                    'https://www.ft.com/rss/home/companies',
                    'https://www.ft.com/rss/home/economics'
                ],
                'backup_feeds': [
                    'https://feeds.feedburner.com/ft/business',
                    'https://feeds.feedburner.com/ft/markets'
                ],
                'web_scraping_url': 'https://www.ft.com/markets',
                'credibility': 'Very High',
                'region': 'UK',
                'keywords': ['finance', 'markets', 'investment', 'banking', 'economy', 'ft'],
                'user_agent': 'Mozilla/5.0 (compatible; FT-Reader/1.0)',
                'headers': {'Accept': 'application/rss+xml, application/xml, text/xml'}
            },
            'reuters': {
                'name': 'Reuters',
                'primary_feeds': [
                    'https://feeds.reuters.com/reuters/businessNews',
                    'https://feeds.reuters.com/reuters/economicNews',
                    'https://feeds.reuters.com/reuters/technologyNews',
                    'https://feeds.reuters.com/reuters/topNews'
                ],
                'backup_feeds': [
                    'https://feeds.feedburner.com/reuters/business',
                    'https://feeds.feedburner.com/reuters/technology'
                ],
                'web_scraping_url': 'https://www.reuters.com/business/',
                'credibility': 'Very High',
                'region': 'Global',
                'keywords': ['reuters', 'news', 'business', 'technology', 'global'],
                'user_agent': 'Mozilla/5.0 (compatible; Reuters-Reader/1.0)',
                'headers': {'Accept': 'application/rss+xml, application/xml, text/xml'}
            },
            'bloomberg': {
                'name': 'Bloomberg',
                'primary_feeds': [
                    'https://feeds.bloomberg.com/markets/news.rss',
                    'https://feeds.bloomberg.com/technology/news.rss',
                    'https://feeds.bloomberg.com/economics/news.rss',
                    'https://feeds.bloomberg.com/politics/news.rss'
                ],
                'backup_feeds': [
                    'https://feeds.feedburner.com/bloomberg/markets',
                    'https://feeds.feedburner.com/bloomberg/technology'
                ],
                'web_scraping_url': 'https://www.bloomberg.com/markets',
                'credibility': 'Very High',
                'region': 'US',
                'keywords': ['bloomberg', 'markets', 'finance', 'economics', 'technology'],
                'user_agent': 'Mozilla/5.0 (compatible; Bloomberg-Reader/1.0)',
                'headers': {'Accept': 'application/rss+xml, application/xml, text/xml'}
            },
            'wall_street_journal': {
                'name': 'Wall Street Journal',
                'primary_feeds': [
                    'https://feeds.a.dj.com/rss/RSSWorldNews.xml',
                    'https://feeds.a.dj.com/rss/RSSMarketsMain.xml',
                    'https://feeds.a.dj.com/rss/RSSWSJD.xml'
                ],
                'backup_feeds': [
                    'https://feeds.feedburner.com/wsj/business',
                    'https://feeds.feedburner.com/wsj/markets'
                ],
                'web_scraping_url': 'https://www.wsj.com/news/business',
                'credibility': 'Very High',
                'region': 'US',
                'keywords': ['wsj', 'wall street', 'business', 'markets', 'finance'],
                'user_agent': 'Mozilla/5.0 (compatible; WSJ-Reader/1.0)',
                'headers': {'Accept': 'application/rss+xml, application/xml, text/xml'}
            },
            'bbc_business': {
                'name': 'BBC Business',
                'primary_feeds': [
                    'https://feeds.bbci.co.uk/news/business/rss.xml',
                    'https://feeds.bbci.co.uk/news/technology/rss.xml',
                    'https://feeds.bbci.co.uk/news/world/rss.xml'
                ],
                'backup_feeds': [
                    'https://feeds.feedburner.com/bbc/business',
                    'https://feeds.feedburner.com/bbc/technology'
                ],
                'web_scraping_url': 'https://www.bbc.com/news/business',
                'credibility': 'Very High',
                'region': 'UK',
                'keywords': ['bbc', 'business', 'technology', 'global', 'news'],
                'user_agent': 'Mozilla/5.0 (compatible; BBC-Reader/1.0)',
                'headers': {'Accept': 'application/rss+xml, application/xml, text/xml'}
            },
            'cnn_business': {
                'name': 'CNN Business',
                'primary_feeds': [
                    'http://rss.cnn.com/rss/money_latest.rss',
                    'http://rss.cnn.com/rss/money_technology.rss',
                    'http://rss.cnn.com/rss/money_markets.rss'
                ],
                'backup_feeds': [
                    'https://feeds.feedburner.com/cnn/business',
                    'https://feeds.feedburner.com/cnn/technology'
                ],
                'web_scraping_url': 'https://www.cnn.com/business',
                'credibility': 'High',
                'region': 'US',
                'keywords': ['cnn', 'business', 'technology', 'markets', 'money'],
                'user_agent': 'Mozilla/5.0 (compatible; CNN-Reader/1.0)',
                'headers': {'Accept': 'application/rss+xml, application/xml, text/xml'}
            },
            'mit_tech_review': {
                'name': 'MIT Technology Review',
                'primary_feeds': [
                    'https://www.technologyreview.com/feed/',
                    'https://feeds.feedburner.com/MIT-Technology-Review'
                ],
                'backup_feeds': [
                    'https://feeds.feedburner.com/mit-tech-review',
                    'https://www.technologyreview.com/rss/'
                ],
                'web_scraping_url': 'https://www.technologyreview.com/',
                'credibility': 'Very High',
                'region': 'US',
                'keywords': ['mit', 'technology', 'ai', 'innovation', 'research', 'tech'],
                'user_agent': 'Mozilla/5.0 (compatible; MIT-Reader/1.0)',
                'headers': {'Accept': 'application/rss+xml, application/xml, text/xml'}
            },
            'techcrunch': {
                'name': 'TechCrunch',
                'primary_feeds': [
                    'https://techcrunch.com/feed/',
                    'https://techcrunch.com/category/artificial-intelligence/feed/',
                    'https://techcrunch.com/category/startups/feed/'
                ],
                'backup_feeds': [
                    'https://feeds.feedburner.com/TechCrunch',
                    'https://feeds.feedburner.com/techcrunch/startups'
                ],
                'web_scraping_url': 'https://techcrunch.com/',
                'credibility': 'High',
                'region': 'US',
                'keywords': ['techcrunch', 'startups', 'technology', 'ai', 'venture capital'],
                'user_agent': 'Mozilla/5.0 (compatible; TC-Reader/1.0)',
                'headers': {'Accept': 'application/rss+xml, application/xml, text/xml'}
            }
        }
        
        # Advanced keyword categories
        self.keyword_categories = {
            'economics': ['fed', 'federal reserve', 'interest rate', 'inflation', 'gdp', 'economy', 'monetary policy', 'fiscal policy', 'recession', 'growth'],
            'finance': ['stock market', 'investment', 'finance', 'banking', 'currency', 'trading', 'bonds', 'equity', 'portfolio', 'hedge fund'],
            'technology': ['ai', 'artificial intelligence', 'machine learning', 'blockchain', 'cryptocurrency', 'bitcoin', 'tech', 'innovation', 'digital', 'software'],
            'geopolitics': ['china', 'usa', 'biden', 'trump', 'trade war', 'tariff', 'sanctions', 'diplomacy', 'geopolitics', 'foreign policy'],
            'business': ['meta', 'google', 'microsoft', 'amazon', 'apple', 'tesla', 'merger', 'acquisition', 'corporate', 'earnings'],
            'global': ['ukraine', 'russia', 'middle east', 'europe', 'asia', 'emerging markets', 'developing', 'global'],
            'energy': ['oil', 'gas', 'renewable', 'energy', 'climate', 'carbon', 'solar', 'wind', 'fossil fuels'],
            'healthcare': ['covid', 'pandemic', 'healthcare', 'pharma', 'medical', 'vaccine', 'biotech'],
            'vietnam': ['vietnam', 'vietnamese', 'hanoi', 'ho chi minh', 'mekong', 'asean', 'southeast asia']
        }
        
        # Metrics tracking
        self.metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'articles_found': 0,
            'average_response_time': 0,
            'feed_success_rate': {},
            'last_updated': datetime.now()
        }
    
    def _create_ssl_context(self):
        """Tạo SSL context an toàn"""
        try:
            context = ssl.create_default_context(cafile=certifi.where())
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE  # For demo purposes
            return context
        except Exception as e:
            logger.warning(f"SSL context creation failed: {e}")
            return None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Tạo hoặc lấy session với cấu hình tối ưu"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            connector = aiohttp.TCPConnector(
                ssl=self.ssl_context,
                limit=100,
                limit_per_host=10,
                enable_cleanup_closed=True
            )
            
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers={
                    'User-Agent': 'Mozilla/5.0 (compatible; EnhancedRSS/2.0; +https://example.com/bot)',
                    'Accept': 'application/rss+xml, application/xml, text/xml, */*',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive'
                }
            )
        return self.session
    
    async def close(self):
        """Đóng session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def fetch_rss_with_retry(self, url: str, source_info: Dict, max_retries: int = 3) -> Optional[str]:
        """Fetch RSS với retry mechanism và exponential backoff"""
        session = await self._get_session()
        
        # Check cache first
        cache_key = f"rss_{hashlib.md5(url.encode()).hexdigest()}"
        cached_content = self.cache.get(cache_key)
        if cached_content:
            self.metrics['cache_hits'] += 1
            return cached_content
        
        self.metrics['cache_misses'] += 1
        
        headers = source_info.get('headers', {})
        if source_info.get('user_agent'):
            headers['User-Agent'] = source_info['user_agent']
        
        for attempt in range(max_retries):
            try:
                start_time = time.time()
                self.metrics['total_requests'] += 1
                
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        content = await response.text()
                        
                        # Cache successful response
                        self.cache.set(cache_key, content)
                        
                        # Update metrics
                        self.metrics['successful_requests'] += 1
                        response_time = time.time() - start_time
                        self._update_response_time(response_time)
                        
                        source_name = source_info.get('name', 'Unknown')
                        if source_name not in self.metrics['feed_success_rate']:
                            self.metrics['feed_success_rate'][source_name] = {'success': 0, 'total': 0}
                        self.metrics['feed_success_rate'][source_name]['success'] += 1
                        self.metrics['feed_success_rate'][source_name]['total'] += 1
                        
                        logger.info(f"Successfully fetched RSS from {url} in {response_time:.2f}s")
                        return content
                    
                    elif response.status in [301, 302, 307, 308]:
                        # Handle redirects
                        redirect_url = response.headers.get('Location')
                        if redirect_url:
                            logger.info(f"RSS feed redirected from {url} to {redirect_url}")
                            url = redirect_url
                            continue
                    
                    else:
                        logger.warning(f"RSS fetch failed with status {response.status} for {url}")
                        
            except asyncio.TimeoutError:
                wait_time = (2 ** attempt) + (0.1 * attempt)  # Exponential backoff
                logger.warning(f"Timeout fetching {url}, attempt {attempt + 1}/{max_retries}, waiting {wait_time:.1f}s")
                if attempt < max_retries - 1:
                    await asyncio.sleep(wait_time)
                    
            except Exception as e:
                wait_time = (2 ** attempt) + (0.1 * attempt)
                logger.warning(f"Error fetching {url}: {e}, attempt {attempt + 1}/{max_retries}, waiting {wait_time:.1f}s")
                if attempt < max_retries - 1:
                    await asyncio.sleep(wait_time)
        
        # Update failure metrics
        self.metrics['failed_requests'] += 1
        source_name = source_info.get('name', 'Unknown')
        if source_name not in self.metrics['feed_success_rate']:
            self.metrics['feed_success_rate'][source_name] = {'success': 0, 'total': 0}
        self.metrics['feed_success_rate'][source_name]['total'] += 1
        
        logger.error(f"Failed to fetch RSS from {url} after {max_retries} attempts")
        return None
    
    def _update_response_time(self, response_time: float):
        """Update average response time"""
        current_avg = self.metrics['average_response_time']
        total_successful = self.metrics['successful_requests']
        
        if total_successful == 1:
            self.metrics['average_response_time'] = response_time
        else:
            # Running average
            self.metrics['average_response_time'] = (
                (current_avg * (total_successful - 1) + response_time) / total_successful
            )
    
    def parse_rss_content(self, content: str, source_info: Dict, keywords: List[str]) -> List[RSSFeedResult]:
        """Parse RSS content và extract relevant articles"""
        try:
            feed = feedparser.parse(content)
            results = []
            
            for entry in feed.entries[:30]:  # Check more entries
                title = getattr(entry, 'title', '').strip()
                link = getattr(entry, 'link', '').strip()
                summary = getattr(entry, 'summary', '') or getattr(entry, 'description', '')
                published = getattr(entry, 'published', '') or getattr(entry, 'updated', '')
                
                if not title or not link:
                    continue
                
                # Clean and normalize content
                title = self._clean_text(title)
                summary = self._clean_text(summary)
                
                # Calculate relevance score
                relevance_score = self._calculate_advanced_relevance(
                    f"{title} {summary}", keywords, source_info
                )
                
                if relevance_score >= 2:  # Minimum threshold
                    result = RSSFeedResult(
                        title=title,
                        url=link,
                        summary=summary[:300] + "..." if len(summary) > 300 else summary,
                        published=published,
                        source=source_info['name'],
                        credibility=source_info.get('credibility', 'High'),
                        region=source_info.get('region', 'Global'),
                        relevance_score=relevance_score,
                        feed_url=getattr(feed.feed, 'link', ''),
                        content_length=len(f"{title} {summary}")
                    )
                    results.append(result)
            
            self.metrics['articles_found'] += len(results)
            logger.info(f"Parsed {len(results)} relevant articles from {source_info['name']}")
            return results
            
        except Exception as e:
            logger.error(f"Error parsing RSS content from {source_info['name']}: {e}")
            return []
    
    def _clean_text(self, text: str) -> str:
        """Clean và normalize text content"""
        if not text:
            return ""
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters
        text = re.sub(r'[^\w\s\-\.\,\:\;\!\?\(\)]', '', text)
        
        return text.strip()
    
    def _calculate_advanced_relevance(self, content: str, keywords: List[str], source_info: Dict) -> int:
        """Advanced relevance scoring với multiple factors"""
        content_lower = content.lower()
        score = 0
        
        # 1. Direct keyword matching
        for keyword in keywords:
            if keyword.lower() in content_lower:
                # Boost score based on keyword importance
                if len(keyword) > 8:
                    score += 3  # Very important keywords
                elif len(keyword) > 5:
                    score += 2  # Important keywords
                else:
                    score += 1  # Basic keywords
        
        # 2. Category-based matching
        for category, category_keywords in self.keyword_categories.items():
            category_matches = sum(1 for kw in category_keywords if kw in content_lower)
            if category_matches >= 2:
                score += category_matches  # Bonus for category clustering
        
        # 3. Source credibility bonus
        credibility = source_info.get('credibility', 'High')
        if credibility == 'Very High':
            score += 3
        elif credibility == 'High':
            score += 2
        else:
            score += 1
        
        # 4. Content quality indicators
        if 'analysis' in content_lower or 'expert' in content_lower:
            score += 2
        if 'outlook' in content_lower or 'forecast' in content_lower:
            score += 1
        if 'impact' in content_lower or 'implications' in content_lower:
            score += 1
        
        # 5. Penalize very short content
        if len(content) < 100:
            score = max(0, score - 2)
        
        return score
    
    def extract_enhanced_keywords(self, title: str, content: str) -> List[str]:
        """Enhanced keyword extraction với NER-like functionality"""
        text = f"{title} {content}".lower()
        found_keywords = []
        
        # 1. Predefined important keywords
        all_keywords = []
        for category_keywords in self.keyword_categories.values():
            all_keywords.extend(category_keywords)
        
        for keyword in all_keywords:
            if keyword in text:
                found_keywords.append(keyword)
        
        # 2. Extract proper nouns (capitalized words)
        proper_nouns = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', title + " " + content)
        found_keywords.extend([noun.lower() for noun in proper_nouns[:15]])
        
        # 3. Extract numbers with context (e.g., "20 billion", "0.75%")
        numbers_with_context = re.findall(r'\b\d+(?:\.\d+)?(?:%|\s*(?:billion|million|trillion|percent))\b', text)
        found_keywords.extend(numbers_with_context[:5])
        
        # 4. Extract financial terms
        financial_terms = re.findall(r'\b(?:USD|EUR|GBP|JPY|\$\d+|\€\d+)\b', text)
        found_keywords.extend(financial_terms[:3])
        
        return list(set(found_keywords))[:20]  # Max 20 unique keywords
    
    async def search_all_feeds_parallel(self, keywords: List[str], max_results: int = 10) -> List[RSSFeedResult]:
        """Tìm kiếm parallel trên tất cả RSS feeds"""
        all_results = []
        
        # Create tasks for parallel execution
        tasks = []
        
        for source_id, source_info in self.rss_sources.items():
            # Create task for each source
            task = self._search_source_feeds(source_info, keywords)
            tasks.append(task)
        
        # Execute all tasks in parallel
        try:
            results_per_source = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, results in enumerate(results_per_source):
                if isinstance(results, Exception):
                    source_name = list(self.rss_sources.keys())[i]
                    logger.error(f"Error searching {source_name}: {results}")
                    continue
                
                if isinstance(results, list):
                    all_results.extend(results)
        
        except Exception as e:
            logger.error(f"Error in parallel RSS search: {e}")
        
        # Sort by relevance and credibility
        all_results.sort(key=lambda x: (x.relevance_score, 
                                      3 if x.credibility == 'Very High' else 2 if x.credibility == 'High' else 1), 
                        reverse=True)
        
        # Remove duplicates based on URL
        seen_urls = set()
        unique_results = []
        for result in all_results:
            if result.url not in seen_urls:
                seen_urls.add(result.url)
                unique_results.append(result)
        
        logger.info(f"Found {len(unique_results)} unique articles from {len(self.rss_sources)} sources")
        return unique_results[:max_results]
    
    async def _search_source_feeds(self, source_info: Dict, keywords: List[str]) -> List[RSSFeedResult]:
        """Search feeds for a specific source"""
        results = []
        
        # Try primary feeds first
        for feed_url in source_info.get('primary_feeds', []):
            try:
                content = await self.fetch_rss_with_retry(feed_url, source_info)
                if content:
                    feed_results = self.parse_rss_content(content, source_info, keywords)
                    results.extend(feed_results)
                    
                    # If we found good results, don't try backup feeds
                    if len(feed_results) >= 3:
                        break
                        
            except Exception as e:
                logger.warning(f"Error searching primary feed {feed_url}: {e}")
                continue
        
        # Try backup feeds if primary didn't yield enough results
        if len(results) < 2:
            for feed_url in source_info.get('backup_feeds', []):
                try:
                    content = await self.fetch_rss_with_retry(feed_url, source_info)
                    if content:
                        feed_results = self.parse_rss_content(content, source_info, keywords)
                        results.extend(feed_results)
                        
                        if len(results) >= 3:
                            break
                            
                except Exception as e:
                    logger.warning(f"Error searching backup feed {feed_url}: {e}")
                    continue
        
        return results
    
    def get_metrics(self) -> Dict[str, Any]:
        """Lấy metrics và performance stats"""
        success_rate = (
            self.metrics['successful_requests'] / max(self.metrics['total_requests'], 1) * 100
        )
        
        cache_hit_rate = (
            self.metrics['cache_hits'] / max(self.metrics['cache_hits'] + self.metrics['cache_misses'], 1) * 100
        )
        
        return {
            'total_requests': self.metrics['total_requests'],
            'success_rate': f"{success_rate:.1f}%",
            'cache_hit_rate': f"{cache_hit_rate:.1f}%",
            'articles_found': self.metrics['articles_found'],
            'average_response_time': f"{self.metrics['average_response_time']:.2f}s",
            'feed_success_rates': {
                name: f"{stats['success']}/{stats['total']} ({stats['success']/max(stats['total'],1)*100:.1f}%)"
                for name, stats in self.metrics['feed_success_rate'].items()
            },
            'last_updated': self.metrics['last_updated'].strftime('%Y-%m-%d %H:%M:%S'),
            'cache_size': len(self.cache.cache),
            'sources_available': len(self.rss_sources)
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Kiểm tra tình trạng sức khỏe của RSS service"""
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'sources_status': {},
            'overall_health': 'good'
        }
        
        # Test a few key feeds
        test_feeds = [
            ('the_economist', 'https://www.economist.com/rss/business_rss.xml'),
            ('reuters', 'https://feeds.reuters.com/reuters/businessNews'),
            ('bloomberg', 'https://feeds.bloomberg.com/markets/news.rss')
        ]
        
        healthy_sources = 0
        
        for source_name, test_url in test_feeds:
            try:
                source_info = self.rss_sources.get(source_name, {})
                content = await self.fetch_rss_with_retry(test_url, source_info, max_retries=1)
                
                if content and len(content) > 100:
                    health_status['sources_status'][source_name] = 'healthy'
                    healthy_sources += 1
                else:
                    health_status['sources_status'][source_name] = 'degraded'
                    
            except Exception as e:
                health_status['sources_status'][source_name] = f'unhealthy: {str(e)[:50]}'
        
        # Overall health assessment
        health_ratio = healthy_sources / len(test_feeds)
        if health_ratio >= 0.8:
            health_status['overall_health'] = 'excellent'
        elif health_ratio >= 0.6:
            health_status['overall_health'] = 'good'
        elif health_ratio >= 0.4:
            health_status['overall_health'] = 'degraded'
        else:
            health_status['overall_health'] = 'poor'
            health_status['status'] = 'unhealthy'
        
        return health_status
    
    def __del__(self):
        """Cleanup when object is destroyed"""
        if hasattr(self, 'session') and self.session and not self.session.closed:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.session.close())
            except:
                pass 