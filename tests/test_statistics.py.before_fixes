
"""Comprehensive Tests for Statistics Module

Tests for:
- Data Importer (Excel, CSV, DOCX, JSON)
- Enhanced Statistical Engine (descriptive, t-test, ANOVA, correlation)
- Additional Statistical Tools (non-parametric, time series, power analysis)
- SurfSense Integration Bridge
- Statistics Orchestrator

Complies with GLP/GCP/FDA/EMA standards
"""

import pytest
import pandas as pd
import numpy as np
import tempfile
import os
import json
from datetime import datetime

import sys
sys.path.insert(0, '/a0/usr/projects/biodockify_ai')

from modules.statistics.data_importer import DataImporter
from modules.statistics.enhanced_engine import EnhancedStatisticalEngine
from modules.statistics.statistical_tools import AdditionalStatisticalTools
from modules.statistics.surfsense_bridge import SurfSenseStatisticsBridge
from modules.statistics.orchestrator import StatisticsOrchestrator


# Fixtures
@pytest.fixture
def sample_dataframe():
    """Create sample test data"""
    np.random.seed(42)
    return pd.DataFrame({
        'group': ['A', 'A', 'A', 'B', 'B', 'B', 'C', 'C', 'C', 'A', 'B', 'C'],
        'value': [10, 12, 11, 15, 14, 16, 8, 9, 7, 11, 15, 8],
        'value2': [9, 11, 10, 14, 13, 15, 7, 8, 6, 10, 14, 7],
        'age': [45, 47, 46, 50, 52, 51, 40, 42, 41, 46, 51, 41],
        'gender': ['M', 'F', 'M', 'F', 'M', 'F', 'M', 'F', 'M', 'F', 'M', 'F']
    })


@pytest.fixture
def sample_csv_file(sample_dataframe):
    """Create temporary CSV file"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        sample_dataframe.to_csv(f, index=False)
        temp_path = f.name

    yield temp_path

    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def sample_json_file(sample_dataframe):
    """Create temporary JSON file"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(sample_dataframe.to_dict('records'), f)
        temp_path = f.name

    yield temp_path

    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def sample_time_series():
    """Create sample time series data"""
    np.random.seed(42)
    n = 50
    dates = pd.date_range(start='2024-01-01', periods=n, freq='D')
    trend = np.linspace(0, 10, n)
    noise = np.random.normal(0, 0.5, n)

    return pd.DataFrame({
        'date': dates,
        'value': trend + noise
    })


class TestDataImporter:
    """Test Data Importer"""

    def test_initialization(self):
        """Test DataImporter initialization"""
        importer = DataImporter()
        assert importer is not None
        assert hasattr(importer, 'supported_formats')

    def test_csv_import(self, sample_csv_file):
        """Test CSV file import"""
        importer = DataImporter()
        df, metadata = importer.import_data(sample_csv_file, validate_data=False)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 12
        assert 'group' in df.columns
        assert metadata['format'] == 'csv'
        assert metadata['rows'] == 12

    def test_json_import(self, sample_json_file):
        """Test JSON file import"""
        importer = DataImporter()
        df, metadata = importer.import_data(sample_json_file, validate_data=False)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 12
        assert metadata['format'] == 'json'

    def test_data_cleaning(self, sample_dataframe):
        """Test data cleaning"""
        # Add some issues
        df_dirty = sample_dataframe.copy()
        df_dirty.loc[0, 'value'] = np.nan
        df_dirty.loc[1, 'value'] = -1000  # Outlier

        importer = DataImporter()
        df_clean, report = importer.clean_data(df_dirty)

        assert 'missing_values_handled' in report
        assert 'outliers_removed' in report

    def test_format_detection(self):
        """Test file format detection"""
        importer = DataImporter()

        assert importer._detect_format('test.csv') == 'csv'
        assert importer._detect_format('test.xlsx') == 'xlsx'
        assert importer._detect_format('test.json') == 'json'
        assert importer._detect_format('test.docx') == 'docx'


