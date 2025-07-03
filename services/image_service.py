import aiohttp
import asyncio
import os
import hashlib
import time
from datetime import datetime
from typing import Optional, Dict, List
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import requests
import logging
import random
import re

logger = logging.getLogger(__name__)

class ImageService:
    def __init__(self):
        self.generated_images_dir = "generated_images"
        os.makedirs(self.generated_images_dir, exist_ok=True)
        
        # Enhanced image generation sources
        self.image_sources = {
            'unsplash': {
                'base_url': 'https://source.unsplash.com',
                'collections': {
                    'technology': ['technology', 'computer', 'ai', 'artificial-intelligence', 'tech', 'digital'],
                    'business': ['business', 'office', 'finance', 'economy', 'market', 'corporate'],
                    'world': ['world', 'global', 'earth', 'international', 'news', 'politics'],
                    'nature': ['nature', 'environment', 'climate', 'green', 'sustainability'],
                    'people': ['people', 'team', 'meeting', 'conference', 'discussion'],
                    'science': ['science', 'research', 'laboratory', 'innovation'],
                    'sports': ['sports', 'football', 'soccer', 'olympics', 'competition'],
                    'health': ['health', 'medical', 'healthcare', 'medicine'],
                    'education': ['education', 'learning', 'school', 'university'],
                    'travel': ['travel', 'tourism', 'city', 'architecture']
                }
            },
            'picsum': {
                'base_url': 'https://picsum.photos',
                'categories': ['business', 'nature', 'technology', 'city']
            }
        }
        
        self.logo_path = "assets/PioneerX-logo.JPG"
    
    def _extract_keywords_from_content(self, title: str, content: str) -> List[str]:
        """Extract relevant keywords from title and content for better image matching"""
        text = f"{title} {content}".lower()
        
        # Enhanced keyword categories with Vietnamese support
        keyword_categories = {
            'technology': ['ai', 'artificial intelligence', 'technology', 'tech', 'digital', 'computer', 'software', 
                          'internet', 'innovation', 'startup', 'công nghệ', 'trí tuệ nhân tạo', 'phần mềm'],
            'business': ['business', 'economy', 'economic', 'market', 'finance', 'financial', 'company', 
                        'corporate', 'trade', 'investment', 'kinh tế', 'doanh nghiệp', 'thương mại', 'tài chính'],
            'politics': ['politics', 'political', 'government', 'policy', 'election', 'president', 'minister',
                        'chính trị', 'chính phủ', 'bầu cử', 'tổng thống', 'thủ tướng'],
            'world': ['world', 'global', 'international', 'country', 'nation', 'diplomatic', 'relations',
                     'thế giới', 'toàn cầu', 'quốc tế', 'nước', 'ngoại giao'],
            'health': ['health', 'medical', 'medicine', 'healthcare', 'hospital', 'doctor', 'patient',
                      'y tế', 'bác sĩ', 'bệnh viện', 'sức khỏe'],
            'environment': ['environment', 'climate', 'green', 'sustainability', 'energy', 'renewable',
                           'môi trường', 'khí hậu', 'năng lượng', 'bền vững'],
            'sports': ['sports', 'football', 'soccer', 'basketball', 'tennis', 'olympics', 'world cup',
                      'thể thao', 'bóng đá', 'thế vận hội'],
            'education': ['education', 'school', 'university', 'student', 'learning', 'research',
                         'giáo dục', 'học sinh', 'sinh viên', 'trường học', 'đại học'],
            'science': ['science', 'research', 'study', 'discovery', 'laboratory', 'scientist',
                       'khoa học', 'nghiên cứu', 'phát hiện', 'nhà khoa học']
        }
        
        matched_categories = []
        for category, keywords in keyword_categories.items():
            if any(keyword in text for keyword in keywords):
                matched_categories.append(category)
        
        # If no specific category found, use general business/world themes
        if not matched_categories:
            matched_categories = ['business', 'world']
        
        return matched_categories
    
    def _generate_topic_specific_search_terms(self, categories: List[str], title: str) -> List[str]:
        """Generate specific search terms based on detected categories and title"""
        search_terms = []
        
        # Extract key words from title for more specific searches
        title_words = re.findall(r'[a-zA-ZÀ-ỹ]{3,}', title.lower())
        
        for category in categories:
            if category in self.image_sources['unsplash']['collections']:
                base_terms = self.image_sources['unsplash']['collections'][category]
                search_terms.extend(base_terms[:3])  # Take top 3 terms per category
        
        # Add title-specific terms if they're meaningful
        meaningful_words = [word for word in title_words if len(word) > 4 and word not in 
                           ['news', 'today', 'latest', 'update', 'report', 'according']]
        search_terms.extend(meaningful_words[:2])  # Add up to 2 meaningful words from title
        
        return list(set(search_terms))  # Remove duplicates
    
    async def generate_image(self, title: str, content: str) -> Optional[str]:
        """Generate topic-specific image with enhanced relevance"""
        try:
            logger.info(f"🎨 Generating image for: {title[:50]}...")
            
            # Extract keywords and determine categories
            categories = self._extract_keywords_from_content(title, content)
            search_terms = self._generate_topic_specific_search_terms(categories, title)
            
            logger.info(f"🔍 Detected categories: {categories}")
            logger.info(f"🔍 Search terms: {search_terms[:5]}")  # Log first 5 terms
            
            # Generate unique filename with timestamp for freshness
            timestamp = int(time.time())
            content_hash = hashlib.md5(f"{title}{timestamp}".encode()).hexdigest()[:8]
            filename = f"news_image_{content_hash}_{timestamp}.jpg"
            image_path = os.path.join(self.generated_images_dir, filename)
            
            # Try multiple search terms for better variety
            success = False
            for attempt, search_term in enumerate(search_terms[:3]):  # Try up to 3 different terms
                try:
                    logger.info(f"🎯 Attempt {attempt + 1}: Searching for '{search_term}'")
                    
                    # Try Unsplash first with specific dimensions
                    image_url = f"https://source.unsplash.com/1200x630/?{search_term}"
                    
                    # Add variation to avoid same image
                    if attempt > 0:
                        image_url += f"&sig={timestamp + attempt}"
                    
                    success = await self._download_and_process_image(image_url, image_path, title)
                    
                    if success:
                        logger.info(f"✅ Successfully generated image with term: {search_term}")
                        break
                        
                except Exception as e:
                    logger.warning(f"⚠️ Failed attempt {attempt + 1} with '{search_term}': {e}")
                    continue
            
            # Fallback to Picsum if Unsplash fails
            if not success:
                logger.info("🔄 Falling back to Picsum Photos...")
                picsum_url = f"https://picsum.photos/1200/630?random={timestamp}"
                success = await self._download_and_process_image(picsum_url, image_path, title)
            
            # Last resort: create a simple colored background with text
            if not success:
                logger.info("🎨 Creating custom background image...")
                success = self._create_custom_background_image(image_path, title, categories)
            
            return image_path if success else None
            
        except Exception as e:
            logger.error(f"❌ Error generating image: {e}")
            return None
    
    async def _download_and_process_image(self, url: str, output_path: str, title: str) -> bool:
        """Download image and add logo overlay"""
        try:
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        with open(output_path, 'wb') as f:
                            f.write(await response.read())
                        
                        # Process image (add logo, adjust quality)
                        self._process_downloaded_image(output_path, title)
                        return True
                    else:
                        logger.warning(f"❌ HTTP {response.status} for {url}")
                        return False
                        
        except Exception as e:
            logger.error(f"❌ Download failed: {e}")
            return False
    
    def _process_downloaded_image(self, image_path: str, title: str):
        """Process downloaded image: resize, add logo, enhance quality"""
        try:
            with Image.open(image_path) as img:
                # Resize to standard Facebook dimensions
                img = img.resize((1200, 630), Image.Resampling.LANCZOS)
                
                # Enhance image quality
                enhancer = ImageEnhance.Sharpness(img)
                img = enhancer.enhance(1.1)
                
                enhancer = ImageEnhance.Color(img)
                img = enhancer.enhance(1.05)
                
                # Add logo if available
                if os.path.exists(self.logo_path):
                    self._add_logo_overlay(img, title)
                
                # Save with high quality
                img.save(image_path, 'JPEG', quality=90, optimize=True)
                
        except Exception as e:
            logger.error(f"❌ Error processing image: {e}")
    
    def _add_logo_overlay(self, img: Image.Image, title: str):
        """Add logo and title overlay to image"""
        try:
            # Load and resize logo
            with Image.open(self.logo_path) as logo:
                # Make logo smaller and more subtle
                logo_size = (100, 100)
                logo = logo.resize(logo_size, Image.Resampling.LANCZOS)
                
                # Add logo to bottom right corner
                logo_pos = (img.width - logo_size[0] - 20, img.height - logo_size[1] - 20)
                
                # Create mask for transparency
                if logo.mode != 'RGBA':
                    logo = logo.convert('RGBA')
                
                img.paste(logo, logo_pos, logo)
                
        except Exception as e:
            logger.error(f"❌ Error adding logo: {e}")
    
    def _create_custom_background_image(self, output_path: str, title: str, categories: List[str]) -> bool:
        """Create custom background when no external image available"""
        try:
            # Create image with topic-appropriate colors
            color_schemes = {
                'technology': [(30, 144, 255), (0, 100, 200)],  # Blue gradient
                'business': [(25, 25, 112), (72, 61, 139)],     # Navy gradient  
                'politics': [(139, 0, 0), (205, 92, 92)],       # Red gradient
                'health': [(34, 139, 34), (144, 238, 144)],     # Green gradient
                'environment': [(0, 128, 0), (173, 255, 47)],   # Nature green
                'sports': [(255, 140, 0), (255, 165, 0)],       # Orange gradient
                'world': [(70, 130, 180), (135, 206, 235)],     # Sky blue
                'default': [(60, 60, 60), (120, 120, 120)]      # Gray gradient
            }
            
            # Choose color based on primary category
            primary_category = categories[0] if categories else 'default'
            colors = color_schemes.get(primary_category, color_schemes['default'])
            
            # Create gradient background
            img = Image.new('RGB', (1200, 630), colors[0])
            draw = ImageDraw.Draw(img)
            
            # Create simple gradient effect
            for y in range(630):
                ratio = y / 630
                r = int(colors[0][0] * (1 - ratio) + colors[1][0] * ratio)
                g = int(colors[0][1] * (1 - ratio) + colors[1][1] * ratio)
                b = int(colors[0][2] * (1 - ratio) + colors[1][2] * ratio)
                draw.line([(0, y), (1200, y)], fill=(r, g, b))
            
            # Add title text (shortened)
            title_short = title[:60] + "..." if len(title) > 60 else title
            
            try:
                # Try to use a better font
                font = ImageFont.truetype("arial.ttf", 36)
            except:
                font = ImageFont.load_default()
            
            # Add text with outline for better readability
            text_color = (255, 255, 255)
            outline_color = (0, 0, 0)
            
            # Calculate text position (centered)
            bbox = draw.textbbox((0, 0), title_short, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = (1200 - text_width) // 2
            y = (630 - text_height) // 2
            
            # Draw text outline
            for adj in range(-2, 3):
                for adj2 in range(-2, 3):
                    draw.text((x + adj, y + adj2), title_short, font=font, fill=outline_color)
            
            # Draw main text
            draw.text((x, y), title_short, font=font, fill=text_color)
            
            # Add logo if available
            if os.path.exists(self.logo_path):
                self._add_logo_overlay(img, title)
            
            # Save image
            img.save(output_path, 'JPEG', quality=85)
            logger.info(f"✅ Created custom background image: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creating custom background: {e}")
            return False
