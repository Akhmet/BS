# Анализ кода BS_qwen.py для Streamlit-приложения

## 1. Точка входа
- **Основная функция:** `main()` (строка 2488)
- **Запуск:** `if __name__ == "__main__":` (строка 2939)

## 2. Глобальные переменные
- `year_1`, `year_2` - годы измерений (строки 2484-2485)

## 3. Параметры конфигурации (все в начале файла, строки 26-120)

### 3.1 Пути и файлы
| Параметр | Тип | Значение по умолчанию |
|----------|-----|----------------------|
| INPUT_FILEPATH | str | 'C:\\Work\\BS\\test_synthetic1.xlsx' |
| OUTPUT_FILENAME | str | 'hydrocarbon_stability_analysis_v4.xlsx' |
| OPTIMAL_HC_FILENAME | str | 'optimal_hydrocarbon_set.xlsx' |

### 3.2 Методы анализа (METHODS_CONFIG)
| Метод | Тип | По умолчанию | Описание |
|-------|-----|--------------|----------|
| clr | bool | False | CLR трансформация |
| ratio | bool | False | Пропорции (нормировка на сумму) |
| pattern | bool | False | Корреляционные паттерны |
| importance | bool | False | Feature Importance (ML) |
| bootstrap | bool | True | Bootstrap доверительные интервалы |
| pca | bool | False | PCA Loadings стабильность |
| cohens_d | bool | False | Robust Cohen's D |
| wasserstein | bool | False | Wasserstein distance |
| pairwise | bool | True | Pairwise Log-Ratio |

- `MIN_METHODS_FOR_CONSENSUS` (int): 1 - минимальное количество методов для консенсуса

### 3.3 Настройки оптимизации
| Параметр | Тип | Значение | Описание |
|----------|-----|----------|----------|
| OPTIMIZATION_ALGORITHM | str | 'hybrid' | 'greedy', 'genetic', 'hybrid' |
| MIN_HC | int | 11 | Мин. количество УВ после оптимизации |
| MAX_HC | int | 35 | Макс. количество УВ |
| MAX_ITERATIONS | int | 60 | Макс. итерации/поколения |
| CONSENSUS_THRESHOLD_MIN | float | 0.3 | Мин. порог consensus score |
| CONSENSUS_THRESHOLD_MAX | float | 0.7 | Макс. порог consensus score |
| CONSENSUS_THRESHOLD_STEP | float | 0.1 | Шаг перебора порога |

### 3.4 Параметры генетического алгоритма
| Параметр | Тип | Значение |
|----------|-----|----------|
| GA_POP_SIZE | int | 60 |
| GA_GENERATIONS | int | 40 |
| GA_MUTATION_RATE | float | 0.15 |
| GA_CROSSOVER_PROBABILITY | float | 0.7 |
| GA_EARLY_STOP_PATIENCE | int | 10 |
| GA_EARLY_STOP_TOLERANCE | float | 0.001 |

### 3.5 Параметры жадного алгоритма
| Параметр | Тип | Значение |
|----------|-----|----------|
| GREEDY_MAX_ITERATIONS | int | 20 |
| GREEDY_N_REMOVE_OPTIONS | list | [1, 2, 3] |
| GREEDY_HYBRID_ITERATIONS | int | 15 |

### 3.6 Кросс-валидация
| Параметр | Тип | Значение |
|----------|-----|----------|
| CV_FOLDS | int | 5 |
| CV_ENABLED | bool | True |

### 3.7 Настройки выбросов
| Параметр | Тип | Значение | Описание |
|----------|-----|----------|----------|
| EXCLUDE_SAMPLE_OUTLIERS | bool | False | Исключать пробы-выбросы |
| SAMPLE_OUTLIER_METHOD | str | 'mahalanobis' | 'mahalanobis', 'isolation_forest', 'aitchison' |
| SAMPLE_OUTLIER_THRESHOLD | float | 0.975 | Порог Mahalanobis |
| HC_OUTLIER_METHOD | str | 'robust_z' | 'robust_z', 'iqr', 'zscore' |
| HC_OUTLIER_THRESHOLD | float | 3.5 | Порог обнаружения выбросов УВ |
| ISOLATION_FOREST_CONTAMINATION | float | 0.1 | Загрязнение для Isolation Forest |