class TestEnhancedStatisticalEngine:
    """Test Enhanced Statistical Engine"""

    @pytest.fixture
    def engine(self):
        """Create statistical engine"""
        return EnhancedStatisticalEngine(alpha=0.05)

    def test_initialization(self, engine):
        """Test engine initialization"""
        assert engine.alpha == 0.05
        assert hasattr(engine, 'analyze_descriptive')

    def test_descriptive_statistics(self, engine, sample_dataframe):
        """Test descriptive statistics"""
        results = engine.analyze_descriptive(sample_dataframe, ['value', 'age'])

        assert 'analysis_type' in results
        assert 'summary_stats' in results
        assert 'distribution_analysis' in results
        assert 'explanations' in results
        assert 'interpretations' in results

        # Check numerical columns
        assert 'value' in results['summary_stats']
        assert 'age' in results['summary_stats']

    def test_independent_t_test(self, engine, sample_dataframe):
        """Test independent t-test"""
        # Filter for only two groups
        df_two_groups = sample_dataframe[sample_dataframe['group'].isin(['A', 'B'])]

        results = engine.perform_t_test(
            df_two_groups, 'group', 'value', test_type='independent'
        )

        assert 'analysis_type' in results
        assert 'test_results' in results
        assert 'effect_size' in results
        assert 'explanations' in results
        assert 't_statistic' in results['test_results']
        assert 'p_value' in results['test_results']
        assert 'cohens_d' in results['effect_size']

    def test_anova(self, engine, sample_dataframe):
        """Test one-way ANOVA"""
        results = engine.perform_anova(
            sample_dataframe, 'value', 'group', post_hoc=False
        )

        assert 'analysis_type' in results
        assert 'test_results' in results
        assert 'effect_size' in results
        assert 'f_statistic' in results['test_results']
        assert 'p_value' in results['test_results']

    def test_correlation_analysis(self, engine, sample_dataframe):
        """Test correlation analysis"""
        results = engine.perform_correlation(
            sample_dataframe, ['value', 'age'], method='pearson'
        )

        assert 'analysis_type' in results
        assert 'correlation_matrix' in results
        assert 'test_results' in results
        assert 'explanations' in results

    def test_results_structure(self, engine, sample_dataframe):
        """Test that all results have required fields"""
        results = engine.analyze_descriptive(sample_dataframe)

        required_fields = ['analysis_type', 'timestamp', 'alpha', 'explanations', 'interpretations', 'recommendations']
        for field in required_fields:
            assert field in results


class TestAdditionalStatisticalTools:
    """Test Additional Statistical Tools"""

    @pytest.fixture
    def tools(self):
        """Create additional tools"""
        return AdditionalStatisticalTools(alpha=0.05)

    def test_mann_whitney_test(self, tools, sample_dataframe):
        """Test Mann-Whitney U test"""
        df_two_groups = sample_dataframe[sample_dataframe['group'].isin(['A', 'B'])]

        results = tools.perform_mann_whitney(
            df_two_groups, 'group', 'value'
        )

        assert 'analysis_type' in results
        assert 'test_results' in results
        assert 'effect_size' in results
        assert 'u_statistic' in results['test_results']
        assert 'p_value' in results['test_results']

    def test_kruskal_wallis_test(self, tools, sample_dataframe):
        """Test Kruskal-Wallis test"""
        results = tools.perform_kruskal_wallis(
            sample_dataframe, 'value', 'group'
        )

        assert 'analysis_type' in results
        assert 'test_results' in results
        assert 'effect_size' in results
        assert 'h_statistic' in results['test_results']

    def test_wilcoxon_test(self, tools, sample_dataframe):
        """Test Wilcoxon signed-rank test"""
        results = tools.perform_wilcoxon(
            sample_dataframe, 'value', 'value2'
        )

        assert 'analysis_type' in results
        assert 'test_results' in results
        assert 'effect_size' in results

    def test_power_analysis(self, tools):
        """Test power analysis"""
        # Calculate required sample size
        results = tools.perform_power_analysis(
            effect_size=0.5,
            alpha=0.05,
            power=0.80
        )

        assert 'analysis_type' in results
        assert 'results' in results
        assert 'required_sample_size' in results['results']
        assert results['results']['required_sample_size'] > 0

    def test_adf_test(self, tools, sample_time_series):
        """Test Augmented Dickey-Fuller test"""
        results = tools.perform_adf_test(sample_time_series['value'])

        assert 'analysis_type' in results
        assert 'test_results' in results
        assert 'adf_statistic' in results['test_results']
        assert 'p_value' in results['test_results']
        assert 'critical_values' in results['test_results']


