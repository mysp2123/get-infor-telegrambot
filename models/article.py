from dataclasses import dataclass
from typing import Optional

@dataclass
class Article:
    title: str
    content: str
    url: str
    source: str
    published_date: str
    thumbnail: Optional[str] = None
    total_score: float = 0.0
    
    def __str__(self):
        return f"{self.title} - {self.source}"
