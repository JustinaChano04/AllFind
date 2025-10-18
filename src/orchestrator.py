from typing import List, Optional
import re

try:
    from .types import (
        SearchQuery,
        SearchResponse,
        SearchResult,
        Platform,
        SearchMethod
    )
except ImportError:
    from types import (
        SearchQuery,
        SearchResponse,
        SearchResult,
        Platform,
        SearchMethod
    )


class SearchOrchestrator:
    """
    Orchestrator that determines which platform(s) to search
    and which search method to use based on the query.
    """

    def __init__(self):
        # Initialize platform-specific retrievers (to be implemented)
        self.google_drive_retriever = None  # TODO: Implement
        self.notion_retriever = None         # TODO: Implement

    def determine_platforms(self, query: SearchQuery) -> List[Platform]:
        """
        Determine which platform(s) to search based on query.

        If platform is explicitly specified, use that.
        Otherwise, analyze query for platform hints or search all.
        """
        # If platform explicitly specified, use it
        if query.platform:
            return [query.platform]

        platforms = []
        query_lower = query.query.lower()

        # Check for platform-specific keywords
        google_keywords = ['drive', 'docs', 'sheets', 'slides', 'document']
        notion_keywords = ['notion', 'page', 'database', 'workspace']

        has_google_hint = any(keyword in query_lower for keyword in google_keywords)
        has_notion_hint = any(keyword in query_lower for keyword in notion_keywords)

        # If specific platform hinted, prioritize it
        if has_google_hint and not has_notion_hint:
            platforms.append(Platform.GOOGLE_DRIVE)
        elif has_notion_hint and not has_google_hint:
            platforms.append(Platform.NOTION)
        else:
            # Search both platforms if no clear hint or both hinted
            platforms = [Platform.GOOGLE_DRIVE, Platform.NOTION]

        return platforms

    def determine_search_method(self, query: SearchQuery) -> SearchMethod:
        """
        Determine which search method to use based on query characteristics.

        Logic:
        - If method explicitly specified, use it
        - If query contains quotes, use full-text search
        - If query has metadata filters (date, author), use metadata search
        - If query is conceptual/question-like, use semantic search
        - Otherwise, use keyword search
        """
        # If method explicitly specified, use it
        if query.method:
            return query.method

        query_text = query.query.strip()

        # Check for quoted phrases (exact match needed)
        if '"' in query_text or "'" in query_text:
            return SearchMethod.FULL_TEXT

        # Check if metadata filters are provided
        if query.filters and any(
            key in query.filters
            for key in ['date', 'author', 'modified_date', 'created_date', 'owner']
        ):
            return SearchMethod.METADATA

        # Check for question-like queries (semantic search works better)
        question_patterns = [
            r'^\s*(what|how|why|when|where|who)',
            r'\?$',
            r'explain|describe|tell me about'
        ]
        if any(re.search(pattern, query_text, re.IGNORECASE) for pattern in question_patterns):
            return SearchMethod.SEMANTIC

        # Check if query is long and conceptual (semantic search)
        words = query_text.split()
        if len(words) > 8:
            return SearchMethod.SEMANTIC

        # Default to keyword search for simple queries
        return SearchMethod.KEYWORD

    def search(self, query: SearchQuery) -> SearchResponse:
        """
        Main orchestration method that determines platforms and method,
        then executes the search and aggregates results.
        """
        # Determine which platforms to search
        platforms = self.determine_platforms(query)

        # Determine which search method to use
        method = self.determine_search_method(query)

        # Execute search on each platform
        all_results: List[SearchResult] = []

        for platform in platforms:
            platform_results = self._search_platform(
                query=query,
                platform=platform,
                method=method
            )
            all_results.extend(platform_results)

        # Sort by score (descending) and limit results
        all_results.sort(key=lambda x: x.score, reverse=True)
        limited_results = all_results[:query.limit]

        return SearchResponse(
            results=limited_results,
            query=query,
            total_results=len(all_results),
            platforms_searched=platforms,
            method_used=method
        )

    def _search_platform(
        self,
        query: SearchQuery,
        platform: Platform,
        method: SearchMethod
    ) -> List[SearchResult]:
        """
        Execute search on a specific platform using specified method.
        """
        if platform == Platform.GOOGLE_DRIVE:
            if not self.google_drive_retriever:
                # TODO: Initialize retriever if not done
                return []
            return self._search_google_drive(query, method)

        elif platform == Platform.NOTION:
            if not self.notion_retriever:
                # TODO: Initialize retriever if not done
                return []
            return self._search_notion(query, method)

        return []

    def _search_google_drive(
        self,
        query: SearchQuery,
        method: SearchMethod
    ) -> List[SearchResult]:
        """Search Google Drive using specified method."""
        # TODO: Implement Google Drive search
        # This will call the appropriate retriever method based on SearchMethod
        return []

    def _search_notion(
        self,
        query: SearchQuery,
        method: SearchMethod
    ) -> List[SearchResult]:
        """Search Notion using specified method."""
        # TODO: Implement Notion search
        # This will call the appropriate retriever method based on SearchMethod
        return []


