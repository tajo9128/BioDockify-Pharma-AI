"""Data Importer Module for BioDockify AI Statistics

Supports multiple input formats: Excel, CSV, DOCX, JSON
Following international pharmaceutical research standards (GLP/GCP)
"""

import os
import pandas as pd
import numpy as np
import json
import csv
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path
from docx import Document, table
from datetime import datetime
import warnings

warnings.filterwarnings("ignore")


class DataImporter:
    """Multi-format data importer for statistical analysis

    Supports:
    - Excel (.xlsx, .xls)
    - CSV (.csv)
    - Word documents (.docx) with tables
    - JSON (.json)

    Complies with GLP/GCP standards for data integrity
    """

    def __init__(self):
        self.supported_formats = {
            ".xlsx": self._import_excel,
            ".xls": self._import_excel,
            ".csv": self._import_csv,
            ".json": self._import_json,
            ".docx": self._import_docx,
        }
        self.import_log = []

    def _detect_format(self, file_path: str) -> str:
        """Detect file format from extension

        Args:
            file_path: Path to the file

        Returns:
            Detected format (xlsx, csv, json, docx)
        """
        path = Path(file_path)
        ext = path.suffix.lower()
        format_map = {
            ".xlsx": "xlsx",
            ".xls": "xlsx",
            ".csv": "csv",
            ".json": "json",
            ".docx": "docx",
        }
        return format_map.get(ext, "unknown")

    def import_data(
        self,
        file_path: Union[str, Path],
        sheet_name: Optional[str] = None,
        encoding: str = "utf-8",
        validate_data: bool = True,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Import data from various formats

        Args:
            file_path: Path to data file
            sheet_name: Sheet name for Excel files (None for first sheet)
            encoding: File encoding for CSV files
            validate_data: Whether to validate data integrity

        Returns:
            Tuple of (DataFrame, metadata)
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        file_ext = file_path.suffix.lower()

        if file_ext not in self.supported_formats:
            raise ValueError(
                f"Unsupported format: {file_ext}. "
                f"Supported formats: {list(self.supported_formats.keys())}"
            )

        # Import data
        import_func = self.supported_formats[file_ext]
        df = import_func(file_path, sheet_name, encoding)

        # Generate metadata
        metadata = self._generate_metadata(df, file_path)

        # Validate data if requested
        if validate_data:
            validation_results = self._validate_data(df)
            metadata["validation"] = validation_results

            if not validation_results["is_valid"]:
                warnings.warn(
                    f"Data validation issues detected: {validation_results['issues']}"
                )

        # Log import
        self._log_import(file_path, metadata)

        return df, metadata

    def _import_excel(
        self, file_path: Path, sheet_name: Optional[str], encoding: str
    ) -> pd.DataFrame:
        """Import data from Excel file"""
        try:
            if sheet_name:
                df = pd.read_excel(file_path, sheet_name=sheet_name, engine="openpyxl")
            else:
                df = pd.read_excel(file_path, engine="openpyxl")
            return df
        except Exception as e:
            # Try xlrd for older formats
            try:
                if sheet_name:
                    df = pd.read_excel(file_path, sheet_name=sheet_name, engine="xlrd")
                else:
                    df = pd.read_excel(file_path, engine="xlrd")
                return df
            except Exception:
                raise ValueError(f"Failed to import Excel file: {str(e)}")

    def _import_csv(
        self, file_path: Path, sheet_name: Optional[str], encoding: str
    ) -> pd.DataFrame:
        """Import data from CSV file"""
        try:
            # Try different delimiters
            for delimiter in [",", ";", "	", "|"]:
                try:
                    df = pd.read_csv(file_path, encoding=encoding, delimiter=delimiter)
                    if df.shape[1] > 1:  # Valid table found
                        return df
                except:
                    continue

            # Fallback to comma delimiter
            df = pd.read_csv(file_path, encoding=encoding)
            return df
        except Exception as e:
            raise ValueError(f"Failed to import CSV file: {str(e)}")

    def _import_json(
        self, file_path: Path, sheet_name: Optional[str], encoding: str
    ) -> pd.DataFrame:
        """Import data from JSON file"""
        try:
            with open(file_path, "r", encoding=encoding) as f:
                data = json.load(f)

            # Handle different JSON structures
            if isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, dict):
                if "data" in data:
                    df = pd.DataFrame(data["data"])
                elif "results" in data:
                    df = pd.DataFrame(data["results"])
                else:
                    df = pd.DataFrame([data])
            else:
                raise ValueError("Unsupported JSON structure")

            return df
        except Exception as e:
            raise ValueError(f"Failed to import JSON file: {str(e)}")

    def _import_docx(
        self, file_path: Path, sheet_name: Optional[str], encoding: str
    ) -> pd.DataFrame:
        """Import data from Word document tables"""
        try:
            doc = Document(file_path)
            tables = doc.tables

            if not tables:
                raise ValueError("No tables found in Word document")

            # Combine all tables or use first one
            dfs = []
            for i, table in enumerate(tables):
                data = []
                for row in table.rows:
                    row_data = [cell.text.strip() for cell in row.cells]
                    data.append(row_data)

                df = pd.DataFrame(data[1:], columns=data[0])
                df["source_table"] = f"table_{i + 1}"
                dfs.append(df)

            if len(dfs) == 1:
                return dfs[0]
            else:
                combined_df = pd.concat(dfs, ignore_index=True)
                return combined_df

        except Exception as e:
            raise ValueError(f"Failed to import Word document: {str(e)}")

    def _generate_metadata(self, df: pd.DataFrame, file_path: Path) -> Dict[str, Any]:
        """Generate metadata about imported data"""
        file_format = self._detect_format(str(file_path))
        metadata = {
            "file_name": file_path.name,
            "file_path": str(file_path.absolute()),
            "format": file_format,
            "import_timestamp": datetime.now().isoformat(),
            "rows": len(df),
            "columns": len(df.columns),
            "columns_list": df.columns.tolist(),
            "data_types": df.dtypes.astype(str).to_dict(),
            "memory_usage_mb": df.memory_usage(deep=True).sum() / (1024 * 1024),
            "missing_values": df.isnull().sum().to_dict(),
            "duplicate_rows": df.duplicated().sum(),
        }
        return metadata

    def _validate_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Validate data integrity according to GLP standards"""
        issues = []
        warnings_list = []

        # Check for missing values
        missing_pct = (df.isnull().sum() / len(df)) * 100
        high_missing = missing_pct[missing_pct > 50].index.tolist()
        if high_missing:
            issues.append(f"High missing values (>50%) in columns: {high_missing}")

        # Check for duplicates
        dup_count = df.duplicated().sum()
        if dup_count > 0:
            warnings_list.append(f"Found {dup_count} duplicate rows")

        # Check numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if df[col].isnull().all():
                issues.append(f"Numeric column '{col}' is entirely missing")

        # Check for constant columns
        const_cols = df.columns[df.nunique() <= 1].tolist()
        if const_cols:
            warnings_list.append(f"Constant columns found: {const_cols}")

        is_valid = len(issues) == 0

        return {
            "is_valid": is_valid,
            "issues": issues,
            "warnings": warnings_list,
            "missing_percentage": missing_pct.to_dict(),
            "numeric_columns": numeric_cols.tolist(),
            "categorical_columns": df.select_dtypes(
                include=["object"]
            ).columns.tolist(),
        }

    def _log_import(self, file_path: Path, metadata: Dict[str, Any]):
        """Log data import for audit trail"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "file": str(file_path),
            "rows": metadata["rows"],
            "columns": metadata["columns"],
            "validation": metadata.get("validation", {}),
        }
        self.import_log.append(log_entry)

    def get_import_log(self) -> List[Dict[str, Any]]:
        """Get import audit log"""
        return self.import_log

    def clean_data(
        self,
        df: pd.DataFrame,
        remove_duplicates: bool = True,
        handle_missing: str = "drop",  # 'drop', 'fill_mean', 'fill_median', 'fill_mode'
        convert_numeric: bool = True,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Clean imported data according to research standards

        Args:
            df: Input DataFrame
            remove_duplicates: Remove duplicate rows
            handle_missing: Strategy for handling missing values
            convert_numeric: Convert possible numeric columns

        Returns:
            Tuple of (cleaned DataFrame, cleaning report)
        """
        df_clean = df.copy()
        report = {
            "original_rows": len(df),
            "original_columns": len(df.columns),
            "operations": [],
        }

        # Remove duplicates
        if remove_duplicates:
            before = len(df_clean)
            df_clean = df_clean.drop_duplicates()
            after = len(df_clean)
            removed = before - after
            if removed > 0:
                report["operations"].append(f"Removed {removed} duplicate rows")

        # Handle missing values
        if handle_missing == "drop":
            before = len(df_clean)
            df_clean = df_clean.dropna()
            after = len(df_clean)
            removed = before - after
            if removed > 0:
                report["operations"].append(
                    f"Removed {removed} rows with missing values"
                )

        elif handle_missing == "fill_mean":
            numeric_cols = df_clean.select_dtypes(include=[np.number]).columns
            for col in numeric_cols:
                if df_clean[col].isnull().any():
                    mean_val = df_clean[col].mean()
                    df_clean[col].fillna(mean_val, inplace=True)
                    report["operations"].append(
                        f"Filled missing values in '{col}' with mean: {mean_val:.2f}"
                    )

        elif handle_missing == "fill_median":
            numeric_cols = df_clean.select_dtypes(include=[np.number]).columns
            for col in numeric_cols:
                if df_clean[col].isnull().any():
                    median_val = df_clean[col].median()
                    df_clean[col].fillna(median_val, inplace=True)
                    report["operations"].append(
                        f"Filled missing values in '{col}' with median: {median_val:.2f}"
                    )

        elif handle_missing == "fill_mode":
            for col in df_clean.columns:
                if df_clean[col].isnull().any():
                    mode_val = (
                        df_clean[col].mode()[0]
                        if not df_clean[col].mode().empty
                        else "Unknown"
                    )
                    df_clean[col].fillna(mode_val, inplace=True)
                    report["operations"].append(
                        f"Filled missing values in '{col}' with mode: {mode_val}"
                    )

        # Convert possible numeric columns
        if convert_numeric:
            for col in df_clean.select_dtypes(include=["object"]).columns:
                try:
                    converted = pd.to_numeric(df_clean[col], errors="coerce")
                    if (
                        converted.notna().sum() > len(df_clean) * 0.5
                    ):  # >50% convertible
                        df_clean[col] = converted
                        report["operations"].append(
                            f"Converted column '{col}' to numeric"
                        )
                except:
                    pass

        report["final_rows"] = len(df_clean)
        report["final_columns"] = len(df_clean.columns)
        report["rows_removed"] = report["original_rows"] - report["final_rows"]
        report["missing_values_handled"] = (
            len([op for op in report["operations"] if "missing" in op.lower()]) > 0
        )
        report["outliers_removed"] = False  # Not implemented in this version

        return df_clean, report


# Example usage
if __name__ == "__main__":
    importer = DataImporter()

    # Test with sample data
    sample_data = {
        "patient_id": [1, 2, 3, 4, 5],
        "age": [45, 52, 38, 61, 55],
        "treatment": ["Drug A", "Drug B", "Placebo", "Drug A", "Drug B"],
        "outcome": [7.2, 6.8, 5.1, 7.5, 6.9],
    }
    df_sample = pd.DataFrame(sample_data)
    df_sample.to_csv("/tmp/test_data.csv", index=False)

    df, metadata = importer.import_data("/tmp/test_data.csv")
    print("Import successful!")
    print(f"Metadata: {json.dumps(metadata, indent=2)}")
    print(f"Data shape: {df.shape}")
    print(df.head())
