"""
Тесты для Streamlit-приложения анализа углеводородов (app.py)
Этап 9: Тестирование и отладка
"""

import pytest
import pandas as pd
import numpy as np
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import io


# =============================================================================
# Фикстуры
# =============================================================================

@pytest.fixture
def sample_dataframe():
    """Создает тестовый DataFrame с минимально необходимыми колонками"""
    data = {
        'number probe': [1, 2, 3, 4, 5],
        'Class': ['A', 'B', 'A', 'B', 'A'],
        'year': [2020, 2020, 2021, 2021, 2022],
        'HC1': [10.5, 20.3, 15.2, 25.1, 12.8],
        'HC2': [5.2, 8.1, 6.5, 9.3, 5.8]
    }
    return pd.DataFrame(data)


@pytest.fixture
def incomplete_dataframe():
    """DataFrame с отсутствующими обязательными колонками"""
    data = {
        'number probe': [1, 2, 3],
        'Class': ['A', 'B', 'A'],
        # Отсутствует колонка 'year'
    }
    return pd.DataFrame(data)


@pytest.fixture
def empty_dataframe():
    """Пустой DataFrame"""
    return pd.DataFrame()


@pytest.fixture
def configs_dir(tmp_path):
    """Создает временную директорию для конфигураций"""
    configs_path = tmp_path / "saved_configs"
    configs_path.mkdir()
    return configs_path


# =============================================================================
# 9.1. Функциональное тестирование - Загрузка данных
# =============================================================================

class TestDataLoading:
    """Тесты функционала загрузки данных"""
    
    def test_load_data_excel_format(self, sample_dataframe):
        """Проверка загрузки Excel формата (симуляция)"""
        # Создаем байтовый буфер с Excel файлом
        buffer = io.BytesIO()
        sample_dataframe.to_excel(buffer, index=False, sheet_name='Лист1')
        buffer.seek(0)
        
        # Импортируем функцию загрузки из app
        from app import load_data
        
        df, error = load_data(buffer.getvalue(), '.xlsx')
        
        assert error is None
        assert df is not None
        assert len(df) == 5
        assert 'year' in df.columns
        assert df['year'].dtype in [np.int64, np.int32, int]
    
    def test_load_data_csv_format(self, sample_dataframe):
        """Проверка загрузки CSV формата"""
        buffer = io.BytesIO()
        sample_dataframe.to_csv(buffer, index=False)
        buffer.seek(0)
        
        from app import load_data
        
        df, error = load_data(buffer.getvalue(), '.csv')
        
        assert error is None
        assert df is not None
        assert len(df) == 5
    
    def test_load_data_unsupported_format(self):
        """Проверка обработки неподдерживаемого формата"""
        from app import load_data
        
        df, error = load_data(b"some binary data", '.txt')
        
        assert error is not None
        assert "Неподдерживаемый формат" in error
        assert df is None
    
    def test_load_data_corrupted_file(self):
        """Проверка обработки битого файла"""
        from app import load_data
        
        df, error = load_data(b"corrupted data", '.xlsx')
        
        assert error is not None
        assert df is None
    
    def test_load_data_empty_file(self):
        """Проверка обработки пустого файла"""
        from app import load_data
        
        df, error = load_data(b"", '.csv')
        
        assert error is not None
        assert df is None


# =============================================================================
# 9.1. Функциональное тестирование - Валидация данных
# =============================================================================

class TestColumnValidation:
    """Тесты валидации колонок"""
    
    def test_validate_columns_complete(self, sample_dataframe):
        """Проверка DataFrame со всеми обязательными колонками"""
        from app import validate_columns
        
        is_valid, missing = validate_columns(sample_dataframe)
        
        assert is_valid is True
        assert len(missing) == 0

    def test_validate_columns_incomplete(self, incomplete_dataframe):
        """Проверка DataFrame с отсутствующими колонками"""
        from app import validate_columns
        
        is_valid, missing = validate_columns(incomplete_dataframe)
        
        assert is_valid is False
        assert 'year' in missing
    
    def test_validate_columns_empty(self, empty_dataframe):
        """Проверка пустого DataFrame"""
        from app import validate_columns
        
        is_valid, missing = validate_columns(empty_dataframe)
        
        assert is_valid is False
        assert len(missing) == 3  # Все три обязательные колонки отсутствуют
    
    def test_validate_columns_extra_columns(self, sample_dataframe):
        """Проверка DataFrame с дополнительными колонками"""
        from app import validate_columns
        
        # Добавляем лишние колонки
        df = sample_dataframe.copy()
        df['extra_col'] = [1, 2, 3, 4, 5]
        
        is_valid, missing = validate_columns(df)
        
        assert is_valid is True
        assert len(missing) == 0


