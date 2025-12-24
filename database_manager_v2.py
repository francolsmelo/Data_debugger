
import sqlite3
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional
import json
import os

class DatabaseManagerV2:
    """
    Gestor de base de datos optimizado para análisis eléctricos
    con funciones completas de almacenamiento y recuperación
    """
    
    def __init__(self, db_path: str = "electrical_analysis_v2.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Inicializa la base de datos con todas las tablas necesarias"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tabla principal de análisis
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analysis_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                file_type TEXT NOT NULL,
                analysis_data TEXT NOT NULL,
                total_measurements INTEGER DEFAULT 0,
                processing_status TEXT DEFAULT 'completed',
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                file_size_kb REAL DEFAULT 0,
                validation_score REAL DEFAULT 100.0
            )
        ''')
        
        # Índices para mejor rendimiento
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_filename ON analysis_results(filename)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_file_type ON analysis_results(file_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON analysis_results(timestamp)')
        
        conn.commit()
        conn.close()
    
    def save_analysis(self, filename: str, file_type: str, analysis_data: Dict[str, Any]) -> int:
        """Guarda un análisis completo con metadatos"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Calcular metadatos
        total_measurements = analysis_data.get('total_measurements', 0)
        validation_score = self._calculate_validation_score(analysis_data)
        
        cursor.execute('''
            INSERT INTO analysis_results (
                filename, file_type, analysis_data, total_measurements, 
                validation_score, processing_status
            )
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            filename, file_type, json.dumps(analysis_data, indent=2), 
            total_measurements, validation_score, 'completed'
        ))
        
        analysis_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return analysis_id
    
    def _calculate_validation_score(self, analysis_data: Dict[str, Any]) -> float:
        """Calcula puntuación de validación del análisis"""
        score = 100.0
        
        # Penalizar si hay errores
        if 'error' in analysis_data:
            score -= 50.0
        
        # Bonificar completitud de datos
        data_completeness = 0
        expected_sections = ['voltage_deviations', 'flickers', 'thd_analysis', 'harmonics_analysis']
        
        for section in expected_sections:
            if section in analysis_data and analysis_data[section]:
                data_completeness += 25
        
        score = max(score * (data_completeness / 100), 0)
        
        return min(100.0, score)
    
    def get_all_analyses(self) -> List[Dict[str, Any]]:
        """Obtiene todos los análisis con metadatos"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, filename, file_type, analysis_data, total_measurements,
                   validation_score, processing_status, timestamp
            FROM analysis_results
            ORDER BY timestamp DESC
        ''')
        
        results = []
        for row in cursor.fetchall():
            try:
                analysis_data = json.loads(row[3])
                results.append({
                    'id': row[0],
                    'filename': row[1],
                    'file_type': row[2],
                    'analysis_data': analysis_data,
                    'total_measurements': row[4],
                    'validation_score': row[5],
                    'processing_status': row[6],
                    'timestamp': row[7]
                })
            except json.JSONDecodeError:
                continue
        
        conn.close()
        return results
    
    def get_voltage_deviations(self) -> pd.DataFrame:
        """Obtiene todas las desviaciones de voltaje en formato DataFrame"""
        analyses = self.get_all_analyses()
        voltage_data = []
        
        for analysis in analyses:
            if 'voltage_deviations' in analysis['analysis_data']:
                for deviation in analysis['analysis_data']['voltage_deviations']:
                    # Añadir metadatos del archivo
                    deviation_record = deviation.copy()
                    deviation_record.update({
                        'analysis_id': analysis['id'],
                        'filename': analysis['filename'],
                        'file_type': analysis['file_type'],
                        'timestamp': analysis['timestamp'],
                        'validation_score': analysis['validation_score']
                    })
                    voltage_data.append(deviation_record)
        
        return pd.DataFrame(voltage_data) if voltage_data else pd.DataFrame()
    
    def get_flickers(self) -> pd.DataFrame:
        """Obtiene todos los análisis de flickers"""
        analyses = self.get_all_analyses()
        flicker_data = []
        
        for analysis in analyses:
            if 'flickers' in analysis['analysis_data']:
                for flicker in analysis['analysis_data']['flickers']:
                    flicker_record = flicker.copy()
                    flicker_record.update({
                        'analysis_id': analysis['id'],
                        'filename': analysis['filename'],
                        'file_type': analysis['file_type'],
                        'timestamp': analysis['timestamp'],
                        'validation_score': analysis['validation_score']
                    })
                    flicker_data.append(flicker_record)
        
        return pd.DataFrame(flicker_data) if flicker_data else pd.DataFrame()
    
    def get_thd_analysis(self) -> pd.DataFrame:
        """Obtiene todos los análisis de THD"""
        analyses = self.get_all_analyses()
        thd_data = []
        
        for analysis in analyses:
            if 'thd_analysis' in analysis['analysis_data']:
                for thd in analysis['analysis_data']['thd_analysis']:
                    thd_record = thd.copy()
                    thd_record.update({
                        'analysis_id': analysis['id'],
                        'filename': analysis['filename'],
                        'file_type': analysis['file_type'],
                        'timestamp': analysis['timestamp'],
                        'validation_score': analysis['validation_score']
                    })
                    thd_data.append(thd_record)
        
        return pd.DataFrame(thd_data) if thd_data else pd.DataFrame()
    
    def get_harmonics_analysis(self) -> pd.DataFrame:
        """Obtiene todos los análisis de armónicos"""
        analyses = self.get_all_analyses()
        harmonic_data = []
        
        for analysis in analyses:
            if 'harmonics_analysis' in analysis['analysis_data']:
                for harmonic in analysis['analysis_data']['harmonics_analysis']:
                    harmonic_record = harmonic.copy()
                    harmonic_record.update({
                        'analysis_id': analysis['id'],
                        'filename': analysis['filename'],
                        'file_type': analysis['file_type'],
                        'timestamp': analysis['timestamp'],
                        'validation_score': analysis['validation_score']
                    })
                    harmonic_data.append(harmonic_record)
        
        return pd.DataFrame(harmonic_data) if harmonic_data else pd.DataFrame()
    
    def get_analysis_by_id(self, analysis_id: int) -> Optional[Dict[str, Any]]:
        """Obtiene un análisis específico por ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, filename, file_type, analysis_data, total_measurements,
                   validation_score, processing_status, timestamp
            FROM analysis_results
            WHERE id = ?
        ''', (analysis_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            try:
                return {
                    'id': row[0],
                    'filename': row[1],
                    'file_type': row[2],
                    'analysis_data': json.loads(row[3]),
                    'total_measurements': row[4],
                    'validation_score': row[5],
                    'processing_status': row[6],
                    'timestamp': row[7]
                }
            except json.JSONDecodeError:
                return None
        return None
    
    def delete_analysis(self, analysis_id: int) -> bool:
        """Elimina un análisis específico"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM analysis_results WHERE id = ?', (analysis_id,))
        deleted = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        
        return deleted
    
    def clear_all_data(self):
        """Elimina todos los datos de la base de datos"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM analysis_results')
        
        conn.commit()
        conn.close()
    
    def get_database_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas generales de la base de datos"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Estadísticas básicas
        cursor.execute('SELECT COUNT(*) FROM analysis_results')
        total_analyses = cursor.fetchone()[0]
        
        cursor.execute('SELECT file_type, COUNT(*) FROM analysis_results GROUP BY file_type')
        type_counts = dict(cursor.fetchall())
        
        cursor.execute('SELECT AVG(validation_score) FROM analysis_results')
        avg_validation_score = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT SUM(total_measurements) FROM analysis_results')
        total_measurements = cursor.fetchone()[0] or 0
        
        # Tamaño de base de datos
        db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
        
        conn.close()
        
        return {
            'total_analyses': total_analyses,
            'analyses_by_type': type_counts,
            'average_validation_score': round(avg_validation_score, 2),
            'total_measurements': total_measurements,
            'database_size_kb': round(db_size / 1024, 2),
            'last_updated': datetime.now().isoformat()
        }
    
    def export_complete_analysis(self) -> str:
        """Exporta análisis completo a Excel con formato mejorado"""
        output_path = f"analisis_completo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Hoja resumen
            stats = self.get_database_statistics()
            summary_data = pd.DataFrame([{
                'Métrica': k,
                'Valor': v
            } for k, v in stats.items()])
            summary_data.to_excel(writer, sheet_name='Resumen', index=False)
            
            # Desviaciones de voltaje
            voltage_df = self.get_voltage_deviations()
            if not voltage_df.empty:
                # Reorganizar columnas para mejor legibilidad
                voltage_export = voltage_df[[
                    'filename', 'fase', 'voltaje_promedio', 'porcentaje_desviacion',
                    'violaciones', 'total_mediciones', 'excede_limite', 'timestamp'
                ]].copy()
                voltage_export.to_excel(writer, sheet_name='Desviaciones_Voltaje', index=False)
            
            # Flickers
            flicker_df = self.get_flickers()
            if not flicker_df.empty:
                flicker_export = flicker_df[[
                    'filename', 'fase', 'valor_promedio', 'porcentaje_flicker',
                    'violaciones', 'total_mediciones', 'excede_limite', 'timestamp'
                ]].copy()
                flicker_export.to_excel(writer, sheet_name='Flickers', index=False)
            
            # THD
            thd_df = self.get_thd_analysis()
            if not thd_df.empty:
                thd_export = thd_df[[
                    'filename', 'fase', 'thd_promedio', 'porcentaje_thd',
                    'violaciones', 'total_mediciones', 'excede_limite', 'timestamp'
                ]].copy()
                thd_export.to_excel(writer, sheet_name='Distorsion_Armonica', index=False)
            
            # Armónicos
            harmonic_df = self.get_harmonics_analysis()
            if not harmonic_df.empty:
                harmonic_export = harmonic_df[[
                    'filename', 'orden_armonico', 'fase', 'porcentaje',
                    'valores_negativos', 'total_mediciones', 'valor_promedio', 'timestamp'
                ]].copy()
                harmonic_export.to_excel(writer, sheet_name='Analisis_Armonicos', index=False)
            
            # Lista de todos los archivos procesados
            all_analyses = self.get_all_analyses()
            if all_analyses:
                files_data = pd.DataFrame([{
                    'ID': a['id'],
                    'Archivo': a['filename'],
                    'Tipo': a['file_type'],
                    'Mediciones': a['total_measurements'],
                    'Puntuación': a['validation_score'],
                    'Estado': a['processing_status'],
                    'Fecha': a['timestamp']
                } for a in all_analyses])
                files_data.to_excel(writer, sheet_name='Archivos_Procesados', index=False)
        
        return output_path
    
    def backup_database(self, backup_path: str = None) -> str:
        """Crea una copia de seguridad de la base de datos"""
        if not backup_path:
            backup_path = f"backup_electrical_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        
        # Copiar archivo de base de datos
        import shutil
        shutil.copy2(self.db_path, backup_path)
        
        return backup_path
    
    def restore_database(self, backup_path: str) -> bool:
        """Restaura la base de datos desde una copia de seguridad"""
        try:
            import shutil
            shutil.copy2(backup_path, self.db_path)
            return True
        except Exception:
            return False
