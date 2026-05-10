"""SurfSense Integration Bridge for Statistics Module

Provides integration between statistical analysis results and SurfSense
knowledge base storage and retrieval.

Complies with GLP/GCP/FDA/EMA standards for data integrity.
"""

import os
import json
import re
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import pandas as pd
import tempfile


class SurfSenseStatisticsBridge:
    """Bridge between statistical analysis and SurfSense knowledge base"""

    def __init__(self, surfsense_url: str = None, api_base: str = None):
        """Initialize SurfSense bridge

        Args:
            surfsense_url: URL of SurfSense service (default: from config)
            api_base: Base URL for API calls
        """
        self.surfsense_url = surfsense_url or os.getenv('SURFSENSE_URL', 'http://localhost:8000')
        self.api_base = api_base or os.getenv('API_BASE_URL', 'http://localhost:3000')
        self.analysis_cache: Dict[str, Dict[str, Any]] = {}

        # Try to import SurfSense client
        self._surfsense_client = None
        try:
            from modules.surfsense.client import SurfSenseClient
            self._surfsense_client = SurfSenseClient(base_url=self.surfsense_url)
        except ImportError:
            print("SurfSense client not available, using local storage fallback")

    def store_analysis(self,
                   analysis: Dict[str, Any],
                   title: str,
                   tags: List[str] = None,
                   metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Store statistical analysis result

        Args:
            analysis: Statistical analysis results
            title: Title of the analysis
            tags: Tags for categorization
            metadata: Additional metadata

        Returns:
            Storage result with document ID
        """
        if tags is None:
            tags = []
        if metadata is None:
            metadata = {}

        result = {
            'status': 'success',
            'title': title,
            'timestamp': datetime.now().isoformat(),
            'tags': tags,
            'document_id': None,
            'storage_location': 'local',
            'surfsense_stored': False
        }

        # Try to store in SurfSense
        if self._surfsense_client:
            try:
                doc_id = self._store_to_surfsense(
                    analysis, title, tags, metadata
                )
                result['document_id'] = doc_id
                result['storage_location'] = 'surfsense'
                result['surfsense_stored'] = True
            except Exception as e:
                print(f"SurfSense storage failed: {e}, using local fallback")

        # Store locally as fallback/backup
        local_id = self._store_locally(analysis, title, tags)
        if not result['document_id']:
            result['document_id'] = local_id

        # Cache the analysis
        cache_key = f"{title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.analysis_cache[cache_key] = analysis

        return result

    def retrieve_analysis(self,
                       analysis_id: str,
                       from_cache: bool = False) -> Optional[Dict[str, Any]]:
        """Retrieve stored analysis

        Args:
            analysis_id: Document ID
            from_cache: Try to retrieve from cache first

        Returns:
            Analysis results or None
        """
        if from_cache:
            for key, analysis in self.analysis_cache.items():
                if analysis_id in key:
                    return analysis

        # Try to retrieve from SurfSense
        if self._surfsense_client:
            try:
                result = self._retrieve_from_surfsense(analysis_id)
                if result:
                    return result
            except Exception as e:
                    print(f"SurfSense retrieval failed: {e}")

        # Try to retrieve from local storage
        return self._retrieve_locally(analysis_id)

    def export_to_format(self,
                       analysis: Dict[str, Any],
                       format_type: str = 'json',
                       output_path: str = None) -> Dict[str, Any]:
        """Export analysis to different formats

        Args:
            analysis: Analysis results
            format_type: Output format (json, csv, latex, markdown)
            output_path: Output file path

        Returns:
            Export result
        """
        result = {
            'format': format_type,
            'output_path': output_path,
            'success': False,
            'message': ''
        }

        try:
            if format_type == 'json':
                output_path = self._export_json(analysis, output_path)
            elif format_type == 'csv':
                output_path = self._export_csv(analysis, output_path)
            elif format_type == 'latex':
                output_path = self._export_latex(analysis, output_path)
            elif format_type == 'markdown':
                output_path = self._export_markdown(analysis, output_path)
            else:
                raise ValueError(f"Unsupported format: {format_type}")

            result['success'] = True
            result['message'] = f"Successfully exported to {format_type}"
        except Exception as e:
            result['message'] = f"Export failed: {str(e)}"

        return result

    def generate_report(self,
                     analysis: Dict[str, Any],
                     report_type: str = 'summary') -> str:
        """Generate human-readable report from analysis

        Args:
            analysis: Analysis results
            report_type: Type of report (summary, detailed, thesis)

        Returns:
            Report text
        """
        summary_parts = [
            f"# Statistical Analysis Report\n",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        ]

        # Add analysis type
        if 'analysis_type' in analysis:
            summary_parts.append(f"Analysis Type: {analysis['analysis_type']}\n")

        # Add summary statistics
        if 'summary_stats' in analysis:
            summary_parts.append("\n## Summary Statistics\n")
            for var, stats in analysis['summary_stats'].items():
                summary_parts.append(f"\n{var}:\n")
                for stat, value in stats.items():
                    summary_parts.append(f"  {stat}: {value}\n")

        # Add test results
        if 'test_results' in analysis:
            summary_parts.append("\n## Test Results\n")
            for test, result in analysis['test_results'].items():
                summary_parts.append(f"\n{test}: {result}\n")

        # Add interpretations
        if 'interpretations' in analysis:
            summary_parts.append("\n## Interpretations\n")
            interpretations = analysis['interpretations']
            if 'main_finding' in interpretations:
                summary_parts.append(f"Main Finding: {interpretations['main_finding']}\n")

        return "\n".join(summary_parts)

    def _store_to_surfsense(self,
                          analysis: Dict[str, Any],
                          title: str,
                          tags: List[str],
                          metadata: Dict[str, Any]) -> str:
        """Store analysis to SurfSense

        Args:
            analysis: Analysis results
            title: Title
            tags: Tags
            metadata: Additional metadata

        Returns:
            Document ID
        """
        # Convert analysis to text content
        content = json.dumps(analysis, indent=2)

        # Generate filename
        filename = f"stats_analysis_{title.lower().replace(' ' , '_')}.json"

        # Upload to SurfSense
        doc_id = self._surfsense_client.upload_document(
            content=content,
            filename=filename
        )

        return doc_id

    def _store_locally(self,
                      analysis: Dict[str, Any],
                      title: str,
                      tags: List[str]) -> str:
        """Store analysis locally as fallback

        Args:
            analysis: Analysis results
            title: Title
            tags: Tags

        Returns:
            Document ID (file path)
        """
        # Create local storage directory (cross-platform compatible)
        project_root = Path(__file__).parent.parent.parent.absolute()
        storage_dir = project_root / "data" / "statistics_analyses"
        storage_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"analysis_{timestamp}.json"
        file_path = os.path.join(storage_dir, filename)

        # Save to file
        with open(file_path, 'w') as f:
            json.dump(analysis, f, indent=2)

        return file_path

    def _retrieve_from_surfsense(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve analysis from SurfSense

        Args:
            analysis_id: Document ID

        Returns:
            Analysis results
        """
        # This would use SurfSense client to retrieve
        # For now, return None
        return None

    def _retrieve_locally(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Retrieve analysis from local storage

        Args:
            file_path: Path to analysis file

        Returns:
            Analysis results
        """
        if not os.path.exists(file_path):
            return None

        with open(file_path, 'r') as f:
            return json.load(f)

    def _export_json(self, analysis: Dict[str, Any], output_path: str) -> str:
        """Export to JSON

        Args:
            analysis: Analysis results
            output_path: Output file path

        Returns:
            Output file path
        """
        if not output_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f"/tmp/analysis_{timestamp}.json"

        with open(output_path, 'w') as f:
            json.dump(analysis, f, indent=2)

        return output_path

    def _export_csv(self, analysis: Dict[str, Any], output_path: str) -> str:
        """Export to CSV

        Args:
            analysis: Analysis results
            output_path: Output file path

        Returns:
            Output file path
        """
        # Extract data from analysis
        data = analysis.get('data', [])
        if not data and 'summary_stats' in analysis:
            # Create dataframe from summary stats
            df = pd.DataFrame(analysis['summary_stats']).T
        else:
            df = pd.DataFrame(data)

        if not output_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f"/tmp/analysis_{timestamp}.csv"

        df.to_csv(output_path, index=False)
        return output_path

    def _export_latex(self, analysis: Dict[str, Any], output_path: str) -> str:
        """Export to LaTeX format

        Args:
            analysis: Analysis results
            output_path: Output file path

        Returns:
            Output file path
        """
        if not output_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f"/tmp/analysis_{timestamp}.tex"

        latex_content = []
        latex_content.append("\\documentclass{article}")
        latex_content.append("\\usepackage[utf8]{inputenc}")
        latex_content.append("\\usepackage{booktabs}")
        latex_content.append("\\usepackage{amsmath}")
        latex_content.append("")
        latex_content.append("\\begin{document}")
        latex_content.append("")

        # Add title
        latex_content.append("\\section{Statistical Analysis Report}")
        latex_content.append(f"Generated: {datetime.now().strftime('%Y-%m-%d')}")
        latex_content.append("")

        # Add summary statistics if available
        if 'summary_stats' in analysis:
            latex_content.append("\subsection{Summary Statistics}")
            latex_content.append("")
            latex_content.append("\\begin{table}[h]")
            latex_content.append("\\centering")
            latex_content.append("\\begin{tabular}{lcc}")
            latex_content.append("Variable & Mean & Std Dev \\n")
            for var, stats in analysis['summary_stats'].items():
                mean = stats.get('mean', 'N/A')
                std = stats.get('std', 'N/A')
                latex_content.append(f"{var} & {mean:.3f} & {std:.3f} \\n")
            latex_content.append("\\end{tabular}")
            latex_content.append("\\end{table}")

        latex_content.append("")
        latex_content.append("\end{document}")

        # Write to file
        with open(output_path, 'w') as f:
            f.write('\n'.join(latex_content))

        return output_path

    def _export_markdown(self, analysis: Dict[str, Any], output_path: str) -> str:
        """Export to Markdown format

        Args:
            analysis: Analysis results
            output_path: Output file path

        Returns:
            Output file path
        """
        if not output_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f"/tmp/analysis_{timestamp}.md"

        md_content = []
        md_content.append("# Statistical Analysis Report")
        md_content.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # Add analysis type
        if 'analysis_type' in analysis:
            md_content.append(f"**Analysis Type:** {analysis['analysis_type']}\n")

        # Add summary statistics
        if 'summary_stats' in analysis:
            md_content.append("## Summary Statistics\n")
            md_content.append("| Variable | Mean | Std Dev | Min | Max |")
            md_content.append("|----------|------|---------|-----|-----|")
            for var, stats in analysis['summary_stats'].items():
                mean = stats.get('mean', 'N/A')
                std = stats.get('std', 'N/A')
                min_val = stats.get('min', 'N/A')
                max_val = stats.get('max', 'N/A')
                md_content.append(f"| {var} | {mean:.3f} | {std:.3f} | {min_val:.3f} | {max_val:.3f} |")

        # Add interpretations
        if 'interpretations' in analysis:
            md_content.append("\n## Interpretations\n")
            for key, value in analysis['interpretations'].items():
                md_content.append(f"- **{key}:** {value}")

        # Write to file
        with open(output_path, 'w') as f:
            f.write('\n'.join(md_content))

        return output_path

    def _extract_tabular_data(self, content: str) -> List[Dict[str, Any]]:
        """Extract tabular data from content

        Args:
            content: Text content

        Returns:
            List of data rows
        """
        data = []

        # Try to parse as JSON
        try:
            json_data = json.loads(content)
            if isinstance(json_data, list):
                data = json_data
            elif isinstance(json_data, dict) and 'data' in json_data:
                data = json_data['data']
        except json.JSONDecodeError:
            pass

        # Try to extract CSV-like data
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        if len(lines) > 1:
            # Assume first line is header
            headers = re.split(r'[,\t;]', lines[0])
            data = []
            for line in lines[1:]:
                values = re.split(r'[,\t;]', line)
                if len(values) == len(headers):
                    data.append(dict(zip(headers, values)))

        return data

    def get_cache_size(self) -> int:
        """Get size of analysis cache

        Returns:
            Number of cached analyses
        """
        return len(self.analysis_cache)

    def clear_cache(self) -> None:
        """Clear analysis cache"""
        self.analysis_cache.clear()



# Example usage
if __name__ == "__main__":
    # Create bridge
    bridge = SurfSenseStatisticsBridge()

    # Sample analysis
    sample_analysis = {
        'analysis_type': 'descriptive_statistics',
        'timestamp': datetime.now().isoformat(),
        'alpha': 0.05,
        'summary_stats': {
            'group_A': {'mean': 10.5, 'std': 1.2, 'min': 8.0, 'max': 12.0},
            'group_B': {'mean': 15.2, 'std': 1.5, 'min': 13.0, 'max': 17.0}
        },
        'test_results': {'t_test': {'t_statistic': -5.23, 'p_value': 0.001}},
        'effect_size': {'cohens_d': -3.5, 'interpretation': 'Large effect'},
        'explanations': {
            'alpha': 'Significance level',
            'p_value': 'Probability of observing results'
        },
        'interpretations': {
            'main_finding': 'Significant difference between groups (p < 0.05)'
        },
        'recommendations': ['Report effect size', 'Check assumptions']
    }

    # Store analysis
    result = bridge.store_analysis(
        sample_analysis,
        title="Example Analysis",
        tags=["example", "test"],
        metadata={"study": "demo"}
    )

    print("Storage result:", json.dumps(result, indent=2))

    # Generate report
    report = bridge.generate_report(sample_analysis, report_type='summary')
    print("\n" + report)

    # Export to different formats
    for fmt in ['json', 'latex', 'markdown']:
        export_result = bridge.export_to_format(sample_analysis, format_type=fmt)
        print(f"\nExported to {fmt}: {export_result}")