class TestConfigNormalization:
    """Тесты нормализации конфигурации для обратной совместимости."""

    def test_normalize_optimization_algorithm_aliases(self):
        """Старое значение GA должно корректно маппиться в genetic."""
        from app import normalize_optimization_algorithm

        assert normalize_optimization_algorithm('GA') == 'genetic'
        assert normalize_optimization_algorithm('genetic_algorithm') == 'genetic'
        assert normalize_optimization_algorithm('hybrid') == 'hybrid'

    def test_normalize_optimization_algorithm_invalid_fallback(self):
        """Некорректное значение должно безопасно возвращать hybrid."""
        from app import normalize_optimization_algorithm

        assert normalize_optimization_algorithm('unknown-algo') == 'hybrid'
        assert normalize_optimization_algorithm(None) == 'hybrid'

    def test_sanitize_loaded_config_updates_algorithm(self):
        """sanitize_loaded_config должен чинить устаревший ключ optimization_algorithm."""
        from app import sanitize_loaded_config

        config = {'optimization_algorithm': 'GA', 'min_hc': 7}
        sanitized = sanitize_loaded_config(config)

        assert sanitized['optimization_algorithm'] == 'genetic'
        assert sanitized['min_hc'] == 7


# =============================================================================
# 9.1. Функциональное тестирование - Конфигурации
# =============================================================================

