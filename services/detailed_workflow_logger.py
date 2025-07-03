# 📊 DETAILED WORKFLOW CSV LOGGER
# Real-time logging for complete News-Facebook AI workflow

import csv
import json
import os
import threading
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

class DetailedWorkflowLogger:
    """
    Detailed real-time CSV logger for tracking complete workflow process
    Records each step with comprehensive data as requested
    """
    
    def __init__(self, csv_file_path: str = "data/detailed_workflow_log.csv"):
        self.csv_file_path = csv_file_path
        self.lock = threading.Lock()
        self.session_id = None
        self._ensure_csv_file()
        
    def _ensure_csv_file(self):
        """Ensure CSV file exists with comprehensive headers"""
        if not os.path.exists(self.csv_file_path):
            os.makedirs(os.path.dirname(self.csv_file_path), exist_ok=True)
            
            headers = [
                'timestamp',
                'session_id',
                'user_id',
                'step_category',
                'step_action',
                'source',
                'articles_count',
                'article_summaries',
                'relevance_scores',
                'appeal_scores',
                'user_selection_rank',
                'ai_call_timestamp',
                'ai_retries',
                'caption_text',
                'approval_action',
                'content_changes',
                'image_api_timestamp',
                'image_retries',
                'image_url_or_id',
                'image_approval_action',
                'new_image_prompt',
                'facebook_post_id',
                'publish_timestamp',
                'api_response_status',
                'error_message',
                'retry_count',
                'duration_ms',
                'metadata'
            ]
            
            with open(self.csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(headers)
    
    def start_new_session(self, user_id: int) -> str:
        """Start a new workflow session"""
        self.session_id = f"{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self._log_event(
            user_id=user_id,
            step_category='workflow_start',
            step_action='session_started'
        )
        return self.session_id
    
    def _log_event(self, user_id: int, step_category: str, step_action: str, **kwargs):
        """Internal method to log events to CSV"""
        with self.lock:
            try:
                timestamp = datetime.now().isoformat()
                
                # Default values for all fields
                row_data = {
                    'timestamp': timestamp,
                    'session_id': self.session_id or f"{user_id}_no_session",
                    'user_id': user_id,
                    'step_category': step_category,
                    'step_action': step_action,
                    'source': kwargs.get('source', ''),
                    'articles_count': kwargs.get('articles_count', ''),
                    'article_summaries': json.dumps(kwargs.get('article_summaries', []), ensure_ascii=False) if kwargs.get('article_summaries') else '',
                    'relevance_scores': json.dumps(kwargs.get('relevance_scores', []), ensure_ascii=False) if kwargs.get('relevance_scores') else '',
                    'appeal_scores': json.dumps(kwargs.get('appeal_scores', []), ensure_ascii=False) if kwargs.get('appeal_scores') else '',
                    'user_selection_rank': kwargs.get('user_selection_rank', ''),
                    'ai_call_timestamp': kwargs.get('ai_call_timestamp', ''),
                    'ai_retries': kwargs.get('ai_retries', ''),
                    'caption_text': kwargs.get('caption_text', ''),
                    'approval_action': kwargs.get('approval_action', ''),
                    'content_changes': kwargs.get('content_changes', ''),
                    'image_api_timestamp': kwargs.get('image_api_timestamp', ''),
                    'image_retries': kwargs.get('image_retries', ''),
                    'image_url_or_id': kwargs.get('image_url_or_id', ''),
                    'image_approval_action': kwargs.get('image_approval_action', ''),
                    'new_image_prompt': kwargs.get('new_image_prompt', ''),
                    'facebook_post_id': kwargs.get('facebook_post_id', ''),
                    'publish_timestamp': kwargs.get('publish_timestamp', ''),
                    'api_response_status': kwargs.get('api_response_status', ''),
                    'error_message': kwargs.get('error_message', ''),
                    'retry_count': kwargs.get('retry_count', ''),
                    'duration_ms': kwargs.get('duration_ms', ''),
                    'metadata': json.dumps(kwargs.get('metadata', {}), ensure_ascii=False) if kwargs.get('metadata') else ''
                }
                
                # Write to CSV
                with open(self.csv_file_path, 'a', newline='', encoding='utf-8') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=row_data.keys())
                    writer.writerow(row_data)
                    
                logger.info(f"📊 Detailed log: {step_category}.{step_action} - User {user_id}")
                    
            except Exception as e:
                logger.error(f"❌ Error in detailed logging: {e}")
    
    # =================================
    # 1. NEWS FETCH LOGGING
    # =================================
    
    def log_news_fetch_start(self, user_id: int, sources: List[str]):
        """Log start of news fetching"""
        self._log_event(
            user_id=user_id,
            step_category='news_fetch',
            step_action='fetch_started',
            source=', '.join(sources),
            metadata={'sources_list': sources}
        )
    
    def log_news_fetch_complete(self, user_id: int, source: str, articles_count: int, 
                               duration_ms: int, articles_data: Optional[List[Dict]] = None):
        """Log completion of news fetching"""
        summaries = []
        relevance_scores = []
        appeal_scores = []
        
        if articles_data:
            for article in articles_data:
                summaries.append(article.get('summary', article.get('title', '')))
                relevance_scores.append(article.get('relevance_score', 0))
                appeal_scores.append(article.get('appeal_score', 0))
        
        self._log_event(
            user_id=user_id,
            step_category='news_fetch',
            step_action='fetch_completed',
            source=source,
            articles_count=articles_count,
            article_summaries=summaries,
            relevance_scores=relevance_scores,
            appeal_scores=appeal_scores,
            duration_ms=duration_ms
        )
    
    # =================================
    # 2. DEDUPLICATION & RANKING
    # =================================
    
    def log_deduplication_ranking(self, user_id: int, original_count: int, 
                                 final_count: int, ranked_articles: List[Dict],
                                 duration_ms: int):
        """Log deduplication and ranking process"""
        summaries = [article.get('summary', article.get('title', '')) for article in ranked_articles]
        relevance_scores = [article.get('relevance_score', 0) for article in ranked_articles]
        appeal_scores = [article.get('appeal_score', 0) for article in ranked_articles]
        
        self._log_event(
            user_id=user_id,
            step_category='deduplication_ranking',
            step_action='ranking_completed',
            articles_count=final_count,
            article_summaries=summaries,
            relevance_scores=relevance_scores,
            appeal_scores=appeal_scores,
            duration_ms=duration_ms,
            metadata={
                'original_count': original_count,
                'deduplication_removed': original_count - final_count,
                'ranking_algorithm': 'relevance_appeal_combined'
            }
        )
    
    # =================================
    # 3. USER SELECTION
    # =================================
    
    def log_user_selection(self, user_id: int, selected_rank: int, selected_article: Dict):
        """Log user article selection"""
        self._log_event(
            user_id=user_id,
            step_category='user_selection',
            step_action='article_selected',
            user_selection_rank=selected_rank,
            caption_text=selected_article.get('title', ''),
            metadata={'selected_article': selected_article}
        )
    
    # =================================
    # 4. CAPTION DRAFT (AI GENERATION)
    # =================================
    
    def log_caption_draft_start(self, user_id: int, ai_provider: str):
        """Log start of AI caption generation"""
        self._log_event(
            user_id=user_id,
            step_category='caption_draft',
            step_action='ai_call_started',
            ai_call_timestamp=datetime.now().isoformat(),
            ai_retries=0,
            metadata={'ai_provider': ai_provider}
        )
    
    def log_caption_draft_retry(self, user_id: int, retry_count: int, error_message: str):
        """Log AI caption generation retry"""
        self._log_event(
            user_id=user_id,
            step_category='caption_draft',
            step_action='ai_call_retry',
            ai_retries=retry_count,
            error_message=error_message,
            retry_count=retry_count
        )
    
    def log_caption_draft_complete(self, user_id: int, final_caption: str, 
                                  total_retries: int, duration_ms: int):
        """Log completion of AI caption generation"""
        self._log_event(
            user_id=user_id,
            step_category='caption_draft',
            step_action='ai_generation_completed',
            ai_retries=total_retries,
            caption_text=final_caption,
            duration_ms=duration_ms
        )
    
    # =================================
    # 5. CAPTION APPROVAL
    # =================================
    
    def log_caption_approval_action(self, user_id: int, approval_action: str, 
                                   content_changes: str = '', new_caption: str = ''):
        """Log each caption approval action"""
        self._log_event(
            user_id=user_id,
            step_category='caption_approval',
            step_action=approval_action,
            approval_action=approval_action,
            content_changes=content_changes,
            caption_text=new_caption if new_caption else ''
        )
    
    # =================================
    # 6. IMAGE GENERATION
    # =================================
    
    def log_image_generation_start(self, user_id: int, image_provider: str, prompt: str):
        """Log start of image generation"""
        self._log_event(
            user_id=user_id,
            step_category='image_generation',
            step_action='api_call_started',
            image_api_timestamp=datetime.now().isoformat(),
            image_retries=0,
            new_image_prompt=prompt,
            metadata={'image_provider': image_provider}
        )
    
    def log_image_generation_retry(self, user_id: int, retry_count: int, 
                                  error_message: str, new_prompt: str = ''):
        """Log image generation retry"""
        self._log_event(
            user_id=user_id,
            step_category='image_generation',
            step_action='api_call_retry',
            image_retries=retry_count,
            error_message=error_message,
            retry_count=retry_count,
            new_image_prompt=new_prompt if new_prompt else ''
        )
    
    def log_image_generation_complete(self, user_id: int, image_url_or_id: str,
                                     total_retries: int, duration_ms: int):
        """Log completion of image generation"""
        self._log_event(
            user_id=user_id,
            step_category='image_generation',
            step_action='generation_completed',
            image_retries=total_retries,
            image_url_or_id=image_url_or_id,
            duration_ms=duration_ms
        )
    
    # =================================
    # 7. IMAGE APPROVAL
    # =================================
    
    def log_image_approval_action(self, user_id: int, approval_action: str, 
                                 new_prompt: str = ''):
        """Log each image approval action"""
        self._log_event(
            user_id=user_id,
            step_category='image_approval',
            step_action=approval_action,
            image_approval_action=approval_action,
            new_image_prompt=new_prompt
        )
    
    # =================================
    # 8. PUBLISHING
    # =================================
    
    def log_facebook_publish_start(self, user_id: int):
        """Log start of Facebook publishing"""
        self._log_event(
            user_id=user_id,
            step_category='publishing',
            step_action='publish_started',
            publish_timestamp=datetime.now().isoformat()
        )
    
    def log_facebook_publish_complete(self, user_id: int, post_id: str, 
                                     api_response_status: str, duration_ms: int):
        """Log completion of Facebook publishing"""
        self._log_event(
            user_id=user_id,
            step_category='publishing',
            step_action='publish_completed',
            facebook_post_id=post_id,
            publish_timestamp=datetime.now().isoformat(),
            api_response_status=api_response_status,
            duration_ms=duration_ms
        )
    
    def log_facebook_publish_error(self, user_id: int, error_message: str, 
                                  retry_count: int):
        """Log Facebook publishing error"""
        self._log_event(
            user_id=user_id,
            step_category='publishing',
            step_action='publish_error',
            error_message=error_message,
            retry_count=retry_count,
            api_response_status='error'
        )
    
    # =================================
    # 9. ERRORS & RETRIES
    # =================================
    
    def log_general_error(self, user_id: int, step_category: str, error_message: str,
                         retry_count: int = 0):
        """Log general errors and retries"""
        self._log_event(
            user_id=user_id,
            step_category=step_category,
            step_action='error_occurred',
            error_message=error_message,
            retry_count=retry_count
        )
    
    def log_workflow_complete(self, user_id: int, total_duration_ms: int, final_status: str):
        """Log workflow completion"""
        self._log_event(
            user_id=user_id,
            step_category='workflow_complete',
            step_action='session_completed',
            api_response_status=final_status,
            duration_ms=total_duration_ms,
            metadata={'session_id': self.session_id}
        )
    
    # =================================
    # UTILITY METHODS
    # =================================
    
    def get_session_logs(self, session_id: str) -> List[Dict]:
        """Get all logs for a specific session"""
        try:
            logs = []
            with open(self.csv_file_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if row['session_id'] == session_id:
                        logs.append(row)
            return logs
        except Exception as e:
            logger.error(f"❌ Error reading session logs: {e}")
            return []
    
    def get_user_sessions(self, user_id: int) -> List[str]:
        """Get all session IDs for a user"""
        try:
            sessions = set()
            with open(self.csv_file_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if str(row['user_id']) == str(user_id):
                        sessions.add(row['session_id'])
            return list(sessions)
        except Exception as e:
            logger.error(f"❌ Error reading user sessions: {e}")
            return [] 