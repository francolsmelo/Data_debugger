
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io
import os
from datetime import datetime
import time

from electrical_analyzer_v2 import ElectricalAnalyzerV2
from database_manager_v2 import DatabaseManagerV2

# Configuración de la página
st.set_page_config(
    page_title="Ecuador Regulation 009/2024 - Analizador Eléctrico",
    page_icon="⚡",
    layout="wide"
)

def check_admin_credentials(username: str, password: str) -> bool:
    """Verifica credenciales de administrador"""
    admin_users = {
        "admin": "admin123",
        "supervisor": "super123",
        "usuario": "password123"
    }
    return admin_users.get(username) == password

def admin_login():
    """Pantalla de login para administrador"""
    st.header("🔒 Acceso de Administrador")
    st.info("Ingrese sus credenciales para acceder al panel de administración")
    
    with st.form("admin_login"):
        col1, col2 = st.columns([1, 2])
        with col1:
            username = st.text_input("👤 Usuario", placeholder="Ingrese usuario")
            password = st.text_input("🔐 Contraseña", type="password", placeholder="Ingrese contraseña")
        
        with col2:
            st.markdown("**Usuarios por defecto:**")
            st.code("admin / admin123\nsupervisor / super123\nusuario / password123")
        
        submit = st.form_submit_button("🚀 Iniciar Sesión", use_container_width=True)
        
        if submit:
            if username and password:
                if check_admin_credentials(username, password):
                    st.session_state.admin_authenticated = True
                    st.session_state.admin_user = username
                    st.success(f"✅ Acceso autorizado para {username}")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Credenciales incorrectas")
            else:
                st.warning("⚠️ Complete todos los campos")

def main():
    st.title("⚡ Ecuador Regulation 009/2024 - Analizador de Datos Eléctricos")
    st.markdown("Dashboard integrado para análisis de mediciones eléctricas según normativa ecuatoriana")
    
    # Inicializar componentes
    analyzer = ElectricalAnalyzerV2()
    db_manager = DatabaseManagerV2()
    
    # Inicializar session state
    if 'analysis_results' not in st.session_state:
        st.session_state.analysis_results = []
    if 'admin_authenticated' not in st.session_state:
        st.session_state.admin_authenticated = False
    if 'processed_files' not in st.session_state:
        st.session_state.processed_files = []
    
    # Sidebar para subir archivos
    with st.sidebar:
        st.header("📁 Gestión de Archivos")
        
        # Información del sistema
        st.info("📋 **Formatos aceptados:**\n- Tendencia (voltaje, flicker, THD)\n- Armónicos Potencia\n- Máximo 30 archivos")
        
        uploaded_files = st.file_uploader(
            "🔍 Browse Files - Seleccionar archivos Excel",
            type=['xls', 'xlsx'],
            accept_multiple_files=True,
            help="Formatos: Tendencia 8 matrix, Armónicos potencia 8 matrix"
        )
        
        if uploaded_files:
            if len(uploaded_files) <= 30:
                st.success(f"✅ {len(uploaded_files)} archivo(s) cargado(s)")
                
                st.markdown("### 📋 Archivos Cargados")
                selected_files = []
                
                for i, uploaded_file in enumerate(uploaded_files):
                    # Detectar tipo de archivo automáticamente
                    file_type = detect_file_type(uploaded_file.name)
                    type_icon = "📈" if file_type == "tendencia" else "🌊"
                    
                    if st.checkbox(f"{type_icon} {uploaded_file.name}", 
                                 key=f"select_{i}_{uploaded_file.name}", 
                                 value=True):
                        selected_files.append(uploaded_file)
                
                st.markdown("---")
                
                # Botón de análisis prominente
                if st.button("🚀 Analizar Archivos Seleccionados", 
                           type="primary", 
                           use_container_width=True):
                    if selected_files:
                        analyze_files_and_show_results(selected_files, analyzer, db_manager)
                    else:
                        st.warning("⚠️ Seleccione al menos un archivo")
                
                # Estadísticas de selección
                st.markdown(f"**📊 Seleccionados:** {len(selected_files)}/{len(uploaded_files)}")
                
            else:
                st.error(f"❌ Máximo 30 archivos permitidos. Tienes {len(uploaded_files)}")
    
    # Tabs principales del dashboard
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Dashboard Principal-Resumen", 
        "⚡ Desviaciones de Voltaje", 
        "💫 Flickers", 
        "🌊 Distorsión Armónica", 
        "🔢 Análisis Armónicos",
        "👤 Administrador"
    ])
    
    with tab1:
        display_main_dashboard(db_manager)
    
    with tab2:
        display_voltage_deviations(db_manager)
    
    with tab3:
        display_flickers(db_manager)
    
    with tab4:
        display_harmonic_distortion(db_manager)
    
    with tab5:
        display_harmonics_analysis(db_manager)
    
    with tab6:
        display_admin_configuration(db_manager)

