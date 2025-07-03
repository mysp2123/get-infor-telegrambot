import aiohttp
from typing import Dict, Optional
from config import Config
import os
import logging

logger = logging.getLogger(__name__)

class FacebookService:
    def __init__(self):
        self.config = Config()
        self.base_url = "https://graph.facebook.com/v18.0"
        self._page_access_token = None  # Cache for page access token
    
    async def get_page_access_token(self) -> Optional[str]:
        """Get Page Access Token using User Access Token"""
        if self._page_access_token:
            return self._page_access_token
            
        try:
            # Get user's pages and their access tokens
            url = f"{self.base_url}/me/accounts"
            params = {
                'access_token': self.config.FACEBOOK_ACCESS_TOKEN
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    response_data = await response.json()
                    
                    if response.status == 200:
                        pages = response_data.get('data', [])
                        
                        # Find our target page
                        for page in pages:
                            if page.get('id') == self.config.FACEBOOK_PAGE_ID:
                                page_access_token = page.get('access_token')
                                logger.info(f"✅ Got Page Access Token for page: {page.get('name')}")
                                self._page_access_token = page_access_token
                                return page_access_token
                        
                        logger.error(f"❌ Page {self.config.FACEBOOK_PAGE_ID} not found in user's pages")
                        return None
                    else:
                        logger.error(f"❌ Failed to get page access token: {response_data}")
                        return None
                        
        except Exception as e:
            logger.error(f"❌ Error getting page access token: {e}")
            return None
    
    async def check_token_permissions(self) -> Dict:
        """Check what permissions the current access token has"""
        try:
            url = f"{self.base_url}/me/permissions"
            params = {
                'access_token': self.config.FACEBOOK_ACCESS_TOKEN
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    response_data = await response.json()
                    
                    if response.status == 200:
                        permissions = response_data.get('data', [])
                        granted_permissions = [p['permission'] for p in permissions if p['status'] == 'granted']
                        
                        logger.info(f"✅ Current token permissions: {granted_permissions}")
                        
                        # Check for required permissions
                        required_permissions = ['pages_manage_posts', 'pages_read_engagement']
                        missing_permissions = [p for p in required_permissions if p not in granted_permissions]
                        
                        if missing_permissions:
                            logger.warning(f"⚠️ Missing required permissions: {missing_permissions}")
                        
                        return {
                            "success": True,
                            "granted_permissions": granted_permissions,
                            "missing_permissions": missing_permissions,
                            "has_required_permissions": len(missing_permissions) == 0
                        }
                    else:
                        logger.error(f"❌ Failed to check permissions: {response_data}")
                        return {"success": False, "error": "Failed to check permissions"}
        except Exception as e:
            logger.error(f"❌ Error checking permissions: {e}")
            return {"success": False, "error": str(e)}
    
    async def publish_post(self, content: str, image_path: Optional[str] = None) -> Dict:
        """Publish post to Facebook page"""
        try:
            if not self.config.FACEBOOK_PAGE_ID:
                logger.error("❌ No Facebook page ID configured")
                return {"success": False, "error": "No Facebook page ID configured"}
            
            logger.info(f"📱 Publishing to Facebook page ID: {self.config.FACEBOOK_PAGE_ID}")
            
            # Try to use direct Page Access Token first (preferred method)
            page_access_token = self.config.FACEBOOK_PAGE_ACCESS_TOKEN
            
            if page_access_token:
                logger.info("✅ Using direct Page Access Token")
            else:
                # Fallback: Get Page Access Token from User Access Token
                if not self.config.FACEBOOK_ACCESS_TOKEN:
                    logger.error("❌ No Facebook access token configured")
                    return {"success": False, "error": "No Facebook access token configured"}
                
                logger.info("🔄 Getting Page Access Token from User Access Token...")
                page_access_token = await self.get_page_access_token()
                if not page_access_token:
                    error_msg = "❌ Could not obtain Page Access Token. Make sure your User Access Token has 'pages_show_list' permission and you are an admin of the page."
                    logger.error(error_msg)
                    return {"success": False, "error": error_msg}
            
            if image_path and os.path.exists(image_path):
                logger.info("🖼️ Publishing with image")
                return await self._publish_with_image(content, image_path, page_access_token)
            else:
                logger.info("📝 Publishing text-only post")
                return await self._publish_text_only(content, page_access_token)
        except Exception as e:
            logger.error(f"❌ Facebook publishing error: {e}")
            return {"success": False, "error": str(e)}
    
    async def _publish_text_only(self, content: str, page_access_token: str) -> Dict:
        """Publish text-only post using Page Access Token"""
        url = f"{self.base_url}/{self.config.FACEBOOK_PAGE_ID}/feed"
        
        data = {
            'message': content,
            'access_token': page_access_token  # Use Page Access Token instead of User Access Token
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data) as response:
                response_data = await response.json()
                
                if response.status == 200:
                    post_id = response_data.get('id', '')
                    post_url = f"https://facebook.com/{post_id}"
                    
                    logger.info(f"✅ Text post published successfully: {post_id}")
                    return {
                        "success": True,
                        "post_id": post_id,
                        "post_url": post_url
                    }
                else:
                    error_info = response_data.get('error', {})
                    error_message = error_info.get('message', 'Unknown error')
                    error_code = error_info.get('code', 'Unknown')
                    
                    # Handle specific permission errors
                    if 'publish_actions' in error_message and 'deprecated' in error_message:
                        error_message = "❌ Your Facebook access token was created with deprecated 'publish_actions' permission. Please create a new access token with 'pages_manage_posts' and 'pages_read_engagement' permissions instead."
                    elif 'pages_manage_posts' in error_message:
                        error_message = "❌ Missing Facebook permissions. Token needs 'pages_manage_posts' and 'pages_read_engagement' permissions."
                    elif 'OAuthException' in error_info.get('type', ''):
                        if 'publish_actions' in error_message:
                            error_message = "❌ Your access token uses deprecated permissions. Please regenerate it with 'pages_manage_posts' and 'pages_read_engagement' permissions."
                        else:
                            error_message = f"❌ Facebook OAuth Error: {error_message}"
                    
                    logger.error(f"❌ Facebook API error {error_code}: {error_message}")
                    return {
                        "success": False,
                        "error": error_message
                    }
    
    async def _publish_with_image(self, content: str, image_path: str, page_access_token: str) -> Dict:
        """Publish post with image using Page Access Token"""
        # Upload image to page using Page Access Token
        photo_upload_url = f"{self.base_url}/{self.config.FACEBOOK_PAGE_ID}/photos"
        
        data = aiohttp.FormData()
        data.add_field('message', content)
        data.add_field('access_token', page_access_token)  # Use Page Access Token instead of User Access Token
        data.add_field('published', 'true')
        
        with open(image_path, 'rb') as f:
            data.add_field('source', f, filename='image.jpg', content_type='image/jpeg')
            
            async with aiohttp.ClientSession() as session:
                async with session.post(photo_upload_url, data=data) as response:
                    response_data = await response.json()
                    
                    if response.status == 200:
                        post_id = response_data.get('id', '')
                        post_url = f"https://facebook.com/{post_id}"
                        
                        logger.info(f"✅ Image post published successfully: {post_id}")
                        return {
                            "success": True,
                            "post_id": post_id,
                            "post_url": post_url
                        }
                    else:
                        error_info = response_data.get('error', {})
                        error_message = error_info.get('message', 'Unknown error')
                        error_code = error_info.get('code', 'Unknown')
                        
                        # Handle specific permission errors
                        if 'publish_actions' in error_message and 'deprecated' in error_message:
                            error_message = "❌ Your Facebook access token was created with deprecated 'publish_actions' permission. Please create a new access token with 'pages_manage_posts' and 'pages_read_engagement' permissions instead."
                        elif 'pages_manage_posts' in error_message:
                            error_message = "❌ Missing Facebook permissions. Token needs 'pages_manage_posts' and 'pages_read_engagement' permissions."
                        elif 'OAuthException' in error_info.get('type', ''):
                            if 'publish_actions' in error_message:
                                error_message = "❌ Your access token uses deprecated permissions. Please regenerate it with 'pages_manage_posts' and 'pages_read_engagement' permissions."
                            else:
                                error_message = f"❌ Facebook OAuth Error: {error_message}"
                        
                        logger.error(f"❌ Facebook API error {error_code}: {error_message}")
                        return {
                            "success": False,
                            "error": error_message
                        }
