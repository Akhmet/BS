"""
Streamlit-приложение для анализа стабильности углеводородов
На основе скрипта BS_qwen.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import io
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# =============================================================================
# 2.1. Инициализация проекта - Конфигурация страницы
# =============================================================================
st.set_page_config(
    page_title="Анализ Углеводородов",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# Обязательные колонки в данных (согласно BS_qwen.py)
# =============================================================================
REQUIRED_COLUMNS = ['number probe', 'Class', 'year']

# =============================================================================
# 3.1. Кэшируемая функция загрузки данных
# =============================================================================
@st.cache_data
def load_data(file_bytes, file_extension):
    """
    Загрузка данных из Excel или CSV файла.
    Кэшируется для производительности.
    """
    try:
        if file_extension in ['.xlsx', '.xls']:
            df = pd.read_excel(io.BytesIO(file_bytes), sheet_name='Лист1')
        elif file_extension == '.csv':
            df = pd.read_csv(io.BytesIO(file_bytes))
        else:
            return None, "Неподдерживаемый формат файла"
        
        # Очистка данных (аналогично BS_qwen.py)
        # Удаление строк с NaN в колонке year
        df = df.dropna(subset=['year'])
        
        # Преобразование year в int
        df['year'] = df['year'].astype(int)
        
        return df, None
    except Exception as e:
        return None, f"Ошибка при чтении файла: {str(e)}"


# =============================================================================
# 3.2. Функция проверки обязательных колонок
# =============================================================================
def validate_columns(df):
    """
    Проверка наличия обязательных колонок в DataFrame.
    Возвращает tuple: (is_valid, missing_columns)
    """
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    return len(missing) == 0, missing


# =============================================================================
# Заголовок и описание приложения
# =============================================================================
st.title("🧪 Анализ стабильности углеводородов")
st.markdown("""
Интерактивное веб-приложение для анализа данных по стабильности углеводородов 
на основе скрипта **BS_qwen.py**.

