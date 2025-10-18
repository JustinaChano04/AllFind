from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel


class Platform(str, Enum):
    """Supported platforms for search"""
    GOOGLE_DRIVE = "google_drive"
    NOTION = "notion"


class SearchMethod(str, Enum):
    """Available search methods"""
    KEYWORD = "keyword"           # Simple keyword matching
    SEMANTIC = "semantic"         # Semantic/embedding-based search
    FULL_TEXT = "full_text"       # Full-text search
    METADATA = "metadata"         # Search by metadata (date, author, etc.)


class SearchQuery(BaseModel):
    """Query model for search requests"""
    query: str
    platform: Optional[Platform] = None  # If None, search all platforms
    method: Optional[SearchMethod] = None  # If None, orchestrator decides
    filters: Optional[Dict[str, Any]] = None
    limit: int = 10


class SearchResult(BaseModel):
    """Individual search result"""
    id: str
    title: str
    content: Optional[str] = None
    url: str
    platform: Platform
    score: float
    metadata: Dict[str, Any] = {}


class SearchResponse(BaseModel):
    """Response model for search results"""
    results: List[SearchResult]
    query: SearchQuery
    total_results: int
    platforms_searched: List[Platform]
    method_used: SearchMethod