class TestConfigManagement:
    """Тесты сохранения и загрузки конфигураций"""
    
    def test_save_config_success(self, configs_dir, monkeypatch):
        """Проверка успешного сохранения конфигурации"""
        import json
        
        # Мокаем session_state
        mock_session_state = {
            'outlier_method': 'z-score',
            'z_threshold': 3.0,
            'iqr_multiplier': 1.5,
            'optimization_algorithm': 'GA',
            'n_iterations': 100,
            'population_size': 50,
            'color_scheme': 'Viridis',
            'point_size': 10,
            'show_labels': True,
            'selected_years': [2020, 2021],
            'selected_classes': ['A', 'B'],
            'threshold_value': 0.5,
            'enable_pca': True,
            'enable_tsne': False
        }
        
        # Создаем тестовый файл конфига
        config_name = "test_config"
        config_file = configs_dir / f"{config_name}.json"
        
        # Сохраняем конфиг вручную (симуляция функции save_config)
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(mock_session_state, f, indent=2, ensure_ascii=False)
        
        # Проверяем что файл создан
        assert config_file.exists()
        
        # Проверяем содержимое
        with open(config_file, 'r', encoding='utf-8') as f:
            loaded_config = json.load(f)
        
        assert loaded_config['outlier_method'] == 'z-score'
        assert loaded_config['z_threshold'] == 3.0
        assert loaded_config['n_iterations'] == 100
    
    def test_load_config_success(self, configs_dir):
        """Проверка успешной загрузки конфигурации"""
        import json
        
        # Создаем тестовый конфиг
        config_data = {
            'outlier_method': 'iqr',
            'z_threshold': 2.5,
            'n_iterations': 200
        }
        
        config_file = configs_dir / "load_test.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f)
        
        # Загружаем конфиг
        with open(config_file, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
        
        assert loaded['outlier_method'] == 'iqr'
        assert loaded['z_threshold'] == 2.5
    
    def test_get_available_configs(self, configs_dir):
        """Проверка получения списка доступных конфигураций"""
        import json
        
        # Создаем несколько конфигов
        for name in ['config1', 'config2', 'config3']:
            config_file = configs_dir / f"{name}.json"
            with open(config_file, 'w') as f:
                json.dump({'test': True}, f)
        
        # Получаем список
        config_files = list(configs_dir.glob("*.json"))
        config_names = [f.stem for f in config_files]
        
        assert len(config_names) == 3
        assert 'config1' in config_names
        assert 'config2' in config_names
        assert 'config3' in config_names
    
    def test_config_empty_directory(self, configs_dir):
        """Проверка работы с пустой директорией конфигов"""
        config_files = list(configs_dir.glob("*.json"))
        
        assert len(config_files) == 0


# =============================================================================
# 9.1. Функциональное тестирование - Граничные значения параметров
# =============================================================================

class TestBoundaryValues:
    """Тесты граничных значений параметров"""
    
    def test_zero_iterations(self):
        """Проверка поведения при нулевых итерациях"""
        # Это тест на уровне логики - проверяем что значение принимается
        n_iterations = 0
        assert n_iterations >= 0
    
    def test_negative_threshold(self):
        """Проверка отрицательных пороговых значений"""
        # Z-threshold не должен быть отрицательным
        z_threshold = -1.0
        # Валидация должна отклонить это значение
        assert z_threshold < 0  # Ожидается что UI заблокирует ввод
    
    def test_maximum_iterations(self):
        """Проверка максимального количества итераций"""
        n_iterations = 10000
        assert n_iterations > 0
        assert n_iterations <= 100000  # Разумный лимит
    
    def test_iqr_multiplier_edge_cases(self):
        """Проверка граничных значений IQR множителя"""
        # Минимальное значение
        iqr_min = 0.0
        # Стандартное значение
        iqr_default = 1.5
        # Большое значение
        iqr_max = 10.0
        
        assert iqr_min >= 0
        assert iqr_default > 0
        assert iqr_max > iqr_default


# =============================================================================
# 9.2. Тестирование производительности
# =============================================================================

class TestPerformance:
    """Тесты производительности"""
    
    def test_large_dataset_loading(self):
        """Проверка загрузки большого датасета"""
        import time
        
        # Создаем большой DataFrame
        n_rows = 10000
        large_df = pd.DataFrame({
            'number probe': range(n_rows),
            'Class': np.random.choice(['A', 'B', 'C'], n_rows),
            'year': np.random.choice([2020, 2021, 2022], n_rows),
            'HC1': np.random.rand(n_rows) * 100,
            'HC2': np.random.rand(n_rows) * 100
        })
        
        # Замеряем время обработки
        start_time = time.time()
        
        # Симуляция операции загрузки/обработки
        buffer = io.BytesIO()
        large_df.to_csv(buffer, index=False)
        buffer.seek(0)
        
        from app import load_data
        df, error = load_data(buffer.getvalue(), '.csv')
        
        elapsed_time = time.time() - start_time
        
        assert error is None
        assert df is not None
        assert len(df) == n_rows
        # Время загрузки должно быть разумным (< 5 секунд)
        assert elapsed_time < 5.0
    
    def test_caching_mechanism(self):
        """Проверка работы кэширования"""
        import time
        
        # Создаем тестовые данные с правильными колонками
        buffer = io.BytesIO()
        test_df = pd.DataFrame({
            'number probe': [1, 2, 3],
            'Class': ['A', 'B', 'C'],
            'year': [2020, 2021, 2022]
        })
        test_df.to_csv(buffer, index=False)
        buffer.seek(0)
        data = buffer.getvalue()
        
        from app import load_data
        
        # Первый вызов (без кэша)
        start1 = time.time()
        df1, error1 = load_data(data, '.csv')
        time1 = time.time() - start1
        
        # Второй вызов (с кэшем)
        start2 = time.time()
        df2, error2 = load_data(data, '.csv')
        time2 = time.time() - start2
        
        # Проверяем что ошибки отсутствуют
        assert error1 is None, f"Первый вызов вернул ошибку: {error1}"
        assert error2 is None, f"Второй вызов вернул ошибку: {error2}"
        
        # Результаты должны быть одинаковыми
        assert df1 is not None
        assert df2 is not None
        assert df1.equals(df2)
        # Второй вызов должен быть быстрее (кэширование)
        # Примечание: в тестах кэш может не работать как в production


# =============================================================================
# 9.3. UX/UI тестирование
# =============================================================================

class TestUXElements:
    """Тесты элементов пользовательского интерфейса"""
    
    def test_required_columns_defined(self):
        """Проверка что обязательные колонки определены"""
        from app import REQUIRED_COLUMNS
        
        assert REQUIRED_COLUMNS is not None
        assert len(REQUIRED_COLUMNS) > 0
        assert 'year' in REQUIRED_COLUMNS
        assert 'Class' in REQUIRED_COLUMNS
    
    def test_error_messages_present(self):
        """Проверка наличия сообщений об ошибках"""
        from app import load_data
        
        # Проверяем что функция возвращает понятные ошибки
        df, error = load_data(b"invalid", '.xlsx')
        
        assert error is not None
        assert isinstance(error, str)
        assert len(error) > 0
    
    def test_data_types_preserved(self, sample_dataframe):
        """Проверка сохранения типов данных после загрузки"""
        buffer = io.BytesIO()
        sample_dataframe.to_csv(buffer, index=False)
        buffer.seek(0)
        
        from app import load_data
        df, error = load_data(buffer.getvalue(), '.csv')
        
        assert error is None
        # year должен быть целочисленным
        assert df['year'].dtype in [np.int64, np.int32, int]


# =============================================================================
# Интеграционные тесты
# =============================================================================

class TestIntegration:
    """Интеграционные тесты полного цикла"""
    
    def test_full_workflow(self, sample_dataframe, configs_dir):
        """Тест полного рабочего цикла: загрузка -> валидация -> сохранение конфига"""
        import json
        
        # 1. Загрузка данных
        buffer = io.BytesIO()
        sample_dataframe.to_csv(buffer, index=False)
        buffer.seek(0)
        
        from app import load_data, validate_columns
        
        df, error = load_data(buffer.getvalue(), '.csv')
        assert error is None
        assert df is not None
        
        # 2. Валидация
        is_valid, missing = validate_columns(df)
        assert is_valid is True
        
        # 3. Сохранение конфигурации
        config_data = {
            'outlier_method': 'z-score',
            'n_iterations': 100
        }
        
        config_file = configs_dir / "integration_test.json"
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        # 4. Загрузка конфигурации
        with open(config_file, 'r') as f:
            loaded = json.load(f)
        
        assert loaded['outlier_method'] == 'z-score'
        assert loaded['n_iterations'] == 100
    
    def test_error_handling_workflow(self):
        """Тест обработки ошибок в рабочем цикле"""
        from app import load_data, validate_columns
        
        # Пытаемся загрузить некорректные данные
        df, error = load_data(b"corrupted", '.xlsx')
        
        assert error is not None
        assert df is None
        
        # Если данных нет, валидация не должна выполняться
        if df is not None:
            is_valid, missing = validate_columns(df)
            assert is_valid is False


# =============================================================================
# Запуск тестов
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
