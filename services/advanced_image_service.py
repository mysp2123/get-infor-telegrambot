import re
import os
import time
import base64
import io
import asyncio
import aiohttp
import json
from typing import Dict, List, Optional, Any
from PIL import Image
import logging

logger = logging.getLogger(__name__)

class AdvancedImageService:
    """Enhanced image generation service with multiple AI providers"""
    
    def __init__(self):
        self.generated_images_dir = "generated_images"
        self._ensure_directory_exists()
        
        # Image generation APIs configuration
        self.image_apis = {
            'stability': {
                'enabled': True,
                'priority': 1,  # Highest priority
                'url': 'https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image',
                'keys': [os.getenv('STABILITY_API_KEY')]
            },
            'flux_schnell': {
                'enabled': True,
                'priority': 2,
                'url': 'https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell',
                'keys': [os.getenv('HUGGINGFACE_API_KEY')]
            }
        }
        
        # Initialize API health tracking
        self._initialize_api_health()

    def _ensure_directory_exists(self):
        """Ensure generated images directory exists"""
        if not os.path.exists(self.generated_images_dir):
            os.makedirs(self.generated_images_dir)

    def _initialize_api_health(self):
        """Initialize API health tracking"""
        self.api_health = {}
        for api_name in self.image_apis:
            self.api_health[api_name] = {
                'success_count': 0,
                'error_count': 0,
                'last_error': None,
                'current_key_index': 0
            }

    def _get_next_api_key(self, api_name: str) -> Optional[str]:
        """Get next available API key for rotation"""
        api_config = self.image_apis.get(api_name, {})
        keys = api_config.get('keys', [])
        
        if not keys or not any(keys):
            return None
            
        health = self.api_health[api_name]
        current_index = health['current_key_index']
        
        # Try current key first
        if current_index < len(keys) and keys[current_index]:
            return keys[current_index]
        
        # Find next available key
        for i in range(len(keys)):
            if keys[i]:
                health['current_key_index'] = i
                return keys[i]
        
        return None

    def _mark_api_error(self, api_name: str, error: str):
        """Mark API as having error"""
        if api_name in self.api_health:
            health = self.api_health[api_name]
            health['error_count'] += 1
            health['last_error'] = error

    def _mark_api_success(self, api_name: str):
        """Mark API as successful"""
        if api_name in self.api_health:
            self.api_health[api_name]['success_count'] += 1

    async def generate_image(self, title: str, content: str, context: Optional[Dict] = None) -> Optional[str]:
        """Generate image using multiple AI providers with Google Imagen priority"""
        try:
            logger.info(f"🎨 Starting image generation for: {title[:50]}...")
            
            # Generate optimized prompts
            prompt_data = await self._generate_optimized_prompts(title, content, context or {})
            
            # Try AI generation with priority order
            image_path = await self._try_ai_generation_with_priority(prompt_data, context or {})
            
            if image_path:
                logger.info(f"✅ Successfully generated image: {image_path}")
                return image_path
            else:
                logger.warning("⚠️ All AI providers failed, no image generated")
                return None
                
        except Exception as e:
            logger.error(f"❌ Image generation failed: {e}")
            return None

    async def _generate_optimized_prompts(self, title: str, content: str, context: Dict) -> Dict:
        """Generate optimized prompts for image generation"""
        try:
            # Extract keywords and visual elements
            keywords = self._extract_keywords_from_content(title, content)
            visual_elements = self._identify_visual_elements(title, content)
            
            # Construct positive prompt with enhanced elements
            positive_elements = []
            
            # Main subject based on content
            main_subject = self._extract_main_subject(title, keywords)
            if main_subject:
                positive_elements.append(main_subject)
            
            # Add human elements for people-related content
            if any(word in title.lower() + ' '.join(keywords) for word in 
                  ['trump', 'president', 'leader', 'ceo', 'people', 'person', 'human', 'man', 'woman']):
                positive_elements.append('realistic human figures, professional portrait style, authentic expressions')
            
            # Add specific visual elements
            if visual_elements:
                positive_elements.append(f"featuring {', '.join(visual_elements[:3])}")
            
            # Add keywords for context
            if keywords:
                positive_elements.append(f"related to {', '.join(keywords[:3])}")
            
            # Enhanced style and quality modifiers
            positive_elements.append('professional photography, photorealistic, high quality, detailed, sharp focus')
            positive_elements.append('good composition, professional lighting, high resolution, vibrant colors')
            positive_elements.append('news photography style, journalistic quality, compelling visual narrative')
            
            # Combine into final prompt
            positive_prompt = ', '.join(positive_elements)
            
            # Negative prompt
            negative_prompt = ('low quality, blurry, distorted, cartoon, anime, sketch, watermark, '
                             'text overlay, inappropriate content, nsfw, violent, disturbing')
            
            return {
                'positive_prompt': positive_prompt,
                'negative_prompt': negative_prompt
            }
            
        except Exception as e:
            logger.error(f"❌ Error generating prompts: {e}")
            return {
                'positive_prompt': f"professional illustration representing {title}, high quality, detailed",
                'negative_prompt': 'low quality, blurry, distorted'
            }

    def _extract_keywords_from_content(self, title: str, content: str) -> List[str]:
        """Extract meaningful keywords from content"""
        text = f"{title} {content}".lower()
        
        # Vietnamese to English translation for common terms
        translations = {
            'kinh tế': 'economy', 'chính trị': 'politics', 'công nghệ': 'technology',
            'thể thao': 'sports', 'giáo dục': 'education', 'y tế': 'healthcare',
            'môi trường': 'environment', 'xã hội': 'society', 'kinh doanh': 'business'
        }
        
        # Extract Vietnamese keywords and translate
        keywords = []
        for vn_word, en_word in translations.items():
            if vn_word in text:
                keywords.append(en_word)
        
        # Extract English words
        english_words = re.findall(r'\b[a-zA-Z]{4,}\b', text)
        keywords.extend([word for word in english_words if len(word) > 3][:5])
        
        return list(set(keywords))[:5]

    def _identify_visual_elements(self, title: str, content: str) -> List[str]:
        """Identify visual elements for the image"""
        text = (title + " " + content).lower()
        visual_elements = []
        
        # Map concepts to visual elements
        visual_maps = {
            'economy': ['business charts', 'office buildings', 'financial graphs'],
            'politics': ['government building', 'meeting room', 'official documents'],
            'technology': ['modern devices', 'computer screens', 'digital interface'],
            'sports': ['athletic equipment', 'stadium', 'sports action'],
            'education': ['classroom', 'books', 'learning environment'],
            'healthcare': ['medical equipment', 'hospital', 'healthcare workers'],
            'business': ['office space', 'business meeting', 'corporate environment']
        }
        
        for concept, elements in visual_maps.items():
            if concept in text:
                visual_elements.extend(elements[:2])
        
        return visual_elements[:3]

    def _extract_main_subject(self, title: str, keywords: List[str]) -> str:
        """Extract main subject for the image"""
        title_lower = title.lower()
        
        subject_patterns = {
            'technology': 'modern technology concept',
            'business': 'business professional scene',
            'economy': 'economic and financial concept',
            'education': 'educational environment',
            'healthcare': 'medical and healthcare scene',
            'sports': 'athletic and sports scene'
        }
        
        for pattern, subject in subject_patterns.items():
            if pattern in title_lower or pattern in keywords:
                return subject
        
        return "professional news illustration"

    async def _try_ai_generation_with_priority(self, prompt_data: Dict, context: Dict) -> Optional[str]:
        """Try AI generation with priority order"""
        # Sort APIs by priority
        available_apis = []
        for api_name, config in self.image_apis.items():
            if config.get('enabled', False) and self._get_next_api_key(api_name):
                priority = config.get('priority', 999)
                available_apis.append((priority, api_name))
        
        available_apis.sort(key=lambda x: x[0])
        
        for priority, api_name in available_apis:
            try:
                logger.info(f"🔄 Trying {api_name} (priority: {priority})")
                
                image_path = await self._generate_with_api(api_name, prompt_data)
                
                if image_path:
                    self._mark_api_success(api_name)
                    logger.info(f"✅ Successfully generated image with {api_name}")
                    return image_path
                    
            except Exception as e:
                error_msg = str(e)
                self._mark_api_error(api_name, error_msg)
                logger.warning(f"⚠️ {api_name} failed: {error_msg}")
                continue
        
        return None

    async def _generate_with_api(self, api_name: str, prompt_data: Dict) -> Optional[str]:
        """Generate image with specific API"""
        try:
            if api_name == 'stability':
                return await self._generate_stability_ai(prompt_data)
            elif api_name == 'flux_schnell':
                return await self._generate_huggingface_flux(prompt_data)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ {api_name} generation failed: {e}")
            return None



    async def _generate_stability_ai(self, prompt_data: Dict) -> Optional[str]:
        """Generate with Stability AI"""
        try:
            api_key = self._get_next_api_key('stability')
            if not api_key:
                raise Exception("No Stability AI API key available")
            
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            payload = {
                'text_prompts': [
                    {
                        'text': prompt_data['positive_prompt'],
                        'weight': 1.0
                    },
                    {
                        'text': prompt_data['negative_prompt'],
                        'weight': -1.0
                    }
                ],
                'cfg_scale': 7,
                'height': 1024,
                'width': 1024,
                'samples': 1,
                'steps': 30,
                'style_preset': 'photographic'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.image_apis['stability']['url'],
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        
                        if 'artifacts' in result and result['artifacts']:
                            image_data = result['artifacts'][0]['base64']
                            
                            image_bytes = base64.b64decode(image_data)
                            image = Image.open(io.BytesIO(image_bytes))
                            
                            timestamp = int(time.time())
                            filename = f"stability_{timestamp}.png"
                            filepath = os.path.join(self.generated_images_dir, filename)
                            image.save(filepath)
                            
                            # Add company logo
                            filepath_with_logo = await self._add_company_logo(filepath)
                            
                            return filepath_with_logo
                    else:
                        error_text = await response.text()
                        raise Exception(f"Stability AI error {response.status}: {error_text}")
                        
        except Exception as e:
            logger.error(f"❌ Stability AI generation failed: {e}")
            raise e
    
    async def _add_company_logo(self, image_path: str) -> str:
        """Add company logo to generated image"""
        try:
            from PIL import Image
            
            logo_path = "assets/PioneerX-logo.JPG"
            if not os.path.exists(logo_path):
                logger.warning("⚠️ Company logo not found, skipping logo overlay")
                return image_path
            
            # Open the generated image
            with Image.open(image_path) as img:
                # Open and resize logo
                with Image.open(logo_path) as logo:
                    # Resize logo to be smaller and more subtle
                    logo_size = (120, 120)
                    logo = logo.resize(logo_size, Image.Resampling.LANCZOS)
                    
                    # Convert to RGBA for transparency
                    if logo.mode != 'RGBA':
                        logo = logo.convert('RGBA')
                    
                    if img.mode != 'RGBA':
                        img = img.convert('RGBA')
                    
                    # Position at bottom right
                    logo_pos = (img.width - logo_size[0] - 30, img.height - logo_size[1] - 30)
                    
                    # Paste logo with transparency
                    img.paste(logo, logo_pos, logo)
                    
                    # Convert back to RGB and save
                    final_img = img.convert('RGB')
                    final_img.save(image_path, 'JPEG', quality=95)
                    
                    logger.info("✅ Company logo added successfully")
            
            return image_path
            
        except Exception as e:
            logger.error(f"❌ Error adding company logo: {e}")
            return image_path

    async def _generate_huggingface_flux(self, prompt_data: Dict) -> Optional[str]:
        """Generate with Hugging Face FLUX"""
        try:
            api_key = self._get_next_api_key('flux_schnell')
            if not api_key:
                raise Exception("No Hugging Face API key available")
            
            headers = {'Authorization': f'Bearer {api_key}'}
            payload = {'inputs': prompt_data['positive_prompt']}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.image_apis['flux_schnell']['url'],
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    
                    if response.status == 200:
                        image_bytes = await response.read()
                        image = Image.open(io.BytesIO(image_bytes))
                        
                        timestamp = int(time.time())
                        filename = f"flux_{timestamp}.png"
                        filepath = os.path.join(self.generated_images_dir, filename)
                        image.save(filepath)
                        
                        # Add company logo
                        filepath_with_logo = await self._add_company_logo(filepath)
                        
                        return filepath_with_logo
                    else:
                        error_text = await response.text()
                        raise Exception(f"Hugging Face FLUX error {response.status}: {error_text}")
                        
        except Exception as e:
            logger.error(f"❌ Hugging Face FLUX generation failed: {e}")
            raise e

    def get_api_status(self) -> Dict[str, Any]:
        """Get status of all image generation APIs"""
        status = {}
        for api_name, health in self.api_health.items():
            config = self.image_apis[api_name]
            has_keys = bool(self._get_next_api_key(api_name))
            
            status[api_name] = {
                'enabled': config.get('enabled', False),
                'has_api_keys': has_keys,
                'priority': config.get('priority', 999),
                'success_count': health['success_count'],
                'error_count': health['error_count'],
                'last_error': health['last_error'],
                'status': 'healthy' if has_keys and health['error_count'] < 3 else 'unhealthy'
            }
        
        return status
