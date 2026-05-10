"""
Preclinical Gap & Novelty Analysis

This module provides analysis tools for identifying research gaps and assessing
novelty in pharmaceutical literature, including:
- Entity frequency analysis
- Under-explored research direction detection
- Semantic gap detection using embeddings
- Graph-based gap detection (with Neo4j)
- Research novelty scoring
- Knowledge gap visualization

Pipeline Flow:
Papers + Embeddings → Entity Extraction → Frequency Analysis → Gap Detection → Novelty Scoring
"""

from typing import List, Dict, Optional, Any, Tuple
import numpy as np
from collections import Counter, defaultdict
import logging
from pathlib import Path
import json


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Entity:
    """Represents a pharmaceutical entity (drug, target, disease, etc.)"""

    def __init__(
        self,
        text: str,
        entity_type: str,
        confidence: float = 1.0,
        metadata: Optional[Dict] = None
    ):
        self.text = text
        self.entity_type = entity_type
        self.confidence = confidence
        self.metadata = metadata or {}

    def to_dict(self) -> Dict:
        """Convert entity to dictionary"""
        return {
            'text': self.text,
            'entity_type': self.entity_type,
            'confidence': self.confidence,
            'metadata': self.metadata
        }


class PreclinicalGapAnalyzer:
    """
    Analyzer for detecting research gaps and assessing novelty

    Features:
    - Entity frequency analysis
    - Under-explored combination detection
    - Semantic gap detection using FAISS
    - Graph-based gap detection (Neo4j)
    - Novelty scoring for hypotheses
    - Gap ranking and prioritization

    Methods:
    - detect_research_gaps: Identify under-explored research directions
    - assess_novelty: Score research novelty (0-1)
    - find_semantic_gaps: Find gaps in embedding space
    - find_graph_gaps: Find missing interactions in knowledge graph
    """

    def __init__(
        self,
        embedder,
        faiss_index=None,
        neo4j_client=None,
        min_entity_count: int = 3,
        density_threshold: float = 0.1
    ):
        """
        Initialize Preclinical Gap Analyzer

        Args:
            embedder: SciBERT embedder instance
            faiss_index: Optional FAISS index for similarity search
            neo4j_client: Optional Neo4j client for graph analysis
            min_entity_count: Minimum count for entity to be considered
            density_threshold: Threshold for semantic gap detection
        """
        self.embedder = embedder
        self.index = faiss_index
        self.graph = neo4j_client
        self.min_entity_count = min_entity_count
        self.density_threshold = density_threshold

        logger.info("Preclinical Gap Analyzer initialized")

    def extract_entities(self, text: str) -> List[Dict]:
        """
        Extract pharmaceutical entities from text

        Note: This is a simplified implementation. In production,
        use specialized NER models like BioBERT or SciSpacy.

        Args:
            text: Input text

        Returns:
            List of entity dictionaries
        """
        # Simplified entity extraction using keyword matching
        # In production, replace with proper NER model

        # Pharmaceutical-related keywords
        keywords = {
            'drug': ['inhibitor', 'agonist', 'antagonist', 'modulator', 'compound'],
            'protein': ['protein', 'enzyme', 'receptor', 'kinase', 'channel'],
            'disease': ['disease', 'disorder', 'syndrome', 'cancer', 'diabetes', 'alzheimer'],
            'target': ['target', 'biomarker', 'pathway', 'mechanism']
        }

        entities = []
        text_lower = text.lower()

        for entity_type, type_keywords in keywords.items():
            for keyword in type_keywords:
                if keyword in text_lower:
                    entities.append({
                        'text': keyword,
                        'entity_type': entity_type,
                        'confidence': 0.8
                    })

        return entities

    def detect_research_gaps(
        self,
        research_area: str,
        papers: List[Dict],
        gap_types: List[str] = None
    ) -> List[Dict]:
        """
        Identify under-explored research directions

        Args:
            research_area: Domain (e.g., "Alzheimer's drug discovery")
            papers: List of parsed papers with metadata
            gap_types: Types of gaps to detect (default: all)

        Returns:
            List of research gaps with novelty scores
        """
        if gap_types is None:
            gap_types = ['under_explored', 'semantic', 'combination']

        logger.info(f"Detecting research gaps in: {research_area}")
        logger.info(f"Analyzing {len(papers)} papers")

        gaps = []

        # 1. Entity frequency-based gaps
        if 'under_explored' in gap_types:
            entity_gaps = self._detect_underexplored_entities(papers)
            gaps.extend(entity_gaps)

        # 2. Semantic gaps using embeddings
        if 'semantic' in gap_types and self.index is not None:
            semantic_gaps = self._find_semantic_gaps(papers)
            gaps.extend(semantic_gaps)

        # 3. Combination gaps (under-studied entity pairs)
        if 'combination' in gap_types:
            combination_gaps = self._detect_combination_gaps(papers)
            gaps.extend(combination_gaps)

        # 4. Graph-based gaps (if Neo4j available)
        if self.graph is not None:
            graph_gaps = self._find_graph_gaps(research_area)
            gaps.extend(graph_gaps)

        # Sort by novelty score (descending)
        gaps.sort(key=lambda x: x.get('novelty_score', 0), reverse=True)

        # Assign rankings
        for idx, gap in enumerate(gaps, 1):
            gap['rank'] = idx

        logger.info(f"Identified {len(gaps)} research gaps")

        return gaps

    def _detect_underexplored_entities(self, papers: List[Dict]) -> List[Dict]:
        """Detect under-explored entities"""
        gaps = []

        # Collect all entities
        all_entities = []
        for paper in papers:
            paper_entities = paper.get('entities', [])

            # Extract entities if not present
            if not paper_entities and 'abstract' in paper:
                paper_entities = self.extract_entities(paper['abstract'])

            all_entities.extend(paper_entities)

        # Count entity occurrences
        entity_counts = Counter()
        entity_by_type = defaultdict(list)

        for entity in all_entities:
            entity_text = entity.get('text', '')
            entity_counts[entity_text] += 1
            entity_by_type[entity_text].append(entity.get('entity_type', 'unknown'))

        # Find under-explored entities
        for entity, count in entity_counts.items():
            if count < self.min_entity_count:
                # Higher novelty for less frequently mentioned entities
                novelty_score = 1.0 / (count + 1)

                gaps.append({
                    'entity': entity,
                    'entity_types': list(set(entity_by_type[entity])),
                    'paper_count': count,
                    'gap_type': 'under_explored_entity',
                    'novelty_score': novelty_score,
                    'description': f"Entity '{entity}' mentioned in only {count} papers"
                })

        logger.info(f"Found {len(gaps)} under-explored entity gaps")

        return gaps

    def _detect_combination_gaps(self, papers: List[Dict]) -> List[Dict]:
        """Detect under-studied entity combinations"""
        gaps = []

        # Collect entities per paper
        papers_entities = []
        for paper in papers:
            entities = paper.get('entities', [])

            if not entities and 'abstract' in paper:
                entities = self.extract_entities(paper['abstract'])

            entity_texts = [e.get('text', '') for e in entities]
            papers_entities.append(set(entity_texts))

        # Count co-occurrences
        co_occurrences = Counter()

        for i, entities1 in enumerate(papers_entities):
            for entities2 in papers_entities[i+1:]:
                # Find intersection
                common = entities1 & entities2

                if len(common) >= 2:
                    # Create sorted pairs
                    common_list = sorted(common)
                    for j in range(len(common_list)):
                        for k in range(j+1, len(common_list)):
                            pair = f"{common_list[j]} + {common_list[k]}"
                            co_occurrences[pair] += 1

        # Find under-explored combinations
        for combo, count in co_occurrences.items():
            if count < self.min_entity_count:
                novelty_score = 1.0 / (count + 1)

                gaps.append({
                    'combination': combo,
                    'paper_count': count,
                    'gap_type': 'under_explored_combination',
                    'novelty_score': novelty_score,
                    'description': f"Combination '{combo}' studied in only {count} papers"
                })

        logger.info(f"Found {len(gaps)} under-explored combination gaps")

        return gaps

    def assess_novelty(
        self,
        hypothesis: str,
        papers: List[Dict],
        method: str = 'semantic'
    ) -> float:
        """
        Score research novelty (0-1)

        Higher scores indicate higher novelty (more different from existing work)

        Uses:
        - Semantic similarity to existing work (method='semantic')
        - Entity overlap analysis (method='entity')
        - Combined approach (method='combined')

        Args:
            hypothesis: Research hypothesis text
            papers: List of papers for comparison
            method: Method for novelty assessment

        Returns:
            Novelty score between 0 and 1
        """
        if method == 'semantic':
            return self._assess_novelty_semantic(hypothesis, papers)
        elif method == 'entity':
            return self._assess_novelty_entity(hypothesis, papers)
        elif method == 'combined':
            semantic_score = self._assess_novelty_semantic(hypothesis, papers)
            entity_score = self._assess_novelty_entity(hypothesis, papers)
            # Weighted average (semantic 70%, entity 30%)
            return 0.7 * semantic_score + 0.3 * entity_score
        else:
            raise ValueError(f"Unknown method: {method}")

    def _assess_novelty_semantic(self, hypothesis: str, papers: List[Dict]) -> float:
        """Assess novelty using semantic similarity"""
        try:
            # Embed hypothesis
            hyp_embedding = self.embedder.embed_text(hypothesis, normalize=True)

            # Get abstracts from papers
            abstracts = []
            for paper in papers:
                if 'abstract' in paper and paper['abstract']:
                    abstracts.append(paper['abstract'])

            if not abstracts:
                return 1.0  # No papers to compare, maximum novelty

            # Embed abstracts
            abstract_embeddings = self.embedder.embed_batch(
                abstracts,
                batch_size=32,
                normalize=True,
                show_progress=False
            )

            # Calculate similarities
            similarities = self.embedder.compute_similarities(
                hyp_embedding,
                abstract_embeddings
            )

            # Novelty = 1 - max_similarity
            max_similarity = np.max(similarities)
            novelty = max(0.0, min(1.0, 1.0 - max_similarity))

            logger.debug(f"Semantic novelty: {novelty:.3f} (max similarity: {max_similarity:.3f})")

            return float(novelty)

        except Exception as e:
            logger.error(f"Error in semantic novelty assessment: {e}")
            return 0.5  # Return moderate score on error

    def _assess_novelty_entity(self, hypothesis: str, papers: List[Dict]) -> float:
        """Assess novelty using entity overlap"""
        try:
            # Extract entities from hypothesis
            hyp_entities = self.extract_entities(hypothesis)
            hyp_entity_texts = set(e['text'] for e in hyp_entities)

            if not hyp_entity_texts:
                return 0.5  # Can't assess without entities

            # Collect all entities from papers
            all_paper_entities = set()
            for paper in papers:
                paper_entities = paper.get('entities', [])
                if not paper_entities and 'abstract' in paper:
                    paper_entities = self.extract_entities(paper['abstract'])
                all_paper_entities.update(e['text'] for e in paper_entities)

            if not all_paper_entities:
                return 1.0  # No entities in papers, maximum novelty

            # Calculate overlap
            overlap = hyp_entity_texts & all_paper_entities
            overlap_ratio = len(overlap) / len(hyp_entity_texts)

            # Novelty = 1 - overlap_ratio
            novelty = max(0.0, min(1.0, 1.0 - overlap_ratio))

            logger.debug(f"Entity novelty: {novelty:.3f} (overlap: {overlap_ratio:.3f})")

            return float(novelty)

        except Exception as e:
            logger.error(f"Error in entity novelty assessment: {e}")
            return 0.5

    def _find_semantic_gaps(self, papers: List[Dict]) -> List[Dict]:
        """
        Find semantic gaps using FAISS

        Identifies regions of the embedding space with low document density,
        suggesting under-explored research areas.
        """
        gaps = []

        if self.index is None:
            logger.warning("No FAISS index provided for semantic gap detection")
            return gaps

        try:
            # Get abstracts
            abstracts = [p.get('abstract', '') for p in papers if p.get('abstract')]
            if not abstracts:
                return gaps

            # Generate embeddings
            embeddings = self.embedder.embed_batch(
                abstracts,
                batch_size=32,
                normalize=True,
                show_progress=False
            )

            # Calculate local density for each point
            # Simplified: use k-nearest neighbors distance
            n_neighbors = min(5, len(embeddings))
            densities = []

            for i, embedding in enumerate(embeddings):
                # Find k nearest neighbors (excluding self)
                embedding_reshaped = embedding.reshape(1, -1).astype('float32')
                distances, indices = self.index.search(embedding_reshaped, n_neighbors + 1)

                # Average distance to neighbors (excluding self at index 0)
                if len(distances[0]) > 1:
                    avg_distance = np.mean(distances[0][1:])  # Skip self
                else:
                    avg_distance = 0

                densities.append(avg_distance)

            densities = np.array(densities)

            # Identify low-density regions (potential gaps)
            density_threshold = np.percentile(densities, 90)  # Top 10% most isolated

            low_density_indices = np.where(densities > density_threshold)[0]

            for idx in low_density_indices:
                gaps.append({
                    'paper_index': int(idx),
                    'paper_title': papers[idx].get('title', 'Unknown'),
                    'density_score': float(densities[idx]),
                    'gap_type': 'semantic_gap',
                    'novelty_score': float(densities[idx]) / np.max(densities),
                    'description': 'Paper in low-density region of semantic space'
                })

            logger.info(f"Found {len(gaps)} semantic gaps")

        except Exception as e:
            logger.error(f"Error finding semantic gaps: {e}")

        return gaps

    def _find_graph_gaps(self, area: str) -> List[Dict]:
        """
        Find gaps using Neo4j graph analysis

        Identifies missing connections in the knowledge graph,
        such as drug-target pairs that haven't been studied.

        Args:
            area: Research area/domain
        """
        gaps = []

        if self.graph is None:
            logger.warning("No Neo4j client provided for graph gap detection")
            return gaps

        try:
            # Query for missing drug-target interactions
            query = """
            MATCH (d:Drug)
            WHERE toLower(d.name) CONTAINS toLower($area)
            MATCH (t:Target)
            WHERE NOT (d)-[:BINDS_TO]->(t)
            RETURN d.name as drug, t.name as target
            LIMIT 100
            """

            try:
                results = self.graph.run(query, area=area)
            except Exception as e:
                logger.warning(f"Neo4j query failed: {e}")
                return gaps

            for record in results:
                gaps.append({
                    'drug': record['drug'],
                    'target': record['target'],
                    'gap_type': 'missing_interaction',
                    'novelty_score': 0.8,  # High novelty for unstudied interactions
                    'description': f"Drug '{record['drug']}' not tested against target '{record['target']}'"
                })

            logger.info(f"Found {len(gaps)} graph-based gaps")

        except Exception as e:
            logger.error(f"Error finding graph gaps: {e}")

        return gaps

    def rank_gaps_by_potential(
        self,
        gaps: List[Dict],
        criteria: List[str] = None
    ) -> List[Dict]:
        """
        Rank research gaps by potential impact

        Args:
            gaps: List of identified gaps
            criteria: Ranking criteria (default: novelty, feasibility, impact)

        Returns:
            Ranked list of gaps
        """
        if criteria is None:
            criteria = ['novelty_score', 'feasibility', 'impact']

        for gap in gaps:
            # Calculate composite score
            scores = []
            for criterion in criteria:
                if criterion in gap:
                    scores.append(gap[criterion])
                elif criterion == 'feasibility':
                    # Estimate feasibility (simplified)
                    scores.append(0.5)  # Default moderate feasibility
                elif criterion == 'impact':
                    # Estimate impact (simplified)
                    scores.append(gap.get('novelty_score', 0.5))

            # Weighted average (can be customized)
            if scores:
                gap['potential_score'] = np.mean(scores)
            else:
                gap['potential_score'] = gap.get('novelty_score', 0)

        # Sort by potential score
        gaps.sort(key=lambda x: x.get('potential_score', 0), reverse=True)

        return gaps

    def generate_gap_report(
        self,
        gaps: List[Dict],
        output_path: str = None,
        top_n: int = 20
    ) -> Dict:
        """
        Generate a comprehensive gap analysis report

        Args:
            gaps: List of identified gaps
            output_path: Optional path to save JSON report
            top_n: Number of top gaps to include in summary

        Returns:
            Dictionary with gap report
        """
        # Summary statistics
        report = {
            'total_gaps': len(gaps),
            'gap_types': {},
            'top_gaps': [],
            'novelty_distribution': {},
            'recommendations': []
        }

        # Count gaps by type
        for gap in gaps:
            gap_type = gap.get('gap_type', 'unknown')
            report['gap_types'][gap_type] = report['gap_types'].get(gap_type, 0) + 1

        # Top N gaps
        report['top_gaps'] = gaps[:top_n]

        # Novelty distribution
        novelty_scores = [g.get('novelty_score', 0) for g in gaps]
        if novelty_scores:
            report['novelty_distribution'] = {
                'mean': float(np.mean(novelty_scores)),
                'median': float(np.median(novelty_scores)),
                'std': float(np.std(novelty_scores)),
                'min': float(np.min(novelty_scores)),
                'max': float(np.max(novelty_scores))
            }

        # Generate recommendations
        report['recommendations'] = [
            f"Focus on {report['gap_types'].get('under_explored_entity', 0)} under-explored entities",
            f"Investigate {report['gap_types'].get('semantic_gap', 0)} semantic gaps",
            f"Consider {report['gap_types'].get('under_explored_combination', 0)} novel combinations"
        ]

        # Save report if path provided
        if output_path:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)

            logger.info(f"Gap report saved to {output_path}")

        return report

    def save_gaps(self, gaps: List[Dict], output_path: str):
        """Save gaps to JSON file"""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w') as f:
            json.dump(gaps, f, indent=2)

        logger.info(f"Gaps saved to {output_path}")

    def load_gaps(self, input_path: str) -> List[Dict]:
        """Load gaps from JSON file"""
        with open(input_path, 'r') as f:
            gaps = json.load(f)

        logger.info(f"Loaded {len(gaps)} gaps from {input_path}")
        return gaps