def detect_file_type(filename):
    """Detecta automáticamente el tipo de archivo"""
    filename_lower = filename.lower()
    if 'tendencia' in filename_lower:
        return 'tendencia'
    elif 'armonic' in filename_lower and 'potencia' in filename_lower:
        return 'armonicos_potencia'
    elif 'armonic' in filename_lower:
        return 'armonicos_potencia'
    else:
        return 'tendencia'  # Por defecto

def analyze_files_and_show_results(selected_files, analyzer, db_manager):
    """Analiza archivos y muestra resultados inmediatamente"""
    
    # Crear contenedor para mostrar progreso
    progress_container = st.container()
    
    with progress_container:
        st.markdown("### 🔄 Procesando Archivos...")
        progress_bar = st.progress(0)
        status_text = st.empty()
        results_summary = st.empty()
    
    results = []
    successful_analyses = 0
    
    for i, uploaded_file in enumerate(selected_files):
        try:
            # Actualizar progreso
            progress = (i + 1) / len(selected_files)
            progress_bar.progress(progress)
            status_text.text(f"📂 Analizando: {uploaded_file.name}")
            
            # Guardar archivo temporalmente
            temp_path = f"temp_{uploaded_file.name}"
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Detectar tipo automáticamente
            file_type = detect_file_type(uploaded_file.name)
            
            # Analizar archivo
            analysis_result = analyzer.analyze_file(temp_path, file_type)
            
            if 'error' not in analysis_result:
                # Guardar en base de datos
                db_manager.save_analysis(uploaded_file.name, file_type, analysis_result)
                results.append(analysis_result)
                successful_analyses += 1
                
                # Mostrar progreso en tiempo real
                results_summary.success(f"✅ Procesados: {successful_analyses}/{len(selected_files)} archivos")
            else:
                st.error(f"❌ Error en {uploaded_file.name}: {analysis_result['error']}")
            
            # Limpiar archivo temporal
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
        except Exception as e:
            st.error(f"❌ Error procesando {uploaded_file.name}: {str(e)}")
    
    # Limpiar indicadores de progreso
    progress_bar.empty()
    status_text.empty()
    
    if results:
        st.session_state.analysis_results = results
        st.session_state.processed_files.extend([f.name for f in selected_files])
        
        # Mostrar resumen inmediato
        with st.container():
            st.success(f"🎉 ¡Análisis completado! {successful_analyses} archivo(s) procesado(s) exitosamente")
            
            # Mostrar métricas inmediatas
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                total_voltage_violations = sum(len([d for d in r.get('voltage_deviations', []) if d.get('excede_limite', False)]) for r in results)
                st.metric("🔋 Desviaciones Voltaje", total_voltage_violations)
            
            with col2:
                total_flicker_violations = sum(len([f for f in r.get('flickers', []) if f.get('excede_limite', False)]) for r in results)
                st.metric("💫 Flickers Detectados", total_flicker_violations)
            
            with col3:
                total_thd_violations = sum(len([t for t in r.get('thd_analysis', []) if t.get('excede_limite', False)]) for r in results)
                st.metric("🌊 THD Excedidos", total_thd_violations)
            
            with col4:
                total_harmonics = sum(len(r.get('harmonics_analysis', [])) for r in results)
                st.metric("🔢 Armónicos Analizados", total_harmonics)
        
        # Auto-refrescar para mostrar datos en las pestañas
        time.sleep(0.5)
        st.rerun()

