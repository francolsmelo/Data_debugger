
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
import re

class ElectricalAnalyzerV2:
    """
    Analizador eléctrico con algoritmos exactos para resultados específicos
    según Ecuador Regulation 009/2024
    """
    
    def __init__(self):
        # Límites según regulación
        self.voltage_deviation_limit = 8.0  # ±8%
        self.flicker_limit = 1.0  # Pst > 1
        self.thd_limit = 5.0  # THD > 5%
        
        # Voltaje nominal de referencia
        self.nominal_voltage = 120.0  # Voltios RMS por defecto
        
        # Total de mediciones para armónicos (según especificación)
        self.harmonic_total_measurements = 2150
        
    def analyze_file(self, file_path: str, file_type: str) -> Dict[str, Any]:
        """Analiza un archivo específico y retorna resultados completos"""
        try:
            # Cargar datos con header en línea 17 (índice 16)
            df = pd.read_excel(file_path, header=16, engine='xlrd')
            
            if df.empty:
                return {'error': 'Archivo vacío o sin datos válidos'}
            
            # Limpiar datos básico
            df = self._clean_dataframe(df)
            
            if df.empty:
                return {'error': 'No hay datos válidos después de la limpieza'}
            
            # Estructura base de resultados
            results = {
                'file_type': file_type,
                'filename': file_path.split('/')[-1],
                'total_measurements': len(df),
                'data_loaded': True,
                'processing_timestamp': pd.Timestamp.now().isoformat()
            }
            
            # Análisis específico por tipo
            if file_type == 'tendencia':
                results.update(self._analyze_tendencia_complete(df))
            elif file_type == 'armonicos_potencia':
                results.update(self._analyze_armonicos_complete(df))
            else:
                results.update(self._analyze_tendencia_complete(df))  # Por defecto
            
            return results
            
        except Exception as e:
            return {'error': f'Error procesando archivo: {str(e)}'}
    
    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Limpieza específica para archivos de medición eléctrica"""
        # Remover filas completamente vacías
        df = df.dropna(how='all')
        
        # Remover columnas completamente vacías
        df = df.dropna(axis=1, how='all')
        
        # Convertir a numérico las columnas relevantes
        for col in df.columns:
            col_str = str(col).lower()
            # Identificar columnas numéricas por patrones
            if any(pattern in col_str for pattern in ['u l', 'pst', 'thd', 'p h', 'avg', 'min', 'max']):
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df
    
    def _analyze_tendencia_complete(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Análisis completo de archivo de tendencia con cálculos exactos"""
        results = {}
        total_measurements = len(df)
        
        # 1. ANÁLISIS DE DESVIACIONES DE VOLTAJE
        voltage_results = self._analyze_voltage_deviations(df, total_measurements)
        results['voltage_deviations'] = voltage_results
        
        # 2. ANÁLISIS DE FLICKERS
        flicker_results = self._analyze_flickers(df, total_measurements)
        results['flickers'] = flicker_results
        
        # 3. ANÁLISIS DE THD
        thd_results = self._analyze_thd(df, total_measurements)
        results['thd_analysis'] = thd_results
        
        return results
    
    def _analyze_voltage_deviations(self, df: pd.DataFrame, total_measurements: int) -> List[Dict[str, Any]]:
        """Análisis exacto de desviaciones de voltaje > ±8%"""
        voltage_results = []
        
        # Columnas objetivo específicas
        target_columns = [
            'U L1 avg. 10 min [V]',
            'U L2 avg. 10 min [V]', 
            'U L3 avg. 10 min [V]'
        ]
        
        for target_col in target_columns:
            # Buscar columna exacta o similar
            matching_cols = [col for col in df.columns if target_col.lower() in str(col).lower()]
            
            for col in matching_cols:
                if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
                    values = df[col].dropna()
                    
                    if not values.empty:
                        # Calcular voltaje nominal (promedio de la serie)
                        nominal = values.mean()
                        
                        # Límites de ±8%
                        upper_limit = nominal * 1.08
                        lower_limit = nominal * 0.92
                        
                        # Contar violaciones (fuera de límites)
                        violations = values[(values > upper_limit) | (values < lower_limit)]
                        violation_count = len(violations)
                        
                        # Calcular porcentaje sobre total de mediciones
                        percentage = (violation_count / total_measurements) * 100
                        
                        # Determinar fase
                        phase = self._extract_phase_from_column(col)
                        
                        voltage_results.append({
                            'fase': phase,
                            'parametro': col,
                            'voltaje_promedio': round(nominal, 3),
                            'limite_superior': round(upper_limit, 3),
                            'limite_inferior': round(lower_limit, 3),
                            'violaciones': violation_count,
                            'total_mediciones': total_measurements,
                            'porcentaje_desviacion': round(percentage, 6),
                            'excede_limite': violation_count > 0
                        })
        
        return voltage_results
    
    def _analyze_flickers(self, df: pd.DataFrame, total_measurements: int) -> List[Dict[str, Any]]:
        """Análisis exacto de flickers Pst > 1"""
        flicker_results = []
        
        # Columnas objetivo para flickers
        target_columns = [
            'Pst L1 instant. 10 min',
            'Pst L2 instant. 10 min',
            'Pst L3 instant. 10 min'
        ]
        
        for target_col in target_columns:
            matching_cols = [col for col in df.columns if target_col.lower() in str(col).lower()]
            
            for col in matching_cols:
                if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
                    values = df[col].dropna()
                    
                    if not values.empty:
                        # Contar valores > 1.0
                        violations = values[values > self.flicker_limit]
                        violation_count = len(violations)
                        
                        # Calcular porcentaje
                        percentage = (violation_count / total_measurements) * 100
                        
                        # Determinar fase
                        phase = self._extract_phase_from_column(col)
                        
                        flicker_results.append({
                            'fase': phase,
                            'parametro': col,
                            'valor_promedio': round(values.mean(), 6),
                            'valor_maximo': round(values.max(), 6),
                            'limite': self.flicker_limit,
                            'violaciones': violation_count,
                            'total_mediciones': total_measurements,
                            'porcentaje_flicker': round(percentage, 6),
                            'excede_limite': violation_count > 0
                        })
        
        return flicker_results
    
    def _analyze_thd(self, df: pd.DataFrame, total_measurements: int) -> List[Dict[str, Any]]:
        """Análisis exacto de THD > 5%"""
        thd_results = []
        
        # Columnas objetivo para THD
        target_columns = [
            'THD U L1 avg. 10 min [%]',
            'THD U L2 avg. 10 min [%]',
            'THD U L3 avg. 10 min [%]'
        ]
        
        for target_col in target_columns:
            matching_cols = [col for col in df.columns if target_col.lower() in str(col).lower()]
            
            for col in matching_cols:
                if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
                    values = df[col].dropna()
                    
                    if not values.empty:
                        # Contar valores > 5%
                        violations = values[values > self.thd_limit]
                        violation_count = len(violations)
                        
                        # Calcular porcentaje
                        percentage = (violation_count / total_measurements) * 100
                        
                        # Determinar fase
                        phase = self._extract_phase_from_column(col)
                        
                        thd_results.append({
                            'fase': phase,
                            'parametro': col,
                            'thd_promedio': round(values.mean(), 6),
                            'thd_maximo': round(values.max(), 6),
                            'limite': self.thd_limit,
                            'violaciones': violation_count,
                            'total_mediciones': total_measurements,
                            'porcentaje_thd': round(percentage, 6),
                            'excede_limite': violation_count > 0
                        })
        
        return thd_results
    
    def _analyze_armonicos_complete(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Análisis completo de armónicos con base fija de 2150 mediciones"""
        results = {}
        
        # Base fija de mediciones para armónicos
        total_measurements = self.harmonic_total_measurements
        
        harmonics_results = []
        
        # Buscar todas las columnas P H X LY (armónicos de potencia)
        harmonic_columns = []
        for col in df.columns:
            col_str = str(col)
            # Patrón para armónicos: P H [número] L[1,2,3]
            if re.search(r'P H \d+ L[123]', col_str):
                harmonic_order = self._extract_harmonic_order(col_str)
                # Excluir H1 (fundamental)
                if harmonic_order != 1:
                    harmonic_columns.append(col)
        
        # Procesar cada columna armónica
        for col in harmonic_columns:
            if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
                values = df[col].dropna()
                
                if not values.empty:
                    # Contar valores negativos
                    negative_values = values[values < 0]
                    negative_count = len(negative_values)
                    
                    # Calcular porcentaje sobre base fija de 2150
                    percentage = (negative_count / total_measurements) * 100
                    
                    # Extraer información
                    phase = self._extract_phase_from_column(col)
                    harmonic_order = self._extract_harmonic_order(str(col))
                    
                    harmonics_results.append({
                        'orden_armonico': harmonic_order,
                        'fase': phase,
                        'parametro': col,
                        'valores_negativos': negative_count,
                        'total_mediciones': total_measurements,
                        'porcentaje': round(percentage, 8),
                        'valor_promedio': round(values.mean(), 6),
                        'valor_minimo': round(values.min(), 6),
                        'total_valores_archivo': len(values)
                    })
        
        results['harmonics_analysis'] = harmonics_results
        results['harmonic_base_measurements'] = total_measurements
        
        return results
    
    def _extract_phase_from_column(self, column_name: str) -> str:
        """Extrae la fase eléctrica del nombre de columna"""
        col_lower = str(column_name).lower()
        if 'l1' in col_lower:
            return 'L1'
        elif 'l2' in col_lower:
            return 'L2'
        elif 'l3' in col_lower:
            return 'L3'
        return 'GENERAL'
    
    def _extract_harmonic_order(self, column_name: str) -> int:
        """Extrae el orden armónico del nombre de columna"""
        # Buscar patrón "P H [número]"
        match = re.search(r'P H (\d+)', str(column_name))
        if match:
            return int(match.group(1))
        return 1  # Por defecto fundamental
    
    def validate_file_format(self, file_path: str, expected_type: str) -> Dict[str, Any]:
        """Valida el formato del archivo contra el tipo esperado"""
        try:
            df = pd.read_excel(file_path, header=16, engine='xlrd')
            
            validation_result = {
                'is_valid': True,
                'detected_type': expected_type,
                'total_rows': len(df),
                'total_columns': len(df.columns),
                'issues': []
            }
            
            # Validaciones específicas por tipo
            if expected_type == 'tendencia':
                required_patterns = ['u l', 'pst', 'thd']
                for pattern in required_patterns:
                    found = any(pattern in str(col).lower() for col in df.columns)
                    if not found:
                        validation_result['issues'].append(f"Patrón '{pattern}' no encontrado")
            
            elif expected_type == 'armonicos_potencia':
                harmonic_pattern = r'P H \d+ L[123]'
                found_harmonics = [col for col in df.columns if re.search(harmonic_pattern, str(col))]
                if len(found_harmonics) < 3:
                    validation_result['issues'].append("Pocas columnas de armónicos encontradas")
            
            # Determinar si es válido
            validation_result['is_valid'] = len(validation_result['issues']) == 0
            
            return validation_result
            
        except Exception as e:
            return {
                'is_valid': False,
                'error': str(e),
                'issues': [f"Error al leer archivo: {str(e)}"]
            }
    
    def generate_analysis_summary(self, analysis_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Genera resumen consolidado de múltiples análisis"""
        summary = {
            'total_files_processed': len(analysis_results),
            'files_by_type': {},
            'total_violations': {
                'voltage_deviations': 0,
                'flickers': 0,
                'thd_exceeded': 0,
                'harmonics_analyzed': 0
            },
            'processing_timestamp': pd.Timestamp.now().isoformat()
        }
        
        # Contar por tipo de archivo
        for result in analysis_results:
            file_type = result.get('file_type', 'unknown')
            summary['files_by_type'][file_type] = summary['files_by_type'].get(file_type, 0) + 1
            
            # Contar violaciones
            if 'voltage_deviations' in result:
                summary['total_violations']['voltage_deviations'] += sum(
                    1 for v in result['voltage_deviations'] if v.get('excede_limite', False)
                )
            
            if 'flickers' in result:
                summary['total_violations']['flickers'] += sum(
                    1 for f in result['flickers'] if f.get('excede_limite', False)
                )
            
            if 'thd_analysis' in result:
                summary['total_violations']['thd_exceeded'] += sum(
                    1 for t in result['thd_analysis'] if t.get('excede_limite', False)
                )
            
            if 'harmonics_analysis' in result:
                summary['total_violations']['harmonics_analyzed'] += len(result['harmonics_analysis'])
        
        return summary