### Возможности:
- 📤 Загрузка данных из Excel/CSV файлов
- ⚙️ Гибкая настройка параметров анализа
- 📊 Визуализация результатов с использованием Plotly
- 💾 Сохранение и загрузка конфигураций
- 📥 Экспорт результатов в Excel
""")

st.divider()

# =============================================================================
# 2.2. Организация макета (Layout)
# =============================================================================

# --- SIDEBAR: Глобальные действия ---
with st.sidebar:
    st.header("📂 Управление данными")
    
    # =========================================================================
    # 3.1. Виджет загрузки файла
    # =========================================================================
    uploaded_file = st.file_uploader(
        label="Загрузите файл данных",
        type=['xlsx', 'xls', 'csv'],
        help="Поддерживаются файлы Excel (.xlsx, .xls) и CSV (.csv)"
    )
    
    if uploaded_file is not None:
        st.success(f"✅ Файл загружен: {uploaded_file.name}")
        
        # Получение расширения файла
        file_extension = '.' + uploaded_file.name.split('.')[-1].lower()
        
        # Загрузка данных с использованием кэшированной функции
        df, error = load_data(uploaded_file.getvalue(), file_extension)
        
        if error:
            st.error(f"❌ {error}")
            df = None
        else:
            # Сохранение данных в session_state
            st.session_state['data'] = df
            st.session_state['file_name'] = uploaded_file.name
            
            # =========================================================================
            # 3.2. Валидация и предпросмотр
            # =========================================================================
            is_valid, missing_cols = validate_columns(df)
            
            if not is_valid:
                st.error(f"❌ Отсутствуют обязательные колонки: {', '.join(missing_cols)}")
                st.warning(f"Ожидаемые колонки: {', '.join(REQUIRED_COLUMNS)}")
                df = None
            else:
                st.success("✅ Все обязательные колонки найдены")
                
                # Сохранение информации о данных
                st.session_state['data_valid'] = True
                st.session_state['n_rows'] = len(df)
                st.session_state['n_columns'] = len(df.columns)
                st.session_state['years'] = sorted(df['year'].unique())
                st.session_state['classes'] = df['Class'].unique().tolist()
                st.session_state['hc_columns'] = [col for col in df.columns if col not in REQUIRED_COLUMNS]
    else:
        st.info("👈 Выберите файл для загрузки")
        if 'data' in st.session_state:
            del st.session_state['data']
        if 'data_valid' in st.session_state:
            del st.session_state['data_valid']
    
    st.divider()
    
    st.header("⚙️ Глобальные настройки")
    st.info("Параметры анализа будут доступны после загрузки данных")
    
    st.divider()
    
    # =========================================================================
    # 5. СИСТЕМА СОХРАНЕНИЯ И ЗАГРУЗКИ КОНФИГУРАЦИЙ (Этап 5)
    # =========================================================================
    st.header("💾 Конфигурации")
    
    # Создаем папку для конфигов если не существует
    import os
    from pathlib import Path
    configs_dir = Path("saved_configs")
    configs_dir.mkdir(exist_ok=True)
    
    # --- 5.2. Функционал сохранения ---
    st.subheader("Сохранить конфигурацию")
    
    config_name = st.text_input(
        label="Название конфигурации",
        key="config_name_input",
        placeholder="my_config",
        help="Введите имя для сохранения текущих настроек"
    )
    
    def save_config():
        """Сохраняет текущие параметры из session_state в JSON файл"""
        import json
        
        if not config_name:
            st.error("❌ Введите название конфигурации")
            return False
        
        # Собираем все параметры из session_state
        config_data = {}
        
        # Параметры основных настроек
        for key in [
            'outlier_method', 'z_threshold', 'iqr_multiplier',
            'optimization_algorithm', 'n_iterations', 'population_size',
            'color_scheme', 'point_size', 'show_labels',
            'selected_years', 'selected_classes',
            'threshold_value', 'enable_pca', 'enable_tsne'
        ]:
            if key in st.session_state:
                config_data[key] = st.session_state[key]
        
        # Сохраняем в JSON файл
        config_file = configs_dir / f"{config_name}.json"
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            st.success(f"✅ Конфигурация '{config_name}' сохранена!")
            return True
        except Exception as e:
            st.error(f"❌ Ошибка сохранения: {str(e)}")
            return False
    
    if st.button("💾 Сохранить конфигурацию", key="save_config_btn"):
        save_config()
    
    st.divider()
    
    # --- 5.3. Функционал загрузки ---
    st.subheader("Загрузить конфигурацию")
    
    def get_available_configs():
        """Возвращает список доступных конфигураций"""
        if not configs_dir.exists():
            return []
        config_files = list(configs_dir.glob("*.json"))
        return [f.stem for f in config_files]
    
    available_configs = get_available_configs()
    
    if available_configs:
        selected_config = st.selectbox(
            label="Доступные конфигурации",
            options=available_configs,
            key="selected_config_select",
            help="Выберите конфигурацию для загрузки"
        )
        
        def load_selected_config():
            """Загружает выбранную конфигурацию и обновляет session_state"""
            import json
            
            config_file = configs_dir / f"{selected_config}.json"
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # Обновляем session_state значениями из конфига
                for key, value in config_data.items():
                    st.session_state[key] = value
                
                st.success(f"✅ Конфигурация '{selected_config}' загружена!")
                return True
            except Exception as e:
                st.error(f"❌ Ошибка загрузки: {str(e)}")
                return False
        
        if st.button("📂 Загрузить конфигурацию", key="load_config_btn"):
            load_selected_config()
    else:
        st.info("Нет сохраненных конфигураций")
    
    st.divider()
    
    # --- 5.4. Сброс настроек ---
    st.subheader("Сброс настроек")
    
    def reset_all_settings():
        """Сбрасывает все настройки к значениям по умолчанию"""
        keys_to_reset = [
            'outlier_method', 'z_threshold', 'iqr_multiplier',
            'optimization_algorithm', 'n_iterations', 'population_size',
            'color_scheme', 'point_size', 'show_labels',
            'selected_years', 'selected_classes',
            'threshold_value', 'enable_pca', 'enable_tsne'
        ]
        
        # Удаляем ключи из session_state
        for key in keys_to_reset:
            if key in st.session_state:
                del st.session_state[key]
        
        st.success("✅ Настройки сброшены! Страница будет перезагружена...")
        # Перезагрузка страницы через JavaScript
        st.rerun()
    
    if st.button("🔄 Сбросить все настройки", key="reset_btn"):
        reset_all_settings()
    
    st.divider()
    
    # Место для кнопок сохранения/загрузки конфигов
    st.header("ℹ️ Информация")
    st.info("Параметры анализа будут доступны после загрузки данных")

# --- MAIN AREA: Вкладки для разделения этапов работы ---
# Создаем вкладки для логического разделения интерфейса
tab_preview, tab_params, tab_results = st.tabs([
    "📋 Предпросмотр данных",
    "⚙️ Параметры анализа",
    "📊 Результаты"
])

with tab_preview:
    st.subheader("Предпросмотр загруженных данных")
    
    # Проверяем, есть ли загруженные данные в session_state
    if 'data_valid' in st.session_state and st.session_state['data_valid']:
        df = st.session_state['data']
        
        # =========================================================================
        # 3.2. Валидация и предпросмотр - Отображение данных
        # =========================================================================
        
        # Показываем базовую статистику
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📊 Строк", st.session_state['n_rows'])
        with col2:
            st.metric("📝 Колонок", st.session_state['n_columns'])
        with col3:
            st.metric("📅 Годы", f"{st.session_state['years'][0]}-{st.session_state['years'][1] if len(st.session_state['years']) > 1 else ''}")
        with col4:
            st.metric("🔬 УВ колонок", len(st.session_state['hc_columns']))
        
        st.divider()
        
        # Дополнительная информация о классах
        if st.session_state['classes']:
            st.write(f"**Классы образцов:** {', '.join(map(str, st.session_state['classes']))}")
        
        st.divider()
        
        # Предпросмотр первых строк
        st.subheader("📋 Первые 10 строк данных")
        st.dataframe(df.head(10), use_container_width=True, height=300)
        
        st.divider()
        
        # Базовая статистика по числовым колонкам
        st.subheader("📈 Базовая статистика")
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            st.dataframe(df[numeric_cols].describe(), use_container_width=True)
        else:
            st.info("Нет числовых колонок для отображения статистики")
        
        st.divider()
        
        # Информация о типах данных
        st.subheader("ℹ️ Информация о колонках")
        dtype_df = pd.DataFrame({
            'Тип данных': df.dtypes.astype(str),
            'Не-Null значения': df.count(),
            'Null значения': df.isnull().sum()
        })
        st.dataframe(dtype_df, use_container_width=True)
        
    else:
        st.warning("👈 Загрузите файл данных через панель слева, чтобы увидеть предпросмотр")
        
        with st.container():
            st.info("""
            ### Поддерживаемые форматы:
            - `.xlsx` - Excel файлы
            - `.xls` - Excel файлы (старый формат)
            - `.csv` - CSV файлы
            
            После загрузки файла здесь отобразится:
            - Таблица с первыми строками данных
            - Информация о колонках
            - Базовая статистика
            """)

with tab_params:
    st.subheader("Параметры анализа")
    st.warning("👈 Загрузите файл данных, чтобы настроить параметры анализа")
    
    # Место для параметров
    placeholder_params = st.empty()
    
    with placeholder_params.container():
        st.info("""
        ### Группы параметров:
        
        1. **Основные настройки**
           - Выбор колонок с данными (HC, годы)
           - Пороговые значения отсечения
           
        2. **Параметры методов**
           - Включение/выключение методов анализа
           - Настройки алгоритмов
           
        3. **Оптимизация**
           - Выбор алгоритма оптимизации
           - Количество итераций
           - Размер популяции
           
        4. **Фильтрация выбросов**
           - Методы фильтрации (Z-score, IQR)
           - Пороговые значения
           
        5. **Визуализация**
           - Настройки цветов
           - Размеры точек
           - Подписи осей
        """)

with tab_results:
    st.subheader("Результаты анализа")
    
    # Проверяем, есть ли загруженные данные
    if 'data_valid' not in st.session_state or not st.session_state.get('data_valid', False):
        st.warning("⚠️ Загрузите файл данных, чтобы увидеть результаты")
        placeholder_results = st.empty()
        with placeholder_results.container():
            st.info("""
            ### Вкладки результатов:
            
            - **Обзор данных**: Распределения, корреляционные матрицы
            - **Многомерный анализ**: PCA, t-SNE проекции
            - **Сравнение годов**: Графики изменений концентраций
            - **Таблица результатов**: Итоговые расчетные коэффициенты
            - **Отчет**: Текстовое резюме анализа
            
            Для запуска анализа:
            1. Загрузите файл данных
            2. Настройте параметры
            3. Нажмите кнопку \"Запустить анализ\"
            """)
    else:
        df = st.session_state['data']
        
        # =========================================================================
        # 7.2. Организация вкладок результатов
        # =========================================================================
        result_tabs = st.tabs([
            "📊 Обзор данных",
            "🔬 Многомерный анализ",
            "📈 Сравнение годов",
            "📋 Таблица результатов",
            "📝 Отчет"
        ])
        
        # -------------------------------------------------------------------------
        # Вкладка 1: Обзор данных
        # -------------------------------------------------------------------------
        with result_tabs[0]:
            st.subheader("Распределение данных по годам")
            
            years = st.session_state['years']
            year_1 = years[0]
            year_2 = years[1] if len(years) > 1 else None
            
            # Данные по годам
            data_year_1 = df[df['year'] == year_1]
            data_year_2 = df[df['year'] == year_2] if year_2 else None
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric(f"Проб за {year_1}", len(data_year_1))
            with col2:
                if year_2:
                    st.metric(f"Проб за {year_2}", len(data_year_2))
            
            st.divider()
            
            st.subheader("Корреляционная матрица")
            
            # Получаем числовые колонки (HC)
            hc_columns = st.session_state.get('hc_columns', [])
            numeric_data = df[hc_columns].select_dtypes(include=[np.number])
            
            if len(numeric_data.columns) > 0:
                corr_matrix = numeric_data.corr()
                
                # Plotly heatmap для корреляционной матрицы
                fig_corr = px.imshow(
                    corr_matrix,
                    color_continuous_scale='RdBu_r',
                    zmin=-1,
                    zmax=1,
                    aspect='auto',
                    title='Корреляционная матрица углеводородов'
                )
                fig_corr.update_layout(height=600)
                st.plotly_chart(fig_corr, use_container_width=True)
            else:
                st.info("Нет числовых данных для построения корреляционной матрицы")
            
            st.divider()
            
            st.subheader("Распределение значений")
            
            # Выбираем несколько случайных HC для демонстрации
            if len(hc_columns) > 0:
                sample_hc = hc_columns[:min(5, len(hc_columns))]
                
                for hc in sample_hc:
                    fig_dist = px.histogram(
                        df,
                        x=hc,
                        color='year',
                        nbins=30,
                        title=f'Распределение {hc}',
                        opacity=0.7
                    )
                    st.plotly_chart(fig_dist, use_container_width=True)
        
        # -------------------------------------------------------------------------
        # Вкладка 2: Многомерный анализ (PCA + t-SNE)
        # -------------------------------------------------------------------------
        with result_tabs[1]:
            st.subheader("PCA анализ")
            
            from sklearn.decomposition import PCA
            from sklearn.preprocessing import StandardScaler
            from sklearn.manifold import TSNE
            
            # Подготовка данных для многомерного анализа
            hc_columns = st.session_state.get('hc_columns', [])
            if len(hc_columns) > 0:
                X = df[hc_columns].fillna(0)
                
                # Стандартизация
                scaler = StandardScaler()
                X_scaled = scaler.fit_transform(X)
                
                # PCA
                pca = PCA(n_components=min(3, len(hc_columns)))
                pca_result = pca.fit_transform(X_scaled)
                
                # Создаем DataFrame с результатами PCA
                pca_df = pd.DataFrame({
                    'PC1': pca_result[:, 0],
                    'PC2': pca_result[:, 1],
                    'year': df['year'],
                    'Class': df['Class']
                })
                
                if len(years) > 1:
                    pca_df['year'] = pca_df['year'].astype(str)
                
                # 2D PCA scatter plot
                st.subheader("PCA: PC1 vs PC2")
                
                fig_pca_2d = px.scatter(
                    pca_df,
                    x='PC1',
                    y='PC2',
                    color='year' if len(years) > 1 else 'Class',
                    title=f'PCA анализ (объяснено {pca.explained_variance_ratio_[0]+pca.explained_variance_ratio_[1]:.1%} дисперсии)',
                    labels={'PC1': f'PC1 ({pca.explained_variance_ratio_[0]:.1%})', 
                           'PC2': f'PC2 ({pca.explained_variance_ratio_[1]:.1%})'},
                    hover_data=['Class']
                )
                fig_pca_2d.update_traces(marker=dict(size=10, line=dict(width=1, color='DarkSlateGrey')))
                st.plotly_chart(fig_pca_2d, use_container_width=True)
                
                # 3D PCA если возможно
                if pca.n_components_ >= 3:
                    st.subheader("PCA: 3D визуализация")
                    
                    fig_pca_3d = px.scatter_3d(
                        pca_df,
                        x='PC1',
                        y='PC2',
                        z='PC3',
                        color='year' if len(years) > 1 else 'Class',
                        title=f'3D PCA (объяснено {sum(pca.explained_variance_ratio_):.1%} дисперсии)',
                        labels={'PC1': f'PC1 ({pca.explained_variance_ratio_[0]:.1%})', 
                               'PC2': f'PC2 ({pca.explained_variance_ratio_[1]:.1%})',
                               'PC3': f'PC3 ({pca.explained_variance_ratio_[2]:.1%})'},
                        hover_data=['Class']
                    )
                    fig_pca_3d.update_traces(marker=dict(size=5))
                    st.plotly_chart(fig_pca_3d, use_container_width=True)
                
                # Explained variance
                st.subheader("Объясненная дисперсия по компонентам")
                
                variance_df = pd.DataFrame({
                    'Компонента': [f'PC{i+1}' for i in range(len(pca.explained_variance_ratio_))],
                    'Объясненная дисперсия (%)': pca.explained_variance_ratio_ * 100
                })
                
                fig_var = px.bar(
                    variance_df,
                    x='Компонента',
                    y='Объясненная дисперсия (%)',
                    title='Объясненная дисперсия по главным компонентам',
                    text_auto='.1f'
                )
                st.plotly_chart(fig_var, use_container_width=True)
                
                st.divider()
                
                # =========================================================================
                # 7.1 Переход на Plotly - t-SNE визуализация
                # =========================================================================
                st.subheader("t-SNE анализ")
                st.info("t-SNE (t-distributed Stochastic Neighbor Embedding) — метод для визуализации многомерных данных в пространстве меньшей размерности.")
                
                with st.spinner("Выполняется t-SNE... Это может занять несколько секунд"):
                    try:
                        # t-SNE с параметрами по умолчанию
                        tsne = TSNE(n_components=2, random_state=42, perplexity=min(30, len(df)-1), n_iter=1000)
                        tsne_result = tsne.fit_transform(X_scaled)
                        
                        tsne_df = pd.DataFrame({
                            't-SNE 1': tsne_result[:, 0],
                            't-SNE 2': tsne_result[:, 1],
                            'year': df['year'].astype(str),
                            'Class': df['Class']
                        })
                        
                        fig_tsne = px.scatter(
                            tsne_df,
                            x='t-SNE 1',
                            y='t-SNE 2',
                            color='year' if len(years) > 1 else 'Class',
                            title='t-SNE проекция данных',
                            labels={'t-SNE 1': 't-SNE 1', 't-SNE 2': 't-SNE 2'},
                            hover_data=['Class']
                        )
                        fig_tsne.update_traces(marker=dict(size=10, line=dict(width=1, color='DarkSlateGrey')))
                        st.plotly_chart(fig_tsne, use_container_width=True)
                        
                        st.success("✅ t-SNE анализ завершен")
                    except Exception as e:
                        st.error(f"❌ Ошибка при выполнении t-SNE: {str(e)}")
            else:
                st.info("Нет данных для многомерного анализа")
        
        # -------------------------------------------------------------------------
        # Вкладка 3: Сравнение годов
        # -------------------------------------------------------------------------
        with result_tabs[2]:
            st.subheader("Сравнение концентраций по годам")
            
            if year_2:
                hc_columns = st.session_state.get('hc_columns', [])
                
                if len(hc_columns) > 0:
                    # Средние значения по годам
                    mean_by_year = df.groupby('year')[hc_columns].mean()
                    
                    # График сравнения средних
                    st.subheader("Средние концентрации по годам")
                    
                    # Выбираем топ-10 HC с наибольшими различиями
                    diff_means = abs(mean_by_year.loc[year_1] - mean_by_year.loc[year_2]).sort_values(ascending=False)
                    top_hc = diff_means.head(10).index.tolist()
                    
                    comparison_df = df[['year'] + top_hc].copy()
                    comparison_df['year'] = comparison_df['year'].astype(str)
                    
                    fig_comparison = px.box(
                        comparison_df,
                        points="all",
                        title='Сравнение распределений топ-10 углеводородов',
                        labels={'variable': 'Углеводород', 'value': 'Концентрация'}
                    )
                    fig_comparison.update_layout(xaxis_title="Углеводород", yaxis_title="Концентрация")
                    st.plotly_chart(fig_comparison, use_container_width=True)
                    
                    # Дельта между годами
                    st.subheader("Разница средних значений (Year 2 - Year 1)")
                    
                    delta_df = pd.DataFrame({
                        'Углеводород': top_hc,
                        'Разница': [mean_by_year.loc[year_2][hc] - mean_by_year.loc[year_1][hc] for hc in top_hc]
                    })
                    delta_df['Цвет'] = delta_df['Разница'].apply(lambda x: 'positive' if x > 0 else 'negative')
                    
                    fig_delta = px.bar(
                        delta_df,
                        x='Углеводород',
                        y='Разница',
                        color='Цвет',
                        color_discrete_map={'positive': 'green', 'negative': 'red'},
                        title='Изменение средних концентраций',
                        text_auto='.2f'
                    )
                    st.plotly_chart(fig_delta, use_container_width=True)
                else:
                    st.info("Нет данных для сравнения")
            else:
                st.warning("Для сравнения нужны данные минимум за 2 года")
        
        # -------------------------------------------------------------------------
        # Вкладка 4: Таблица результатов
        # -------------------------------------------------------------------------
        with result_tabs[3]:
            st.subheader("Итоговая таблица данных")
            
            # =========================================================================
            # 7.3 Интерактивность таблиц - Отображение с сортировкой и фильтрацией
            # =========================================================================
            # Показываем полную таблицу с возможностью сортировки и фильтрации
            st.dataframe(
                df,
                use_container_width=True,
                height=500,
                hide_index=True,
                column_config={
                    "year": st.column_config.NumberColumn("Год", format="%d"),
                    "Class": st.column_config.TextColumn("Класс"),
                }
            )
            
            st.divider()
            
            # =========================================================================
            # 7.3 Интерактивность таблиц - Подсветка аномальных значений
            # =========================================================================
            st.subheader("Статистика по углеводородам с подсветкой аномалий")
            
            hc_columns = st.session_state.get('hc_columns', [])
            if len(hc_columns) > 0:
                stats_df = df[hc_columns].describe()
                
                # Функция для подсветки выбросов
                def highlight_outliers(val):
                    """Подсвечивает значения выходящие за пределы 2 стандартных отклонений"""
                    try:
                        val_float = float(val)
                        if abs(val_float) > 2:
                            return 'background-color: #ffcccc'  # Светло-красный для аномалий
                        elif abs(val_float) > 1.5:
                            return 'background-color: #fff3cd'  # Светло-желтый для предупреждений
                        return ''
                    except (ValueError, TypeError):
                        return ''
                
                # Отображение статистики с форматированием
                styled_stats = stats_df.style.format(precision=2).map(highlight_outliers, subset=stats_df.columns)
                st.dataframe(styled_stats, use_container_width=True)
                
                st.info("🔴 Красным подсвечены значения > 2σ, 🟡 желтым > 1.5σ от среднего")
        
        # -------------------------------------------------------------------------
        # Вкладка 5: Отчет
        # -------------------------------------------------------------------------
        with result_tabs[4]:
            st.subheader("Отчет по анализу данных")
            
            # Генерация текстового отчета
            report_text = f"""
            ## Общая информация
            
            - **Всего проб:** {len(df)}
            - **Годы измерений:** {', '.join(map(str, years))}
            - **Количество углеводородов:** {len(hc_columns)}
            - **Классы образцов:** {', '.join(map(str, st.session_state.get('classes', [])))}
            
            ## Статистика по годам
            """
            
            for year in years:
                year_data = df[df['year'] == year]
                report_text += f"\n### {year}\n"
                report_text += f"- Количество проб: {len(year_data)}\n"
            
            report_text += "\n## Рекомендации\n\n"
            report_text += "- Проверьте данные на наличие выбросов перед дальнейшим анализом\n"
            report_text += "- Обратите внимание на углеводороды с наибольшей вариацией между годами\n"
            report_text += "- Используйте PCA для выявления скрытых паттернов в данных\n"
            
            st.markdown(report_text)

# =============================================================================
# Секция для логов и статуса
# =============================================================================
st.divider()
status_container = st.empty()
log_container = st.empty()

with status_container:
    st.info("ℹ️ Статус: Ожидание загрузки данных...")

# =============================================================================
# Нижняя информация
# =============================================================================
st.markdown("---")
st.caption("""
Приложение для анализа стабильности углеводородов | 
Версия: 0.7.0 (Этап 7: Визуализация результатов)
""")