# Example usage
if __name__ == "__main__":
    orchestrator = SearchOrchestrator()

    # Test different query types
    test_queries = [
        # Semantic search queries (conceptual/question-like)
        SearchQuery(query="give me content from my tiktok interview"),
        SearchQuery(query="what hikes do i have planned for west virginia?"),
        SearchQuery(query="how do I set up authentication for my app?"),
        SearchQuery(query="explain the architecture of our microservices"),
        SearchQuery(query="why did we choose React over Vue?"),
        SearchQuery(query="when is the product launch scheduled?"),
        SearchQuery(query="where can I find the design system documentation?"),
        SearchQuery(query="who is responsible for the backend infrastructure?"),
        SearchQuery(query="tell me about our Q4 goals and objectives"),
        SearchQuery(query="describe the onboarding process for new engineers"),

        # Full-text search queries (exact matches with quotes)
        SearchQuery(query='"robotics"'),
        SearchQuery(query='"machine learning pipeline"'),
        SearchQuery(query="'API documentation'"),
        SearchQuery(query='"budget 2024"'),
        SearchQuery(query='"team standup notes"'),

        # Platform-specific queries
        SearchQuery(query="find my google docs"),
        SearchQuery(query="search drive for slides"),
        SearchQuery(query="google sheets with sales data"),
        SearchQuery(query="notion page about api"),
        SearchQuery(query="find database in notion workspace"),
        SearchQuery(query="my notion pages on project planning"),

        # Metadata search queries (with filters)
        SearchQuery(query="meeting notes", filters={"author": "john@example.com"}),
        SearchQuery(query="reports", filters={"date": "2024-01", "owner": "sarah"}),
        SearchQuery(query="presentations", filters={"modified_date": "2024-03"}),
        SearchQuery(query="documents", filters={"created_date": "2024-02", "author": "mike"}),

        # Keyword search queries (simple, short queries)
        SearchQuery(query="budget"),
        SearchQuery(query="roadmap 2024"),
        SearchQuery(query="team photo"),
        SearchQuery(query="sprint planning"),
        SearchQuery(query="code review"),
        SearchQuery(query="python tutorial"),

        # Long conceptual queries (semantic search)
        SearchQuery(query="comprehensive guide to implementing authentication and authorization in our backend system"),
        SearchQuery(query="detailed breakdown of customer feedback from last quarter including pain points and feature requests"),

        # Mixed queries
        SearchQuery(query="drive document with budget numbers"),
        SearchQuery(query="notion database for tracking bugs and issues"),
        SearchQuery(query="what are the main features in our product roadmap?"),
        SearchQuery(query='"project kickoff"', platform=Platform.GOOGLE_DRIVE),
        SearchQuery(query="technical specifications", method=SearchMethod.KEYWORD),
    ]

    for query in test_queries:
        method = orchestrator.determine_search_method(query)
        platforms = orchestrator.determine_platforms(query)
        print(f"Query: '{query.query}'")
        print(f"  Method: {method.value}")
        print(f"  Platforms: {[p.value for p in platforms]}")
        print()
