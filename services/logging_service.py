import asyncio
from datetime import datetime
from typing import List, Dict
import gspread
from google.oauth2.service_account import Credentials
from config import Config

class LoggingService:
    def __init__(self):
        self.config = Config()
        self.sheet = None
        self._initialize_sheets()
    
    def _initialize_sheets(self):
        """Initialize Google Sheets connection"""
        try:
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            
            creds = Credentials.from_service_account_file(
                self.config.GOOGLE_CREDENTIALS_PATH, 
                scopes=scopes
            )
            
            client = gspread.authorize(creds)
            self.sheet = client.open_by_key(self.config.GOOGLE_SHEET_ID).sheet1
            
            # Initialize headers if sheet is empty
            if not self.sheet.get_all_values():
                headers = [
                    'Timestamp', 'Event', 'Source', 'User_ID', 'Articles_Count', 
                    'Unique_Count', 'Top_Count', 'Selected_Rank', 'Article_Title', 
                    'Post_Content', 'Edit_Request', 'Revised_Content', 'Approval_Action',
                    'Image_Path', 'Expert_Posts_Count', 'Facebook_Post_ID', 'Post_URL',
                    'Status', 'Error_Message'
                ]
                self.sheet.append_row(headers)
                
        except Exception as e:
            print(f"Error initializing Google Sheets: {e}")
            self.sheet = None
    
    async def log_news_fetch_start(self):
        """Log the start of news fetching"""
        await self._log_event('news_fetch_start', 'system')
    
    async def log_news_fetch_complete(self, article_count: int):
        """Log completion of news fetching"""
        await self._log_event('news_fetch_complete', 'system', articles_count=article_count)
    
    async def log_article_selection(self, rank: int, title: str):
        """Log user's article selection"""
        await self._log_event('article_selection', 'user', 
                            selected_rank=rank, article_title=title)
    
    async def log_post_generation(self, content: str):
        """Log AI post generation"""
        await self._log_event('post_generation', 'ai', post_content=content[:200] + '...')
    
    async def log_publication_success(self, post_id: str):
        """Log successful Facebook publication"""
        await self._log_event('facebook_publish', 'facebook', 
                            facebook_post_id=post_id, status='success')
    
    async def log_error(self, event: str, error_message: str, user_id: int = None):
        """Log error events"""
        await self._log_event(event, 'system', status='error', error_message=error_message, user_id=user_id)
    
    # Enhanced logging methods for News-Facebook AI Agent Workflow
    async def log_workflow_start(self, user_id: int):
        """Log the start of complete workflow"""
        await self._log_event('workflow_start', 'user', user_id=user_id)
    
    async def log_deduplication_ranking(self, total_articles: int, unique_articles: int, top_articles: int, user_id: int):
        """Log deduplication and ranking results"""
        await self._log_event('deduplication_ranking', 'system', 
                            articles_count=total_articles,
                            unique_count=unique_articles,
                            top_count=top_articles,
                            user_id=user_id)
    
    async def log_expert_facebook_check(self, found: bool, post_count: int, user_id: int):
        """Log expert Facebook search results"""
        await self._log_event('expert_facebook_check', 'facebook_scraping',
                            status='success' if found else 'no_posts',
                            expert_posts_count=post_count,
                            user_id=user_id)
    
    async def log_post_approval(self, action: str, user_id: int):
        """Log post approval action"""
        await self._log_event('post_approval', 'user',
                            approval_action=action,
                            user_id=user_id)
    
    async def log_post_edit_request(self, edit_request: str, revised_content: str, user_id: int):
        """Log post edit request and result"""
        await self._log_event('post_edit_request', 'user',
                            edit_request=edit_request[:100],
                            revised_content=revised_content[:200],
                            user_id=user_id)
    
    async def log_image_generation(self, image_path: str, user_id: int):
        """Log successful image generation"""
        await self._log_event('image_generation', 'ai',
                            image_path=image_path,
                            status='success',
                            user_id=user_id)
    
    async def log_image_approval(self, action: str, user_id: int):
        """Log image approval action"""
        await self._log_event('image_approval', 'user',
                            approval_action=action,
                            user_id=user_id)
    
    async def log_publication_success(self, post_id: str, post_url: str, user_id: int):
        """Log successful Facebook publication with URL"""
        await self._log_event('facebook_publish', 'facebook',
                            facebook_post_id=post_id,
                            post_url=post_url,
                            status='success',
                            user_id=user_id)
    
    async def _log_event(self, event: str, source: str, **kwargs):
        """Generic event logging method"""
        if not self.sheet:
            return
        
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            row_data = [
                timestamp,
                event,
                source,
                kwargs.get('user_id', ''),
                kwargs.get('articles_count', ''),
                kwargs.get('unique_count', ''),
                kwargs.get('top_count', ''),
                kwargs.get('selected_rank', ''),
                kwargs.get('article_title', ''),
                kwargs.get('post_content', ''),
                kwargs.get('edit_request', ''),
                kwargs.get('revised_content', ''),
                kwargs.get('approval_action', ''),
                kwargs.get('image_path', ''),
                kwargs.get('expert_posts_count', ''),
                kwargs.get('facebook_post_id', ''),
                kwargs.get('post_url', ''),
                kwargs.get('status', 'in_progress'),
                kwargs.get('error_message', '')
            ]
            
            # Run in thread to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.sheet.append_row, row_data)
            
        except Exception as e:
            print(f"Error logging to Google Sheets: {e}")