### 3.8 Статистические параметры
| Параметр | Тип | Значение |
|----------|-----|----------|
| BOOTSTRAP_ITERATIONS | int | 500 |
| PCA_N_COMPONENTS | int | 5 |
| EPSILON | float | 0.0001 |
| STABILITY_HIGH_THRESHOLD | float | 0.7 |
| STABILITY_MEDIUM_THRESHOLD | float | 0.5 |

### 3.9 Веса метрик (CLR стабильность)
| Параметр | Тип | Значение |
|----------|-----|----------|
| CLR_WEIGHT_MEDIAN | float | 0.30 |
| CLR_WEIGHT_KS | float | 0.25 |
| CLR_WEIGHT_OVERLAP | float | 0.25 |
| CLR_WEIGHT_EFFECT_SIZE | float | 0.20 |

### 3.10 Веса метрик (Пропорции стабильность)
| Параметр | Тип | Значение |
|----------|-----|----------|
| RATIO_WEIGHT_MEDIAN | float | 0.25 |
| RATIO_WEIGHT_KS | float | 0.25 |
| RATIO_WEIGHT_OVERLAP | float | 0.25 |
| RATIO_WEIGHT_EFFECT_SIZE | float | 0.25 |

### 3.11 Веса метрик (Quality Score)
| Параметр | Тип | Значение |
|----------|-----|----------|
| QUALITY_WEIGHT_CENTROID | float | 0.5 |
| QUALITY_WEIGHT_VARIANCE | float | 0.3 |
| QUALITY_WEIGHT_DENSITY | float | 0.2 |

### 3.12 Настройки визуализации
| Параметр | Тип | Значение |
|----------|-----|----------|
| FIG_DPI | int | 300 |
| MAX_HC_PER_PLOT_BOX | int | 10 |
| MAX_HC_PER_PLOT_KDE | int | 6 |
| PLOT_STYLE | str | 'seaborn-v0_8-whitegrid' |
| COLOR_YEAR_1 | str | 'blue' |
| COLOR_YEAR_2 | str | 'green' |
| COLOR_OUTLIER | str | 'red' |
| COLOR_NORMAL | str | 'blue' |

### 3.13 Настройки экспорта
| Параметр | Тип | Значение |
|----------|-----|----------|
| EXPORT_SHEET_TOP_N | int | 10 |

### 3.14 Случайность
| Параметр | Тип | Значение |
|----------|-----|----------|
| RANDOM_STATE | int | 42 |

## 4. Основные функции

### 4.1 Загрузка данных
- `load_data(filepath)` - загрузка Excel файла

### 4.2 Предобработка
- `get_hydrocarbon_columns(df)` - получение списка колонок УВ
- `get_unique_years(df)` - получение уникальных годов
- `prepare_data_by_year(df, hc_columns, year_1, year_2)` - разделение по годам
- `normalize_to_proportions(data)` - нормировка на сумму
- `clr_transform(proportions)` - CLR трансформация
- `prepare_compositional_data(...)` - полная подготовка композиционных данных

### 4.3 Обнаружение выбросов
- `detect_sample_outliers(clr_data, method, contamination)` - выбросы проб
- `detect_hydrocarbon_outliers(clr_data, method, threshold)` - выбросы УВ
- `visualize_outliers(...)` - визуализация выбросов
- `create_outlier_report(...)` - создание отчета

### 4.4 Расчет стабильности (методы)
- `calculate_clr_stability(clr_year_1, clr_year_2, hc_columns)`
- `calculate_ratio_stability_metrics(proportions_year_1, proportions_year_2, hc_columns)`
- `correlation_pattern_stability(proportions_year_1, proportions_year_2, hc_columns)`
- `year_prediction_importance(log_proportions_year_1, log_proportions_year_2, hc_columns)`
- `bootstrap_stability_ci(log_proportions_year_1, log_proportions_year_2, hc_columns, n_iterations)`
- `pca_loadings_stability(clr_year_1, clr_year_2, hc_columns, n_components)`
- `calculate_cohens_d(y1, y2, method)` + `calculate_wasserstein_stability(clr_year_1, clr_year_2, hc_columns)`
- `calculate_pairwise_logratio_stability(proportions_year_1, proportions_year_2, hc_columns)`

