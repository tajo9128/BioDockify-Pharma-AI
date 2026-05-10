"""
Agent Zero Curator

Saves results as files, adds metadata, updates search index, and maintains knowledge base.
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict
import logging
import json
import hashlib
import os
from pathlib import Path
from datetime import datetime
from .executor import PageResult

logger = logging.getLogger(__name__)


@dataclass
class CuratorConfig:
    """Configuration for the Curator."""
    base_path: str = "./data/web_research"
    max_results_per_query: int = 100
    compression_enabled: bool = True
    index_update_interval: int = 10  # Update index every N results


@dataclass
class QueryMetadata:
    """Metadata for a research query."""
    query_id: str
    query: str
    timestamp: str
    total_results: int
    successful_results: int
    sources: List[str]
    keywords: List[str]


@dataclass
class ResultMetadata:
    """Metadata for a single research result."""
    url: str
    title: str
    content_length: int
    domain: str
    timestamp: str
    query_id: str
    file_path: str
    hash: str


@dataclass
class SearchIndex:
    """Search index for quick lookup of research results."""
    queries: Dict[str, QueryMetadata] = field(default_factory=dict)
    results: Dict[str, List[ResultMetadata]] = field(default_factory=dict)
    last_updated: str = ""


class Curator:
    """
    Saves results as files and manages metadata.
    
    This component:
    - Saves results as files
    - Adds metadata to results
    - Updates search index
    - Maintains knowledge base
    """
    
    def __init__(self, config: Optional[CuratorConfig] = None):
        """
        Initialize the Curator.
        
        Args:
            config: Curator configuration (uses default if None)
        """
        self.config = config or CuratorConfig()
        self.base_path = Path(self.config.base_path)
        self.index = self._load_index()
        
        # Create directory structure
        self._create_directory_structure()
    
    def _create_directory_structure(self):
        """Create the necessary directory structure for storing results."""
        directories = [
            self.base_path,
            self.base_path / "queries",
            self.base_path / "index",
            self.base_path / "cache" / "pages"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Directory structure created at {self.base_path}")
    
    def _load_index(self) -> SearchIndex:
        """Load the search index from disk."""
        index_path = self.base_path / "index" / "search_index.json"
        
        if index_path.exists():
            try:
                with open(index_path, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
                    return SearchIndex(**index_data)
            except Exception as e:
                logger.warning(f"Failed to load index: {e}. Creating new index.")
        
        return SearchIndex(last_updated=datetime.now().isoformat())
    
    def _save_index(self):
        """Save the search index to disk."""
        index_path = self.base_path / "index" / "search_index.json"
        
        try:
            index_data = asdict(self.index)
            index_data['last_updated'] = datetime.now().isoformat()
            
            with open(index_path, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Index saved to {index_path}")
        except Exception as e:
            logger.error(f"Failed to save index: {e}")
    
    def _generate_query_id(self, query: str) -> str:
        """
        Generate a unique ID for a query.
        
        Args:
            query: The search query
            
        Returns:
            Unique query ID (hash)
        """
        # Create hash from query string
        query_hash = hashlib.md5(query.encode('utf-8')).hexdigest()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"{query_hash[:8]}_{timestamp}"
    
    def _generate_result_hash(self, url: str, content: str) -> str:
        """
        Generate a hash for a result for deduplication.
        
        Args:
            url: Result URL
            content: Result content
            
        Returns:
            Content hash
        """
        combined = f"{url}_{content[:1000]}"  # Use first 1000 chars for hashing
        return hashlib.sha256(combined.encode('utf-8')).hexdigest()
    
    async def save_results(
        self,
        results: List[PageResult],
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Save results as files.
        
        Args:
            results: List of page results to save
            query: Original search query
            context: Additional context for metadata
            
        Returns:
            List of file paths where results were saved
        """
        if not results:
            logger.warning("No results to save")
            return []
        
        # Generate query ID
        query_id = self._generate_query_id(query)
        
        # Create query directory
        query_dir = self.base_path / "queries" / query_id
        results_dir = query_dir / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        
        # Save individual results
        file_paths = []
        saved_results = []
        
        for i, result in enumerate(results):
            if not result.success:
                logger.debug(f"Skipping failed result: {result.url}")
                continue
            
            # Generate filename
            filename = f"page_{i+1:03d}.txt"
            file_path = results_dir / filename
            
            # Save content
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"URL: {result.url}\n")
                    f.write(f"Title: {result.title}\n")
                    f.write(f"Timestamp: {result.timestamp.isoformat()}\n")
                    f.write(f"{'='*80}\n\n")
                    f.write(result.content)
                
                file_paths.append(str(file_path))
                saved_results.append(result)
                
                logger.debug(f"Saved result to {file_path}")
                
            except Exception as e:
                logger.error(f"Failed to save result {result.url}: {e}")
        
        # Save metadata
        await self.add_metadata(saved_results, query, query_id, context)
        
        # Update index
        await self.update_index(saved_results, query_id)
        
        # Save summary
        await self._save_summary(query_id, query, saved_results, context)
        
        logger.info(f"Saved {len(saved_results)} results for query '{query}'")
        return file_paths
    
    async def add_metadata(
        self,
        results: List[PageResult],
        query: str,
        query_id: str,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Add metadata to results.
        
        Args:
            results: List of page results
            query: Original search query
            query_id: Query ID
            context: Additional context
        """
        if not results:
            return
        
        # Extract sources and keywords
        sources = list(set([result.metadata.get('domain', 'unknown') for result in results]))
        keywords = self._extract_keywords(query)
        
        # Create query metadata
        query_metadata = QueryMetadata(
            query_id=query_id,
            query=query,
            timestamp=datetime.now().isoformat(),
            total_results=len(results),
            successful_results=sum(1 for r in results if r.success),
            sources=sources,
            keywords=keywords
        )
        
        # Save query metadata
        metadata_path = self.base_path / "queries" / query_id / "metadata.json"
        
        try:
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(asdict(query_metadata), f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Saved metadata to {metadata_path}")
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")
    
    def _extract_keywords(self, query: str) -> List[str]:
        """
        Extract keywords from a query.
        
        Args:
            query: Query string
            
        Returns:
            List of keywords
        """
        # Simple keyword extraction
        import re
        words = re.findall(r'\b[a-zA-Z]{4,}\b', query.lower())
        return list(set(words))[:10]  # Return top 10 unique words
    
    async def update_index(
        self,
        results: List[PageResult],
        query_id: str
    ):
        """
        Update search index with new results.
        
        Args:
            results: List of page results
            query_id: Query ID
        """
        if not results:
            return
        
        # Add results to index
        if query_id not in self.index.results:
            self.index.results[query_id] = []
        
        for i, result in enumerate(results):
            if not result.success:
                continue
            
            # Generate file path
            file_path = str(self.base_path / "queries" / query_id / "results" / f"page_{i+1:03d}.txt")
            
            # Generate result hash
            content_hash = self._generate_result_hash(result.url, result.content)
            
            # Create result metadata
            result_metadata = ResultMetadata(
                url=result.url,
                title=result.title,
                content_length=len(result.content),
                domain=result.metadata.get('domain', 'unknown'),
                timestamp=result.timestamp.isoformat(),
                query_id=query_id,
                file_path=file_path,
                hash=content_hash
            )
            
            # Check for duplicates
            existing_hashes = [r.hash for r in self.index.results[query_id]]
            if content_hash not in existing_hashes:
                self.index.results[query_id].append(result_metadata)
        
        # Save index
        self._save_index()
        
        logger.debug(f"Updated index for query {query_id}")
    
    async def deduplicate_results(
        self,
        results: List[PageResult]
    ) -> List[PageResult]:
        """
        Remove duplicate results based on URL and content.
        
        Args:
            results: List of page results
            
        Returns:
            Deduplicated list of page results
        """
        if not results:
            return []
        
        seen_hashes = set()
        deduplicated = []
        
        for result in results:
            if not result.success:
                continue
            
            # Generate hash
            content_hash = self._generate_result_hash(result.url, result.content)
            
            # Check if already seen
            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                deduplicated.append(result)
            else:
                logger.debug(f"Removed duplicate: {result.url}")
        
        logger.info(f"Deduplicated {len(results)} -> {len(deduplicated)} results")
        return deduplicated
    
    async def _save_summary(
        self,
        query_id: str,
        query: str,
        results: List[PageResult],
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Save a summary of the research query.
        
        Args:
            query_id: Query ID
            query: Original query
            results: List of results
            context: Additional context
        """
        summary_path = self.base_path / "queries" / query_id / "summary.json"
        
        summary = {
            'query_id': query_id,
            'query': query,
            'timestamp': datetime.now().isoformat(),
            'total_results': len(results),
            'successful_results': sum(1 for r in results if r.success),
            'failed_results': sum(1 for r in results if not r.success),
            'domains': list(set([r.metadata.get('domain', 'unknown') for r in results if r.success])),
            'total_content_length': sum(len(r.content) for r in results if r.success),
            'context': context or {}
        }
        
        try:
            with open(summary_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Saved summary to {summary_path}")
        except Exception as e:
            logger.error(f"Failed to save summary: {e}")
    
    async def get_results(
        self,
        query_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve results for a query.
        
        Args:
            query_id: Query ID
            
        Returns:
            Query results or None if not found
        """
        # Check index
        if query_id not in self.index.results:
            logger.warning(f"Query ID not found in index: {query_id}")
            return None
        
        # Load metadata
        metadata_path = self.base_path / "queries" / query_id / "metadata.json"
        if not metadata_path.exists():
            logger.warning(f"Metadata not found for query: {query_id}")
            return None
        
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # Load results
            results = []
            for result_meta in self.index.results[query_id]:
                result_path = Path(result_meta['file_path'])
                if result_path.exists():
                    with open(result_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        results.append({
                            'url': result_meta['url'],
                            'title': result_meta['title'],
                            'content': content,
                            'metadata': result_meta
                        })
            
            return {
                'metadata': metadata,
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Failed to retrieve results for {query_id}: {e}")
            return None
    
    async def search_index(
        self,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search the index for relevant results.
        Leverages semantic search if the vector store is available.
        """
        matches = []
        
        # 1. Semantic Search (Primary)
        try:
            from modules.rag.vector_store import get_vector_store
            store = get_vector_store()
            v_results = await store.search(query, k=limit)
            for res in v_results:
                meta = res.get("metadata", {})
                if meta.get("file_path"):
                    matches.append({
                        'query_id': meta.get("query_id", "external"),
                        'url': meta.get("url", ""),
                        'title': meta.get("title", meta.get("filename", "Untitled")),
                        'domain': meta.get("domain", "knowledge_base"),
                        'timestamp': meta.get("timestamp", datetime.now().isoformat()),
                        'file_path': meta.get("file_path"),
                        'score': res.get("score", 0.8) # Semantic score
                    })
            if matches:
                logger.debug(f"Found {len(matches)} semantic matches in vector store.")
                return matches
        except Exception as e:
            logger.warning(f"Semantic search failed, falling back to keyword: {e}")

        # 2. Keyword Search (Fallback)
        query_lower = query.lower()
        for query_id, results in self.index.results.items():
            for result in results:
                if (query_lower in result.url.lower() or
                    query_lower in result.title.lower() or
                    query_lower in result.domain.lower()):
                    matches.append({
                        'query_id': query_id,
                        'url': result.url,
                        'title': result.title,
                        'domain': result.domain,
                        'timestamp': result.timestamp,
                        'file_path': result.file_path,
                        'score': 0.5 # Default score for keyword match
                    })
        
        matches.sort(key=lambda x: (x.get('score', 0), x['timestamp']), reverse=True)
        return matches[:limit]
    
    async def cleanup_old_results(
        self,
        days_old: int = 30
    ) -> int:
        """
        Remove old research results.
        
        Args:
            days_old: Remove results older than this many days
            
        Returns:
            Number of results removed
        """
        cutoff_date = datetime.now().timestamp() - (days_old * 24 * 60 * 60)
        removed = 0
        
        # Check each query in index
        queries_to_remove = []
        
        for query_id, query_meta in self.index.queries.items():
            try:
                query_time = datetime.fromisoformat(query_meta['timestamp']).timestamp()
                if query_time < cutoff_date:
                    queries_to_remove.append(query_id)
            except Exception as e:
                logger.warning(f"Failed to parse timestamp for {query_id}: {e}")
        
        # Remove old queries
        for query_id in queries_to_remove:
            try:
                # Remove query directory
                query_dir = self.base_path / "queries" / query_id
                if query_dir.exists():
                    import shutil
                    shutil.rmtree(query_dir)
                
                # Remove from index
                if query_id in self.index.queries:
                    del self.index.queries[query_id]
                if query_id in self.index.results:
                    del self.index.results[query_id]
                
                removed += 1
                logger.info(f"Removed old query: {query_id}")
                
            except Exception as e:
                logger.error(f"Failed to remove {query_id}: {e}")
        
        # Save updated index
        if removed > 0:
            self._save_index()
        
        logger.info(f"Cleaned up {removed} old queries")
        return removed


# Convenience function for easy use
async def save_research_results(
    results: List[PageResult],
    query: str,
    base_path: str = "./data/web_research",
    context: Optional[Dict[str, Any]] = None
) -> List[str]:
    """
    Convenience function to save research results.
    
    Args:
        results: List of page results
        query: Search query
        base_path: Base path for storage
        context: Additional context
        
    Returns:
        List of saved file paths
    """
    config = CuratorConfig(base_path=base_path)
    curator = Curator(config)
    
    return await curator.save_results(results, query, context)
