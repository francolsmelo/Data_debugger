import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
import re

class DataProcessor:
    """
    Handles data cleaning and processing for electrical measurement files
    according to Ecuador Regulation 009/2024
    """
    
    def __init__(self):
        self.numeric_columns_patterns = {
            'tendencia': ['voltage', 'current', 'power', 'frequency', 'thd'],
            'armonicos_potencia': ['harmonic', 'magnitude', 'phase', 'distortion'],
            'armonicos_voltaje': ['voltage', 'harmonic', 'amplitude', 'phase']
        }
    
    def clean_data(self, df: pd.DataFrame, file_type: str, interpolation_method: str = 'linear_interpolation') -> pd.DataFrame:
        """
        Clean and process the data according to file type and regulation requirements
        """
        if df is None or df.empty:
            return pd.DataFrame()
        
        # Make a copy to avoid modifying original data
        cleaned_df = df.copy()
        
        # Step 1: Clean column names
        cleaned_df = self._clean_column_names(cleaned_df)
        
        # Step 2: Remove completely empty rows and columns
        cleaned_df = self._remove_empty_rows_columns(cleaned_df)
        
        # Step 3: Identify and clean numeric columns
        cleaned_df = self._clean_numeric_columns(cleaned_df, file_type)
        
        # Step 4: Handle missing values
        cleaned_df = self._handle_missing_values(cleaned_df, interpolation_method)
        
        # Step 5: Remove duplicates
        cleaned_df = self._remove_duplicates(cleaned_df)
        
        # Step 6: Apply file-type specific cleaning
        cleaned_df = self._apply_file_specific_cleaning(cleaned_df, file_type)
        
        return cleaned_df
    
    def _clean_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize column names"""
        # Remove special characters and normalize spaces
        df.columns = df.columns.astype(str)
        df.columns = [re.sub(r'[^\w\s]', '', col).strip() for col in df.columns]
        df.columns = [re.sub(r'\s+', '_', col) for col in df.columns]
        df.columns = [col.lower() for col in df.columns]
        
        # Remove unnamed columns or columns with generic names
        df = df.loc[:, ~pd.Series(df.columns).str.contains('^unnamed', case=False, na=False)]
        
        return df
    
    def _remove_empty_rows_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove rows and columns that are completely empty"""
        # Remove columns that are entirely NaN or empty strings
        df = df.dropna(axis=1, how='all')
        df = df.loc[:, ~df.apply(lambda x: x.astype(str).str.strip().eq('').all())]
        
        # Remove rows that are entirely NaN or empty
        df = df.dropna(axis=0, how='all')
        df = df.loc[~df.apply(lambda x: x.astype(str).str.strip().eq('').all(), axis=1)]
        
        return df
    
    def _clean_numeric_columns(self, df: pd.DataFrame, file_type: str) -> pd.DataFrame:
        """Identify and clean numeric columns based on file type"""
        for column in df.columns:
            if self._is_numeric_column(column, file_type):
                df[column] = self._convert_to_numeric(df[column])
        
        return df
    
    def _is_numeric_column(self, column_name: str, file_type: str) -> bool:
        """Determine if a column should be treated as numeric based on its name and file type"""
        column_lower = column_name.lower()
        
        # Get patterns for this file type
        patterns = self.numeric_columns_patterns.get(file_type, [])
        
        # Check if column name contains any of the numeric patterns
        for pattern in patterns:
            if pattern in column_lower:
                return True
        
        # Additional common numeric column indicators
        numeric_indicators = [
            'value', 'val', 'measurement', 'reading', 'level', 'amplitude',
            'magnitude', 'rms', 'avg', 'min', 'max', 'std', 'mean',
            'percent', 'ratio', 'factor', 'time', 'date', 'timestamp'
        ]
        
        return any(indicator in column_lower for indicator in numeric_indicators)
    
    def _convert_to_numeric(self, series: pd.Series) -> pd.Series:
        """Convert a series to numeric, handling various text formats"""
        # Convert to string first to handle mixed types
        series_str = series.astype(str)
        
        # Remove common non-numeric characters
        series_str = series_str.str.replace(r'[^\d\.\-\+eE]', '', regex=True)
        
        # Replace empty strings with NaN
        series_str = series_str.replace('', np.nan)
        
        # Convert to numeric
        return pd.to_numeric(series_str, errors='coerce')
    
    def _handle_missing_values(self, df: pd.DataFrame, method: str) -> pd.DataFrame:
        """Handle missing values based on the specified method"""
        if method == 'linear_interpolation':
            # Apply linear interpolation to numeric columns only
            numeric_columns = df.select_dtypes(include=[np.number]).columns
            df[numeric_columns] = df[numeric_columns].interpolate(method='linear')
        
        elif method == 'forward_fill':
            df = df.fillna(method='ffill')
        
        elif method == 'backward_fill':
            df = df.fillna(method='bfill')
        
        elif method == 'remove':
            df = df.dropna()
        
        return df
    
    def _remove_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove duplicate rows while preserving the first occurrence"""
        return df.drop_duplicates(keep='first')
    
    def _apply_file_specific_cleaning(self, df: pd.DataFrame, file_type: str) -> pd.DataFrame:
        """Apply file-type specific cleaning rules"""
        if file_type == 'tendencia':
            return self._clean_tendencia_data(df)
        elif file_type == 'armonicos_potencia':
            return self._clean_armonicos_potencia_data(df)
        elif file_type == 'armonicos_voltaje':
            return self._clean_armonicos_voltaje_data(df)
        
        return df
    
    def _clean_tendencia_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean tendencia (trend) data specific formatting"""
        # Sort by timestamp if available
        timestamp_cols = [col for col in df.columns if 'time' in col.lower() or 'date' in col.lower()]
        if timestamp_cols:
            try:
                df[timestamp_cols[0]] = pd.to_datetime(df[timestamp_cols[0]], errors='coerce')
                df = df.sort_values(by=timestamp_cols[0])
            except:
                pass
        
        # Remove rows with invalid voltage readings (negative values where not expected)
        voltage_cols = [col for col in df.columns if 'voltage' in col.lower() or 'volt' in col.lower()]
        for col in voltage_cols:
            if col in df.columns and df[col].dtype in ['float64', 'int64']:
                # Remove rows where voltage is negative (assuming AC RMS measurements)
                df = df[df[col] >= 0]
        
        return df
    
    def _clean_armonicos_potencia_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean harmonic power data specific formatting"""
        # Ensure harmonic order is positive integer
        harmonic_cols = [col for col in df.columns if 'harmonic' in col.lower()]
        for col in harmonic_cols:
            if col in df.columns and df[col].dtype in ['float64', 'int64']:
                df = df[df[col] > 0]  # Harmonic order must be positive
                df[col] = df[col].round().astype(int)  # Round to nearest integer
        
        # Phase values should be between -180 and 180 degrees
        phase_cols = [col for col in df.columns if 'phase' in col.lower() or 'angle' in col.lower()]
        for col in phase_cols:
            if col in df.columns and df[col].dtype in ['float64', 'int64']:
                # Wrap phase values to [-180, 180] range
                df[col] = ((df[col] + 180) % 360) - 180
        
        return df
    
    def _clean_armonicos_voltaje_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean harmonic voltage data specific formatting"""
        # Similar to power harmonics but with voltage-specific validations
        harmonic_cols = [col for col in df.columns if 'harmonic' in col.lower()]
        for col in harmonic_cols:
            if col in df.columns and df[col].dtype in ['float64', 'int64']:
                df = df[df[col] > 0]  # Harmonic order must be positive
                df[col] = df[col].round().astype(int)
        
        # Voltage amplitude should be positive
        amplitude_cols = [col for col in df.columns if 'amplitude' in col.lower() or 'magnitude' in col.lower()]
        for col in amplitude_cols:
            if col in df.columns and df[col].dtype in ['float64', 'int64']:
                df = df[df[col] >= 0]  # Amplitude must be non-negative
        
        # Phase values should be between -180 and 180 degrees
        phase_cols = [col for col in df.columns if 'phase' in col.lower() or 'angle' in col.lower()]
        for col in phase_cols:
            if col in df.columns and df[col].dtype in ['float64', 'int64']:
                df[col] = ((df[col] + 180) % 360) - 180
        
        return df
    
    def get_data_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate a summary of the processed data"""
        if df.empty:
            return {}
        
        summary = {
            'total_rows': len(df),
            'total_columns': len(df.columns),
            'numeric_columns': len(df.select_dtypes(include=[np.number]).columns),
            'missing_values': df.isnull().sum().sum(),
            'duplicate_rows': df.duplicated().sum(),
            'data_types': df.dtypes.to_dict(),
            'memory_usage': df.memory_usage(deep=True).sum()
        }
        
        # Add column-wise statistics for numeric columns
        numeric_df = df.select_dtypes(include=[np.number])
        if not numeric_df.empty:
            summary['numeric_stats'] = {
                'mean': numeric_df.mean().to_dict(),
                'std': numeric_df.std().to_dict(),
                'min': numeric_df.min().to_dict(),
                'max': numeric_df.max().to_dict(),
                'median': numeric_df.median().to_dict()
            }
        
        return summary
