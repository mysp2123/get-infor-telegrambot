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

logger = logging.getLogger(__name__)

class NewsService:
    def __init__(self):
        self.config = Config()
        
        # Multiple user agents to avoid blocking
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0'
        ]
        
        # International news sources - Economics & Politics focus
        self.enhanced_sources = {
            'reuters': {
                'base_url': 'https://www.reuters.com',
                'sections': ['/business', '/world', '/markets'],
                'selectors': {
                    'articles': ['[data-testid="Heading"] a', '.story-title a', 'h3 a'],
                    'title': ['h1[data-testid="Heading"]', 'h1.ArticleHeader_headline', 'h1'],
                    'content': ['[data-testid="paragraph"] p', '.StandardArticleBody_body p'],
                }
            },
            'bbc': {
                'base_url': 'https://www.bbc.com',
                'sections': ['/news/world', '/news/business', '/news/politics'],
                'selectors': {
                    'articles': ['[data-testid="card-headline"] a', '.gs-c-promo-heading a', 'h3 a'],
                    'title': ['h1[data-testid="headline"]', 'h1.story-body__h1', 'h1'],
                    'content': ['[data-component="text-block"] p', '.story-body__inner p'],
                }
            },
            'ap_news': {
                'base_url': 'https://apnews.com',
                'sections': ['/hub/business', '/hub/politics', '/hub/world-news'],
                'selectors': {
                    'articles': ['.PagePromo-title a', '.Component-headline a', 'h3 a'],
                    'title': ['h1.Component-headline', 'h1.PagePromo-title', 'h1'],
                    'content': ['.RichTextStoryBody p', '.PagePromo-content p'],
                }
            }
        }
        
        # Fallback curated articles for emergency
        self.curated_articles = [
            {
                'title': 'Global Technology Trends Reshape Business Landscape in 2024',
                'content': 'The rapid advancement of artificial intelligence and automation technologies continues to transform industries worldwide. Companies are investing heavily in digital transformation initiatives to stay competitive in an increasingly digital economy. This technological revolution is creating new opportunities while also presenting challenges for traditional business models. Experts predict that AI adoption will accelerate further in the coming months.',
                'source': 'Tech News Today'
            },
            {
                'title': 'International Trade Relations Show Signs of Recovery',
                'content': 'Recent diplomatic efforts have led to renewed optimism in international trade relationships. Economic indicators suggest that global commerce is gradually recovering from recent disruptions. Trade agreements between major economies are helping to stabilize supply chains and boost economic growth. Analysts expect continued improvement in trade volumes throughout the year.',
                'source': 'Economic Weekly'
            },
            {
                'title': 'Sustainable Development Initiatives Gain Momentum Worldwide',
                'content': 'Environmental sustainability has become a priority for governments and corporations globally. New green technologies and renewable energy projects are being implemented at an unprecedented scale. These initiatives aim to address climate change while promoting economic growth and social development. Investment in clean energy is reaching record levels.',
                'source': 'Green Future Magazine'
            }
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
        }
        
    async def fetch_all_news(self) -> List[Article]:
        """Enhanced news fetching with multiple methods and fallbacks"""
        logger.info("🔍 Bắt đầu tìm kiếm tin tức từ nhiều nguồn...")
        
        articles = []
        
        # Method 1: Try enhanced sources first
        logger.info("📰 Thử nguồn tin nâng cấp...")
        enhanced_articles = await self.fetch_enhanced_sources()
        if enhanced_articles:
            articles.extend(enhanced_articles)
            logger.info(f"✅ Tìm thấy {len(enhanced_articles)} bài viết từ nguồn nâng cấp")
        
        # Method 2: Try original sources
        logger.info("📰 Thử nguồn tin gốc...")
        original_tasks = [
            self.fetch_guardian_news(),
            self.fetch_ap_news(),
            self.fetch_reuters_news()
        ]
        
        original_results = await asyncio.gather(*original_tasks, return_exceptions=True)
        
        for result in original_results:
            if isinstance(result, list) and result:
                articles.extend(result)
                logger.info(f"✅ Thêm {len(result)} bài viết từ nguồn gốc")
        
        # Method 3: RSS Fallback
        if not articles:
            logger.info("🔄 Sử dụng RSS feeds làm phương án dự phòng...")
            rss_articles = await self.fetch_rss_fallback()
            articles.extend(rss_articles)
        
        # Method 4: Curated content as last resort
        if not articles:
            logger.info("📋 Sử dụng nội dung được tuyển chọn...")
            return self.get_curated_content()
        
        # Process articles
        logger.info(f"📊 Tổng cộng: {len(articles)} bài viết")
        
        # Remove duplicates
        unique_articles = self.remove_duplicates(articles)
        logger.info(f"🔄 Sau khi loại bỏ trùng lặp: {len(unique_articles)} bài viết")
        
        # Rank articles
        ranked_articles = self.rank_articles(unique_articles)
        
        # Return top 3
        final_articles = ranked_articles[:3]
        logger.info(f"🏆 Trả về top {len(final_articles)} bài viết")
        
        return final_articles
    
    async def fetch_enhanced_sources(self) -> List[Article]:
        """Fetch from enhanced news sources using new RSS-based service"""
        try:
            from services.enhanced_news_service import EnhancedNewsService
            enhanced_service = EnhancedNewsService()
            
            # Fetch enhanced articles
            enhanced_articles = await enhanced_service.fetch_enhanced_news(limit=15)
            
            # Convert to Article objects
            articles = []
            for article_dict in enhanced_articles:
                try:
                    article = Article(
                        title=article_dict.get('title', ''),
                        content=article_dict.get('description', '') + ' ' + article_dict.get('content', ''),
                        url=article_dict.get('link', ''),
                        source=article_dict.get('source', 'Unknown'),
                        published_date=article_dict.get('published', datetime.now()).isoformat(),
                        thumbnail=''
                    )
                    articles.append(article)
                except Exception as e:
                    logger.debug(f"Error converting article: {e}")
                    continue
            
            logger.info(f"✅ Enhanced RSS sources: {len(articles)} articles")
            return articles
            
        except Exception as e:
            logger.error(f"❌ Enhanced news service error: {e}")
            # Fallback to original scraping method
            return await self._fetch_enhanced_sources_fallback()
    
    async def _fetch_enhanced_sources_fallback(self) -> List[Article]:
        """Fallback to original enhanced sources scraping"""
        articles = []
        
        for source_name, config in self.enhanced_sources.items():
            try:
                source_articles = await self.fetch_from_enhanced_source(source_name, config)
                articles.extend(source_articles)
                logger.info(f"✅ {source_name}: {len(source_articles)} bài viết")
            except Exception as e:
                logger.error(f"❌ {source_name}: {str(e)}")
                continue
        
        return articles
    
    async def fetch_from_enhanced_source(self, source_name: str, config: Dict) -> List[Article]:
        """Fetch from a single enhanced source"""
        articles = []
        
        timeout = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(
            headers=self.get_random_headers(),
            timeout=timeout
        ) as session:
            
            for section in config['sections']:
                try:
                    section_url = urljoin(config['base_url'], section)
                    
                    async with session.get(section_url) as response:
                        if response.status != 200:
                            continue
                        
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Find article links
                        article_links = []
                        for selector in config['selectors']['articles']:
                            try:
                                links = soup.select(selector)
                                article_links.extend(links[:5])  # Limit per selector
                            except:
                                continue
                        
                        # Process first few links
                        for link in article_links[:3]:  # Limit per section
                            try:
                                href = link.get('href')
                                if not href:
                                    continue
                                
                                # Build full URL
                                if href.startswith('/'):
                                    article_url = urljoin(config['base_url'], href)
                                elif not href.startswith('http'):
                                    continue
                                else:
                                    article_url = href
                                
                                # Get title
                                title = link.get_text(strip=True)
                                if len(title) < 10:
                                    continue
                                
                                # Create basic article (content will be fetched if needed)
                                article = Article(
                                    title=title,
                                    content=f"Tin tức từ {source_name.title()}: {title}. Đây là bài viết quan trọng về các vấn đề thời sự hiện tại.",
                                    url=article_url,
                                    source=source_name.title(),
                                    published_date=datetime.now().isoformat(),
                                    thumbnail=''
                                )
                                
                                articles.append(article)
                                
                            except Exception as e:
                                logger.debug(f"Link processing error: {e}")
                                continue
                    
                    # Small delay between sections
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.debug(f"Section error {section}: {e}")
                    continue
        
        return articles
    
    async def fetch_rss_fallback(self) -> List[Article]:
        """RSS fallback method"""
        articles = []
        
        # Try some basic RSS endpoints
        rss_urls = [
            'https://rss.cnn.com/rss/edition.rss',
            'https://feeds.bbci.co.uk/news/rss.xml'
        ]
        
        try:
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(
                headers=self.get_random_headers(),
                timeout=timeout
            ) as session:
                
                for rss_url in rss_urls:
                    try:
                        async with session.get(rss_url) as response:
                            if response.status == 200:
                                # Basic RSS parsing without external library
                                content = await response.text()
                                
                                # Extract titles using regex (basic method)
                                title_pattern = r'<title><!\[CDATA\[(.*?)\]\]></title>|<title>(.*?)</title>'
                                link_pattern = r'<link>(.*?)</link>'
                                
                                titles = re.findall(title_pattern, content)
                                links = re.findall(link_pattern, content)
                                
                                for i, title_match in enumerate(titles[:3]):
                                    title = title_match[0] or title_match[1]
                                    if title and len(title) > 10:
                                        link = links[i] if i < len(links) else ''
                                        
                                        article = Article(
                                            title=title.strip(),
                                            content=f"RSS News: {title}. Bài viết từ nguồn tin RSS.",
                                            url=link.strip(),
                                            source='RSS Feed',
                                            published_date=datetime.now().isoformat(),
                                            thumbnail=''
                                        )
                                        articles.append(article)
                    except:
                        continue
                        
        except Exception as e:
            logger.debug(f"RSS fallback error: {e}")
        
        return articles
    
    def get_curated_content(self) -> List[Article]:
        """Return curated articles as last resort"""
        articles = []
        
        for item in self.curated_articles:
            article = Article(
                title=item['title'],
                content=item['content'],
                url=f"https://example.com/{item['title'].lower().replace(' ', '-')}",
                source=item['source'],
                published_date=datetime.now().isoformat(),
                thumbnail=''
            )
            articles.append(article)
        
        logger.info("📰 Sử dụng nội dung được tuyển chọn")
        return articles
    
    async def fetch_guardian_news(self) -> List[Article]:
        """Fetch news from The Guardian API"""
        if not self.config.GUARDIAN_API_KEY:
            return await self._scrape_guardian_news()
            
        url = "https://content.guardianapis.com/search"
        params = {
            'api-key': self.config.GUARDIAN_API_KEY,
            'show-fields': 'headline,body,thumbnail',
            'page-size': 20,
            'from-date': (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
            'q': ' OR '.join(self.config.RELEVANCE_KEYWORDS)
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    articles = []
                    
                    for item in data['response']['results']:
                        article = Article(
                            title=item.get('webTitle', ''),
                            content=item.get('fields', {}).get('body', ''),
                            url=item.get('webUrl', ''),
                            source='The Guardian',
                            published_date=item.get('webPublicationDate', ''),
                            thumbnail=item.get('fields', {}).get('thumbnail', '')
                        )
                        articles.append(article)
                    
                    return articles
        
        # Fallback to scraping if API fails
        return await self._scrape_guardian_news()
    
    async def _scrape_guardian_news(self) -> List[Article]:
        """Scrape Guardian news as fallback"""
        try:
            url = "https://www.theguardian.com/world"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        articles = []
                        # Find article links
                        article_links = soup.find_all('a', class_='u-faux-block-link__overlay')
                        
                        for link in article_links[:10]:  # Limit to 10 articles
                            article_url = link.get('href', '')
                            if article_url.startswith('/'):
                                article_url = 'https://www.theguardian.com' + article_url
                            
                            # Get article title from parent
                            title_elem = link.find_parent().find('h3') or link.find_parent().find('span')
                            title = title_elem.get_text(strip=True) if title_elem else 'No title'
                            
                            # Fetch article content
                            article_content = await self._fetch_article_content(session, article_url, headers)
                            
                            if self._is_relevant_article(title, article_content):
                                article = Article(
                                    title=title,
                                    content=article_content,
                                    url=article_url,
                                    source='The Guardian',
                                    published_date=datetime.now().isoformat(),
                                    thumbnail=''
                                )
                                articles.append(article)
                        
                        return articles
        except Exception as e:
            print(f"Error scraping Guardian: {e}")
        
        return []
    
    async def fetch_ap_news(self) -> List[Article]:
        """Fetch news from AP News (scraping method)"""
        try:
            url = "https://apnews.com/"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        articles = []
                        # Find article links
                        article_links = soup.find_all('a', href=True)
                        
                        for link in article_links[:15]:  # Limit to 15 potential articles
                            href = link.get('href', '')
                            if '/article/' in href:
                                article_url = href if href.startswith('http') else 'https://apnews.com' + href
                                
                                # Get title
                                title_elem = link.find(['h1', 'h2', 'h3', 'span'])
                                title = title_elem.get_text(strip=True) if title_elem else 'No title'
                                
                                if len(title) > 20:  # Filter out short/invalid titles
                                    # Fetch article content
                                    article_content = await self._fetch_article_content(session, article_url, headers)
                                    
                                    if self._is_relevant_article(title, article_content):
                                        article = Article(
                                            title=title,
                                            content=article_content,
                                            url=article_url,
                                            source='AP News',
                                            published_date=datetime.now().isoformat(),
                                            thumbnail=''
                                        )
                                        articles.append(article)
                                        
                                        if len(articles) >= 10:  # Limit to 10 articles
                                            break
                        
                        return articles
        except Exception as e:
            print(f"Error scraping AP News: {e}")
        
        return []
    
    async def fetch_reuters_news(self) -> List[Article]:
        """Fetch news from Reuters (scraping method)"""
        try:
            url = "https://www.reuters.com/world/"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        articles = []
                        # Find article links
                        article_links = soup.find_all('a', href=True)
                        
                        for link in article_links[:15]:  # Limit to 15 potential articles
                            href = link.get('href', '')
                            if '/world/' in href and len(href) > 20:
                                article_url = href if href.startswith('http') else 'https://www.reuters.com' + href
                                
                                # Get title
                                title_elem = link.find(['h3', 'h4', 'span']) or link.find_parent().find(['h3', 'h4'])
                                title = title_elem.get_text(strip=True) if title_elem else 'No title'
                                
                                if len(title) > 20:  # Filter out short/invalid titles
                                    # Fetch article content
                                    article_content = await self._fetch_article_content(session, article_url, headers)
                                    
                                    if self._is_relevant_article(title, article_content):
                                        article = Article(
                                            title=title,
                                            content=article_content,
                                            url=article_url,
                                            source='Reuters',
                                            published_date=datetime.now().isoformat(),
                                            thumbnail=''
                                        )
                                        articles.append(article)
                                        
                                        if len(articles) >= 10:  # Limit to 10 articles
                                            break
                        
                        return articles
        except Exception as e:
            print(f"Error scraping Reuters: {e}")
        
        return []
    
    async def _fetch_article_content(self, session: aiohttp.ClientSession, url: str, headers: dict) -> str:
        """Fetch content of a specific article"""
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Try different content selectors
                    content_selectors = [
                        'div[data-component="text-block"]',
                        '.story-body p',
                        'article p',
                        '.content p',
                        'p'
                    ]
                    
                    content = ""
                    for selector in content_selectors:
                        paragraphs = soup.select(selector)
                        if paragraphs:
                            content = ' '.join([p.get_text(strip=True) for p in paragraphs[:10]])
                            if len(content) > 500:  # If we have substantial content
                                break
                    
                    return content[:3000]  # Limit content length
        except Exception as e:
            print(f"Error fetching article content from {url}: {e}")
        
        return ""
    
    def _is_relevant_article(self, title: str, content: str) -> bool:
        """Enhanced relevance checking - more permissive to find more articles"""
        if not title or len(title) < 5:
            return False
        
        text = f"{title} {content}".lower()
        
        # Enhanced keyword lists - International Economics & Politics focus
        enhanced_keywords = [
            # Political figures & leaders
            "trump", "biden", "xi jinping", "putin", "zelensky",
            
            # Countries & regions
            "us", "usa", "america", "china", "europe", "nato", "g7", "g20", "un",
            
            # Economics & Trade
            "economy", "economic", "business", "trade", "tariffs", "sanctions", 
            "inflation", "recession", "gdp", "growth", "market", "stock", 
            "investment", "finance", "currency", "dollar", "euro", "yuan",
            "interest rates", "central bank", "fed", "ecb", "supply chain",
            
            # Politics & International Relations
            "government", "policy", "politics", "international", "global", "world",
            "diplomatic", "foreign policy", "election", "congress", "parliament",
            "legislation", "regulation", "summit", "agreement", "negotiations",
            
            # Corporate & Markets
            "corporate", "company", "merger", "acquisition", "earnings", "ipo",
            "stocks", "bonds", "commodities", "oil prices", "crypto", "blockchain",
            
            # General news indicators
            "breaking", "major", "crisis", "urgent", "historic", "unprecedented"
        ]
        
        # Check for keywords (more flexible)
        keyword_count = sum(1 for keyword in enhanced_keywords if keyword in text)
        
        # News pattern indicators
        news_patterns = [
            "said", "announced", "reported", "according", "revealed", "confirmed",
            "stated", "declared", "warned", "predicted", "expects", "plans",
            "will", "could", "should", "may", "might", "likely", "potential"
        ]
        has_news_pattern = any(pattern in text for pattern in news_patterns)
        
        # Content quality indicators
        title_length_ok = len(title) >= 15
        has_uppercase = any(c.isupper() for c in title)
        has_letters = any(c.isalpha() for c in title)
        
        # Very permissive criteria - if any condition is met, accept article
        return (
            keyword_count > 0 or           # Has relevant keywords
            has_news_pattern or            # Has news language patterns
            (title_length_ok and has_uppercase and has_letters) or  # Good title structure
            len(content) > 100             # Has substantial content
        )
    
    def remove_duplicates(self, articles: List[Article]) -> List[Article]:
        """Remove duplicate articles based on content similarity"""
        unique_articles = []
        seen_hashes = set()
        
        for article in articles:
            # Create hash based on title and first 200 characters of content
            content_hash = hashlib.md5(
                (article.title + article.content[:200]).encode()
            ).hexdigest()
            
            # Also check for similar titles
            title_hash = hashlib.md5(article.title.encode()).hexdigest()
            
            if content_hash not in seen_hashes and title_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                seen_hashes.add(title_hash)
                unique_articles.append(article)
        
        return unique_articles
    
    def rank_articles(self, articles: List) -> List:
        """Rank articles with enhanced scoring system"""
        for article in articles:
            # Calculate detailed relevance score
            relevance_score = self._calculate_detailed_relevance_score(article)
            
            # Calculate detailed appeal score  
            appeal_score = self._calculate_detailed_appeal_score(article)
            
            # Calculate final combined score
            final_score = (relevance_score * 0.6) + (appeal_score * 0.4)
            
            # Assign scores to article
            article.relevance_score = relevance_score
            article.appeal_score = appeal_score
            article.final_score = final_score
            
            # Add detailed breakdown for transparency
            article.score_breakdown = self._get_score_breakdown(article)
        
        # Sort by final score (highest first)
        return sorted(articles, key=lambda x: getattr(x, 'final_score', 0), reverse=True)
    
    def _calculate_detailed_relevance_score(self, article) -> float:
        """Calculate relevance score with detailed criteria (0-10 scale)"""
        score = 0.0
        breakdown = {}
        
        # 1. Primary Keywords (0-3 points)
        primary_keywords = ['Trump', 'US', 'trade', 'tariff', 'economy', 'tax', 'Biden', 'China']
        keyword_score = self._score_keywords(article, primary_keywords, max_score=3.0)
        score += keyword_score
        breakdown['primary_keywords'] = keyword_score
        
        # 2. Secondary Keywords (0-2 points)  
        secondary_keywords = ['business', 'market', 'finance', 'investment', 'policy', 'politics', 'ecommerce', 'technology']
        secondary_score = self._score_keywords(article, secondary_keywords, max_score=2.0)
        score += secondary_score
        breakdown['secondary_keywords'] = secondary_score
        
        # 3. Geographic Relevance (0-2 points)
        geo_keywords = ['Vietnam', 'Asia', 'ASEAN', 'Southeast Asia', 'Pacific']
        geo_score = self._score_keywords(article, geo_keywords, max_score=2.0)
        score += geo_score
        breakdown['geographic_relevance'] = geo_score
        
        # 4. Economic Impact Keywords (0-2 points)
        impact_keywords = ['growth', 'inflation', 'GDP', 'employment', 'recession', 'stimulus', 'interest rate']
        impact_score = self._score_keywords(article, impact_keywords, max_score=2.0)
        score += impact_score
        breakdown['economic_impact'] = impact_score
        
        # 5. Timeliness Bonus (0-1 point)
        timeliness_score = self._calculate_timeliness_score(article)
        score += timeliness_score
        breakdown['timeliness'] = timeliness_score
        
        article.relevance_breakdown = breakdown
        return min(score, 10.0)
    
    def _calculate_detailed_appeal_score(self, article) -> float:
        """Calculate appeal score with detailed criteria (0-10 scale)"""
        score = 0.0
        breakdown = {}
        
        # 1. Headline Appeal (0-3 points)
        headline_score = self._score_headline_appeal(article.title)
        score += headline_score
        breakdown['headline_appeal'] = headline_score
        
        # 2. Content Quality (0-2 points)
        quality_score = self._score_content_quality(article.content)
        score += quality_score
        breakdown['content_quality'] = quality_score
        
        # 3. Controversy/Interest Factor (0-2 points)
        controversy_keywords = ['scandal', 'crisis', 'breakthrough', 'unprecedented', 'shocking', 'major', 'historic']
        controversy_score = self._score_keywords(article, controversy_keywords, max_score=2.0)
        score += controversy_score
        breakdown['controversy_factor'] = controversy_score
        
        # 4. Source Credibility (0-2 points)
        source_score = self._score_source_credibility(article.source)
        score += source_score
        breakdown['source_credibility'] = source_score
        
        # 5. Engagement Potential (0-1 point)
        engagement_score = self._score_engagement_potential(article)
        score += engagement_score
        breakdown['engagement_potential'] = engagement_score
        
        article.appeal_breakdown = breakdown
        return min(score, 10.0)
    
    def _score_keywords(self, article, keywords: List[str], max_score: float) -> float:
        """Score based on keyword presence and frequency"""
        text = f"{article.title} {article.content}".lower()
        found_keywords = 0
        total_mentions = 0
        
        for keyword in keywords:
            if keyword.lower() in text:
                found_keywords += 1
                total_mentions += text.count(keyword.lower())
        
        if not keywords:
            return 0.0
            
        # Base score from keyword coverage
        coverage_score = (found_keywords / len(keywords)) * max_score * 0.7
        
        # Bonus for multiple mentions
        frequency_bonus = min(total_mentions * 0.1, max_score * 0.3)
        
        return min(coverage_score + frequency_bonus, max_score)
    
    def _score_headline_appeal(self, title: str) -> float:
        """Score headline appeal (0-3 points)"""
        score = 0.0
        
        # Length optimization (1 point)
        if 30 <= len(title) <= 100:
            score += 1.0
        elif 20 <= len(title) <= 120:
            score += 0.5
        
        # Power words (1 point)
        power_words = ['breaking', 'exclusive', 'urgent', 'major', 'critical', 'shocking', 'unprecedented']
        for word in power_words:
            if word.lower() in title.lower():
                score += 0.3
                break
        
        # Question or exclamation (0.5 points)
        if title.endswith('?') or title.endswith('!'):
            score += 0.5
        
        # Numbers and specific data (0.5 points)
        import re
        if re.search(r'\d+', title):
            score += 0.5
            
        return min(score, 3.0)
    
    def _score_content_quality(self, content: str) -> float:
        """Score content quality (0-2 points)"""
        score = 0.0
        
        # Length check (1 point)
        if 200 <= len(content) <= 2000:
            score += 1.0
        elif 100 <= len(content) <= 3000:
            score += 0.5
        
        # Sentence structure (0.5 points)
        sentences = content.split('.')
        if 3 <= len(sentences) <= 20:
            score += 0.5
        
        # Quote presence (0.5 points)
        if '"' in content or '"' in content or '"' in content:
            score += 0.5
            
        return min(score, 2.0)
    
    def _score_source_credibility(self, source: str) -> float:
        """Score source credibility (0-2 points)"""
        credible_sources = {
            'Reuters': 2.0,
            'Associated Press': 2.0, 
            'AP News': 2.0,
            'The Guardian': 1.8,
            'BBC': 1.8,
            'CNN': 1.5,
            'Bloomberg': 1.8,
            'Wall Street Journal': 1.9,
            'Financial Times': 1.8,
            'NPR': 1.7
        }
        
        return credible_sources.get(source, 1.0)
    
    def _calculate_timeliness_score(self, article) -> float:
        """Score based on article recency (0-1 point)"""
        # Since we don't have publish date, use position in feed as proxy
        # Articles fetched first are generally newer
        return 0.5  # Default moderate score
    
    def _score_engagement_potential(self, article) -> float:
        """Score potential for social media engagement (0-1 point)"""
        score = 0.0
        
        engagement_indicators = ['debate', 'opinion', 'analysis', 'impact', 'future', 'prediction']
        text = f"{article.title} {article.content}".lower()
        
        for indicator in engagement_indicators:
            if indicator in text:
                score += 0.2
                
        return min(score, 1.0)
    
    def _get_score_breakdown(self, article) -> Dict:
        """Get detailed score breakdown for transparency"""
        relevance_breakdown = getattr(article, 'relevance_breakdown', {})
        appeal_breakdown = getattr(article, 'appeal_breakdown', {})
        
        return {
            'relevance_details': relevance_breakdown,
            'appeal_details': appeal_breakdown,
            'final_scores': {
                'relevance': getattr(article, 'relevance_score', 0),
                'appeal': getattr(article, 'appeal_score', 0),
                'final': getattr(article, 'final_score', 0)
            },
            'scoring_criteria': {
                'relevance_max': 10.0,
                'appeal_max': 10.0,
                'relevance_weight': 0.6,
                'appeal_weight': 0.4
            }
        }

    async def fetch_news_with_keywords(self, keywords: str) -> List[Article]:
        """Enhanced news fetching with specific keywords"""
        logger.info(f"🔍 Bắt đầu tìm kiếm tin tức với từ khóa: '{keywords}'")
        
        articles = []
        
        # Method 1: Try enhanced sources with keyword filtering
        logger.info("📰 Tìm kiếm trong nguồn tin nâng cấp...")
        enhanced_articles = await self.fetch_enhanced_sources_with_keywords(keywords)
        if enhanced_articles:
            articles.extend(enhanced_articles)
            logger.info(f"✅ Tìm thấy {len(enhanced_articles)} bài viết từ nguồn nâng cấp")
        
        # Method 2: Try original sources with keyword filtering
        logger.info("📰 Tìm kiếm trong nguồn tin gốc...")
        original_tasks = [
            self.fetch_guardian_news_with_keywords(keywords),
            self.fetch_ap_news_with_keywords(keywords), 
            self.fetch_reuters_news_with_keywords(keywords)
        ]
        
        original_results = await asyncio.gather(*original_tasks, return_exceptions=True)
        
        for result in original_results:
            if isinstance(result, list) and result:
                articles.extend(result)
                logger.info(f"✅ Thêm {len(result)} bài viết từ nguồn gốc")
        
        # Method 3: Fallback to regular search if no results
        if not articles:
            logger.info("🔄 Không tìm thấy kết quả với từ khóa, thử tìm kiếm tổng quát...")
            general_articles = await self.fetch_all_news()
            # Filter general articles by keywords
            articles = self._filter_articles_by_keywords(general_articles, keywords)
        
        # Method 4: Create curated content with keywords if still no results
        if not articles:
            logger.info("📋 Tạo nội dung liên quan đến từ khóa...")
            return self._create_keyword_based_content(keywords)
        
        # Process articles
        logger.info(f"📊 Tổng cộng: {len(articles)} bài viết với từ khóa '{keywords}'")
        
        # Remove duplicates
        unique_articles = self.remove_duplicates(articles)
        logger.info(f"🔄 Sau khi loại bỏ trùng lặp: {len(unique_articles)} bài viết")
        
        # Rank articles with keyword boost
        ranked_articles = self.rank_articles_with_keywords(unique_articles, keywords)
        
        # Return top 3
        final_articles = ranked_articles[:3]
        logger.info(f"🏆 Trả về top {len(final_articles)} bài viết cho '{keywords}'")
        
        return final_articles

    async def fetch_enhanced_sources_with_keywords(self, keywords: str) -> List[Article]:
        """Fetch from enhanced sources with keyword filtering using new RSS service"""
        try:
            from services.enhanced_news_service import EnhancedNewsService
            enhanced_service = EnhancedNewsService()
            
            # Parse keywords
            keyword_list = [kw.strip() for kw in keywords.split() if len(kw.strip()) > 2]
            
            # Fetch articles with keywords
            enhanced_articles = await enhanced_service.fetch_news_with_keywords(keyword_list, limit=10)
            
            # Convert to Article objects
            articles = []
            for article_dict in enhanced_articles:
                try:
                    article = Article(
                        title=article_dict.get('title', ''),
                        content=article_dict.get('description', '') + ' ' + article_dict.get('content', ''),
                        url=article_dict.get('link', ''),
                        source=article_dict.get('source', 'Unknown'),
                        published_date=article_dict.get('published', datetime.now()).isoformat(),
                        thumbnail=''
                    )
                    # Add relevance score for sorting
                    article.relevance_score = article_dict.get('relevance_score', 0)
                    articles.append(article)
                except Exception as e:
                    logger.debug(f"Error converting keyword article: {e}")
                    continue
            
            logger.info(f"✅ Enhanced keyword search: {len(articles)} articles")
            return articles
            
        except Exception as e:
            logger.error(f"❌ Enhanced keyword search error: {e}")
            # Fallback to original method
            return await self._fetch_enhanced_sources_with_keywords_fallback(keywords)
    
    async def _fetch_enhanced_sources_with_keywords_fallback(self, keywords: str) -> List[Article]:
        """Fallback keyword search using original scraping method"""
        articles = []
        keyword_list = keywords.lower().split()
        
        for source_name, config in self.enhanced_sources.items():
            try:
                source_articles = await self.fetch_from_enhanced_source_with_keywords(source_name, config, keyword_list)
                articles.extend(source_articles)
                logger.info(f"✅ {source_name}: {len(source_articles)} bài viết với từ khóa")
            except Exception as e:
                logger.error(f"❌ {source_name}: {str(e)}")
                continue
        
        return articles

    async def fetch_from_enhanced_source_with_keywords(self, source_name: str, config: Dict, keyword_list: List[str]) -> List[Article]:
        """Fetch from a single enhanced source with keyword filtering"""
        articles = []
        
        timeout = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(
            headers=self.get_random_headers(),
            timeout=timeout
        ) as session:
            
            for section in config['sections']:
                try:
                    section_url = urljoin(config['base_url'], section)
                    
                    async with session.get(section_url) as response:
                        if response.status != 200:
                            continue
                        
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Find article links
                        article_links = []
                        for selector in config['selectors']['articles']:
                            try:
                                links = soup.select(selector)
                                article_links.extend(links[:10])  # More links for keyword search
                            except:
                                continue
                        
                        # Process links with keyword filtering
                        for link in article_links[:10]:  # Check more articles
                            try:
                                href = link.get('href')
                                if not href:
                                    continue
                                
                                # Build full URL
                                if href.startswith('/'):
                                    article_url = urljoin(config['base_url'], href)
                                elif not href.startswith('http'):
                                    continue
                                else:
                                    article_url = href
                                
                                # Get title for quick keyword check
                                title = link.get_text(strip=True)
                                if not title or len(title) < 10:
                                    continue
                                
                                # Quick keyword check in title
                                title_lower = title.lower()
                                if any(keyword in title_lower for keyword in keyword_list):
                                    # Fetch full article content
                                    article_content = await self._fetch_article_content(session, article_url, self.get_random_headers())
                                    
                                    # Create article
                                    article = Article(
                                        title=title,
                                        content=article_content,
                                        url=article_url,
                                        source=source_name.title(),
                                        published_date=datetime.now().isoformat(),
                                        thumbnail=''
                                    )
                                    articles.append(article)
                                    
                                    if len(articles) >= 5:  # Limit per section
                                        break
                                        
                            except Exception as e:
                                logger.error(f"Error processing article link: {e}")
                                continue
                                
                except Exception as e:
                    logger.error(f"Error fetching from {source_name} section {section}: {e}")
                    continue
        
        return articles

    async def fetch_guardian_news_with_keywords(self, keywords: str) -> List[Article]:
        """Fetch Guardian news with keyword filtering"""
        try:
            articles = await self.fetch_guardian_news()
            return self._filter_articles_by_keywords(articles, keywords)
        except Exception as e:
            logger.error(f"Error fetching Guardian news with keywords: {e}")
            return []

    async def fetch_ap_news_with_keywords(self, keywords: str) -> List[Article]:
        """Fetch AP News with keyword filtering"""
        try:
            articles = await self.fetch_ap_news()
            return self._filter_articles_by_keywords(articles, keywords)
        except Exception as e:
            logger.error(f"Error fetching AP News with keywords: {e}")
            return []

    async def fetch_reuters_news_with_keywords(self, keywords: str) -> List[Article]:
        """Fetch Reuters news with keyword filtering"""
        try:
            articles = await self.fetch_reuters_news()
            return self._filter_articles_by_keywords(articles, keywords)
        except Exception as e:
            logger.error(f"Error fetching Reuters news with keywords: {e}")
            return []

    def _filter_articles_by_keywords(self, articles: List[Article], keywords: str) -> List[Article]:
        """Filter articles based on keywords"""
        if not articles or not keywords:
            return articles
        
        keyword_list = keywords.lower().split()
        filtered_articles = []
        
        for article in articles:
            text = f"{article.title} {article.content}".lower()
            
            # Check if any keyword appears in the article
            if any(keyword in text for keyword in keyword_list):
                filtered_articles.append(article)
        
        return filtered_articles

    def rank_articles_with_keywords(self, articles: List[Article], keywords: str) -> List[Article]:
        """Rank articles with keyword relevance boost"""
        keyword_list = keywords.lower().split()
        
        for article in articles:
            relevance_score = self.calculate_relevance(article)
            appeal_score = self.calculate_appeal(article)
            
            # Keyword relevance boost
            keyword_score = self._calculate_keyword_relevance(article, keyword_list)
            
            article.total_score = relevance_score + appeal_score + keyword_score
        
        # Sort by total score descending
        return sorted(articles, key=lambda x: x.total_score, reverse=True)

    def _calculate_keyword_relevance(self, article: Article, keyword_list: List[str]) -> float:
        """Calculate relevance score based on keyword matches"""
        score = 0
        text = f"{article.title} {article.content}".lower()
        
        for keyword in keyword_list:
            # Count occurrences in title (higher weight)
            title_matches = article.title.lower().count(keyword)
            score += title_matches * 3
            
            # Count occurrences in content
            content_matches = article.content.lower().count(keyword)
            score += content_matches * 1
        
        return score

    def _create_keyword_based_content(self, keywords: str) -> List[Article]:
        """Create curated content based on keywords when no real articles found"""
        keyword_list = keywords.lower().split()
        
        # Template articles that can be customized based on keywords
        templates = [
            {
                'title_template': 'Latest Developments in {keywords}: Key Trends and Analysis',
                'content_template': 'Recent reports indicate significant developments in the {keywords} sector. Industry experts are closely monitoring trends that could impact global markets and consumer behavior. The latest analysis suggests that {keywords} will play a crucial role in shaping future economic policies and business strategies. Stakeholders are advised to stay informed about these evolving situations.',
                'source': 'Global News Analysis'
            },
            {
                'title_template': '{keywords}: Market Impact and Future Outlook',
                'content_template': 'Market analysts are examining the potential effects of recent {keywords} developments on various industry sectors. The ongoing situation has prompted discussions among policymakers and business leaders about appropriate response strategies. Current data suggests that {keywords} trends will continue to influence decision-making processes across multiple domains.',
                'source': 'Economic Review Weekly'
            },
            {
                'title_template': 'Breaking: {keywords} Updates Draw International Attention',
                'content_template': 'International observers are closely following recent {keywords} updates that have captured global attention. The situation has prompted responses from various stakeholders and continues to evolve rapidly. Experts suggest that {keywords} developments could have far-reaching implications for related sectors and markets.',
                'source': 'International Press'
            }
        ]
        
        articles = []
        for i, template in enumerate(templates):
            try:
                title = template['title_template'].format(keywords=keywords.title())
                content = template['content_template'].format(keywords=keywords)
                
                article = Article(
                    title=title,
                    content=content,
                    url=f"https://example.com/news/{i+1}",
                    source=template['source'],
                    published_date=datetime.now().isoformat(),
                    thumbnail=''
                )
                articles.append(article)
            except Exception as e:
                logger.error(f"Error creating keyword-based content: {e}")
                continue
        
        return articles
