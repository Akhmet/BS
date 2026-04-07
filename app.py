"""
Streamlit-приложение для анализа стабильности углеводородов
На основе скрипта BS_qwen.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import io

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
    
    # Место для кнопок сохранения/загрузки конфигов
    st.header("💾 Конфигурации")
    st.info("Сохранение и загрузка настроек будет доступно после настройки параметров")

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
    st.warning("⚠️ Запустите анализ, чтобы увидеть результаты")
    
    # Место для результатов
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
Версия: 0.2.0 (Этап 3: Загрузка и предпросмотр данных)
""")
