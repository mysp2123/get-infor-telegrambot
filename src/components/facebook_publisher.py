import facebook
import requests
import logging
from typing import Optional, Dict, Any
import time
import os
from io import BytesIO

logger = logging.getLogger(__name__)

class FacebookPublisher:
    """Class để đăng bài tự động lên Facebook"""
    
    def __init__(self, access_token: str, page_id: Optional[str] = None):
        """
        Initialize Facebook Publisher
        
        Args:
            access_token: Facebook Page Access Token
            page_id: Facebook Page ID (optional)
        """
        self.access_token = access_token
        self.page_id = page_id
        self.graph = facebook.GraphAPI(access_token)
        
    def publish_post(self, message: str, image_url: Optional[str] = None, link: Optional[str] = None) -> Dict[str, Any]:
        """
        Đăng bài viết lên Facebook
        
        Args:
            message: Nội dung bài viết
            image_url: URL hình ảnh (optional)
            link: Link đính kèm (optional)
            
        Returns:
            Dict chứa thông tin post đã đăng
        """
        try:
            post_data = {
                'message': message
            }
            
            # Thêm link nếu có
            if link:
                post_data['link'] = link
            
            # Đăng với hình ảnh
            if image_url:
                return self._publish_with_image(message, image_url, link)
            
            # Đăng text only
            target = f"{self.page_id}/feed" if self.page_id else "me/feed"
            result = self.graph.put_object(target, **post_data)
            
            logger.info(f"Post published successfully: {result.get('id')}")
            return {
                'success': True,
                'post_id': result.get('id'),
                'message': 'Post đã được đăng thành công'
            }
            
        except facebook.GraphAPIError as e:
            logger.error(f"Facebook API Error: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Lỗi khi đăng bài lên Facebook'
            }
        except Exception as e:
            logger.error(f"Error publishing post: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Có lỗi xảy ra khi đăng bài'
            }
    
    def _publish_with_image(self, message: str, image_url: str, link: Optional[str] = None) -> Dict[str, Any]:
        """Đăng bài với hình ảnh"""
        try:
            # Download image
            image_response = requests.get(image_url, timeout=30)
            if image_response.status_code != 200:
                raise Exception(f"Cannot download image: HTTP {image_response.status_code}")
            
            # Prepare image data
            image_data = BytesIO(image_response.content)
            
            # Upload photo with message
            target = f"{self.page_id}/photos" if self.page_id else "me/photos"
            
            post_data = {
                'message': message,
                'source': image_data
            }
            
            # Thêm link nếu có
            if link:
                post_data['message'] += f"\n\n🔗 {link}"
            
            result = self.graph.put_photo(**post_data, target=target)
            
            logger.info(f"Photo post published successfully: {result.get('id')}")
            return {
                'success': True,
                'post_id': result.get('id'),
                'message': 'Bài viết với hình ảnh đã được đăng thành công'
            }
            
        except Exception as e:
            logger.error(f"Error publishing photo post: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Có lỗi khi đăng bài với hình ảnh'
            }
    
    def get_page_info(self) -> Dict[str, Any]:
        """Lấy thông tin page"""
        try:
            if not self.page_id:
                return {'success': False, 'message': 'Page ID chưa được cấu hình'}
            
            page_info = self.graph.get_object(self.page_id)
            return {
                'success': True,
                'name': page_info.get('name'),
                'id': page_info.get('id'),
                'likes': page_info.get('fan_count', 0)
            }
        except Exception as e:
            logger.error(f"Error getting page info: {e}")
            return {'success': False, 'error': str(e)}
    
    def schedule_post(self, message: str, publish_time: int, image_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Lên lịch đăng bài
        
        Args:
            message: Nội dung bài viết
            publish_time: Unix timestamp để đăng bài
            image_url: URL hình ảnh (optional)
        """
        try:
            post_data = {
                'message': message,
                'published': False,
                'scheduled_publish_time': publish_time
            }
            
            target = f"{self.page_id}/feed" if self.page_id else "me/feed"
            result = self.graph.put_object(target, **post_data)
            
            return {
                'success': True,
                'post_id': result.get('id'),
                'message': 'Bài viết đã được lên lịch thành công'
            }
            
        except Exception as e:
            logger.error(f"Error scheduling post: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Có lỗi khi lên lịch đăng bài'
            }
