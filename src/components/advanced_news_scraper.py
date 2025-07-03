#!/usr/bin/env python3
"""
🌐 Advanced News Scraper with AI-Enhanced Features
Scrape news from multiple Vietnamese and international sources with advanced recognition
"""

import requests
from bs4 import BeautifulSoup
import asyncio
import aiohttp
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, field
import re
from urllib.parse import urljoin, urlparse
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import logging
import hashlib
from datetime import datetime, timedelta
import json
import nltk
from textblob import TextBlob
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import spacy
from concurrent.futures import ThreadPoolExecutor
import newspaper
# from readability import Readability  # Optional, commented out to avoid import error

# Download required NLTK data
try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('vader_lexicon', quiet=True)
except:
    pass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class NewsArticle:
    title: str
    content: str
    url: str
    source: str
    publish_date: Optional[str] = None
    author: Optional[str] = None
    summary: str = ""
    score: float = 0.0
    image_url: Optional[str] = None
    
    # Enhanced fields
    category: str = ""
    sentiment: float = 0.0  # -1 to 1
    reading_time: int = 0  # minutes
    word_count: int = 0
    content_hash: str = ""
    language: str = "en"
    keywords: List[str] = field(default_factory=list)
    entities: List[Dict[str, str]] = field(default_factory=list)  # Named entities
    readability_score: float = 0.0
    credibility_score: float = 0.0
    engagement_potential: float = 0.0
    topics: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Calculate derived fields after initialization"""
        self.word_count = len(self.content.split())
        self.reading_time = max(1, self.word_count // 200)  # 200 words per minute
        self.content_hash = hashlib.md5(self.content.encode()).hexdigest()
        
class ContentClassifier:
    """AI-powered content classification and analysis"""
    
    def __init__(self):
        self.categories = {
            'politics': ['politics', 'government', 'election', 'vote', 'policy', 'congress', 'parliament'],
            'business': ['business', 'economy', 'market', 'financial', 'trade', 'company', 'stock'],
            'technology': ['technology', 'tech', 'AI', 'software', 'digital', 'cyber', 'innovation'],
            'health': ['health', 'medical', 'medicine', 'hospital', 'doctor', 'treatment', 'disease'],
            'sports': ['sports', 'football', 'soccer', 'basketball', 'game', 'match', 'championship'],
            'entertainment': ['entertainment', 'movie', 'music', 'celebrity', 'film', 'show', 'artist'],
            'science': ['science', 'research', 'study', 'discovery', 'scientist', 'experiment', 'breakthrough'],
            'world': ['international', 'global', 'country', 'nation', 'world', 'foreign', 'diplomatic']
        }
        
        # Initialize TF-IDF vectorizer
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
            self.sklearn_available = True
        except ImportError:
            self.sklearn_available = False
            logger.warning("Scikit-learn not available, using basic classification")
    
    def classify_category(self, title: str, content: str) -> str:
        """Classify article category using keyword matching and ML"""
        text = f"{title} {content}".lower()
        
        # Score each category
        category_scores = {}
        for category, keywords in self.categories.items():
            score = sum(text.count(keyword) for keyword in keywords)
            category_scores[category] = score
        
        # Return category with highest score
        if not category_scores:
            return 'general'
        best_category = max(category_scores.keys(), key=lambda k: category_scores[k])
        return best_category if category_scores[best_category] > 0 else 'general'
    
    def analyze_sentiment(self, text: str) -> float:
        """Analyze sentiment using TextBlob or basic approach"""
        try:
            from textblob import TextBlob
            blob = TextBlob(text)
            return blob.sentiment.polarity
        except ImportError:
            # Basic sentiment analysis using keyword counting
            positive_words = ['good', 'great', 'excellent', 'positive', 'success', 'win', 'growth']
            negative_words = ['bad', 'terrible', 'negative', 'fail', 'loss', 'decline', 'crisis']
            
            text_lower = text.lower()
            pos_count = sum(text_lower.count(word) for word in positive_words)
            neg_count = sum(text_lower.count(word) for word in negative_words)
            
            if pos_count + neg_count == 0:
                return 0.0
            return (pos_count - neg_count) / (pos_count + neg_count)
    
    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """Extract important keywords from text"""
        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        
        # Clean and tokenize
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        words = [word for word in words if word not in stop_words]
        
        # Count word frequency
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # Return top keywords
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words[:max_keywords]]
    
    def calculate_readability(self, text: str) -> float:
        """Calculate readability score (Flesch Reading Ease)"""
        sentences = len(re.findall(r'[.!?]+', text))
        words = len(text.split())
        syllables = sum(self._count_syllables(word) for word in text.split())
        
        if sentences == 0 or words == 0:
            return 0.0
        
        # Flesch Reading Ease formula
        score = 206.835 - (1.015 * words/sentences) - (84.6 * syllables/words)
        return max(0, min(100, score))
    
    def _count_syllables(self, word: str) -> int:
        """Count syllables in a word"""
        word = word.lower().strip(".:;?!")
        vowels = "aeiouy"
        syllable_count = 0
        previous_was_vowel = False
        
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not previous_was_vowel:
                syllable_count += 1
            previous_was_vowel = is_vowel
        
        if word.endswith('e'):
            syllable_count -= 1
        
        return max(1, syllable_count)
    
    def calculate_engagement_potential(self, article: NewsArticle) -> float:
        """Calculate potential engagement score based on various factors"""
        score = 0.0
        
        # Title factors
        title_words = len(article.title.split())
        if 6 <= title_words <= 12:  # Optimal title length
            score += 0.2
        
        # Sentiment impact (extreme sentiments get higher scores)
        sentiment_impact = abs(article.sentiment)
        score += sentiment_impact * 0.3
        
        # Category boost
        high_engagement_categories = ['politics', 'business', 'technology', 'entertainment']
        if article.category in high_engagement_categories:
            score += 0.2
        
        # Readability (easier to read = more engagement)
        if article.readability_score > 60:
            score += 0.2
        
        # Content length (optimal range)
        if 300 <= article.word_count <= 1000:
            score += 0.1
        
        return min(1.0, score)

class AdvancedNewsScraper:
    def __init__(self):
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0'
        ]
        
        # Initialize content classifier
        self.classifier = ContentClassifier()
        
        # Enhanced duplicate detection
        self.seen_hashes = set()
        self.seen_titles = set()
        
        # Rate limiting
        self.request_delays = {
            'vnexpress': (1, 3),
            'tuoitre': (1, 2),
            'thanhnien': (1, 2),
            'reuters': (2, 4),
            'bbc': (2, 4),
            'cnn': (2, 5),
            'apnews': (1, 3)
        }
        
        # Cấu hình nâng cao cho các trang báo
        self.news_sources = {
            # Báo Việt Nam
            'vnexpress': {
                'base_url': 'https://vnexpress.net',
                'sections': [
                    '/kinh-doanh',
                    '/the-gioi', 
                    '/thoi-su',
                    '/giai-tri',
                    '/the-thao',
                    '/khoa-hoc',
                    '/suc-khoe'
                ],
                'selectors': {
                    'article_links': [
                        'h3.title-news a',
                        'h2.title-news a', 
                        'h1.title-news a',
                        '.title_news a',
                        '.item-news .title-news a'
                    ],
                    'title': ['h1.title-detail', 'h1.title_detail', 'h1'],
                    'content': [
                        'article.fck_detail p',
                        '.Normal p',
                        '.content_detail p',
                        'article p'
                    ],
                    'date': ['.date', '.time-publish', '.datePublished'],
                    'author': ['.author', '.Normal strong'],
                    'image': [
                        'meta[property="og:image"]',
                        '.fig-picture img',
                        '.detail-img img'
                    ]
                },
                'language': 'vi',
                'encoding': 'utf-8'
            },
            'tuoitre': {
                'base_url': 'https://tuoitre.vn',
                'sections': ['/kinh-te.htm', '/the-gioi.htm', '/thoi-su.htm', '/giai-tri.htm'],
                'selectors': {
                    'article_links': [
                        'h3 a',
                        '.box-title-detail a',
                        '.box-category-link-title a'
                    ],
                    'title': ['h1', '.article-title', '.detail-title'],
                    'content': [
                        '.detail-content p',
                        '.content p',
                        '#main-detail-body p'
                    ],
                    'date': ['.date-time', '.time-ago'],
                    'author': ['.author'],
                    'image': ['meta[property="og:image"]']
                },
                'language': 'vi',
                'encoding': 'utf-8'
            },
            'thanhnien': {
                'base_url': 'https://thanhnien.vn',
                'sections': ['/kinh-doanh', '/the-gioi', '/thoi-su', '/giai-tri'],
                'selectors': {
                    'article_links': [
                        '.story__title a',
                        '.story-title a',
                        '.box-title a'
                    ],
                    'title': ['h1', '.story-title', '.detail-title'],
                    'content': [
                        '.content p',
                        '.story-body p',
                        '#detail-content p'
                    ],
                    'date': ['.time', '.story-time'],
                    'author': ['.author'],
                    'image': ['meta[property="og:image"]']
                },
                'language': 'vi',
                'encoding': 'utf-8'
            },
            # Báo quốc tế với improved selectors
            'reuters': {
                'base_url': 'https://www.reuters.com',
                'sections': ['/world/', '/business/', '/markets/', '/technology/'],
                'selectors': {
                    'article_links': [
                        'a[data-testid="Heading"]',
                        '.story-title a',
                        'h3 a',
                        '.media-story-card__headline a'
                    ],
                    'title': ['h1', '[data-testid="Heading"]'],
                    'content': [
                        'div[data-testid="paragraph"] p',
                        '.ArticleBody_container p',
                        '.StandardArticleBody_body p'
                    ],
                    'date': ['time', '[data-testid="Timestamp"]'],
                    'author': ['.author', '.Attribution_attribution'],
                    'image': ['meta[property="og:image"]']
                },
                'language': 'en',
                'encoding': 'utf-8'
            },
            'bbc': {
                'base_url': 'https://www.bbc.com',
                'sections': ['/news/world', '/news/business', '/news/technology'],
                'selectors': {
                    'article_links': [
                        'h3 a[href^="/news/"]',
                        '.media__link',
                        '.gs-c-promo-heading a'
                    ],
                    'title': ['h1', '.story-headline'],
                    'content': [
                        'div[data-component="text-block"] p',
                        '.story-body p',
                        '[data-component="text-block"]'
                    ],
                    'date': ['time', '.date'],
                    'author': ['.author'],
                    'image': ['meta[property="og:image"]']
                },
                'language': 'en',
                'encoding': 'utf-8'
            },
            'cnn': {
                'base_url': 'https://edition.cnn.com',
                'sections': ['/world', '/business', '/tech'],
                'selectors': {
                    'article_links': [
                        '.container__headline a',
                        '.cd__headline a',
                        'h3 a[href*="/2024/"]',
                        'h3 a[href*="/2025/"]'
                    ],
                    'title': ['h1', '.headline__text'],
                    'content': [
                        '.zn-body__paragraph',
                        '.el__article__body p',
                        'div.l-container p'
                    ],
                    'date': ['.timestamp', 'time'],
                    'author': ['.byline__name', '.metadata__byline'],
                    'image': ['meta[property="og:image"]']
                },
                'language': 'en',
                'encoding': 'utf-8'
            },
            'apnews': {
                'base_url': 'https://apnews.com',
                'sections': ['/hub/business', '/hub/world-news', '/hub/technology'],
                'selectors': {
                    'article_links': [
                        '.PageListStandardB-title a',
                        '.CardHeadline a',
                        'h2 a',
                        'h3 a'
                    ],
                    'title': ['h1', '.PagePromo-title'],
                    'content': [
                        '.Article p',
                        '.RichTextStoryBody p',
                        'div[data-key="StandardArticleBody"] p'
                    ],
                    'date': ['.Timestamp', 'time'],
                    'author': ['.Component-bylines', '.byline'],
                    'image': ['meta[property="og:image"]']
                },
                'language': 'en',
                'encoding': 'utf-8'
            },
            # Thêm nguồn mới
            'techcrunch': {
                'base_url': 'https://techcrunch.com',
                'sections': ['/category/startups/', '/category/venture/', '/category/ai/'],
                'selectors': {
                    'article_links': [
                        '.post-block__title__link',
                        'h2 a',
                        '.loop-card__title a'
                    ],
                    'title': ['h1.article__title', 'h1'],
                    'content': [
                        '.article-content p',
                        '.entry-content p'
                    ],
                    'date': ['.full-date-time', 'time'],
                    'author': ['.article__byline a'],
                    'image': ['meta[property="og:image"]']
                },
                'language': 'en',
                'encoding': 'utf-8'
            }
        }

    def get_random_headers(self) -> Dict[str, str]:
        """Tạo headers ngẫu nhiên để tránh bị block"""
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,vi;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }

    def is_duplicate(self, article: NewsArticle) -> bool:
        """Kiểm tra trùng lặp nâng cao"""
        # Check content hash
        if article.content_hash in self.seen_hashes:
            return True
        
        # Check title similarity
        for seen_title in self.seen_titles:
            similarity = self.calculate_text_similarity(article.title, seen_title)
            if similarity > 0.8:  # 80% similarity threshold
                return True
        
        return False
    
    def calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Tính độ tương đồng giữa hai văn bản"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0
    
    def validate_content_quality(self, article: NewsArticle) -> bool:
        """Kiểm tra chất lượng nội dung"""
        # Minimum content length
        if len(article.content) < 100:
            return False
        
        # Check for common spam indicators
        spam_indicators = [
            'click here', 'buy now', 'limited time',
            'subscribe', 'download', 'register now'
        ]
        
        content_lower = article.content.lower()
        spam_score = sum(content_lower.count(indicator) for indicator in spam_indicators)
        
        if spam_score > 3:
            return False
        
        # Check content structure
        sentences = len(re.findall(r'[.!?]+', article.content))
        if sentences < 3:  # Too few sentences
            return False
        
        return True
    
    def extract_with_multiple_selectors(self, soup: BeautifulSoup, selectors: List[str]) -> Optional[str]:
        """Thử nhiều selector để tìm nội dung"""
        for selector in selectors:
            try:
                elements = soup.select(selector)
                if elements:
                    if len(elements) == 1:
                        return elements[0].get_text(strip=True)
                    else:
                        # Multiple elements, join them
                        return ' '.join(elem.get_text(strip=True) for elem in elements)
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue
        return None
    
    def enhance_article_data(self, article: NewsArticle) -> NewsArticle:
        """Nâng cao dữ liệu bài viết bằng AI"""
        # Classify category
        article.category = self.classifier.classify_category(article.title, article.content)
        
        # Analyze sentiment
        article.sentiment = self.classifier.analyze_sentiment(f"{article.title} {article.content}")
        
        # Extract keywords
        article.keywords = self.classifier.extract_keywords(f"{article.title} {article.content}")
        
        # Calculate readability
        article.readability_score = self.classifier.calculate_readability(article.content)
        
        # Calculate engagement potential
        article.engagement_potential = self.classifier.calculate_engagement_potential(article)
        
        # Extract named entities (basic)
        article.entities = self.extract_basic_entities(article.content)
        
        # Calculate credibility score
        article.credibility_score = self.calculate_credibility_score(article)
        
        return article
    
    def extract_basic_entities(self, text: str) -> List[Dict[str, str]]:
        """Trích xuất entities cơ bản"""
        entities = []
        
        # Find capitalized words (potential names/places)
        capitalized_words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        
        # Find numbers with context
        numbers = re.findall(r'\b\d+(?:\.\d+)?(?:\s*(?:million|billion|thousand|percent|%))?\b', text)
        
        # Find URLs
        urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text)
        
        for word in capitalized_words[:10]:  # Limit to first 10
            entities.append({"text": word, "type": "PERSON_OR_PLACE"})
        
        for num in numbers[:5]:  # Limit to first 5
            entities.append({"text": num, "type": "NUMBER"})
        
        for url in urls[:3]:  # Limit to first 3
            entities.append({"text": url, "type": "URL"})
        
        return entities
    
    def calculate_credibility_score(self, article: NewsArticle) -> float:
        """Tính điểm độ tin cậy"""
        score = 0.5  # Base score
        
        # Source credibility
        trusted_sources = ['reuters', 'bbc', 'apnews', 'vnexpress']
        if article.source.lower() in trusted_sources:
            score += 0.3
        
        # Author presence
        if article.author and len(article.author) > 2:
            score += 0.1
        
        # Publication date
        if article.publish_date:
            score += 0.1
        
        # Content quality indicators
        if article.word_count > 200:
            score += 0.1
        
        if article.readability_score > 30:  # Reasonable readability
            score += 0.1
        
        # Penalty for suspicious content
        suspicious_words = ['shocking', 'unbelievable', 'amazing', 'incredible']
        title_lower = article.title.lower()
        penalty = sum(0.05 for word in suspicious_words if word in title_lower)
        score -= penalty
        
        return max(0.0, min(1.0, score))

    async def scrape_source(self, source_name: str, max_articles: int = 10) -> List[NewsArticle]:
        """Scrape tin tức từ một nguồn cụ thể với cải tiến"""
        if source_name not in self.news_sources:
            logger.error(f"Unknown source: {source_name}")
            return []
        
        source_config = self.news_sources[source_name]
        articles = []
        
        # Get delay range for this source
        delay_range = self.request_delays.get(source_name, (1, 3))
        
        for section in source_config['sections']:
            try:
                section_articles = await self._scrape_section_enhanced(
                    source_name, section, max_articles // len(source_config['sections'])
                )
                articles.extend(section_articles)
                
                # Dynamic delay based on source
                await asyncio.sleep(random.uniform(*delay_range))
                
            except Exception as e:
                logger.error(f"Error scraping {source_name}{section}: {e}")
        
        # Filter duplicates and enhance articles
        unique_articles = []
        for article in articles[:max_articles]:
            if not self.is_duplicate(article) and self.validate_content_quality(article):
                enhanced_article = self.enhance_article_data(article)
                unique_articles.append(enhanced_article)
                
                # Update seen sets
                self.seen_hashes.add(article.content_hash)
                self.seen_titles.add(article.title)
        
        logger.info(f"Scraped {len(unique_articles)} quality articles from {source_name}")
        return unique_articles

    async def _scrape_section_enhanced(self, source_name: str, section: str, max_items: int) -> List[NewsArticle]:
        """Scrape một section với kỹ thuật nâng cao"""
        source_config = self.news_sources[source_name]
        base_url = source_config['base_url']
        section_url = urljoin(base_url, section)
        
        articles = []
        
        try:
            # Use session with retry logic
            timeout = aiohttp.ClientTimeout(total=30)
            connector = aiohttp.TCPConnector(limit=10)
            
            async with aiohttp.ClientSession(
                headers=self.get_random_headers(),
                timeout=timeout,
                connector=connector
            ) as session:
                
                # Retry logic
                for attempt in range(3):
                    try:
                        async with session.get(section_url) as response:
                            if response.status == 200:
                                html = await response.text()
                                break
                            else:
                                logger.warning(f"HTTP {response.status} for {section_url}, attempt {attempt + 1}")
                                if attempt < 2:
                                    await asyncio.sleep(2 ** attempt)
                    except Exception as e:
                        logger.warning(f"Request failed for {section_url}, attempt {attempt + 1}: {e}")
                        if attempt < 2:
                            await asyncio.sleep(2 ** attempt)
                else:
                    logger.error(f"Failed to fetch {section_url} after 3 attempts")
                    return articles
                
                soup = BeautifulSoup(html, 'html.parser')
                
                # Try multiple selectors for article links
                article_links = []
                for selector in source_config['selectors']['article_links']:
                    links = soup.select(selector)
                    article_links.extend(links)
                    if len(article_links) >= max_items:
                        break
                
                # Remove duplicates while preserving order
                seen_hrefs = set()
                unique_links = []
                for link in article_links:
                    href = link.get('href')
                    if href and href not in seen_hrefs:
                        seen_hrefs.add(href)
                        unique_links.append(link)
                
                # Process links
                for i, link in enumerate(unique_links[:max_items]):
                    try:
                        href = link.get('href')
                        if not href:
                            continue
                        
                        # Handle relative URLs
                        if href.startswith('http'):
                            article_url = href
                        else:
                            article_url = urljoin(base_url, href)
                        
                        # Skip certain URLs
                        if self._should_skip_url(article_url):
                            continue
                        
                        # Get title hint
                        title_hint = link.get_text(strip=True)
                        
                        # Scrape article content
                        article = await self._scrape_article_enhanced(
                            source_name, article_url, title_hint, session
                        )
                        
                        if article:
                            articles.append(article)
                        
                        # Progressive delay (longer for each article)
                        base_delay = random.uniform(0.5, 1.5)
                        delay = base_delay + (i * 0.1)  # Increase delay for each article
                        await asyncio.sleep(delay)
                        
                    except Exception as e:
                        logger.error(f"Error processing article link: {e}")
        
        except Exception as e:
            logger.error(f"Error scraping section {section_url}: {e}")
        
        return articles
    
    def _should_skip_url(self, url: str) -> bool:
        """Kiểm tra có nên bỏ qua URL này không"""
        skip_patterns = [
            '/video/', '/photos/', '/gallery/', '/multimedia/',
            '/live/', '/podcast/', '/radio/',
            '.pdf', '.jpg', '.png', '.gif',
            'javascript:', 'mailto:', '#'
        ]
        
        url_lower = url.lower()
        return any(pattern in url_lower for pattern in skip_patterns)

    async def _scrape_article_enhanced(self, source_name: str, url: str, title_hint: str = "", session: Optional[aiohttp.ClientSession] = None) -> Optional[NewsArticle]:
        """Scrape nội dung chi tiết với nhiều cải tiến"""
        source_config = self.news_sources[source_name]
        
        try:
            # Use existing session or create new one
            should_close_session = False
            if session is None:
                session = aiohttp.ClientSession(headers=self.get_random_headers())
                should_close_session = True
            
            try:
                async with session.get(url) as response:
                    if response.status != 200:
                        return None
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Remove unwanted elements
                    for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'advertisement']):
                        tag.decompose()
                    
                    # Extract title using multiple selectors
                    title = self.extract_with_multiple_selectors(soup, source_config['selectors']['title'])
                    if not title and title_hint:
                        title = title_hint
                    
                    if not title:
                        return None
                    
                    # Extract content using multiple selectors
                    content_parts = []
                    for selector in source_config['selectors']['content']:
                        try:
                            content_elems = soup.select(selector)
                            for elem in content_elems:
                                text = elem.get_text(strip=True)
                                if text and len(text) > 20:  # Filter short fragments
                                    content_parts.append(text)
                        except Exception:
                            continue
                    
                    content = ' '.join(content_parts)
                    
                    # Skip if content is too short
                    if len(content) < 100:
                        return None
                    
                    # Extract metadata
                    publish_date = self.extract_with_multiple_selectors(soup, source_config['selectors']['date'])
                    author = self.extract_with_multiple_selectors(soup, source_config['selectors']['author'])
                    
                    # Extract image
                    image_url = ""
                    for selector in source_config['selectors']['image']:
                        try:
                            img_elem = soup.select_one(selector)
                            if img_elem:
                                if img_elem.name == 'meta':
                                    image_url = img_elem.get('content', '')
                                else:
                                    image_url = img_elem.get('src', '')
                                break
                        except Exception:
                            continue
                    
                    # Ensure image_url is string
                    if isinstance(image_url, list):
                        image_url = image_url[0] if image_url else ""
                    
                    # Create article
                    article = NewsArticle(
                        title=title,
                        content=content[:3000],  # Limit content length
                        url=url,
                        source=source_name.title(),
                        publish_date=publish_date or "",
                        author=author or "",
                        image_url=image_url,
                        language=source_config.get('language', 'en')
                    )
                    
                    return article
                    
            finally:
                if should_close_session:
                    await session.close()
        
        except Exception as e:
            logger.error(f"Error scraping article {url}: {e}")
        
        return None

    async def scrape_with_selenium(self, source_name: str, max_articles: int = 5) -> List[NewsArticle]:
        """Sử dụng Selenium cho các trang cần JavaScript"""
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument(f'--user-agent={random.choice(self.user_agents)}')
        
        articles = []
        driver = None
        
        try:
            driver = webdriver.Chrome(options=options)
            source_config = self.news_sources[source_name]
            
            for section in source_config['sections']:
                section_url = urljoin(source_config['base_url'], section)
                
                try:
                    driver.get(section_url)
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, source_config['article_selector']))
                    )
                    
                    # Scroll để load thêm content (cho SPA)
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)
                    
                    # Tìm các bài viết
                    article_elements = driver.find_elements(By.CSS_SELECTOR, source_config['article_selector'])
                    
                    for elem in article_elements[:max_articles // len(source_config['sections'])]:
                        try:
                            link = elem.get_attribute('href')
                            title = elem.text.strip()
                            
                            if link and title:
                                # Scrape chi tiết bài viết
                                article = await self._scrape_article_selenium(driver, source_name, link, title)
                                if article:
                                    articles.append(article)
                            
                        except Exception as e:
                            logger.error(f"Error processing article element: {e}")
                
                except Exception as e:
                    logger.error(f"Error scraping section {section_url}: {e}")
                
                time.sleep(random.uniform(2, 4))
        
        finally:
            if driver:
                driver.quit()
        
        return articles

    async def _scrape_article_selenium(self, driver, source_name: str, url: str, title: str) -> Optional[NewsArticle]:
        """Scrape bài viết sử dụng Selenium"""
        source_config = self.news_sources[source_name]
        
        try:
            driver.get(url)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, 'body'))
            )
            
            # Trích xuất nội dung
            content_parts = []
            try:
                content_elements = driver.find_elements(By.CSS_SELECTOR, source_config['content_selector'])
                for elem in content_elements:
                    text = elem.text.strip()
                    if text and len(text) > 20:
                        content_parts.append(text)
            except:
                pass
            
            content = ' '.join(content_parts)
            
            if content and len(content) > 100:
                return NewsArticle(
                    title=title,
                    content=content[:2000],
                    url=url,
                    source=source_name.title()
                )
        
        except Exception as e:
            logger.error(f"Error scraping article with Selenium {url}: {e}")
        
        return None

    async def scrape_all_sources(self, max_per_source: int = 10, priority_sources: Optional[List[str]] = None) -> List[NewsArticle]:
        """Scrape từ tất cả các nguồn với ưu tiên"""
        all_articles = []
        
        # Determine sources to scrape
        sources_to_scrape = priority_sources if priority_sources else list(self.news_sources.keys())
        
        # Scrape from high-priority sources first
        high_priority = ['reuters', 'bbc', 'apnews', 'vnexpress']
        low_priority = [s for s in sources_to_scrape if s not in high_priority]
        
        ordered_sources = [s for s in high_priority if s in sources_to_scrape] + low_priority
        
        # Scrape with controlled concurrency
        semaphore = asyncio.Semaphore(3)  # Limit concurrent requests
        
        async def scrape_with_semaphore(source_name: str):
            async with semaphore:
                return await self.scrape_source(source_name, max_per_source)
        
        # Create tasks
        tasks = [scrape_with_semaphore(source_name) for source_name in ordered_sources]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error scraping source {ordered_sources[i]}: {result}")
            elif isinstance(result, list):
                all_articles.extend(result)
        
        # Sort by credibility and engagement
        all_articles.sort(key=lambda x: (x.credibility_score * 0.6 + x.engagement_potential * 0.4), reverse=True)
        
        logger.info(f"Scraped {len(all_articles)} total articles from {len(ordered_sources)} sources")
        return all_articles

    def smart_filter_articles(self, articles: List[NewsArticle], 
                            keywords: Optional[List[str]] = None,
                            categories: Optional[List[str]] = None,
                            min_credibility: float = 0.3,
                            max_articles: int = 50) -> List[NewsArticle]:
        """Lọc bài viết thông minh với nhiều tiêu chí"""
        filtered = []
        
        for article in articles:
            # Credibility filter
            if article.credibility_score < min_credibility:
                continue
            
            # Category filter
            if categories and article.category not in categories:
                continue
            
            # Keyword filter
            score = 0
            if keywords:
                text_content = f"{article.title} {article.content}".lower()
                for keyword in keywords:
                    keyword_lower = keyword.lower()
                    title_matches = article.title.lower().count(keyword_lower) * 3  # Title matches worth more
                    content_matches = article.content.lower().count(keyword_lower)
                    score += title_matches + content_matches
            else:
                score = 1  # No keyword filter, include all
            
            if score > 0:
                article.score = score
                filtered.append(article)
        
        # Sort by combined score (keyword relevance + credibility + engagement)
        filtered.sort(key=lambda x: (x.score * 0.4 + x.credibility_score * 0.3 + x.engagement_potential * 0.3), reverse=True)
        
        return filtered[:max_articles]

    def generate_article_summary(self, article: NewsArticle, max_sentences: int = 3) -> str:
        """Tạo tóm tắt bài viết tự động"""
        sentences = re.split(r'[.!?]+', article.content)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        
        if len(sentences) <= max_sentences:
            return '. '.join(sentences) + '.'
        
        # Simple extractive summarization
        # Score sentences based on keyword frequency and position
        sentence_scores = {}
        
        # Get top keywords
        keywords = self.classifier.extract_keywords(article.content, 10)
        
        for i, sentence in enumerate(sentences):
            score = 0
            sentence_lower = sentence.lower()
            
            # Keyword density score
            for keyword in keywords:
                score += sentence_lower.count(keyword.lower())
            
            # Position score (earlier sentences get higher scores)
            position_score = 1.0 - (i / len(sentences)) * 0.3
            score *= position_score
            
            # Length penalty for very short or very long sentences
            length_penalty = 1.0
            if len(sentence.split()) < 5:
                length_penalty = 0.5
            elif len(sentence.split()) > 30:
                length_penalty = 0.7
            
            score *= length_penalty
            sentence_scores[i] = score
        
        # Select top sentences
        top_sentence_indices = sorted(sentence_scores.keys(), key=lambda i: sentence_scores[i], reverse=True)[:max_sentences]
        top_sentence_indices.sort()  # Maintain original order
        
        summary_sentences = [sentences[i] for i in top_sentence_indices]
        return '. '.join(summary_sentences) + '.'

    def get_trending_topics(self, articles: List[NewsArticle], top_n: int = 10) -> List[Dict[str, str]]:
        """Phân tích xu hướng chủ đề"""
        topic_counts = {}
        topic_articles = {}
        
        for article in articles:
            for keyword in article.keywords:
                if len(keyword) > 2:  # Skip short keywords
                    topic_counts[keyword] = topic_counts.get(keyword, 0) + 1
                    if keyword not in topic_articles:
                        topic_articles[keyword] = []
                    topic_articles[keyword].append(article)
        
        # Sort by frequency and importance
        trending_topics = []
        for topic, count in sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:top_n]:
            avg_credibility = sum(a.credibility_score for a in topic_articles[topic]) / len(topic_articles[topic])
            avg_engagement = sum(a.engagement_potential for a in topic_articles[topic]) / len(topic_articles[topic])
            
            trending_topics.append({
                'topic': topic,
                'count': str(count),
                'avg_credibility': str(round(avg_credibility, 2)),
                'avg_engagement': str(round(avg_engagement, 2)),
                'articles': str(len(topic_articles[topic]))
            })
        
        return trending_topics

    def export_to_dataframe(self, articles: List[NewsArticle]):
        """Xuất dữ liệu ra pandas DataFrame"""
        try:
            import pandas as pd
            
            data = []
            for article in articles:
                data.append({
                    'title': article.title,
                    'source': article.source,
                    'category': article.category,
                    'url': article.url,
                    'publish_date': article.publish_date,
                    'author': article.author,
                    'word_count': article.word_count,
                    'reading_time': article.reading_time,
                    'sentiment': article.sentiment,
                    'readability_score': article.readability_score,
                    'credibility_score': article.credibility_score,
                    'engagement_potential': article.engagement_potential,
                    'keywords': ', '.join(article.keywords),
                    'summary': self.generate_article_summary(article, 2)
                })
            
            return pd.DataFrame(data)
        except ImportError:
            logger.error("Pandas not available for export")
            return None

    async def scrape_with_ai_assist(self, query: str, max_articles: int = 20) -> List[NewsArticle]:
        """Scrape với sự hỗ trợ của AI để tìm nội dung liên quan"""
        # Extract keywords from query
        query_keywords = self.classifier.extract_keywords(query, 5)
        
        # Determine relevant categories
        query_lower = query.lower()
        relevant_categories = []
        for category, category_keywords in self.classifier.categories.items():
            if any(keyword in query_lower for keyword in category_keywords):
                relevant_categories.append(category)
        
        # Scrape all sources
        all_articles = await self.scrape_all_sources(max_per_source=max_articles // 4)
        
        # Smart filter with query context
        filtered_articles = self.smart_filter_articles(
            all_articles,
            keywords=query_keywords,
            categories=relevant_categories if relevant_categories else None,
            max_articles=max_articles
        )
        
        return filtered_articles

# Demo và test functions
async def demo_advanced_scraper():
    """Demo các tính năng nâng cao"""
    scraper = AdvancedNewsScraper()
    
    print("🚀 ADVANCED NEWS SCRAPER DEMO")
    print("=" * 50)
    
    # Test AI-assisted scraping
    print("\n🤖 AI-Assisted Scraping for 'artificial intelligence'...")
    ai_articles = await scraper.scrape_with_ai_assist("artificial intelligence technology", 10)
    print(f"✅ Found {len(ai_articles)} AI-related articles")
    
    if ai_articles:
        print("\n📊 Top Articles:")
        for i, article in enumerate(ai_articles[:3], 1):
            print(f"{i}. {article.title}")
            print(f"   📰 Source: {article.source} | Category: {article.category}")
            print(f"   📈 Credibility: {article.credibility_score:.2f} | Engagement: {article.engagement_potential:.2f}")
            print(f"   💭 Sentiment: {article.sentiment:.2f} | Readability: {article.readability_score:.1f}")
            print(f"   🏷️ Keywords: {', '.join(article.keywords[:5])}")
            print()
    
    # Test trending topics
    print("🔥 Trending Topics Analysis:")
    trending = scraper.get_trending_topics(ai_articles)
    for topic in trending[:5]:
        print(f"   • {topic['topic']}: {topic['count']} articles (Credibility: {topic['avg_credibility']})")
    
    # Test data export
    print(f"\n💾 Exporting {len(ai_articles)} articles to DataFrame...")
    df = scraper.export_to_dataframe(ai_articles)
    if df is not None:
        print(f"✅ DataFrame created with shape: {df.shape}")
        print(f"📊 Columns: {list(df.columns)}")

if __name__ == "__main__":
    asyncio.run(demo_advanced_scraper())
