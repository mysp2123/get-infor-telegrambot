import csv
import json
import os
import threading
from datetime import datetime
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class WorkflowCSVLogger:
    """
    Real-time CSV logger for tracking complete workflow and user decisions
    """
    
    def __init__(self, csv_file_path: str = "data/workflow_realtime_log.csv"):
        self.csv_file_path = csv_file_path
        self.lock = threading.Lock()
        self._ensure_csv_file()
        
    def _ensure_csv_file(self):
        """Ensure CSV file exists with proper headers"""
        if not os.path.exists(self.csv_file_path):
            os.makedirs(os.path.dirname(self.csv_file_path), exist_ok=True)
            
            headers = [
                'timestamp',
                'user_id',
                'step',
                'action',
                'data',
                'status',
                'duration_ms',
                'error',
                'metadata'
            ]
            
            with open(self.csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(headers)
    
    def log_workflow_event(self, user_id: int, step: str, action: str, 
                          data: Optional[Dict[str, Any]] = None, status: str = 'success',
                          duration_ms: int = 0, error: Optional[str] = None, 
                          metadata: Optional[Dict[str, Any]] = None):
        """
        Log a workflow event to CSV
        
        Args:
            user_id: User ID
            step: Workflow step (step1_fetch_news, step2_search_blogs, etc.)
            action: Specific action (start, complete, user_selection, etc.)
            data: Event data
            status: Event status (success, error, in_progress)
            duration_ms: Duration in milliseconds
            error: Error message if any
            metadata: Additional metadata
        """
        with self.lock:
            try:
                timestamp = datetime.now().isoformat()
                
                # Convert data and metadata to JSON strings
                data_json = json.dumps(data, ensure_ascii=False) if data else ''
                metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata else ''
                
                row = [
                    timestamp,
                    user_id,
                    step,
                    action,
                    data_json,
                    status,
                    duration_ms,
                    error or '',
                    metadata_json
                ]
                
                with open(self.csv_file_path, 'a', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(row)
                    
                logger.info(f"📊 Logged workflow event: user={user_id}, step={step}, action={action}, status={status}")
                    
            except Exception as e:
                logger.error(f"❌ Error logging workflow event: {e}")
    
    # Workflow Step Logging Methods
    
    def log_workflow_start(self, user_id: int):
        """Log workflow start"""
        self.log_workflow_event(
            user_id=user_id,
            step='workflow_start',
            action='start',
            data={'workflow_type': 'enhanced_rss_workflow'},
            status='started'
        )
    
    def log_step1_fetch_news(self, user_id: int, article_count: int, sources: list, 
                            duration_ms: int, status: str = 'success'):
        """Log Step 1: Fetch news from RSS sources"""
        self.log_workflow_event(
            user_id=user_id,
            step='step1_fetch_news',
            action='fetch_complete',
            data={
                'article_count': article_count,
                'sources': sources,
                'method': 'enhanced_rss_ultra_summary'
            },
            status=status,
            duration_ms=duration_ms
        )
    
    def log_step2_article_selection(self, user_id: int, selected_rank: int, 
                                   article_title: str, total_articles: int):
        """Log Step 2: User article selection"""
        self.log_workflow_event(
            user_id=user_id,
            step='step2_article_selection',
            action='user_selection',
            data={
                'selected_rank': selected_rank,
                'article_title': article_title,
                'total_articles': total_articles
            },
            status='selected'
        )
    
    def log_step3_international_blogs(self, user_id: int, found_articles: int, 
                                    sources: list, duration_ms: int, status: str = 'success'):
        """Log Step 3: International blog search"""
        self.log_workflow_event(
            user_id=user_id,
            step='step3_international_blogs',
            action='search_complete',
            data={
                'found_articles': found_articles,
                'sources': sources,
                'method': 'rss_international_search'
            },
            status=status,
            duration_ms=duration_ms
        )
    
    def log_step4_writing_style(self, user_id: int, selected_style: str):
        """Log Step 4: User writing style selection"""
        self.log_workflow_event(
            user_id=user_id,
            step='step4_writing_style',
            action='user_selection',
            data={
                'selected_style': selected_style
            },
            status='selected'
        )
    
    def log_step5_content_generation(self, user_id: int, content_length: int, 
                                   ai_provider: str, duration_ms: int, status: str = 'success'):
        """Log Step 5: AI content generation"""
        self.log_workflow_event(
            user_id=user_id,
            step='step5_content_generation',
            action='ai_generation',
            data={
                'content_length': content_length,
                'ai_provider': ai_provider,
                'method': 'enhanced_ai_service'
            },
            status=status,
            duration_ms=duration_ms
        )
    
    def log_step6_content_approval(self, user_id: int, approval_action: str, 
                                 auto_approved: bool = False):
        """Log Step 6: Content approval"""
        self.log_workflow_event(
            user_id=user_id,
            step='step6_content_approval',
            action='approval_decision',
            data={
                'approval_action': approval_action,
                'auto_approved': auto_approved
            },
            status='approved' if approval_action == 'approve' else 'pending'
        )
    
    def log_step7_image_generation(self, user_id: int, image_path: str, 
                                 image_provider: str, duration_ms: int, status: str = 'success'):
        """Log Step 7: Image generation"""
        self.log_workflow_event(
            user_id=user_id,
            step='step7_image_generation',
            action='image_generation',
            data={
                'image_path': image_path,
                'image_provider': image_provider,
                'method': 'advanced_image_service'
            },
            status=status,
            duration_ms=duration_ms
        )
    
    def log_workflow_complete(self, user_id: int, total_duration_ms: int, 
                            final_status: str = 'success'):
        """Log workflow completion"""
        self.log_workflow_event(
            user_id=user_id,
            step='workflow_complete',
            action='complete',
            data={
                'total_duration_ms': total_duration_ms,
                'final_status': final_status
            },
            status=final_status
        )
    
    def log_user_interaction(self, user_id: int, interaction_type: str, 
                           interaction_data: Dict[str, Any]):
        """Log any user interaction"""
        self.log_workflow_event(
            user_id=user_id,
            step='user_interaction',
            action=interaction_type,
            data=interaction_data,
            status='interaction'
        )
    
    def log_error(self, user_id: int, step: str, error_message: str, 
                 error_data: Optional[Dict[str, Any]] = None):
        """Log error events"""
        self.log_workflow_event(
            user_id=user_id,
            step=step,
            action='error',
            data=error_data,
            status='error',
            error=error_message
        )
    
    def get_user_workflow_history(self, user_id: int) -> list:
        """Get workflow history for a specific user"""
        history = []
        
        try:
            with open(self.csv_file_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if int(row['user_id']) == user_id:
                        # Parse JSON data
                        if row['data']:
                            try:
                                row['data'] = json.loads(row['data'])
                            except json.JSONDecodeError:
                                pass
                        if row['metadata']:
                            try:
                                row['metadata'] = json.loads(row['metadata'])
                            except json.JSONDecodeError:
                                pass
                        history.append(row)
        except Exception as e:
            logger.error(f"❌ Error reading workflow history: {e}")
            
        return history
    
    def get_workflow_statistics(self) -> Dict[str, Any]:
        """Get workflow statistics"""
        stats = {
            'total_workflows': 0,
            'completed_workflows': 0,
            'failed_workflows': 0,
            'average_duration_ms': 0,
            'most_selected_writing_style': None,
            'user_count': 0
        }
        
        try:
            with open(self.csv_file_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                workflows = {}
                users = set()
                
                for row in reader:
                    user_id = row['user_id']
                    users.add(user_id)
                    
                    if row['step'] == 'workflow_start':
                        workflows[user_id] = {'status': 'started', 'start_time': row['timestamp']}
                    elif row['step'] == 'workflow_complete':
                        if user_id in workflows:
                            workflows[user_id]['status'] = 'completed'
                            workflows[user_id]['end_time'] = row['timestamp']
                
                stats['total_workflows'] = len(workflows)
                stats['completed_workflows'] = sum(1 for w in workflows.values() if w.get('status') == 'completed')
                stats['failed_workflows'] = stats['total_workflows'] - stats['completed_workflows']
                stats['user_count'] = len(users)
                
        except Exception as e:
            logger.error(f"❌ Error calculating workflow statistics: {e}")
            
        return stats 