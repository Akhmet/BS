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
    
    # Показываем параметры только если данные загружены
    if 'data_valid' in st.session_state and st.session_state['data_valid']:
        st.success("✅ Данные загружены. Параметры анализа доступны ниже.")
        # Здесь будут добавлены параметры анализа в будущем
    else:
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
            'threshold_value', 'enable_pca', 'enable_tsne',
            # Параметры оптимизации
            'min_hc', 'max_hc', 'max_iterations',
            'consensus_threshold_min', 'consensus_threshold_max', 'consensus_threshold_step',
            # Параметры генетического алгоритма
            'ga_pop_size', 'ga_generations', 'ga_mutation_rate', 'ga_crossover_prob',
            'ga_early_stop_patience', 'ga_early_stop_tolerance',
            # Параметры жадного алгоритма
            'greedy_max_iterations', 'greedy_n_remove', 'greedy_hybrid_iterations',
            # Кросс-валидация
            'cv_enabled', 'cv_folds'
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
            'threshold_value', 'enable_pca', 'enable_tsne',
            # Параметры оптимизации
            'min_hc', 'max_hc', 'max_iterations',
            'consensus_threshold_min', 'consensus_threshold_max', 'consensus_threshold_step',
            # Параметры генетического алгоритма
            'ga_pop_size', 'ga_generations', 'ga_mutation_rate', 'ga_crossover_prob',
            'ga_early_stop_patience', 'ga_early_stop_tolerance',
            # Параметры жадного алгоритма
            'greedy_max_iterations', 'greedy_n_remove', 'greedy_hybrid_iterations',
            # Кросс-валидация
            'cv_enabled', 'cv_folds'
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
    
    # Проверяем, есть ли загруженные данные
    if 'data_valid' in st.session_state and st.session_state['data_valid']:
        df = st.session_state['data']
        
        st.success("✅ Данные загружены. Настройте параметры анализа ниже.")
        
        st.divider()
        
        # =========================================================================
        # Параметры анализа будут добавлены здесь
        # =========================================================================
        st.subheader("🔧 Основные настройки")
        
        # Выбор колонок для анализа
        hc_columns = st.session_state.get('hc_columns', [])
        if hc_columns:
            selected_hc = st.multiselect(
                label="Выберите колонки с данными углеводородов",
                options=hc_columns,
                default=hc_columns[:5] if len(hc_columns) >= 5 else hc_columns,
                help="Выберите колонки, которые будут использоваться в анализе"
            )
            st.session_state['selected_hc_columns'] = selected_hc
        
        st.divider()
        
        # =========================================================================
        # ВЫБОР МЕТОДОВ АНАЛИЗА (согласно BS_qwen.py METHODS_CONFIG)
        # =========================================================================
        st.subheader("🔬 Выбор методов анализа")
        
        st.markdown("""
        **Выберите методы для расчета стабильности углеводородов:**
        - Можно выбрать несколько методов
        - Консенсусный рейтинг будет рассчитан на основе выбранных методов
        """)
        
        col_m1, col_m2 = st.columns(2)
        
        with col_m1:
            method_clr = st.checkbox(
                label="CLR трансформация ⭐⭐⭐⭐⭐",
                value=False,
                key='method_clr',
                help="Centred Log-Ratio трансформация (обязательно для композиционных данных)"
            )
            
            method_ratio = st.checkbox(
                label="Пропорции (нормировка) ⭐⭐⭐",
                value=False,
                key='method_ratio',
                help="Нормировка на сумму внутри каждой пробы"
            )
            
            method_pattern = st.checkbox(
                label="Корреляционные паттерны ⭐⭐",
                value=False,
                key='method_pattern',
                help="Анализ корреляционных паттернов между годами"
            )
            
            method_importance = st.checkbox(
                label="Feature Importance (ML) ⭐",
                value=False,
                key='method_importance',
                help="Важность признаков на основе ML (может переобучаться)"
            )
            
            method_bootstrap = st.checkbox(
                label="Bootstrap доверительные интервалы ⭐⭐⭐⭐",
                value=True,
                key='method_bootstrap',
                help="Расчет доверительных интервалов методом bootstrap"
            )
        
        with col_m2:
            method_pca = st.checkbox(
                label="PCA Loadings стабильность ⭐⭐",
                value=False,
                key='method_pca',
                help="Стабильность loadings компонент PCA"
            )
            
            method_cohens_d = st.checkbox(
                label="Robust Cohen's D ⭐⭐⭐⭐",
                value=False,
                key='method_cohens_d',
                help="Эффект размера (медиана + MAD)"
            )
            
            method_wasserstein = st.checkbox(
                label="Wasserstein distance ⭐⭐⭐⭐",
                value=False,
                key='method_wasserstein',
                help="Расстояние между распределениями (форма распределения)"
            )
            
            method_pairwise = st.checkbox(
                label="Pairwise Log-Ratio ⭐⭐⭐⭐⭐",
                value=True,
                key='method_pairwise',
                help="Попарные логарифмические отношения (лучший для композиционных данных)"
            )
        
        # Сохраняем конфигурацию методов в session_state
        st.session_state['methods_config'] = {
            'clr': method_clr,
            'ratio': method_ratio,
            'pattern': method_pattern,
            'importance': method_importance,
            'bootstrap': method_bootstrap,
            'pca': method_pca,
            'cohens_d': method_cohens_d,
            'wasserstein': method_wasserstein,
            'pairwise': method_pairwise
        }
        
        # Показываем количество выбранных методов
        enabled_count = sum(st.session_state['methods_config'].values())
        if enabled_count > 0:
            st.success(f"✅ Выбрано методов: {enabled_count}")
        else:
            st.warning("⚠️ Не выбрано ни одного метода. Минимум 1 метод требуется для анализа.")
        
        st.divider()
        
        # Параметры фильтрации выбросов
        st.subheader("🎯 Фильтрация выбросов")
        
        outlier_method = st.selectbox(
            label="Метод фильтрации выбросов",
            options=['Нет', 'Z-score', 'IQR'],
            index=0,
            key='outlier_method',
            help="Выберите метод для обнаружения и фильтрации выбросов"
        )
        
        if outlier_method == 'Z-score':
            z_threshold = st.slider(
                label="Порог Z-score",
                min_value=1.0,
                max_value=5.0,
                value=3.0,
                step=0.1,
                key='z_threshold',
                help="Значения с Z-score больше этого порога будут считаться выбросами"
            )
        elif outlier_method == 'IQR':
            iqr_multiplier = st.slider(
                label="Множитель IQR",
                min_value=1.0,
                max_value=3.0,
                value=1.5,
                step=0.1,
                key='iqr_multiplier',
                help="Значения за пределами Q1 - k*IQR и Q3 + k*IQR будут считаться выбросами"
            )
        
        st.divider()
        
        # Параметры оптимизации
        st.subheader("🔬 Оптимизация набора углеводородов")
        
        # Выбор алгоритма оптимизации
        optimization_algorithm = st.selectbox(
            label="Алгоритм оптимизации",
            options=['hybrid', 'greedy', 'genetic'],
            index=0,
            key='optimization_algorithm',
            help="Выберите алгоритм для оптимизации набора углеводородов"
        )
        
        col_opt1, col_opt2 = st.columns(2)
        with col_opt1:
            min_hc = st.number_input(
                label="Мин. количество УВ",
                min_value=3,
                max_value=50,
                value=11,
                step=1,
                key='min_hc',
                help="Минимальное количество углеводородов после оптимизации"
            )
            max_iterations = st.number_input(
                label="Макс. итераций",
                min_value=10,
                max_value=200,
                value=60,
                step=5,
                key='max_iterations',
                help="Максимальное количество итераций оптимизации"
            )
        with col_opt2:
            max_hc = st.number_input(
                label="Макс. количество УВ",
                min_value=5,
                max_value=100,
                value=35,
                step=1,
                key='max_hc',
                help="Максимальное количество углеводородов после оптимизации"
            )
        
        st.divider()
        
        st.subheader("📊 Порог консенсуса")
        
        col_cons1, col_cons2, col_cons3 = st.columns(3)
        with col_cons1:
            consensus_threshold_min = st.slider(
                label="Мин. порог",
                min_value=0.0,
                max_value=0.5,
                value=0.3,
                step=0.05,
                key='consensus_threshold_min',
                help="Минимальный порог consensus score"
            )
        with col_cons2:
            consensus_threshold_max = st.slider(
                label="Макс. порог",
                min_value=0.5,
                max_value=1.0,
                value=0.7,
                step=0.05,
                key='consensus_threshold_max',
                help="Максимальный порог consensus score"
            )
        with col_cons3:
            consensus_threshold_step = st.slider(
                label="Шаг",
                min_value=0.01,
                max_value=0.2,
                value=0.1,
                step=0.01,
                key='consensus_threshold_step',
                help="Шаг перебора порога консенсуса"
            )
        
        # Параметры генетического алгоритма
        if optimization_algorithm in ['genetic', 'hybrid']:
            st.divider()
            st.subheader("🧬 Параметры генетического алгоритма")
            
            col_ga1, col_ga2 = st.columns(2)
            with col_ga1:
                ga_pop_size = st.number_input(
                    label="Размер популяции",
                    min_value=10,
                    max_value=200,
                    value=60,
                    step=5,
                    key='ga_pop_size',
                    help="Размер популяции в генетическом алгоритме"
                )
                ga_mutation_rate = st.slider(
                    label="Частота мутаций",
                    min_value=0.01,
                    max_value=0.5,
                    value=0.15,
                    step=0.01,
                    key='ga_mutation_rate',
                    help="Вероятность мутации"
                )
            with col_ga2:
                ga_generations = st.number_input(
                    label="Количество поколений",
                    min_value=10,
                    max_value=200,
                    value=40,
                    step=5,
                    key='ga_generations',
                    help="Максимальное количество поколений"
                )
                ga_crossover_prob = st.slider(
                    label="Вероятность кроссовера",
                    min_value=0.3,
                    max_value=1.0,
                    value=0.7,
                    step=0.05,
                    key='ga_crossover_prob',
                    help="Вероятность кроссовера"
                )
            
            col_ga3, col_ga4 = st.columns(2)
            with col_ga3:
                ga_early_stop_patience = st.number_input(
                    label="Терпение ранней остановки",
                    min_value=5,
                    max_value=50,
                    value=10,
                    step=1,
                    key='ga_early_stop_patience',
                    help="Поколений без улучшения для ранней остановки"
                )
            with col_ga4:
                ga_early_stop_tolerance = st.number_input(
                    label="Допуск ранней остановки",
                    min_value=0.0001,
                    max_value=0.01,
                    value=0.001,
                    step=0.0001,
                    format="%.4f",
                    key='ga_early_stop_tolerance',
                    help="Минимальное улучшение для считания прогрессом"
                )
        
        # Параметры жадного алгоритма
        if optimization_algorithm in ['greedy', 'hybrid']:
            st.divider()
            st.subheader("🎯 Параметры жадного алгоритма")
            
            greedy_max_iterations = st.number_input(
                label="Макс. итераций жадного алгоритма",
                min_value=5,
                max_value=100,
                value=20,
                step=1,
                key='greedy_max_iterations',
                help="Максимум итераций жадного алгоритма"
            )
            
            greedy_n_remove = st.multiselect(
                label="Сколько УВ удалять за шаг",
                options=[1, 2, 3, 4, 5],
                default=[1, 2, 3],
                key='greedy_n_remove',
                help="Варианты количества УВ для удаления за один шаг"
            )
            
            if optimization_algorithm == 'hybrid':
                greedy_hybrid_iterations = st.number_input(
                    label="Итераций жадного в гибридном режиме",
                    min_value=5,
                    max_value=50,
                    value=15,
                    step=1,
                    key='greedy_hybrid_iterations',
                    help="Количество итераций жадного алгоритма в гибридном режиме"
                )
        
        # Кросс-валидация
        st.divider()
        st.subheader("✅ Кросс-валидация")
        
        cv_enabled = st.checkbox(
            label="Включить кросс-валидацию",
            value=True,
            key='cv_enabled',
            help="Использовать кросс-валидацию для оценки качества оптимизации"
        )
        
        if cv_enabled:
            cv_folds = st.number_input(
                label="Количество фолдов",
                min_value=2,
                max_value=10,
                value=5,
                step=1,
                key='cv_folds',
                help="Количество фолдов для кросс-валидации"
            )
        
        st.divider()
        
        # Параметры визуализации
        st.subheader("📊 Визуализация")
        
        col1, col2 = st.columns(2)
        with col1:
            color_scheme = st.selectbox(
                label="Цветовая схема",
                options=['Plotly', 'Viridis', 'Plasma', 'Inferno', 'Magma', 'Set1', 'Set2'],
                index=0,
                key='color_scheme',
                help="Выберите цветовую палитру для графиков"
            )
        with col2:
            point_size = st.slider(
                label="Размер точек",
                min_value=2,
                max_value=20,
                value=8,
                step=1,
                key='point_size',
                help="Размер точек на графиках"
            )
        
        show_labels = st.checkbox(
            label="Показывать подписи на графиках",
            value=True,
            key='show_labels',
            help="Отображать подписи осей и легенду"
        )
        
        st.divider()
        
        # Кнопка запуска анализа
        st.subheader("🚀 Запуск анализа")
        
        if st.button("▶️ Запустить анализ", type="primary", use_container_width=True):
            st.session_state['analysis_run'] = True
            st.success("✅ Анализ запущен! Перейдите на вкладку 'Результаты'")
            st.rerun()
        
    else:
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
                
                # Добавляем PC3 только если он существует
                if pca_result.shape[1] >= 3:
                    pca_df['PC3'] = pca_result[:, 2]
                
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
                if 'PC3' in pca_df.columns:
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
                    
                    # Преобразуем в длинный формат для px.box
                    comparison_df_melted = comparison_df.melt(
                        id_vars=['year'],
                        var_name='variable',
                        value_name='value'
                    )
                    
                    fig_comparison = px.box(
                        comparison_df_melted,
                        x='variable',
                        y='value',
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
# ЭТАП 8: ЭКСПОРТ И СОХРАНЕНИЕ РЕЗУЛЬТАТОВ
# =============================================================================
if 'data_valid' in st.session_state and st.session_state['data_valid']:
    st.divider()
    st.header("📥 Экспорт результатов")
    
    # =========================================================================
    # 8.1. Скачивание отчетов (Excel)
    # =========================================================================
    st.subheader("Скачать результаты (Excel)")
    
    def create_excel_report():
        """
        Создает Excel-файл с результатами анализа на лету.
        Возвращает BytesIO объект с Excel файлом.
        """
        import io
        
        df = st.session_state['data']
        
        # Создаем буфер в памяти
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Лист 1: Исходные данные
            df.to_excel(writer, sheet_name='Исходные данные', index=False)
            
            # Лист 2: Итоговая таблица расчетов (базовая статистика)
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                stats_df = df[numeric_cols].describe()
                stats_df.to_excel(writer, sheet_name='Статистика расчетов')
            
            # Лист 3: Параметры запуска (из конфига/session_state)
            params_data = {
                'Параметр': [],
                'Значение': []
            }
            
            # Собираем параметры из session_state
            param_mapping = {
                'outlier_method': 'Метод фильтрации выбросов',
                'z_threshold': 'Z-score порог',
                'iqr_multiplier': 'IQR множитель',
                'optimization_algorithm': 'Алгоритм оптимизации',
                'n_iterations': 'Количество итераций',
                'population_size': 'Размер популяции',
                'color_scheme': 'Цветовая схема',
                'point_size': 'Размер точек',
                'show_labels': 'Показывать подписи',
                'threshold_value': 'Пороговое значение',
                'enable_pca': 'Включить PCA',
                'enable_tsne': 'Включить t-SNE'
            }
            
            for key, label in param_mapping.items():
                value = st.session_state.get(key, 'Не задано')
                params_data['Параметр'].append(label)
                params_data['Значение'].append(str(value))
            
            params_df = pd.DataFrame(params_data)
            params_df.to_excel(writer, sheet_name='Параметры запуска', index=False)
            
            # Лист 4: Информация о данных
            info_data = {
                'Метрика': ['Количество строк', 'Количество колонок', 'Годы', 'Классы', 'HC колонки'],
                'Значение': [
                    str(st.session_state.get('n_rows', 'N/A')),
                    str(st.session_state.get('n_columns', 'N/A')),
                    str(st.session_state.get('years', 'N/A')),
                    str(st.session_state.get('classes', 'N/A')),
                    str(len(st.session_state.get('hc_columns', [])))
                ]
            }
            info_df = pd.DataFrame(info_data)
            info_df.to_excel(writer, sheet_name='Информация о данных', index=False)
        
        output.seek(0)
        return output
    
    excel_file = create_excel_report()
    
    st.download_button(
        label="📊 Скачать результаты (Excel)",
        data=excel_file,
        file_name=f"analysis_results_{st.session_state.get('file_name', 'data').split('.')[0]}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        help="Скачать Excel-файл с исходными данными, статистикой, параметрами и информацией"
    )
    
    st.divider()
    
    # =========================================================================
    # 8.2. Скачивание графиков
    # =========================================================================
    st.subheader("Скачать графики")
    
    st.markdown("""
    **Примечание:** Каждый интерактивный график выше имеет встроенную кнопку 
    сохранения (иконка камеры 📷 в правом верхнем углу графика). 
    Нажмите на неё, чтобы скачать график в PNG формате.
    """)
    
    # Опционально: кнопка "Скачать все графики (ZIP)"
    def create_plots_zip():
        """
        Создает ZIP-архив со всеми графиками в PNG формате.
        Возвращает BytesIO объект с ZIP архивом.
        """
        import io
        import zipfile
        import base64
        
        df = st.session_state['data']
        years = sorted(df['year'].unique())
        
        # Создаем буфер для ZIP
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Генерируем и сохраняем основные графики
            
            # График 1: Распределение данных по годам
            fig1 = make_subplots(
                rows=1, cols=2,
                subplot_titles=('Распределение по годам', 'Распределение по классам'),
                specs=[[{'type': 'bar'}, {'type': 'pie'}]]
            )
            
            # Бар-чарт по годам
            year_counts = df['year'].value_counts().sort_index()
            fig1.add_trace(
                go.Bar(x=year_counts.index.astype(str), y=year_counts.values, name='По годам'),
                row=1, col=1
            )
            
            # Pie-чарт по классам
            class_counts = df['Class'].value_counts()
            fig1.add_trace(
                go.Pie(labels=class_counts.index.astype(str), values=class_counts.values, name='По классам'),
                row=1, col=2
            )
            
            fig1.update_layout(height=400, showlegend=False, title_text="Обзор данных")
            
            # Сохраняем как PNG (через kaleido если установлен, иначе как HTML)
            try:
                img_bytes1 = fig1.to_image(format="png", width=800, height=400)
                zip_file.writestr('01_overview.png', img_bytes1)
            except Exception:
                # Если kaleido не установлен, сохраняем как HTML
                html1 = fig1.to_html(full_html=False, include_plotlyjs='cdn')
                zip_file.writestr('01_overview.html', html1)
            
            # График 2: Тепловая карта корреляций (если есть числовые данные)
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            hc_cols = [col for col in numeric_cols if col not in REQUIRED_COLUMNS]
            
            if len(hc_cols) >= 2:
                corr_matrix = df[hc_cols].corr()
                
                fig2 = go.Figure(data=go.Heatmap(
                    z=corr_matrix.values,
                    x=corr_matrix.columns,
                    y=corr_matrix.columns,
                    colorscale='RdBu_r',
                    zmid=0
                ))
                fig2.update_layout(title='Корреляционная матрица углеводородов', height=600)
                
                try:
                    img_bytes2 = fig2.to_image(format="png", width=800, height=600)
                    zip_file.writestr('02_correlation_heatmap.png', img_bytes2)
                except Exception:
                    html2 = fig2.to_html(full_html=False, include_plotlyjs='cdn')
                    zip_file.writestr('02_correlation_heatmap.html', html2)
            
            # График 3: Сравнение по годам (box plot)
            if len(years) >= 2 and len(hc_cols) > 0:
                sample_col = hc_cols[0]  # Берем первую HC колонку для примера
                
                fig3 = px.box(df, x='year', y=sample_col, color='year',
                             title=f'Распределение {sample_col} по годам',
                             labels={'year': 'Год', sample_col: sample_col})
                fig3.update_layout(height=400)
                
                try:
                    img_bytes3 = fig3.to_image(format="png", width=800, height=400)
                    zip_file.writestr('03_year_comparison_boxplot.png', img_bytes3)
                except Exception:
                    html3 = fig3.to_html(full_html=False, include_plotlyjs='cdn')
                    zip_file.writestr('03_year_comparison_boxplot.html', html3)
        
        zip_buffer.seek(0)
        return zip_buffer
    
    try:
        zip_file = create_plots_zip()
        
        st.download_button(
            label="📦 Скачать все графики (ZIP)",
            data=zip_file,
            file_name=f"plots_archive_{st.session_state.get('file_name', 'data').split('.')[0]}.zip",
            mime="application/zip",
            help="Скачать ZIP-архив со всеми основными графиками в PNG формате"
        )
        
        st.info("💡 **Совет:** Для экспорта в PNG требуется библиотека `kaleido`. Установите её командой: `pip install kaleido`")
        
    except Exception as e:
        st.warning(f"⚠️ Не удалось создать ZIP-архив: {str(e)}")
        st.info("Вы можете скачать каждый график индивидуально через кнопку камеры в интерфейсе графика.")

# =============================================================================
# Нижняя информация
# =============================================================================
st.markdown("---")
st.caption("""
Приложение для анализа стабильности углеводородов | 
Версия: 0.8.0 (Этап 8: Экспорт и сохранение результатов)
""")