### 4.5 Консенсус и классификация
- `consensus_ranking(results_dict, method_names, hc_columns, use_variance_weighting)`
- `classify_hydrocarbons(hc_columns)`

### 4.6 Оптимизация
- `evaluate_hydrocarbon_set(proportions_year_1, proportions_year_2, hc_subset, consensus_df)`
- `optimize_greedy(proportions_year_1, proportions_year_2, candidate_hc, consensus_df, ...)`
- `optimize_genetic(proportions_year_1, proportions_year_2, hc_columns, consensus_df, ...)`
- `optimize_hybrid(proportions_year_1, proportions_year_2, hc_columns, consensus_df, ...)`
- `optimize_hydrocarbon_set(proportions_year_1, proportions_year_2, candidate_hc, consensus_df, ...)`
- `optimize_consensus_threshold(proportions_year_1, proportions_year_2, hc_columns, consensus_df, ...)`
- `cross_validate_optimization(proportions_year_1, proportions_year_2, hc_columns, consensus_df, ...)`
- `sensitivity_analysis(proportions_year_1, proportions_year_2, optimal_hc, consensus_df)`

### 4.7 Визуализация
- `plot_method_comparison(all_scores_df, enabled_methods, output_dir, output_path)`
- `plot_consensus_ranking(consensus_df, output_dir, output_path)`
- `plot_cohens_d_distribution(cohens_d_results, output_dir, output_path)`
- `plot_bootstrap_ci(bootstrap_df, output_dir, output_path)`
- `plot_feature_importance(importance_df, output_dir, output_path)`
- `plot_pca_loadings(loadings_df, output_dir, output_path)`
- `plot_correlation_matrices(corr_year_1, corr_year_2, year_1, year_2, output_dir, output_path)`
- `plot_optimization_history(history, output_dir)`
- `plot_pca_comparison_before_after(proportions_year_1, proportions_year_2, hc_all, hc_optimized, ...)`
- `plot_stable_hc_comparison_final(df, hc_optimized, consensus_df, year_1, year_2, output_dir, output_path)`
- `plot_parallel_coordinates_final(df, hc_optimized, consensus_df, year_1, year_2, output_dir)`
- `plot_correlation_heatmap_stable_final(df, hc_optimized, year_1, year_2, output_dir)`
- `plot_distribution_overlap_final(df, hc_optimized, consensus_df, year_1, year_2, output_dir, output_path)`
- `plot_pca_biplot_final(proportions_year_1, proportions_year_2, hc_optimized, year_1, year_2, output_dir)`

### 4.8 Экспорт
- `export_results(all_results, enabled_methods, output_dir, output_path)`

## 5. Особенности кода

### 5.1 Проблемы для рефакторинга
1. **Глобальные переменные** `year_1`, `year_2` используются в функциях визуализации
2. **Константы конфигурации** определены на модульном уровне - нужно передавать параметрами
3. **Функции визуализации** сохраняют файлы напрямую через `plt.savefig()` - нужно возвращать фигуры
4. **Функция `main()`** жестко завязана на `INPUT_FILEPATH` - нужно передавать DataFrame

### 5.2 Что уже хорошо
1. ✅ Нет вызовов `plt.show()` - все графики сохраняются через `plt.savefig()` с последующим `plt.close()`
2. ✅ Нет вызовов `input()` - все параметры из конфигурации
3. ✅ Функции модульные, каждая отвечает за свою задачу
4. ✅ Обработка ошибок присутствует в ключевых местах

## 6. Рекомендации для рефакторинга (Этап 1.3)

1. Создать функцию `run_analysis(df, params, output_dir)` которая:
   - Принимает DataFrame вместо загрузки из файла
   - Принимает словарь параметров `params`
   - Принимает директорию для вывода `output_dir`
   - Возвращает результаты (all_results, optimized_hc, optimization_history)

2. Создать функцию `_apply_params(params)` для применения параметров из GUI к глобальным настройкам

3. Модифицировать функции визуализации для возврата объектов matplotlib Figure вместо сохранения файлов

4. Сохранить функцию `main()` для обратной совместимости при запуске как скрипт