def display_main_dashboard(db_manager):
    """Dashboard principal con resumen completo"""
    st.header("📊 Dashboard Principal - Resumen de Análisis")
    
    # Obtener todos los datos
    voltage_data = db_manager.get_voltage_deviations()
    flicker_data = db_manager.get_flickers()
    thd_data = db_manager.get_thd_analysis()
    harmonic_data = db_manager.get_harmonics_analysis()
    all_analyses = db_manager.get_all_analyses()
    
    if not all_analyses:
        st.info("📋 No hay datos disponibles. Suba archivos para comenzar el análisis.")
        st.markdown("### 🚀 Cómo usar el sistema:")
        st.markdown("""
        1. **📁 Suba archivos** usando el panel lateral
        2. **✅ Seleccione** los archivos a analizar
        3. **🚀 Pulse** "Analizar Archivos Seleccionados"
        4. **📊 Vea** los resultados en las pestañas correspondientes
        """)
        return
    
    # Métricas principales en tarjetas
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📁 Archivos Procesados",
            value=len(all_analyses),
            help="Total de archivos analizados"
        )
    
    with col2:
        voltage_violations = len(voltage_data[voltage_data['excede_limite'] == True]) if not voltage_data.empty else 0
        st.metric(
            label="⚡ Desviaciones > ±8%",
            value=voltage_violations,
            delta=f"{voltage_violations} violaciones",
            delta_color="inverse"
        )
    
    with col3:
        flicker_violations = len(flicker_data[flicker_data['excede_limite'] == True]) if not flicker_data.empty else 0
        st.metric(
            label="💫 Flickers > 1",
            value=flicker_violations,
            delta=f"{flicker_violations} violaciones",
            delta_color="inverse"
        )
    
    with col4:
        thd_violations = len(thd_data[thd_data['excede_limite'] == True]) if not thd_data.empty else 0
        st.metric(
            label="🌊 THD > 5%",
            value=thd_violations,
            delta=f"{thd_violations} violaciones",
            delta_color="inverse"
        )
    
    # Gráfico resumen
    if not voltage_data.empty or not flicker_data.empty or not thd_data.empty:
        st.markdown("### 📈 Resumen Visual de Violaciones")
        
        # Crear gráfico de barras con violaciones por tipo
        violation_summary = {
            'Tipo de Análisis': ['Desviaciones Voltaje', 'Flickers', 'Distorsión THD'],
            'Violaciones': [voltage_violations, flicker_violations, thd_violations],
            'Color': ['red', 'orange', 'blue']
        }
        
        fig = px.bar(
            violation_summary,
            x='Tipo de Análisis',
            y='Violaciones',
            color='Color',
            title="Violaciones Detectadas por Tipo de Análisis"
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    # Tabla resumen detallada
    st.markdown("### 📋 Detalle de Archivos Procesados")
    
    summary_data = []
    for analysis in all_analyses:
        data = analysis['analysis_data']
        summary_data.append({
            'Archivo': analysis['filename'],
            'Tipo': analysis['file_type'].replace('_', ' ').title(),
            'Fecha': analysis['timestamp'][:19],
            'Mediciones': data.get('total_measurements', 0),
            'Desviaciones Voltaje': len([d for d in data.get('voltage_deviations', []) if d.get('excede_limite', False)]),
            'Flickers': len([f for f in data.get('flickers', []) if f.get('excede_limite', False)]),
            'THD Excedidos': len([t for t in data.get('thd_analysis', []) if t.get('excede_limite', False)]),
            'Armónicos': len(data.get('harmonics_analysis', []))
        })
    
    if summary_data:
        summary_df = pd.DataFrame(summary_data)
        st.dataframe(summary_df, use_container_width=True)
    
    # Controles de administración
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📥 Exportar Análisis Excel", use_container_width=True):
            try:
                output_file = db_manager.export_complete_analysis()
                with open(output_file, "rb") as f:
                    st.download_button(
                        label="📥 Descargar Reporte Completo",
                        data=f.read(),
                        file_name=f"reporte_completo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    with col2:
        if st.button("🔄 Actualizar Datos", use_container_width=True):
            st.rerun()
    
    with col3:
        if st.button("🗑️ Limpiar Base de Datos", use_container_width=True):
            if st.session_state.get('confirm_delete', False):
                db_manager.clear_all_data()
                st.session_state.analysis_results = []
                st.success("✅ Datos eliminados")
                st.rerun()
            else:
                st.session_state.confirm_delete = True
                st.warning("⚠️ Pulse nuevamente para confirmar")

def display_voltage_deviations(db_manager):
    """Análisis detallado de desviaciones de voltaje"""
    st.header("⚡ Desviaciones de Voltaje > ±8%")
    st.markdown("Análisis de violaciones según Ecuador Regulation 009/2024")
    
    voltage_data = db_manager.get_voltage_deviations()
    
    if voltage_data.empty:
        st.info("📊 No hay datos de desviaciones de voltaje. Suba archivos de tipo 'Tendencia' para ver análisis.")
        return
    
    # Filtros interactivos
    col1, col2, col3 = st.columns(3)
    with col1:
        files = ['Todos'] + list(voltage_data['filename'].unique())
        selected_file = st.selectbox("📁 Filtrar por archivo", files)
    
    with col2:
        phases = ['Todas'] + list(voltage_data['fase'].unique())
        selected_phase = st.selectbox("⚡ Filtrar por fase", phases)
    
    with col3:
        show_violations_only = st.checkbox("🚨 Solo violaciones", help="Mostrar solo registros que exceden límites")
    
    # Aplicar filtros
    filtered_data = voltage_data.copy()
    if selected_file != 'Todos':
        filtered_data = filtered_data[filtered_data['filename'] == selected_file]
    if selected_phase != 'Todas':
        filtered_data = filtered_data[filtered_data['fase'] == selected_phase]
    if show_violations_only:
        filtered_data = filtered_data[filtered_data['excede_limite'] == True]
    
    # Mostrar métricas
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📊 Total Registros", len(filtered_data))
    with col2:
        violations = len(filtered_data[filtered_data['excede_limite'] == True])
        st.metric("🚨 Violaciones", violations)
    with col3:
        if len(filtered_data) > 0:
            violation_rate = (violations / len(filtered_data)) * 100
            st.metric("📈 Tasa Violación", f"{violation_rate:.1f}%")
    
    # Tabla de datos
    st.markdown("### 📋 Datos Detallados")
    
    # Formatear datos para mejor visualización
    display_data = filtered_data.copy()
    if not display_data.empty:
        display_data['porcentaje_desviacion'] = display_data['porcentaje_desviacion'].round(2)
        display_data['voltaje_promedio'] = display_data['voltaje_promedio'].round(2)
        display_data['excede_limite'] = display_data['excede_limite'].map({True: '🚨 SÍ', False: '✅ NO'})
        
        st.dataframe(display_data, use_container_width=True)
        
        # Gráficos
        st.markdown("### 📊 Visualizaciones")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Gráfico de barras por fase
            if not filtered_data.empty:
                fig1 = px.bar(
                    filtered_data,
                    x='fase',
                    y='porcentaje_desviacion',
                    color='filename',
                    title="Porcentaje de Desviaciones por Fase",
                    labels={'porcentaje_desviacion': 'Porcentaje (%)', 'fase': 'Fase'}
                )
                fig1.add_hline(y=8, line_dash="dash", line_color="red", annotation_text="Límite ±8%")
                st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # Gráfico de violaciones
            violation_summary = filtered_data.groupby('fase')['excede_limite'].apply(lambda x: (x == True).sum()).reset_index()
            violation_summary.columns = ['fase', 'violaciones']
            
            if not violation_summary.empty:
                fig2 = px.pie(
                    violation_summary,
                    values='violaciones',
                    names='fase',
                    title="Distribución de Violaciones por Fase"
                )
                st.plotly_chart(fig2, use_container_width=True)

def display_flickers(db_manager):
    """Análisis detallado de flickers"""
    st.header("💫 Flickers > 1 (Pst)")
    st.markdown("Análisis de severidad de flicker según normativa")
    
    flicker_data = db_manager.get_flickers()
    
    if flicker_data.empty:
        st.info("📊 No hay datos de flickers. Suba archivos de tipo 'Tendencia' para ver análisis.")
        return
    
    # Mostrar datos con formato mejorado
    display_data = flicker_data.copy()
    display_data['valor_promedio'] = display_data['valor_promedio'].round(4)
    display_data['porcentaje_flicker'] = display_data['porcentaje_flicker'].round(2)
    display_data['excede_limite'] = display_data['excede_limite'].map({True: '🚨 SÍ', False: '✅ NO'})
    
    st.dataframe(display_data, use_container_width=True)
    
    # Gráficos
    if not flicker_data.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            fig1 = px.scatter(
                flicker_data,
                x='fase',
                y='valor_promedio',
                color='filename',
                size='porcentaje_flicker',
                title="Valores de Flicker por Fase",
                labels={'valor_promedio': 'Valor Promedio Pst', 'fase': 'Fase'}
            )
            fig1.add_hline(y=1, line_dash="dash", line_color="red", annotation_text="Límite = 1")
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # Distribución de violaciones
            violations_by_phase = flicker_data[flicker_data['excede_limite'] == True].groupby('fase').size()
            if not violations_by_phase.empty:
                fig2 = px.bar(
                    x=violations_by_phase.index,
                    y=violations_by_phase.values,
                    title="Violaciones de Flicker por Fase",
                    labels={'x': 'Fase', 'y': 'Número de Violaciones'}
                )
                st.plotly_chart(fig2, use_container_width=True)

def display_harmonic_distortion(db_manager):
    """Análisis de distorsión armónica THD"""
    st.header("🌊 Distorsión Armónica THD > 5%")
    st.markdown("Análisis de distorsión armónica total de voltaje")
    
    thd_data = db_manager.get_thd_analysis()
    
    if thd_data.empty:
        st.info("📊 No hay datos de THD. Suba archivos de tipo 'Tendencia' para ver análisis.")
        return
    
    # Formatear datos
    display_data = thd_data.copy()
    display_data['thd_promedio'] = display_data['thd_promedio'].round(3)
    display_data['porcentaje_thd'] = display_data['porcentaje_thd'].round(2)
    display_data['excede_limite'] = display_data['excede_limite'].map({True: '🚨 SÍ', False: '✅ NO'})
    
    st.dataframe(display_data, use_container_width=True)
    
    # Gráficos
    if not thd_data.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            fig1 = px.bar(
                thd_data,
                x='fase',
                y='thd_promedio',
                color='filename',
                title="Valores Promedio de THD por Fase (%)",
                labels={'thd_promedio': 'THD Promedio (%)', 'fase': 'Fase'}
            )
            fig1.add_hline(y=5, line_dash="dash", line_color="red", annotation_text="Límite 5%")
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # Análisis de cumplimiento
            compliance_data = thd_data.groupby('excede_limite').size()
            labels = ['Cumple Norma', 'Excede Límite']
            fig2 = px.pie(
                values=compliance_data.values,
                names=[labels[i] for i in compliance_data.index],
                title="Cumplimiento de Límites THD"
            )
            st.plotly_chart(fig2, use_container_width=True)

def display_harmonics_analysis(db_manager):
    """Análisis completo de armónicos individuales"""
    st.header("🔢 Análisis de Armónicos (excluyendo H1)")
    st.markdown("Análisis de valores negativos en armónicos de potencia")
    
    harmonic_data = db_manager.get_harmonics_analysis()
    
    if harmonic_data.empty:
        st.info("📊 No hay datos de armónicos. Suba archivos de tipo 'Armónicos Potencia' para ver análisis.")
        return
    
    # Filtros
    col1, col2 = st.columns(2)
    with col1:
        orders = ['Todos'] + sorted(list(harmonic_data['orden_armonico'].unique()))
        selected_order = st.selectbox("🔢 Filtrar por orden armónico", orders)
    
    with col2:
        phases = ['Todas'] + list(harmonic_data['fase'].unique())
        selected_phase = st.selectbox("⚡ Filtrar por fase", phases)
    
    # Aplicar filtros
    filtered_data = harmonic_data.copy()
    if selected_order != 'Todos':
        filtered_data = filtered_data[filtered_data['orden_armonico'] == selected_order]
    if selected_phase != 'Todas':
        filtered_data = filtered_data[filtered_data['fase'] == selected_phase]
    
    # Formatear datos para visualización
    display_data = filtered_data.copy()
    display_data['porcentaje'] = display_data['porcentaje'].round(4)
    display_data['valor_promedio'] = display_data['valor_promedio'].round(4)
    
    st.dataframe(display_data, use_container_width=True)
    
    # Gráficos
    if not filtered_data.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            fig1 = px.line(
                filtered_data,
                x='orden_armonico',
                y='porcentaje',
                color='fase',
                title="Porcentaje de Valores Negativos por Orden Armónico",
                labels={'porcentaje': 'Porcentaje (%)', 'orden_armonico': 'Orden Armónico'}
            )
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # Mapa de calor de armónicos por fase
            pivot_data = filtered_data.pivot_table(
                values='porcentaje',
                index='orden_armonico',
                columns='fase',
                fill_value=0
            )
            
            if not pivot_data.empty:
                fig2 = px.imshow(
                    pivot_data.values,
                    x=pivot_data.columns,
                    y=pivot_data.index,
                    title="Mapa de Calor: Armónicos por Fase",
                    labels={'x': 'Fase', 'y': 'Orden Armónico', 'color': 'Porcentaje (%)'}
                )
                st.plotly_chart(fig2, use_container_width=True)

def display_admin_configuration(db_manager):
    """Panel de administración con autenticación"""
    st.header("👤 Panel de Administrador")
    
    if not st.session_state.admin_authenticated:
        admin_login()
        return
    
    # Panel autenticado
    col1, col2 = st.columns([3, 1])
    with col1:
        st.success(f"✅ Sesión activa: **{st.session_state.admin_user}**")
    with col2:
        if st.button("🔓 Cerrar Sesión"):
            st.session_state.admin_authenticated = False
            st.session_state.admin_user = None
            st.rerun()
    
    st.markdown("---")
    
    # Configuración de límites
    st.markdown("### ⚙️ Límites de Calidad - Ecuador Regulation 009/2024")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📊 Parámetros de Voltaje")
        st.info("🔋 **Desviaciones de Voltaje:** ±8% del voltaje nominal")
        st.info("💫 **Flicker (Pst):** > 1.0 (Severidad corta duración)")
        st.info("🌊 **Distorsión THD:** > 5% (Total Harmonic Distortion)")
    
    with col2:
        st.markdown("#### 🔢 Análisis Armónico")
        st.info("⚡ **Armónicos de Potencia:** Análisis de valores negativos")
        st.info("📋 **Exclusiones:** H1 (frecuencia fundamental)")
        st.info("🎯 **Base de cálculo:** 2150 mediciones por archivo")
    
    # Estadísticas del sistema
    st.markdown("### 📈 Estadísticas del Sistema")
    
    all_analyses = db_manager.get_all_analyses()
    voltage_data = db_manager.get_voltage_deviations()
    flicker_data = db_manager.get_flickers()
    thd_data = db_manager.get_thd_analysis()
    harmonic_data = db_manager.get_harmonics_analysis()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📁 Total Archivos", len(all_analyses))
    with col2:
        st.metric("⚡ Registros Voltaje", len(voltage_data))
    with col3:
        st.metric("💫 Registros Flicker", len(flicker_data))
    with col4:
        st.metric("🔢 Registros Armónicos", len(harmonic_data))
    
    # Herramientas de administración
    st.markdown("### 🛠️ Herramientas de Administración")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### 📥 Exportación")
        if st.button("📊 Exportar Reporte Completo", use_container_width=True):
            try:
                output_file = db_manager.export_complete_analysis()
                with open(output_file, "rb") as f:
                    st.download_button(
                        label="📥 Descargar Excel",
                        data=f.read(),
                        file_name=f"reporte_admin_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                st.success("✅ Reporte generado exitosamente")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
    
    with col2:
        st.markdown("#### 🗑️ Limpieza")
        if st.button("🗑️ Limpiar Base de Datos", use_container_width=True):
            if st.session_state.get('admin_confirm_delete', False):
                db_manager.clear_all_data()
                st.session_state.analysis_results = []
                st.session_state.processed_files = []
                st.session_state.admin_confirm_delete = False
                st.success("✅ Base de datos limpiada")
                time.sleep(1)
                st.rerun()
            else:
                st.session_state.admin_confirm_delete = True
                st.warning("⚠️ Confirme pulsando nuevamente")
    
    with col3:
        st.markdown("#### 🔄 Mantenimiento")
        if st.button("🔄 Reiniciar Sistema", use_container_width=True):
            st.session_state.clear()
            st.success("✅ Sistema reiniciado")
            st.rerun()
    
    # Información técnica
    st.markdown("---")
    st.markdown("### 🔧 Información Técnica")
    
    with st.expander("📋 Detalles de Implementación"):
        st.markdown("""
        **🎯 Funcionalidades Implementadas:**
        - ✅ Análisis automático de desviaciones de voltaje (±8%)
        - ✅ Detección de flickers Pst > 1.0
        - ✅ Análisis de distorsión armónica THD > 5%
        - ✅ Análisis de armónicos individuales (excluyendo H1)
        - ✅ Base de datos SQLite integrada
        - ✅ Exportación a Excel
        - ✅ Dashboard interactivo con filtros
        
        **📁 Formatos de Archivo Soportados:**
        - Tendencia 8 matrix (.xls/.xlsx)
        - Armónicos potencia 8 matrix (.xls/.xlsx)
        
        **🔐 Seguridad:**
        - Autenticación de administrador
        - Validación de tipos de archivo
        - Manejo seguro de archivos temporales
        """)

if __name__ == "__main__":
    main()