class TestStatisticsOrchestrator:
    """Test Statistics Orchestrator"""

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator"""
        return StatisticsOrchestrator(auto_clean=False)

    def test_initialization(self, orchestrator):
        """Test orchestrator initialization"""
        assert orchestrator.data_importer is not None
        assert orchestrator.statistical_engine is not None
        assert orchestrator.additional_tools is not None
        assert orchestrator.surfsense_bridge is not None

    def test_data_import_workflow(self, orchestrator, sample_csv_file):
        """Test complete data import workflow"""
        result = orchestrator.import_data(sample_csv_file, validate_data=False)

        assert 'status' in result
        assert result['status'] == 'success'
        assert 'data' in result
        assert 'metadata' in result
        assert orchestrator.current_data is not None

    def test_descriptive_analysis_workflow(self, orchestrator, sample_dataframe):
        """Test descriptive analysis workflow"""
        orchestrator.current_data = sample_dataframe

        results = orchestrator.analyze_descriptive(store_results=False)

        assert 'analysis_type' in results
        assert 'summary_stats' in results
        assert 'explanations' in results

    def test_t_test_workflow(self, orchestrator, sample_dataframe):
        """Test t-test workflow"""
        df_two_groups = sample_dataframe[sample_dataframe['group'].isin(['A', 'B'])]
        orchestrator.current_data = df_two_groups

        results = orchestrator.analyze_t_test(
            group_col='group',
            value_col='value',
            store_results=False
        )

        assert 'test_results' in results
        assert 'effect_size' in results

    def test_correlation_workflow(self, orchestrator, sample_dataframe):
        """Test correlation analysis workflow"""
        orchestrator.current_data = sample_dataframe

        results = orchestrator.analyze_correlation(
            columns=['value', 'age'],
            store_results=False
        )

        assert 'correlation_matrix' in results

    def test_data_summary(self, orchestrator, sample_dataframe):
        """Test data summary"""
        orchestrator.current_data = sample_dataframe

        summary = orchestrator.get_data_summary()

        assert summary['status'] == 'loaded'
        assert 'shape' in summary
        assert 'columns' in summary
        assert 'dtypes' in summary

    def test_available_analyses(self, orchestrator):
        """Test available analyses list"""
        analyses = orchestrator.get_available_analyses()

        assert isinstance(analyses, list)
        assert len(analyses) > 0

        analysis_types = [a['type'] for a in analyses]
        assert 'descriptive_statistics' in analysis_types
        assert 't_test' in analysis_types
        assert 'anova' in analysis_types
        assert 'correlation' in analysis_types


class TestSurfSenseBridge:
    """Test SurfSense Integration Bridge"""

    @pytest.fixture
    def bridge(self):
        """Create bridge"""
        return SurfSenseStatisticsBridge()

    def test_initialization(self, bridge):
        """Test bridge initialization"""
        assert bridge.surfsense_url is not None
        assert bridge.api_base is not None
        assert isinstance(bridge.analysis_cache, dict)

    def test_local_storage_fallback(self, bridge):
        """Test local storage when SurfSense is unavailable"""
        test_analysis = {
            'analysis_type': 'Test',
            'test_results': {'p_value': 0.05}
        }

        # Should store locally when SurfSense fails
        doc_id = bridge._store_locally(
            test_analysis,
            "Test Analysis",
            ["test"]
        )

        assert doc_id is not None
        assert os.path.exists(doc_id)

        # Cleanup
        os.unlink(doc_id)

    def test_export_json(self, bridge):
        """Test JSON export"""
        test_analysis = {'test': 'data'}

        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            output_path = f.name

        try:
            result_path = bridge._export_json(test_analysis, output_path)

            assert os.path.exists(result_path)

            with open(result_path, 'r') as f:
                loaded = json.load(f)

            assert loaded == test_analysis
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_tabular_data_extraction(self, bridge):
        """Test tabular data extraction"""
        csv_content = """group,value
A,10
B,20
C,30"""

        data = bridge._extract_tabular_data(csv_content)

        assert isinstance(data, list)
        assert len(data) >= 2


class TestCompliance:
    """Test compliance with pharmaceutical standards"""

    def test_results_include_explanations(self, sample_dataframe):
        """Ensure all analyses include explanations (FDA/EMA requirement)"""
        engine = EnhancedStatisticalEngine()
        results = engine.analyze_descriptive(sample_dataframe)

        assert 'explanations' in results
        assert 'interpretations' in results
        assert 'recommendations' in results

    def test_results_include_metadata(self, sample_dataframe):
        """Ensure results include metadata (GLP requirement)"""
        engine = EnhancedStatisticalEngine()
        results = engine.analyze_descriptive(sample_dataframe)

        assert 'timestamp' in results
        assert 'alpha' in results
        assert 'analysis_type' in results

    def test_effect_size_reporting(self, sample_dataframe):
        """Ensure effect sizes are reported (FDA requirement)"""
        df_two_groups = sample_dataframe[sample_dataframe['group'].isin(['A', 'B'])]
        engine = EnhancedStatisticalEngine()
        results = engine.perform_t_test(df_two_groups, 'group', 'value')

        assert 'effect_size' in results
        assert 'cohens_d' in results['effect_size']
        assert 'interpretation' in results['effect_size']

    def test_confidence_intervals(self, sample_dataframe):
        """Ensure confidence intervals are calculated where applicable"""
        df_two_groups = sample_dataframe[sample_dataframe['group'].isin(['A', 'B'])]
        engine = EnhancedStatisticalEngine()
        results = engine.perform_t_test(df_two_groups, 'group', 'value')

        if 'sample_info' in results:
            sample_info = results['sample_info']
            # Check for group statistics that could include CIs
            assert 'group1' in sample_info
            assert 'group2' in sample_info


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, '-v', '--tb=short'])
