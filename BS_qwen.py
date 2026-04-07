# -*- coding: utf-8 -*-
"""
Анализ стабильности углеводородов между измерениями разных годов
Версия: 4.8 (ИСПРАВЛЕНИЕ: Защита от ошибки min_hc >= len(hc_columns))

КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ:
- Добавлена проверка: min_hc не может превышать количество доступных УВ
- Если candidate_hc < MIN_HC, автоматически корректируем min_hc
- Исправлена ошибка ValueError: low >= high в np.random.randint

Проблема версии 4.7:
  - При малом количестве кандидатов (consensus >= threshold)
    MIN_HC мог быть больше len(candidate_hc)
  - np.random.randint(min_hc, max_possible) выдавал ошибку

Решение версии 4.8:
  - Явная проверка и корректировка min_hc в optimize_genetic
  - Проверка в optimize_greedy
  - Информативные сообщения об изменении параметров
"""

# =============================================================================
# КОНФИГУРАЦИЯ И НАСТРОЙКИ (Все параметры в одном месте)
# =============================================================================

# ---------------------- ПУТИ И ФАЙЛЫ ----------------------
INPUT_FILEPATH = r'd:\Work\2026\test\test.xlsx'
OUTPUT_FILENAME = 'hydrocarbon_stability_analysis_v4.xlsx'
OPTIMAL_HC_FILENAME = 'optimal_hydrocarbon_set.xlsx'

# ---------------------- ВЫБОР МЕТОДОВ АНАЛИЗА ----------------------
# Установите True для использования метода, False для отключения
METHODS_CONFIG = {
    'clr': False,  # ⭐⭐⭐⭐⭐ CLR трансформация (обязательно для композиционных данных)
    'ratio': False,  # ⭐⭐⭐ Пропорции (нормировка на сумму)
    'pattern': False,  # ⭐⭐ Корреляционные паттерны
    'importance': False,  # ⭐ Feature Importance (ML, может переобучаться)
    'bootstrap': True,  # ⭐⭐⭐⭐ Bootstrap доверительные интервалы
    'pca': False,  # ⭐⭐ PCA Loadings стабильность
    'cohens_d': False,  # ⭐⭐⭐⭐ Robust Cohen's D (медиана + MAD)
    'wasserstein': False,  # ⭐⭐⭐⭐ Wasserstein distance (форма распределения)
    'pairwise': True,  # ⭐⭐⭐⭐⭐ Pairwise Log-Ratio (лучший для композиционных данных)
}

# Минимальное количество методов для консенсусного рейтинга
MIN_METHODS_FOR_CONSENSUS = 1

# ---------------------- НАСТРОЙКИ ОПТИМИЗАЦИИ ----------------------
OPTIMIZATION_ALGORITHM = 'hybrid'  # 'greedy', 'genetic', 'hybrid'
MIN_HC = 11  # Минимальное количество УВ после оптимизации
MAX_HC = 35  # Максимальное количество УВ
MAX_ITERATIONS = 60  # Для greedy: макс итерации, для genetic: поколения
CONSENSUS_THRESHOLD = 0.4  # Порог consensus score для кандидатов на оптимизацию

# ---------------------- ПАРАМЕТРЫ ГЕНЕТИЧЕСКОГО АЛГОРИТМА ----------------------
GA_POP_SIZE = 60
GA_GENERATIONS = 40
GA_MUTATION_RATE = 0.15
GA_CROSSOVER_PROBABILITY = 0.7

# ---------------------- ПАРАМЕТРЫ ЖАДНОГО АЛГОРИТМА ----------------------
GREEDY_MAX_ITERATIONS = 20  # Максимум итераций жадного алгоритма
GREEDY_N_REMOVE_OPTIONS = [1, 2, 3]  # Сколько УВ пробовать удалять за шаг
GREEDY_HYBRID_ITERATIONS = 15  # Итераций жадного в гибридном режиме

# ---------------------- НАСТРОЙКИ ВЫБРОСОВ ----------------------
EXCLUDE_SAMPLE_OUTLIERS = False  # Исключать ли пробы-выбросы из анализа
SAMPLE_OUTLIER_METHOD = 'mahalanobis'  # 'mahalanobis', 'isolation_forest', 'aitchison'
SAMPLE_OUTLIER_THRESHOLD = 0.975  # Порог для Mahalanobis (chi2.ppf)
HC_OUTLIER_METHOD = 'robust_z'  # 'robust_z', 'iqr', 'zscore'
HC_OUTLIER_THRESHOLD = 3.5  # Порог для обнаружения выбросов углеводородов
ISOLATION_FOREST_CONTAMINATION = 0.1

# ---------------------- СТАТИСТИЧЕСКИЕ ПАРАМЕТРЫ ----------------------
BOOTSTRAP_ITERATIONS = 500
PCA_N_COMPONENTS = 5
EPSILON = 0.0001  # Для защиты от деления на ноль и логарифмов
STABILITY_HIGH_THRESHOLD = 0.7  # Порог для HIGH стабильности
STABILITY_MEDIUM_THRESHOLD = 0.5  # Порог для MEDIUM стабильности

# ---------------------- ВЕСА МЕТРИК (CLR стабильность) ----------------------
CLR_WEIGHT_MEDIAN = 0.30
CLR_WEIGHT_KS = 0.25
CLR_WEIGHT_OVERLAP = 0.25
CLR_WEIGHT_EFFECT_SIZE = 0.20

# ---------------------- ВЕСА МЕТРИК (Пропорции стабильность) ----------------------
RATIO_WEIGHT_MEDIAN = 0.25
RATIO_WEIGHT_KS = 0.25
RATIO_WEIGHT_OVERLAP = 0.25
RATIO_WEIGHT_EFFECT_SIZE = 0.25

# ---------------------- ВЕСА МЕТРИК (Quality Score для оптимизации) ----------------------
QUALITY_WEIGHT_CENTROID = 0.9
QUALITY_WEIGHT_VARIANCE = 0.00
QUALITY_WEIGHT_DENSITY = 0.1

# ---------------------- НАСТРОЙКИ ВИЗУАЛИЗАЦИИ ----------------------
FIG_DPI = 300
MAX_HC_PER_PLOT_BOX = 10
MAX_HC_PER_PLOT_KDE = 6
PLOT_STYLE = 'seaborn-v0_8-whitegrid'
COLOR_YEAR_1 = 'blue'  # Цвет для первого года
COLOR_YEAR_2 = 'green'  # Цвет для второго года
COLOR_OUTLIER = 'red'
COLOR_NORMAL = 'blue'

# ---------------------- НАСТРОЙКИ ЭКСПОРТА ----------------------
EXPORT_SHEET_TOP_N = 10  # Количество топ-результатов для отдельных листов

# ---------------------- СЛУЧАЙНОСТЬ ----------------------
RANDOM_STATE = 42

# =============================================================================
# ИМПОРТЫ
# =============================================================================

# ВАЖНО: Установить backend ДО импорта pyplot (исправляет ошибки tkinter)
import matplotlib

matplotlib.use('Agg')

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import spearmanr, pearsonr, ks_2samp, mannwhitneyu, gaussian_kde, chi2
from scipy.stats import wasserstein_distance
from scipy.spatial.distance import mahalanobis
from sklearn.preprocessing import StandardScaler, RobustScaler, MinMaxScaler
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.decomposition import PCA
from sklearn.utils import resample
import warnings
import os
import time

warnings.filterwarnings('ignore')

# Настройка стилей для графиков
plt.style.use(PLOT_STYLE)
sns.set_palette("husl")


# =============================================================================
# 1. ЗАГРУЗКА ДАННЫХ
# =============================================================================

def load_data(filepath):
    """Загрузка данных из Excel файла"""
    print(f"Загрузка данных из {filepath}...")
    df = pd.read_excel(filepath, sheet_name='Лист1')

    # Удаление строк с NaN в колонке year
    df = df.dropna(subset=['year'])

    # Преобразование year в int
    df['year'] = df['year'].astype(int)

    print(f"Загружено {len(df)} проб (после очистки от NaN)")
    print(f"Годы измерений: {df['year'].unique()}")
    print(f"Классы: {df['Class'].unique()}")
    return df


# =============================================================================
# 2. ПРЕДОБРАБОТКА ДАННЫХ
# =============================================================================

def get_hydrocarbon_columns(df):
    """Получение списка колонок с углеводородами"""
    exclude_cols = ['number probe', 'Class', 'year']
    hc_columns = [col for col in df.columns if col not in exclude_cols]
    return hc_columns


def get_unique_years(df):
    """Получение уникальных годов из данных"""
    years = sorted(df['year'].unique())
    if len(years) != 2:
        print(f"⚠️  Ожидается 2 года, найдено: {len(years)} ({years})")
        print("   Будут использованы первые два года из сортированного списка")
    return years[0], years[1]


def prepare_data_by_year(df, hc_columns, year_1, year_2):
    """Разделение данных по годам и подготовка матриц"""
    data_year_1 = df[df['year'] == year_1][hc_columns].reset_index(drop=True)
    data_year_2 = df[df['year'] == year_2][hc_columns].reset_index(drop=True)

    print(f"\nПроб {year_1} года: {len(data_year_1)}")
    print(f"Проб {year_2} года: {len(data_year_2)}")

    data_year_1 = data_year_1.map(lambda x: max(x, EPSILON) if pd.notnull(x) else EPSILON)
    data_year_2 = data_year_2.map(lambda x: max(x, EPSILON) if pd.notnull(x) else EPSILON)

    return data_year_1, data_year_2


# =============================================================================
# 3. НОРМИРОВКА И CLR ТРАНСФОРМАЦИЯ
# =============================================================================

def normalize_to_proportions(data):
    """
    ШАГ 1: Нормировка на сумму внутри каждой пробы
    Конвертирует абсолютные концентрации в пропорции (сумма = 1)
    """
    row_sums = data.sum(axis=1)
    proportions = data.div(row_sums, axis=0)
    return proportions


def clr_transform(proportions):
    """
    ШАГ 2: Centred Log-Ratio transformation
    ПРАВИЛЬНЫЙ ПОРЯДОК: пропорции → логарифм → центрирование
    """
    proportions_safe = proportions + EPSILON
    log_proportions = np.log(proportions_safe)
    geometric_mean = log_proportions.mean(axis=1)
    clr_data = log_proportions.sub(geometric_mean, axis=0)
    return clr_data


def prepare_compositional_data(data_year_1, data_year_2, hc_columns):
    """
    Полная подготовка композиционных данных с правильным порядком трансформаций
    """

    print("\n" + "=" * 80)
    print("ПОДГОТОВКА КОМПОЗИЦИОННЫХ ДАННЫХ (ПРАВИЛЬНЫЙ ПОРЯДОК)")
    print("=" * 80)

    # ШАГ 1: Нормировка на сумму (пропорции)
    proportions_year_1 = normalize_to_proportions(data_year_1)
    proportions_year_2 = normalize_to_proportions(data_year_2)

    print(f"  Пропорции год 1: сумма по строкам = {proportions_year_1.sum(axis=1).mean():.6f} (должно быть ~1.0)")
    print(f"  Пропорции год 2: сумма по строкам = {proportions_year_2.sum(axis=1).mean():.6f} (должно быть ~1.0)")

    # ШАГ 2: CLR трансформация
    clr_year_1 = clr_transform(proportions_year_1)
    clr_year_2 = clr_transform(proportions_year_2)

    # ШАГ 3: Логарифмированные пропорции (для некоторых методов)
    log_proportions_year_1 = np.log(proportions_year_1 + EPSILON)
    log_proportions_year_2 = np.log(proportions_year_2 + EPSILON)

    print(f"  CLR год 1: mean={clr_year_1.values.mean():.6f}, std={clr_year_1.values.std():.6f}")
    print(f"  CLR год 2: mean={clr_year_2.values.mean():.6f}, std={clr_year_2.values.std():.6f}")

    return proportions_year_1, proportions_year_2, clr_year_1, clr_year_2, log_proportions_year_1, log_proportions_year_2


# =============================================================================
# 4. ОБНАРУЖЕНИЕ ВЫБРОСОВ
# =============================================================================

def detect_sample_outliers(clr_data, method=SAMPLE_OUTLIER_METHOD, contamination=ISOLATION_FOREST_CONTAMINATION):
    """Обнаружение проб-выбросов на CLR-трансформированных данных"""

    n_samples, n_features = clr_data.shape

    if method == 'mahalanobis':
        center = np.mean(clr_data.values, axis=0)
        cov = np.cov(clr_data.values, rowvar=False)
        cov = cov + np.eye(n_features) * 1e-6

        try:
            cov_inv = np.linalg.inv(cov)
        except:
            cov_inv = np.linalg.pinv(cov)

        scores = np.array([
            mahalanobis(clr_data.iloc[i].values, center, cov_inv)
            for i in range(n_samples)
        ])

        threshold = np.sqrt(chi2.ppf(SAMPLE_OUTLIER_THRESHOLD, n_features))
        outlier_mask = scores > threshold

    elif method == 'isolation_forest':
        iso_forest = IsolationForest(contamination=contamination, random_state=RANDOM_STATE)
        predictions = iso_forest.fit_predict(clr_data.values)
        scores = -iso_forest.score_samples(clr_data.values)
        threshold = np.percentile(scores, 100 * (1 - contamination))
        outlier_mask = predictions == -1

    elif method == 'aitchison':
        geometric_center = np.exp(np.mean(clr_data.values, axis=0))
        scores = np.array([
            np.sqrt(np.sum((clr_data.iloc[i].values - geometric_center) ** 2))
            for i in range(n_samples)
        ])
        threshold = np.percentile(scores, 95)
        outlier_mask = scores > threshold

    else:
        raise ValueError(f"Unknown method: {method}")

    return outlier_mask, scores, threshold


def detect_hydrocarbon_outliers(clr_data, method=HC_OUTLIER_METHOD, threshold=HC_OUTLIER_THRESHOLD):
    """Обнаружение углеводородов-выбросов в отдельных пробах"""

    from scipy.stats import zscore

    outlier_df = pd.DataFrame(False, index=clr_data.index, columns=clr_data.columns)
    outlier_summary = []

    for hc in clr_data.columns:
        values = clr_data[hc].values

        if method == 'robust_z':
            median = np.median(values)
            mad = np.median(np.abs(values - median))
            mad_scaled = mad * 1.4826

            if mad_scaled < 1e-10:
                mad_scaled = 1e-10

            robust_z = np.abs((values - median) / mad_scaled)
            outlier_mask = robust_z > threshold

        elif method == 'iqr':
            q1, q3 = np.percentile(values, [25, 75])
            iqr = q3 - q1
            lower_fence = q1 - 1.5 * iqr
            upper_fence = q3 + 1.5 * iqr
            outlier_mask = (values < lower_fence) | (values > upper_fence)

        elif method == 'zscore':
            z = np.abs(zscore(values))
            outlier_mask = z > threshold

        else:
            raise ValueError(f"Unknown method: {method}")

        outlier_df[hc] = outlier_mask
        outlier_summary.append({
            'hydrocarbon': hc,
            'n_outliers': outlier_mask.sum(),
            'outlier_ratio': outlier_mask.mean(),
            'median': np.median(values),
            'mad': np.median(np.abs(values - np.median(values))) * 1.4826
        })

    outlier_summary_df = pd.DataFrame(outlier_summary)
    outlier_summary_df = outlier_summary_df.sort_values('n_outliers', ascending=False)

    return outlier_df, outlier_summary_df


def visualize_outliers(clr_year_1, clr_year_2, sample_outliers_year_1, sample_outliers_year_2,
                       hc_outliers_year_1, hc_outliers_year_2, year_1, year_2, output_dir):
    """Визуализация обнаруженных выбросов"""

    # 1. PCA plot с выделением выбросов
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    for ax, clr_data, sample_outliers, year, color in [
        (axes[0], clr_year_1, sample_outliers_year_1, year_1, COLOR_YEAR_1),
        (axes[1], clr_year_2, sample_outliers_year_2, year_2, COLOR_YEAR_2)
    ]:
        pca = PCA(n_components=2)
        pca_result = pca.fit_transform(clr_data)

        ax.scatter(pca_result[~sample_outliers, 0], pca_result[~sample_outliers, 1],
                   c=COLOR_NORMAL, alpha=0.6, s=100, label='Normal', edgecolors='black')

        if sample_outliers.sum() > 0:
            ax.scatter(pca_result[sample_outliers, 0], pca_result[sample_outliers, 1],
                       c=COLOR_OUTLIER, alpha=0.8, s=150, label='Outlier', edgecolors='black', linewidth=2)

        ax.set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0] * 100:.1f}%)')
        ax.set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1] * 100:.1f}%)')
        ax.set_title(f'PCA: Выбросы проб {year}', fontsize=12, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)

    plt.suptitle('Обнаружение проб-выбросов (Mahalanobis на CLR)', fontsize=14, fontweight='bold')
    plt.tight_layout()

    full_path = os.path.join(output_dir, 'outlier_detection_samples.png')
    plt.savefig(full_path, dpi=FIG_DPI, bbox_inches='tight')
    plt.close()
    print(f"Сохранено: {full_path}")

    # 2. Heatmap выбросов по углеводородам
    fig, axes = plt.subplots(1, 2, figsize=(16, 8))

    for ax, hc_outliers, year in [
        (axes[0], hc_outliers_year_1, str(year_1)),
        (axes[1], hc_outliers_year_2, str(year_2))
    ]:
        im = ax.imshow(hc_outliers.values.T, cmap='Reds', aspect='auto')
        ax.set_xlabel('Probe Index')
        ax.set_ylabel('Hydrocarbon')
        ax.set_title(f'Выбросы углеводородов {year}\n(красный = выброс)', fontsize=12, fontweight='bold')
        plt.colorbar(im, ax=ax, label='Outlier (1=yes)')
        ax.grid(False)

    plt.suptitle('Обнаружение углеводородов-выбросов (Robust Z-score)', fontsize=14, fontweight='bold')
    plt.tight_layout()

    full_path = os.path.join(output_dir, 'outlier_detection_hydrocarbons.png')
    plt.savefig(full_path, dpi=FIG_DPI, bbox_inches='tight')
    plt.close()
    print(f"Сохранено: {full_path}")

    # 3. Summary bar plot
    hc_summary_year_1 = hc_outliers_year_1.sum().sort_values(ascending=False).head(15)
    hc_summary_year_2 = hc_outliers_year_2.sum().sort_values(ascending=False).head(15)

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    hc_summary_year_1.plot(kind='barh', ax=axes[0], color='coral')
    axes[0].set_xlabel('Number of Outlier Probes')
    axes[0].set_title(f'{year_1}: Углеводороды с наибольшим числом выбросов', fontsize=12, fontweight='bold')
    axes[0].grid(True, alpha=0.3, axis='x')

    hc_summary_year_2.plot(kind='barh', ax=axes[1], color='coral')
    axes[1].set_xlabel('Number of Outlier Probes')
    axes[1].set_title(f'{year_2}: Углеводороды с наибольшим числом выбросов', fontsize=12, fontweight='bold')
    axes[1].grid(True, alpha=0.3, axis='x')

    plt.suptitle('Сводка по выбросам углеводородов', fontsize=14, fontweight='bold')
    plt.tight_layout()

    full_path = os.path.join(output_dir, 'outlier_summary.png')
    plt.savefig(full_path, dpi=FIG_DPI, bbox_inches='tight')
    plt.close()
    print(f"Сохранено: {full_path}")


def create_outlier_report(sample_outliers_year_1, sample_outliers_year_2,
                          hc_outliers_year_1, hc_outliers_year_2,
                          hc_outlier_summary_year_1, hc_outlier_summary_year_2,
                          year_1, year_2, output_dir):
    """Создание отчёта по выбросам"""

    report_path = os.path.join(output_dir, 'outlier_detection_report.xlsx')

    with pd.ExcelWriter(report_path, engine='openpyxl') as writer:
        probes_year_1 = pd.DataFrame({
            'Probe_Index': range(len(sample_outliers_year_1)),
            'Is_Outlier': sample_outliers_year_1,
            'Year': year_1
        })
        probes_year_1.to_excel(writer, sheet_name=f'Sample_Outliers_{year_1}', index=False)

        probes_year_2 = pd.DataFrame({
            'Probe_Index': range(len(sample_outliers_year_2)),
            'Is_Outlier': sample_outliers_year_2,
            'Year': year_2
        })
        probes_year_2.to_excel(writer, sheet_name=f'Sample_Outliers_{year_2}', index=False)

        hc_outlier_summary_year_1.to_excel(writer, sheet_name=f'HC_Outliers_Summary_{year_1}', index=False)
        hc_outlier_summary_year_2.to_excel(writer, sheet_name=f'HC_Outliers_Summary_{year_2}', index=False)

        hc_outliers_year_1.to_excel(writer, sheet_name=f'HC_Outliers_Detail_{year_1}')
        hc_outliers_year_2.to_excel(writer, sheet_name=f'HC_Outliers_Detail_{year_2}')

        recommendations = pd.DataFrame({
            'Тип выброса': [f'Пробы-выбросы {year_1}', f'Пробы-выбросы {year_2}',
                            f'УВ с >30% выбросов {year_1}', f'УВ с >30% выбросов {year_2}'],
            'Количество': [
                sample_outliers_year_1.sum(),
                sample_outliers_year_2.sum(),
                len(hc_outlier_summary_year_1[hc_outlier_summary_year_1['outlier_ratio'] > 0.3]),
                len(hc_outlier_summary_year_2[hc_outlier_summary_year_2['outlier_ratio'] > 0.3])
            ],
            'Рекомендация': [
                'Проверить аналитически, рассмотреть исключение',
                'Проверить аналитически, рассмотреть исключение',
                'Исключить из анализа или заменить на median',
                'Исключить из анализа или заменить на median'
            ]
        })
        recommendations.to_excel(writer, sheet_name='Recommendations', index=False)

    print(f"\nОтчёт по выбросам сохранён: {report_path}")


# =============================================================================
# 5. CLR СТАБИЛЬНОСТЬ
# =============================================================================

def calculate_clr_stability(clr_year_1, clr_year_2, hc_columns):
    """Расчёт стабильности на основе CLR-трансформированных данных"""

    results = []

    for hc in hc_columns:
        y1 = clr_year_1[hc].values
        y2 = clr_year_2[hc].values

        ks_stat, ks_p = ks_2samp(y1, y2)
        mw_stat, mw_p = mannwhitneyu(y1, y2, alternative='two-sided')
        cohens_d_val = calculate_cohens_d(y1, y2)

        median_1 = np.median(y1)
        median_2 = np.median(y2)
        median_ratio = median_2 / median_1 if median_1 != 0 else np.nan

        min_val = min(y1.min(), y2.min())
        max_val = max(y1.max(), y2.max())
        bins = np.linspace(min_val, max_val, 50)

        hist_1, _ = np.histogram(y1, bins=bins, density=True)
        hist_2, _ = np.histogram(y2, bins=bins, density=True)

        bc = np.sum(np.sqrt(np.abs(hist_1 * hist_2))) / len(bins)
        overlap_score = max(0, min(1, bc))

        median_stability = 1 / (1 + abs(np.log10(abs(median_ratio) + EPSILON)))
        ks_stability = 1 - ks_stat
        overlap_stability = overlap_score
        effect_size_stability = 1 / (1 + abs(cohens_d_val))

        clr_stability_score = (
                CLR_WEIGHT_MEDIAN * median_stability +
                CLR_WEIGHT_KS * ks_stability +
                CLR_WEIGHT_OVERLAP * overlap_stability +
                CLR_WEIGHT_EFFECT_SIZE * effect_size_stability
        )

        if clr_stability_score >= STABILITY_HIGH_THRESHOLD and ks_p >= 0.05:
            stability_class = "HIGH"
        elif clr_stability_score >= STABILITY_MEDIUM_THRESHOLD and ks_p >= 0.01:
            stability_class = "MEDIUM"
        else:
            stability_class = "LOW"

        results.append({
            'hydrocarbon': hc,
            'clr_median_ratio': median_ratio,
            'cohens_d': cohens_d_val,
            'ks_statistic': ks_stat,
            'ks_pvalue': ks_p,
            'overlap_score': overlap_score,
            'clr_stability_score': clr_stability_score,
            'clr_stability_class': stability_class
        })

    clr_results_df = pd.DataFrame(results)
    clr_results_df = clr_results_df.sort_values('clr_stability_score', ascending=False)
    clr_results_df['clr_rank'] = range(1, len(clr_results_df) + 1)

    return clr_results_df


# =============================================================================
# 6. COHEN'S D EFFECT SIZE (ROBUST)
# =============================================================================

def calculate_cohens_d(y1, y2, method='robust'):
    """Расчёт effect size. ROBUST VERSION: Median + MAD"""

    if method == 'classic':
        n1, n2 = len(y1), len(y2)
        var1, var2 = np.var(y1, ddof=1), np.var(y2, ddof=1)
        pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
        if pooled_std < EPSILON:
            pooled_std = EPSILON
        d = (np.mean(y1) - np.mean(y2)) / pooled_std
    else:
        median_1 = np.median(y1)
        median_2 = np.median(y2)

        mad_1 = np.median(np.abs(y1 - median_1))
        mad_2 = np.median(np.abs(y2 - median_2))

        mad_1_scaled = mad_1 * 1.4826
        mad_2_scaled = mad_2 * 1.4826

        pooled_mad = np.sqrt((mad_1_scaled ** 2 + mad_2_scaled ** 2) / 2)

        if pooled_mad < EPSILON:
            pooled_mad = EPSILON

        d = (median_1 - median_2) / pooled_mad

    return d


def interpret_cohens_d(d):
    """Интерпретация Cohen's d"""
    abs_d = abs(d)
    if abs_d < 0.2:
        return "negligible"
    elif abs_d < 0.5:
        return "small"
    elif abs_d < 0.8:
        return "medium"
    else:
        return "large"


# =============================================================================
# 7. CORRELATION PATTERN STABILITY
# =============================================================================

def correlation_pattern_stability(proportions_year_1, proportions_year_2, hc_columns):
    """Сравнение корреляционных паттернов между годами"""

    corr_year_1 = proportions_year_1[hc_columns].corr(method='spearman')
    corr_year_2 = proportions_year_2[hc_columns].corr(method='spearman')

    pattern_results = []

    for hc in hc_columns:
        corr_1 = corr_year_1[hc].drop(hc).values
        corr_2 = corr_year_2[hc].drop(hc).values

        pattern_corr, pattern_p = spearmanr(corr_1, corr_2)
        mean_diff = np.mean(np.abs(corr_1 - corr_2))

        pattern_results.append({
            'hydrocarbon': hc,
            'pattern_correlation': pattern_corr if not np.isnan(pattern_corr) else 0,
            'pattern_pvalue': pattern_p if not np.isnan(pattern_p) else 1,
            'pattern_mean_diff': mean_diff,
            'pattern_stability_score': pattern_corr if not np.isnan(pattern_corr) else 0
        })

    pattern_df = pd.DataFrame(pattern_results)
    pattern_df = pattern_df.sort_values('pattern_stability_score', ascending=False)

    return pattern_df, corr_year_1, corr_year_2


# =============================================================================
# 8. FEATURE IMPORTANCE
# =============================================================================

def year_prediction_importance(log_proportions_year_1, log_proportions_year_2, hc_columns):
    """Оценка важности признаков для предсказания года измерения"""

    X_year_1 = log_proportions_year_1[hc_columns].values
    X_year_2 = log_proportions_year_2[hc_columns].values

    X = np.vstack([X_year_1, X_year_2])
    y = np.array([0] * len(X_year_1) + [1] * len(X_year_2))

    rf = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=RANDOM_STATE, n_jobs=-1)
    rf.fit(X, y)

    from sklearn.inspection import permutation_importance
    perm_importance = permutation_importance(rf, X, y, n_repeats=10, random_state=RANDOM_STATE, n_jobs=-1)

    importance = rf.feature_importances_

    importance_df = pd.DataFrame({
        'hydrocarbon': hc_columns,
        'rf_importance': importance,
        'perm_importance_mean': perm_importance.importances_mean,
        'perm_importance_std': perm_importance.importances_std,
        'stability_from_importance': 1 - importance
    })

    importance_df = importance_df.sort_values('stability_from_importance', ascending=False)

    return importance_df, rf


# =============================================================================
# 9. BOOTSTRAP CONFIDENCE INTERVALS
# =============================================================================

def bootstrap_stability_ci(log_proportions_year_1, log_proportions_year_2, hc_columns,
                           n_iterations=BOOTSTRAP_ITERATIONS):
    """Bootstrap для оценки доверительных интервалов stability_score"""

    bootstrap_scores = {hc: [] for hc in hc_columns}

    for i in range(n_iterations):
        sample_year_1 = resample(log_proportions_year_1, replace=True, n_samples=len(log_proportions_year_1),
                                 random_state=i)
        sample_year_2 = resample(log_proportions_year_2, replace=True, n_samples=len(log_proportions_year_2),
                                 random_state=i + 1000)

        for hc in hc_columns:
            y1 = sample_year_1[hc].values
            y2 = sample_year_2[hc].values
            ks_stat, _ = ks_2samp(y1, y2)
            bootstrap_scores[hc].append(1 - ks_stat)

    ci_results = []
    for hc in hc_columns:
        scores = bootstrap_scores[hc]
        ci_results.append({
            'hydrocarbon': hc,
            'bootstrap_mean': np.mean(scores),
            'bootstrap_std': np.std(scores),
            'ci_lower': np.percentile(scores, 2.5),
            'ci_upper': np.percentile(scores, 97.5),
            'ci_width': np.percentile(scores, 97.5) - np.percentile(scores, 2.5),
            'ci_reliability': 1 / (1 + np.percentile(scores, 97.5) - np.percentile(scores, 2.5))
        })

    ci_df = pd.DataFrame(ci_results)
    ci_df = ci_df.sort_values('ci_reliability', ascending=False)

    return ci_df


# =============================================================================
# 10. PCA LOADINGS STABILITY
# =============================================================================

def pca_loadings_stability(clr_year_1, clr_year_2, hc_columns, n_components=PCA_N_COMPONENTS):
    """Сравнение PCA loadings между годами"""

    scaler_1 = StandardScaler()
    scaler_2 = StandardScaler()
    X_1_scaled = scaler_1.fit_transform(clr_year_1)
    X_2_scaled = scaler_2.fit_transform(clr_year_2)

    pca_1 = PCA(n_components=min(n_components, len(clr_year_1) - 1, len(hc_columns)))
    pca_2 = PCA(n_components=min(n_components, len(clr_year_2) - 1, len(hc_columns)))
    pca_1.fit(X_1_scaled)
    pca_2.fit(X_2_scaled)

    loadings_1 = np.mean(np.abs(pca_1.components_), axis=0)
    loadings_2 = np.mean(np.abs(pca_2.components_), axis=0)

    loadings_corr, _ = spearmanr(loadings_1, loadings_2)

    # Преобразование расстояния PCA в схожесть через экспоненциальное затухание
    loadings_diff = np.abs(loadings_1 - loadings_2)
    alpha = 1.0  # Параметр затухания
    loadings_similarity = np.exp(-alpha * loadings_diff)

    loadings_df = pd.DataFrame({
        'hydrocarbon': hc_columns,
        'loadings_diff': loadings_diff,
        'loadings_stability': loadings_similarity
    })

    loadings_df = loadings_df.sort_values('loadings_stability', ascending=False)

    return loadings_df, loadings_corr, pca_1, pca_2


# =============================================================================
# 11. CONSENSUS RANKING
# =============================================================================

def consensus_ranking(results_dict, method_names, hc_columns, use_variance_weighting=True):
    """Консенсусный рейтинг с автоматической коррекцией весов по вариабельности"""

    merged = pd.DataFrame({'hydrocarbon': hc_columns})

    for method_name in method_names:
        df = results_dict[method_name]
        df_subset = df[['hydrocarbon', 'score']].copy()

        min_score = df_subset['score'].min()
        max_score = df_subset['score'].max()
        if max_score - min_score > 0:
            df_subset['score_normalized'] = (df_subset['score'] - min_score) / (max_score - min_score)
        else:
            df_subset['score_normalized'] = 0.5

        df_subset = df_subset.rename(columns={'score_normalized': f'score_{method_name}'})

        merged = merged.merge(df_subset[['hydrocarbon', f'score_{method_name}']],
                              on='hydrocarbon', how='outer')

    score_cols = [col for col in merged.columns if col.startswith('score_')]

    if use_variance_weighting:
        print("\n" + "=" * 80)
        print("АВТОМАТИЧЕСКАЯ КОРРЕКЦИЯ ВЕСОВ ПО ВАРИАБИЛЬНОСТИ")
        print("=" * 80)

        weights = []
        for col in score_cols:
            std_val = merged[col].std()
            weight = max(0.1, std_val)
            weights.append(weight)
            method_name = col.replace('score_', '')
            print(f"  {method_name:15s}: std={std_val:.4f}, weight={weight:.4f}")

        weights = np.array(weights)
        weights = weights / weights.sum()

        print(f"\n  Нормализованные веса: {weights.round(3)}")
    else:
        weights = [1 / len(score_cols)] * len(score_cols)

    merged['consensus_score'] = sum(merged[col] * w for col, w in zip(score_cols, weights))

    merged['consensus_class'] = merged['consensus_score'].apply(
        lambda x: 'HIGH' if x >= STABILITY_HIGH_THRESHOLD else 'MEDIUM' if x >= STABILITY_MEDIUM_THRESHOLD else 'LOW'
    )

    merged = merged.sort_values('consensus_score', ascending=False)
    merged['consensus_rank'] = range(1, len(merged) + 1)

    return merged


# =============================================================================
# 12. АНАЛИЗ СООТНОШЕНИЙ
# =============================================================================

def calculate_ratio_stability_metrics(proportions_year_1, proportions_year_2, hc_columns):
    """Расчёт метрик стабильности для пропорций"""

    results = []

    for hc in hc_columns:
        y1 = proportions_year_1[hc].values
        y2 = proportions_year_2[hc].values

        y1_log = np.log(y1 + EPSILON)
        y2_log = np.log(y2 + EPSILON)

        ks_stat, ks_p = ks_2samp(y1_log, y2_log)
        cohens_d_val = calculate_cohens_d(y1_log, y2_log)

        median_1 = np.median(y1)
        median_2 = np.median(y2)
        median_ratio = median_2 / median_1 if median_1 > 0 else np.nan

        min_val = min(y1_log.min(), y2_log.min())
        max_val = max(y1_log.max(), y2_log.max())
        bins = np.linspace(min_val, max_val, 50)

        hist_1, _ = np.histogram(y1_log, bins=bins, density=True)
        hist_2, _ = np.histogram(y2_log, bins=bins, density=True)

        bc = np.sum(np.sqrt(np.abs(hist_1 * hist_2))) / len(bins)
        overlap_score = max(0, min(1, bc))

        median_stability = 1 / (1 + abs(np.log10(median_ratio + EPSILON)))
        ks_stability = 1 - ks_stat
        overlap_stability = overlap_score
        effect_size_stability = 1 / (1 + abs(cohens_d_val))

        ratio_stability_score = (
                RATIO_WEIGHT_MEDIAN * median_stability +
                RATIO_WEIGHT_KS * ks_stability +
                RATIO_WEIGHT_OVERLAP * overlap_stability +
                RATIO_WEIGHT_EFFECT_SIZE * effect_size_stability
        )

        if ratio_stability_score >= STABILITY_HIGH_THRESHOLD and ks_p >= 0.05:
            ratio_class = "HIGH"
        elif ratio_stability_score >= STABILITY_MEDIUM_THRESHOLD and ks_p >= 0.01:
            ratio_class = "MEDIUM"
        else:
            ratio_class = "LOW"

        results.append({
            'hydrocarbon': hc,
            'ratio_median_ratio': median_ratio,
            'ratio_cohens_d': cohens_d_val,
            'ratio_ks_statistic': ks_stat,
            'ratio_ks_pvalue': ks_p,
            'ratio_overlap_score': overlap_score,
            'ratio_stability_score': ratio_stability_score,
            'ratio_stability_class': ratio_class
        })

    ratio_df = pd.DataFrame(results)
    ratio_df = ratio_df.sort_values('ratio_stability_score', ascending=False)
    ratio_df['ratio_rank'] = range(1, len(ratio_df) + 1)

    return ratio_df


# =============================================================================
# 12.1 WASSERSTEIN DISTANCE STABILITY
# =============================================================================

def calculate_wasserstein_stability(clr_year_1, clr_year_2, hc_columns):
    """Расчёт стабильности на основе Wasserstein distance"""

    results = []

    for hc in hc_columns:
        y1 = clr_year_1[hc].values
        y2 = clr_year_2[hc].values

        w_dist = wasserstein_distance(y1, y2)
        w_stability = 1 / (1 + w_dist)

        results.append({
            'hydrocarbon': hc,
            'wasserstein_distance': w_dist,
            'wasserstein_stability_score': w_stability
        })

    w_df = pd.DataFrame(results)
    w_df = w_df.sort_values('wasserstein_stability_score', ascending=False)
    w_df['wasserstein_rank'] = range(1, len(w_df) + 1)

    return w_df


# =============================================================================
# 12.2 PAIRWISE LOG-RATIO STABILITY
# =============================================================================

def calculate_pairwise_logratio_stability(proportions_year_1, proportions_year_2, hc_columns):
    """Стабильность через все pairwise log-ratios (log(i/j))"""

    results = []
    epsilon = 1e-6

    for hc_i in hc_columns:
        logratio_stabs = []

        for hc_j in hc_columns:
            if hc_i == hc_j:
                continue

            logratio_1 = np.log(proportions_year_1[hc_i].values + epsilon) - \
                         np.log(proportions_year_1[hc_j].values + epsilon)
            logratio_2 = np.log(proportions_year_2[hc_i].values + epsilon) - \
                         np.log(proportions_year_2[hc_j].values + epsilon)

            w_dist = wasserstein_distance(logratio_1, logratio_2)
            stab = 1 / (1 + w_dist)
            logratio_stabs.append(stab)

        mean_stab = np.mean(logratio_stabs) if logratio_stabs else 0.5

        results.append({
            'hydrocarbon': hc_i,
            'pairwise_lr_mean_stability': mean_stab,
            'n_ratios': len(logratio_stabs)
        })

    lr_df = pd.DataFrame(results)
    lr_df = lr_df.sort_values('pairwise_lr_mean_stability', ascending=False)
    lr_df['pairwise_lr_rank'] = range(1, len(lr_df) + 1)

    return lr_df


# =============================================================================
# 13. ГРУППИРОВКА ПО КЛАССАМ
# =============================================================================

def classify_hydrocarbons(hc_columns):
    """Классификация углеводородов по химическим классам"""

    classification = {}

    alkenes = ['1-Pentene', '1-Hexene', '1-Heptene', '1-Octene', '1-Nonene', '1-Decene']
    alkanes = ['Pentane', 'Hexane', 'Heptane', 'Octane', 'Nonane', 'Decane',
               'Undecane', 'Dodecane', 'Tridecane', 'Tetradecane', 'Pentadecane',
               'Hexadecane', 'Heptadecane', 'Octadecane']
    branched_alkanes = ['2-Methylpentane', '3-Methylpentane', '2,4-Dimethylpentane',
                        '2-Methylhexane', '3-Methylhexane', '2,5-Dimethylhexane',
                        '3-Methylheptane']
    cycloalkanes = ['Cyclohexane', 'Methylcyclohexane',
                    'cis-1,3-Dimethylcyclopentane', 'trans-1,3-Dimethylcyclopentane',
                    'trans-1,2-Dimethylcyclopentane', 'cis-1,2-Dimethylcyclohexane',
                    'trans-1,2-Dimethylcyclohexane']
    aromatics_mono = ['Benzene', 'Toluene', 'Ethylbenzene', 'm,p-Xylenes', 'o-Xylene',
                      'Propylbenzene', 'Butylbenzene']
    aromatics_poly = ['1,3,5-Trimethylbenzene', '1-Ethyl-4-methylbenzene',
                      '1,2,4-Trimethylbenzene', '1,2,4,5-Tetramethylbenzene']
    biomarkers = ['Pristane', 'Phytane']

    for hc in hc_columns:
        if hc in alkenes:
            classification[hc] = 'Alkenes'
        elif hc in alkanes:
            classification[hc] = 'Alkanes (n-)'
        elif hc in branched_alkanes:
            classification[hc] = 'Alkanes (iso-)'
        elif hc in cycloalkanes:
            classification[hc] = 'Cycloalkanes'
        elif hc in aromatics_mono:
            classification[hc] = 'Aromatics (mono)'
        elif hc in aromatics_poly:
            classification[hc] = 'Aromatics (poly)'
        elif hc in biomarkers:
            classification[hc] = 'Biomarkers'
        else:
            classification[hc] = 'Other'

    return classification


# =============================================================================
# 14. ЕДИНАЯ ПРЕДОБРАБОТКА ДЛЯ ОЦЕНКИ НАБОРА УВ (НОВАЯ ФУНКЦИЯ - ВЕРСИЯ 4.7!)
# =============================================================================

def preprocess_hydrocarbon_subset(proportions_year_1, proportions_year_2, hc_subset):
    """
    ЕДИНАЯ функция предобработки данных для оценки любого набора углеводородов.

    Используется ВСЕМИ алгоритмами оптимизации (greedy, genetic, hybrid) для
    ГАРАНТИИ одинаковой нормировки и CLR-трансформации.

    Композиционный подход:
    1. Выбор подмножества УВ из пропорций
    2. Перенормировка на сумму = 1 (обязательно для композиционных данных!)
    3. CLR-трансформация на перенормированных данных

    Parameters
    ----------
    proportions_year_1, proportions_year_2 : pd.DataFrame
        Пропорции углеводородов (сумма по строке = 1) для двух лет
    hc_subset : list
        Список углеводородов для оценки

    Returns
    -------
    clr_1, clr_2 : np.ndarray
        CLR-трансформированные данные для двух лет
    """
    # ШАГ 1: Выбрать УВ из пропорций (НЕ из CLR!)
    props_1 = proportions_year_1[hc_subset].values.copy()
    props_2 = proportions_year_2[hc_subset].values.copy()

    # ШАГ 2: ПЕРЕНОРМИРОВКА на сумму (композиционность!)
    # Критически важно: при изменении состава УВ сумма пропорций меняется,
    # поэтому нужна повторная нормировка перед CLR
    props_1 = props_1 / props_1.sum(axis=1, keepdims=True)
    props_2 = props_2 / props_2.sum(axis=1, keepdims=True)

    # ШАГ 3: CLR трансформация на ВЫБРАННОМ и ПЕРЕНОРМИРОВАННОМ подмножестве
    clr_1 = clr_transform(pd.DataFrame(props_1, columns=hc_subset))
    clr_2 = clr_transform(pd.DataFrame(props_2, columns=hc_subset))

    return clr_1.values, clr_2.values


# =============================================================================
# 15. ОЦЕНКА КАЧЕСТВА НАБОРА УВ (ИСПОЛЬЗУЕТ ЕДИНУЮ ПРЕДОБРАБОТКУ)
# =============================================================================

def evaluate_hydrocarbon_set(proportions_year_1, proportions_year_2, hc_subset, consensus_df=None):
    """
    Оценка качества набора углеводородов через PCA метрики.

    ИСПОЛЬЗУЕТ функцию preprocess_hydrocarbon_subset() для гарантии
    консистентной предобработки во всех алгоритмах оптимизации.
    """

    if len(hc_subset) < 2:
        return {
            'centroid_distance': np.inf,
            'variance_ratio_score': 0,
            'density_similarity': 0,
            'quality_score': 0,
            'n_hydrocarbons': len(hc_subset)
        }

    # ==========================================================================
    # ЕДИНАЯ ПРЕДОБРАБОТКА (через выделенную функцию)
    # ==========================================================================
    clr_1, clr_2 = preprocess_hydrocarbon_subset(proportions_year_1, proportions_year_2, hc_subset)

    # ==========================================================================
    # PCA на CLR данных
    # ==========================================================================
    X_combined = np.vstack([clr_1, clr_2])
    scaler = StandardScaler()
    X_combined_scaled = scaler.fit_transform(X_combined)
    pca = PCA(n_components=2)
    pca_combined = pca.fit_transform(X_combined_scaled)

    pca_1 = pca_combined[:len(clr_1), :]
    pca_2 = pca_combined[len(clr_1):, :]

    # ==========================================================================
    # Метрики качества
    # ==========================================================================
    centroid_1 = pca_1.mean(axis=0)
    centroid_2 = pca_2.mean(axis=0)
    centroid_distance = np.sqrt(np.sum((centroid_1 - centroid_2) ** 2))

    var_1 = np.trace(np.cov(pca_1, rowvar=False))
    var_2 = np.trace(np.cov(pca_2, rowvar=False))
    variance_ratio = max(var_1, var_2) / min(var_1, var_2) if min(var_1, var_2) > 1e-10 else np.inf
    variance_ratio_score = 1 / (1 + np.log(variance_ratio))

    x_min, x_max = min(pca_1[:, 0].min(), pca_2[:, 0].min()), max(pca_1[:, 0].max(), pca_2[:, 0].max())
    y_min, y_max = min(pca_1[:, 1].min(), pca_2[:, 1].min()), max(pca_1[:, 1].max(), pca_2[:, 1].max())

    if x_max - x_min < 1e-10 or y_max - y_min < 1e-10:
        density_similarity = 1.0
    else:
        x_range = x_max - x_min
        y_range = y_max - y_min
        x_min -= 0.1 * x_range
        x_max += 0.1 * x_range
        y_min -= 0.1 * y_range
        y_max += 0.1 * y_range

        xx, yy = np.meshgrid(np.linspace(x_min, x_max, 30), np.linspace(y_min, y_max, 30))
        grid_points = np.vstack([xx.ravel(), yy.ravel()]).T

        def estimate_density_on_grid(points, grid_points, bandwidth=0.5):
            densities = np.zeros(len(grid_points))
            for i, gp in enumerate(grid_points):
                distances = np.sqrt(np.sum((points - gp) ** 2, axis=1))
                kernel_values = np.exp(-0.5 * (distances / bandwidth) ** 2)
                densities[i] = np.mean(kernel_values)
            densities = densities / (np.sum(densities) * (x_max - x_min) / 30 * (y_max - y_min) / 30 + 1e-10)
            return densities

        adaptive_bandwidth = 0.5 * np.sqrt(len(pca_1) + len(pca_2)) / np.sqrt(20)
        adaptive_bandwidth = np.clip(adaptive_bandwidth, 0.3, 1.0)

        density_1_grid = estimate_density_on_grid(pca_1, grid_points, bandwidth=adaptive_bandwidth)
        density_2_grid = estimate_density_on_grid(pca_2, grid_points, bandwidth=adaptive_bandwidth)

        bc = np.sum(np.sqrt(density_1_grid * density_2_grid)) * (x_max - x_min) / 30 * (y_max - y_min) / 30
        density_similarity = np.clip(bc, 0, 1)

    centroid_score = 1 / (1 + centroid_distance)
    quality_score = centroid_score * QUALITY_WEIGHT_CENTROID + variance_ratio_score * QUALITY_WEIGHT_VARIANCE + density_similarity * QUALITY_WEIGHT_DENSITY

    return {
        'centroid_distance': centroid_distance,
        'variance_ratio_score': variance_ratio_score,
        'density_similarity': density_similarity,
        'quality_score': quality_score,
        'n_hydrocarbons': len(hc_subset),
        'clr_1': clr_1,
        'clr_2': clr_2
    }


# =============================================================================
# 16. АЛГОРИТМЫ ОПТИМИЗАЦИИ (ВСЕ ИСПОЛЬЗУЮТ ЕДИНУЮ ПРЕДОБРАБОТКУ)
# =============================================================================

def optimize_greedy(proportions_year_1, proportions_year_2, candidate_hc, consensus_df,
                    min_hc=MIN_HC, max_iterations=GREEDY_MAX_ITERATIONS):
    """Жадная оптимизация: удаляем наименее стабильные УВ пока Quality Score растёт"""

    # ==========================================================================
    # ИСПРАВЛЕНИЕ ВЕРСИИ 4.8: Проверка и корректировка min_hc
    # ==========================================================================
    original_min_hc = min_hc
    if len(candidate_hc) < min_hc:
        print(f"\n⚠️  ВНИМАНИЕ: Кандидатов ({len(candidate_hc)}) меньше MIN_HC ({min_hc})")
        min_hc = max(2, len(candidate_hc))  # Минимум 2 УВ для работы PCA
        print(f"   MIN_HC автоматически скорректирован: {original_min_hc} → {min_hc}")

    current_hc = candidate_hc.copy()
    history = []

    # Начальная оценка (использует preprocess_hydrocarbon_subset внутри evaluate_)
    metrics = evaluate_hydrocarbon_set(proportions_year_1, proportions_year_2, current_hc, consensus_df)
    history.append({
        'iteration': 0,
        'n_hydrocarbons': len(current_hc),
        'centroid_distance': metrics['centroid_distance'],
        'variance_ratio_score': metrics['variance_ratio_score'],
        'density_similarity': metrics['density_similarity'],
        'quality_score': metrics['quality_score'],
        'removed_hc': None,
        'algorithm': 'Greedy'
    })

    print(f"\nНачальный набор: {len(current_hc)} УВ")
    print(f"  Centroid distance: {metrics['centroid_distance']:.4f}")
    print(f"  Variance ratio score: {metrics['variance_ratio_score']:.4f}")
    print(f"  Density similarity: {metrics['density_similarity']:.4f}")
    print(f"  Quality score: {metrics['quality_score']:.4f}")

    for i in range(max_iterations):
        if len(current_hc) <= min_hc:
            break

        # Сортируем по consensus score (наименее стабильные в конце)
        consensus_sorted = consensus_df.set_index('hydrocarbon').loc[current_hc]
        consensus_sorted = consensus_sorted.sort_values('consensus_score', ascending=True)

        # Пробуем удалить 1-3 наименее стабильных (из конфигурации)
        best_score = history[-1]['quality_score']
        best_removal = None
        best_metrics = None

        for n_remove in GREEDY_N_REMOVE_OPTIONS:
            if len(current_hc) - n_remove < min_hc:
                continue

            candidates = consensus_sorted.head(n_remove).index.tolist()
            test_hc = [hc for hc in current_hc if hc not in candidates]

            # ВСЕ оценки используют ЕДИНУЮ предобработку через evaluate_hydrocarbon_set
            metrics = evaluate_hydrocarbon_set(proportions_year_1, proportions_year_2, test_hc, consensus_df)

            if metrics['quality_score'] > best_score:
                best_score = metrics['quality_score']
                best_removal = candidates
                best_metrics = metrics

        if best_removal is None:
            print(f"\nИтерация {i + 1}: Улучшений нет, останавливаемся")
            break

        # Удаляем наименее стабильные
        current_hc = [hc for hc in current_hc if hc not in best_removal]

        history.append({
            'iteration': i + 1,
            'n_hydrocarbons': len(current_hc),
            'centroid_distance': best_metrics['centroid_distance'],
            'variance_ratio_score': best_metrics['variance_ratio_score'],
            'density_similarity': best_metrics['density_similarity'],
            'quality_score': best_metrics['quality_score'],
            'removed_hc': best_removal,
            'algorithm': 'Greedy'
        })

        print(f"\nИтерация {i + 1}: Удалено {best_removal}")
        print(f"  Осталось УВ: {len(current_hc)}")
        print(f"  Quality score: {best_metrics['quality_score']:.4f}")

    return current_hc, history


def optimize_genetic(proportions_year_1, proportions_year_2, hc_columns, consensus_df,
                     pop_size=GA_POP_SIZE, generations=GA_GENERATIONS, mutation_rate=GA_MUTATION_RATE,
                     min_hc=MIN_HC, max_hc=MAX_HC, initial_individuals=None):
    """Генетический алгоритм для оптимизации набора УВ"""

    # ==========================================================================
    # ИСПРАВЛЕНИЕ ВЕРСИИ 4.8: Проверка и корректировка min_hc и max_hc
    # ==========================================================================
    original_min_hc = min_hc
    original_max_hc = max_hc
    n_available = len(hc_columns)

    # Проверка 1: min_hc не может быть >= n_available
    if min_hc >= n_available:
        print(f"\n⚠️  ВНИМАНИЕ: MIN_HC ({min_hc}) >= доступных УВ ({n_available})")
        min_hc = max(2, n_available - 1)  # Оставляем минимум 2 УВ
        print(f"   MIN_HC автоматически скорректирован: {original_min_hc} → {min_hc}")

    # Проверка 2: max_hc не может быть > n_available
    if max_hc > n_available:
        print(f"\n⚠️  ВНИМАНИЕ: MAX_HC ({max_hc}) > доступных УВ ({n_available})")
        max_hc = n_available
        print(f"   MAX_HC автоматически скорректирован: {original_max_hc} → {max_hc}")

    # Проверка 3: min_hc не может быть > max_hc
    if min_hc > max_hc:
        print(f"\n⚠️  ВНИМАНИЕ: MIN_HC ({min_hc}) > MAX_HC ({max_hc})")
        min_hc = max(2, max_hc - 1)
        print(f"   MIN_HC автоматически скорректирован: {original_min_hc} → {min_hc}")

    print(f"\nГенетический алгоритм: pop_size={pop_size}, generations={generations}")
    print(f"  Доступно УВ: {n_available}")
    print(f"  Диапазон размера индивидуума: [{min_hc}, {max_hc}]")

    # Инициализация популяции
    population = []

    # Добавляем начальные решения (если есть)
    if initial_individuals:
        for individual in initial_individuals[:pop_size // 5]:
            # Фильтруем индивидуума по новым ограничениям
            individual = [hc for hc in individual if hc in hc_columns]
            if min_hc <= len(individual) <= max_hc:
                population.append(individual.copy())
            elif len(individual) > max_hc:
                # Обрезаем до max_hc
                population.append(individual[:max_hc])
            elif len(individual) >= min_hc:
                population.append(individual.copy())

    # Заполняем остальную популяцию случайными наборами
    while len(population) < pop_size:
        # ИСПРАВЛЕНО: Проверка диапазона для randint
        if max_hc > min_hc:
            n_select = np.random.randint(min_hc, min(max_hc + 1, n_available + 1))
        else:
            n_select = min_hc  # Если диапазон вырожденный, берём min_hc

        # Защита от выхода за границы
        n_select = min(n_select, n_available)
        n_select = max(n_select, min_hc)

        individual = np.random.choice(hc_columns, n_select, replace=False).tolist()
        population.append(individual)

    best_solution = None
    best_score = -np.inf
    best_metrics = None
    history = []

    for gen in range(generations):
        # Оценка фитнеса - ВСЕ используют ЕДИНУЮ предобработку через evaluate_
        scores = []
        metrics_list = []

        for individual in population:
            if len(individual) < min_hc:
                scores.append(-np.inf)
                metrics_list.append(None)
            else:
                # evaluate_hydrocarbon_set использует preprocess_hydrocarbon_subset
                metrics = evaluate_hydrocarbon_set(proportions_year_1, proportions_year_2, individual, consensus_df)
                scores.append(metrics['quality_score'])
                metrics_list.append(metrics)

        # Сохранение лучшего
        max_idx = np.argmax(scores)
        if scores[max_idx] > best_score:
            best_score = scores[max_idx]
            best_solution = population[max_idx].copy()
            best_metrics = metrics_list[max_idx]

        # История (каждые 5 поколений)
        if gen % 5 == 0 or gen == generations - 1:
            history.append({
                'iteration': gen,
                'n_hydrocarbons': len(best_solution) if best_solution else 0,
                'centroid_distance': best_metrics['centroid_distance'] if best_metrics else np.inf,
                'variance_ratio_score': best_metrics['variance_ratio_score'] if best_metrics else 0,
                'density_similarity': best_metrics['density_similarity'] if best_metrics else 0,
                'quality_score': best_score,
                'removed_hc': None,
                'algorithm': 'Genetic'
            })
            print(f"Поколение {gen}: Best score={best_score:.4f}, n_HC={len(best_solution) if best_solution else 0}")

        # Селекция (турнирная)
        new_population = []
        for _ in range(pop_size):
            i1, i2 = np.random.choice(len(population), 2, replace=False)
            parent = population[i1] if scores[i1] > scores[i2] else population[i2]
            new_population.append(parent.copy())

        # Кроссовер (одноточечный)
        for i in range(0, pop_size, 2):
            if i + 1 < pop_size and np.random.random() > (1 - GA_CROSSOVER_PROBABILITY):
                p1, p2 = new_population[i], new_population[i + 1]

                if len(p1) > 1 and len(p2) > 1:
                    crossover_point = np.random.randint(1, min(len(p1), len(p2)))
                    child1 = list(set(p1[:crossover_point] + p2[crossover_point:]))
                    child2 = list(set(p2[:crossover_point] + p1[crossover_point:]))

                    # Проверка размера
                    if len(child1) >= min_hc:
                        new_population[i] = child1[:max_hc] if len(child1) > max_hc else child1
                    if len(child2) >= min_hc and i + 1 < pop_size:
                        new_population[i + 1] = child2[:max_hc] if len(child2) > max_hc else child2

        # Мутация
        for i in range(pop_size):
            if np.random.random() < mutation_rate:
                # Добавить случайный УВ
                available = [hc for hc in hc_columns if hc not in new_population[i]]
                if available and np.random.random() > 0.5 and len(new_population[i]) < max_hc:
                    new_population[i].append(np.random.choice(available))
                # Удалить случайный УВ
                elif len(new_population[i]) > min_hc:
                    new_population[i].pop(np.random.randint(0, len(new_population[i])))

        population = new_population

    return best_solution, best_score, best_metrics, history


def optimize_hybrid(proportions_year_1, proportions_year_2, hc_columns, consensus_df,
                    min_hc=MIN_HC, max_hc=MAX_HC, pop_size=GA_POP_SIZE, generations=GA_GENERATIONS,
                    mutation_rate=GA_MUTATION_RATE):
    """Гибридная оптимизация: Жадный + Генетический"""

    print("\n" + "=" * 80)
    print("ГИБРИДНАЯ ОПТИМИЗАЦИЯ: Жадный + Генетический")
    print("=" * 80)

    # ==========================================================================
    # ИСПРАВЛЕНИЕ ВЕРСИИ 4.8: Проверка и корректировка параметров
    # ==========================================================================
    n_available = len(hc_columns)
    if min_hc >= n_available:
        print(f"\n⚠️  ВНИМАНИЕ: MIN_HC ({min_hc}) >= доступных УВ ({n_available})")
        min_hc = max(2, n_available - 1)
        print(f"   MIN_HC автоматически скорректирован для гибридного режима")

    # Шаг 1: Жадная оптимизация (использует единую предобработку)
    print("\n[1/3] Жадная оптимизация...")
    greedy_hc, greedy_history = optimize_greedy(
        proportions_year_1, proportions_year_2, hc_columns, consensus_df,
        min_hc=min_hc, max_iterations=GREEDY_HYBRID_ITERATIONS)

    greedy_metrics = evaluate_hydrocarbon_set(proportions_year_1, proportions_year_2, greedy_hc, consensus_df)
    print(f"\nЖадный результат: score={greedy_metrics['quality_score']:.4f}, n_HC={len(greedy_hc)}")

    # Шаг 2: Генетический алгоритм с жадным решением в начальной популяции
    # (также использует единую предобработку)
    print("\n[2/3] Генетический алгоритм...")
    ga_hc, ga_score, ga_metrics, ga_history = optimize_genetic(
        proportions_year_1, proportions_year_2, hc_columns, consensus_df,
        pop_size=pop_size, generations=generations, mutation_rate=mutation_rate,
        min_hc=min_hc, max_hc=max_hc,
        initial_individuals=[greedy_hc])

    print(f"\nГА результат: score={ga_score:.4f}, n_HC={len(ga_hc)}")

    # Шаг 3: Выбираем лучшее
    print("\n[3/3] Выбор лучшего решения...")
    if ga_score > greedy_metrics['quality_score']:
        print(
            f"\n✅ ГА улучшил решение: {greedy_metrics['quality_score']:.4f} → {ga_score:.4f} (+{(ga_score - greedy_metrics['quality_score']) * 100:.1f}%)")
        combined_history = greedy_history + ga_history
        for h in combined_history:
            h['algorithm'] = 'Hybrid'
        return ga_hc, ga_score, ga_metrics, combined_history, 'Genetic'
    else:
        print(f"\n✅ Жадный алгоритм оказался лучше: {greedy_metrics['quality_score']:.4f}")
        for h in greedy_history:
            h['algorithm'] = 'Hybrid'
        return greedy_hc, greedy_metrics['quality_score'], greedy_metrics, greedy_history, 'Greedy'


def optimize_hydrocarbon_set(proportions_year_1, proportions_year_2, candidate_hc, consensus_df,
                             min_hc=MIN_HC, max_iterations=MAX_ITERATIONS,
                             algorithm=OPTIMIZATION_ALGORITHM, **kwargs):
    """Универсальная функция оптимизации с выбором алгоритма"""

    if algorithm == 'greedy':
        return optimize_greedy(proportions_year_1, proportions_year_2, candidate_hc, consensus_df,
                               min_hc=min_hc, max_iterations=max_iterations)

    elif algorithm == 'genetic':
        pop_size = kwargs.get('pop_size', GA_POP_SIZE)
        generations = kwargs.get('generations', max_iterations)
        mutation_rate = kwargs.get('mutation_rate', GA_MUTATION_RATE)
        max_hc = kwargs.get('max_hc', MAX_HC)

        hc, score, metrics, history = optimize_genetic(
            proportions_year_1, proportions_year_2, candidate_hc, consensus_df,
            pop_size=pop_size, generations=generations, mutation_rate=mutation_rate,
            min_hc=min_hc, max_hc=max_hc)

        return hc, history

    elif algorithm == 'hybrid':
        pop_size = kwargs.get('pop_size', GA_POP_SIZE)
        generations = kwargs.get('generations', max_iterations)
        mutation_rate = kwargs.get('mutation_rate', GA_MUTATION_RATE)
        max_hc = kwargs.get('max_hc', MAX_HC)

        hc, score, metrics, history, best_algo = optimize_hybrid(
            proportions_year_1, proportions_year_2, candidate_hc, consensus_df,
            min_hc=min_hc, max_hc=max_hc,
            pop_size=pop_size, generations=generations, mutation_rate=mutation_rate)

        return hc, history

    else:
        raise ValueError(f"Unknown algorithm: {algorithm}. Choose from: greedy, genetic, hybrid")


# =============================================================================
# 17. ВИЗУАЛИЗАЦИЯ (ОСНОВНАЯ) - ДИНАМИЧЕСКАЯ
# =============================================================================

def plot_method_comparison(all_scores_df, enabled_methods, output_dir, output_path='method_comparison.png'):
    """Сравнение всех методов анализа (только включённые методы)"""

    methods = [col for col in all_scores_df.columns if 'score' in col and 'consensus' not in col]

    # Маппинг имён колонок к ключам METHODS_CONFIG
    method_key_map = {
        'clr_score': 'clr',
        'ratio_score': 'ratio',
        'pattern_score': 'pattern',
        'importance_score': 'importance',
        'bootstrap_score': 'bootstrap',
        'pca_score': 'pca',
        'cohens_d_score': 'cohens_d',
        'wasserstein_score': 'wasserstein',
        'pairwise_score': 'pairwise'
    }

    # Фильтруем методы по METHODS_CONFIG (исправленная логика)
    enabled_keys = [k for k, v in enabled_methods.items() if v]
    filtered_methods = []
    for method in methods:
        key = method_key_map.get(method, None)
        if key and key in enabled_keys:
            filtered_methods.append(method)

    methods = filtered_methods

    if len(all_scores_df) == 0 or len(methods) == 0:
        print("WARNING: Нет данных для построения графика!")
        return

    x = np.arange(len(all_scores_df))
    width = 0.15

    fig, ax = plt.subplots(figsize=(16, 10))

    for i, method in enumerate(methods):
        values = all_scores_df[method].values
        nan_count = np.sum(np.isnan(values))
        if nan_count > 0:
            values = np.nan_to_num(values, nan=0.5)
        ax.bar(x + i * width, values, width, label=method, alpha=0.7)

    ax.set_xlabel('Hydrocarbon Index', fontsize=12)
    ax.set_ylabel('Stability Score', fontsize=12)
    ax.set_title(f'Сравнение stability_score по выбранным методам ({len(methods)} методов)', fontsize=14,
                 fontweight='bold')
    ax.set_xticks(x + width * len(methods) / 2)
    ax.set_xticklabels(all_scores_df['hydrocarbon'].values, rotation=90, fontsize=7)
    ax.legend()
    ax.set_ylim(0, 1)
    ax.axhline(y=STABILITY_HIGH_THRESHOLD, color='green', linestyle='--', alpha=0.5, label='High stability')
    ax.axhline(y=STABILITY_MEDIUM_THRESHOLD, color='orange', linestyle='--', alpha=0.5, label='Medium stability')
    ax.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()

    full_path = os.path.join(output_dir, output_path)
    plt.savefig(full_path, dpi=FIG_DPI, bbox_inches='tight')
    plt.close()
    print(f"Сохранено: {full_path}")


def plot_consensus_ranking(consensus_df, output_dir, output_path='consensus_ranking.png'):
    """Визуализация консенсусного рейтинга"""

    plt.figure(figsize=(14, 12))

    sorted_df = consensus_df.sort_values('consensus_score', ascending=True)

    colors = ['green' if x == 'HIGH' else 'orange' if x == 'MEDIUM' else 'red'
              for x in sorted_df['consensus_class']]

    bars = plt.barh(range(len(sorted_df)), sorted_df['consensus_score'].values,
                    color=colors, alpha=0.7)

    plt.yticks(range(len(sorted_df)), sorted_df['hydrocarbon'].values, fontsize=8)
    plt.xlabel('Consensus Stability Score (0-1)', fontsize=12)
    plt.title(f'Консенсусный рейтинг стабильности углеводородов\n{year_1} vs {year_2}',
              fontsize=14, fontweight='bold')
    plt.xlim(0, 1)
    plt.axvline(x=STABILITY_HIGH_THRESHOLD, color='green', linestyle='--', alpha=0.5, label='High stability')
    plt.axvline(x=STABILITY_MEDIUM_THRESHOLD, color='orange', linestyle='--', alpha=0.5, label='Medium stability')
    plt.legend()
    plt.grid(True, alpha=0.3, axis='x')
    plt.tight_layout()

    full_path = os.path.join(output_dir, output_path)
    plt.savefig(full_path, dpi=FIG_DPI, bbox_inches='tight')
    plt.close()
    print(f"Сохранено: {full_path}")


def plot_cohens_d_distribution(cohens_d_results, output_dir, output_path='cohens_d_distribution.png'):
    """Распределение Cohen's d effect sizes"""

    plt.figure(figsize=(12, 8))

    d_values = cohens_d_results['cohens_d'].values

    plt.hist(d_values, bins=20, alpha=0.7, color='steelblue', edgecolor='black')

    plt.axvline(x=-0.8, color='red', linestyle='--', linewidth=2, label='Large effect')
    plt.axvline(x=-0.5, color='orange', linestyle='--', linewidth=2, label='Medium effect')
    plt.axvline(x=-0.2, color='yellow', linestyle='--', linewidth=2, label='Small effect')
    plt.axvline(x=0.2, color='yellow', linestyle='--', linewidth=2)
    plt.axvline(x=0.5, color='orange', linestyle='--', linewidth=2)
    plt.axvline(x=0.8, color='red', linestyle='--', linewidth=2)

    plt.xlabel("Cohen's d (Robust: Median + MAD)", fontsize=12)
    plt.ylabel('Number of Hydrocarbons', fontsize=12)
    plt.title(f'Распределение Robust Effect Size между {year_1} и {year_2}', fontsize=14, fontweight='bold')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    full_path = os.path.join(output_dir, output_path)
    plt.savefig(full_path, dpi=FIG_DPI, bbox_inches='tight')
    plt.close()
    print(f"Сохранено: {full_path}")


def plot_bootstrap_ci(bootstrap_df, output_dir, output_path='bootstrap_ci.png'):
    """Визуализация Bootstrap доверительных интервалов"""

    plt.figure(figsize=(14, 10))

    sorted_df = bootstrap_df.sort_values('bootstrap_mean', ascending=True)

    y = range(len(sorted_df))

    plt.errorbar(sorted_df['bootstrap_mean'].values, y,
                 xerr=[sorted_df['bootstrap_mean'].values - sorted_df['ci_lower'].values,
                       sorted_df['ci_upper'].values - sorted_df['bootstrap_mean'].values],
                 fmt='o', capsize=5, alpha=0.6, color='steelblue')

    plt.yticks(y, sorted_df['hydrocarbon'].values, fontsize=7)
    plt.xlabel('Bootstrap Mean Stability Score', fontsize=12)
    plt.title(f'Bootstrap 95% Confidence Intervals для stability_score\n{year_1} vs {year_2}', fontsize=14,
              fontweight='bold')
    plt.xlim(0, 1)
    plt.axvline(x=STABILITY_HIGH_THRESHOLD, color='green', linestyle='--', alpha=0.5)
    plt.axvline(x=STABILITY_MEDIUM_THRESHOLD, color='orange', linestyle='--', alpha=0.5)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    full_path = os.path.join(output_dir, output_path)
    plt.savefig(full_path, dpi=FIG_DPI, bbox_inches='tight')
    plt.close()
    print(f"Сохранено: {full_path}")


def plot_feature_importance(importance_df, output_dir, output_path='feature_importance.png'):
    """Визуализация важности признаков"""

    plt.figure(figsize=(14, 10))

    sorted_df = importance_df.sort_values('rf_importance', ascending=True)

    colors = ['green' if x < 0.02 else 'orange' if x < 0.04 else 'red'
              for x in sorted_df['rf_importance'].values]

    bars = plt.barh(range(len(sorted_df)), sorted_df['rf_importance'].values,
                    color=colors, alpha=0.7)

    plt.yticks(range(len(sorted_df)), sorted_df['hydrocarbon'].values, fontsize=8)
    plt.xlabel('Random Forest Feature Importance', fontsize=12)
    plt.title(f'Важность углеводородов для предсказания года измерения\n(меньше = стабильнее)\n{year_1} vs {year_2}',
              fontsize=14, fontweight='bold')
    plt.xlim(0, sorted_df['rf_importance'].max() * 1.2)
    plt.axvline(x=0.02, color='green', linestyle='--', alpha=0.5, label='Low importance (stable)')
    plt.axvline(x=0.04, color='orange', linestyle='--', alpha=0.5, label='Medium importance')
    plt.legend()
    plt.grid(True, alpha=0.3, axis='x')
    plt.tight_layout()

    full_path = os.path.join(output_dir, output_path)
    plt.savefig(full_path, dpi=FIG_DPI, bbox_inches='tight')
    plt.close()
    print(f"Сохранено: {full_path}")


def plot_pca_loadings(loadings_df, output_dir, output_path='pca_loadings.png'):
    """Визуализация стабильности PCA loadings"""

    plt.figure(figsize=(14, 8))

    sorted_df = loadings_df.sort_values('loadings_diff', ascending=True)

    x = range(len(sorted_df))

    plt.bar(x, sorted_df['loadings_diff'].values, color='coral', alpha=0.7)

    plt.xticks(x, sorted_df['hydrocarbon'].values, rotation=90, fontsize=7)
    plt.ylabel('Absolute Loadings Difference', fontsize=12)
    plt.xlabel('Hydrocarbon', fontsize=12)
    plt.title(f'Различие PCA loadings между годами\n(меньше = стабильнее)\n{year_1} vs {year_2}', fontsize=14,
              fontweight='bold')
    plt.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()

    full_path = os.path.join(output_dir, output_path)
    plt.savefig(full_path, dpi=FIG_DPI, bbox_inches='tight')
    plt.close()
    print(f"Сохранено: {full_path}")


def plot_correlation_matrices(corr_year_1, corr_year_2, year_1, year_2, output_dir,
                              output_path='correlation_matrices.png'):
    """Визуализация корреляционных матриц"""

    fig, axes = plt.subplots(1, 2, figsize=(16, 7))

    im0 = axes[0].imshow(corr_year_1, cmap='RdYlGn', vmin=-1, vmax=1)
    axes[0].set_title(f'{year_1} Correlation Matrix', fontsize=12, fontweight='bold')
    plt.colorbar(im0, ax=axes[0])

    im1 = axes[1].imshow(corr_year_2, cmap='RdYlGn', vmin=-1, vmax=1)
    axes[1].set_title(f'{year_2} Correlation Matrix', fontsize=12, fontweight='bold')
    plt.colorbar(im1, ax=axes[1])

    plt.suptitle(f'Меж-углеводородные корреляции по годам\n{year_1} vs {year_2}', fontsize=14, fontweight='bold')
    plt.tight_layout()

    full_path = os.path.join(output_dir, output_path)
    plt.savefig(full_path, dpi=FIG_DPI, bbox_inches='tight')
    plt.close()
    print(f"Сохранено: {full_path}")


# =============================================================================
# 18. ВИЗУАЛИЗАЦИЯ ОПТИМИЗАЦИИ (ОБНОВЛЕНО - 3 метрики!)
# =============================================================================

def plot_optimization_history(history, output_dir):
    """График истории оптимизации с 3 метриками"""

    fig, axes = plt.subplots(2, 2, figsize=(16, 10))

    # Фильтруем уникальные итерации
    unique_history = []
    seen_iters = set()
    for h in history:
        if h['iteration'] not in seen_iters:
            unique_history.append(h)
            seen_iters.add(h['iteration'])

    iterations = [h['iteration'] for h in unique_history]

    # 1. Centroid distance
    axes[0, 0].plot(iterations, [h['centroid_distance'] for h in unique_history],
                    'o-', linewidth=2, markersize=8, color='red')
    axes[0, 0].set_xlabel('Итерация/Поколение', fontsize=12)
    axes[0, 0].set_ylabel('Centroid Distance', fontsize=12)
    axes[0, 0].set_title('Расстояние между центроидами (меньше = лучше)', fontsize=12, fontweight='bold')
    axes[0, 0].grid(True, alpha=0.3)

    # 2. Variance Ratio Score
    axes[0, 1].plot(iterations, [h.get('variance_ratio_score', 0) for h in unique_history],
                    'o-', linewidth=2, markersize=8, color='blue')
    axes[0, 1].set_xlabel('Итерация/Поколение', fontsize=12)
    axes[0, 1].set_ylabel('Variance Ratio Score', fontsize=12)
    axes[0, 1].set_title('Схожесть дисперсий (больше = лучше)', fontsize=12, fontweight='bold')
    axes[0, 1].grid(True, alpha=0.3)

    # 3. Density Similarity
    axes[1, 0].plot(iterations, [h.get('density_similarity', 0) for h in unique_history],
                    'o-', linewidth=2, markersize=8, color='green')
    axes[1, 0].set_xlabel('Итерация/Поколение', fontsize=12)
    axes[1, 0].set_ylabel('Density Similarity', fontsize=12)
    axes[1, 0].set_title('Схожесть плотности кластеров (больше = лучше)', fontsize=12, fontweight='bold')
    axes[1, 0].grid(True, alpha=0.3)

    # 4. Quality Score
    axes[1, 1].plot(iterations, [h['quality_score'] for h in unique_history],
                    'o-', linewidth=2, markersize=8, color='black')
    axes[1, 1].set_xlabel('Итерация/Поколение', fontsize=12)
    axes[1, 1].set_ylabel('Quality Score', fontsize=12)
    axes[1, 1].set_title('Композитный Quality Score', fontsize=12, fontweight='bold')
    axes[1, 1].grid(True, alpha=0.3)

    plt.suptitle(f'История оптимизации набора углеводородов (3 независимые метрики)\n{year_1} vs {year_2}', fontsize=14,
                 fontweight='bold')
    plt.tight_layout()

    full_path = os.path.join(output_dir, 'optimization_history.png')
    plt.savefig(full_path, dpi=FIG_DPI, bbox_inches='tight')
    plt.close()
    print(f"Сохранено: {full_path}")


def plot_pca_comparison_before_after(proportions_year_1, proportions_year_2, hc_all, hc_optimized,
                                     year_1, year_2, output_dir):
    """Сравнение PCA до и после оптимизации (ИСПРАВЛЕНО: 'до' - все УВ из файла)"""

    fig, axes = plt.subplots(1, 2, figsize=(16, 7))

    # ==========================================================================
    # ДО ОПТИМИЗАЦИИ - БЕРЕМ ВСЕ УГЛЕВОДОРОДЫ ИЗ ИСХОДНОГО ФАЙЛА
    # Использует ту же предобработку, что и алгоритмы оптимизации
    # ==========================================================================
    clr_1_orig, clr_2_orig = preprocess_hydrocarbon_subset(proportions_year_1, proportions_year_2, hc_all)

    # ОБЪЕДИНЯЕМ данные для PCA (важно!)
    X_combined_orig = np.vstack([clr_1_orig, clr_2_orig])

    scaler_orig = StandardScaler()
    X_combined_orig_scaled = scaler_orig.fit_transform(X_combined_orig)

    # PCA фитится на объединённых данных
    pca_orig = PCA(n_components=2)
    pca_combined_orig = pca_orig.fit_transform(X_combined_orig_scaled)

    # Разделяем обратно по годам
    pca_1_orig = pca_combined_orig[:len(clr_1_orig), :]
    pca_2_orig = pca_combined_orig[len(clr_1_orig):, :]

    # Центроиды
    centroid_1_orig = np.mean(pca_1_orig, axis=0)
    centroid_2_orig = np.mean(pca_2_orig, axis=0)
    centroid_dist_orig = np.sqrt(np.sum((centroid_1_orig - centroid_2_orig) ** 2))

    axes[0].scatter(pca_1_orig[:, 0], pca_1_orig[:, 1],
                    c=COLOR_YEAR_1, alpha=0.6, s=100, label=str(year_1), edgecolors='black')
    axes[0].scatter(pca_2_orig[:, 0], pca_2_orig[:, 1],
                    c=COLOR_OUTLIER, alpha=0.6, s=100, label=str(year_2), edgecolors='black')
    axes[0].scatter(centroid_1_orig[0], centroid_1_orig[1],
                    c=COLOR_YEAR_1, s=300, marker='*', edgecolors='black', linewidth=2)
    axes[0].scatter(centroid_2_orig[0], centroid_2_orig[1],
                    c=COLOR_OUTLIER, s=300, marker='*', edgecolors='black', linewidth=2)

    # Линия между центроидами
    axes[0].plot([centroid_1_orig[0], centroid_2_orig[0]],
                 [centroid_1_orig[1], centroid_2_orig[1]],
                 'k--', linewidth=2, alpha=0.5)

    axes[0].set_xlabel(f'PC1 ({pca_orig.explained_variance_ratio_[0] * 100:.1f}%)')
    axes[0].set_ylabel(f'PC2 ({pca_orig.explained_variance_ratio_[1] * 100:.1f}%)')
    axes[0].set_title(f'До оптимизации ({len(hc_all)} УВ - все из файла)\nCentroid distance: {centroid_dist_orig:.4f}',
                      fontsize=12, fontweight='bold')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # ==========================================================================
    # ПОСЛЕ ОПТИМИЗАЦИИ - ИСПОЛЬЗУЕТ ТУ ЖЕ ПРЕДОБРАБОТКУ
    # ==========================================================================
    clr_1_opt, clr_2_opt = preprocess_hydrocarbon_subset(proportions_year_1, proportions_year_2, hc_optimized)

    # ОБЪЕДИНЯЕМ данные для PCA (важно!)
    X_combined_opt = np.vstack([clr_1_opt, clr_2_opt])

    scaler_opt = StandardScaler()
    X_combined_opt_scaled = scaler_opt.fit_transform(X_combined_opt)

    # PCA фитится на объединённых данных
    pca_opt = PCA(n_components=2)
    pca_combined_opt = pca_opt.fit_transform(X_combined_opt_scaled)

    # Разделяем обратно
    pca_1_opt = pca_combined_opt[:len(clr_1_opt), :]
    pca_2_opt = pca_combined_opt[len(clr_1_opt):, :]

    # Центроиды
    centroid_1_opt = np.mean(pca_1_opt, axis=0)
    centroid_2_opt = np.mean(pca_2_opt, axis=0)
    centroid_dist_opt = np.sqrt(np.sum((centroid_1_opt - centroid_2_opt) ** 2))

    axes[1].scatter(pca_1_opt[:, 0], pca_1_opt[:, 1],
                    c=COLOR_YEAR_1, alpha=0.6, s=100, label=str(year_1), edgecolors='black')
    axes[1].scatter(pca_2_opt[:, 0], pca_2_opt[:, 1],
                    c=COLOR_YEAR_2, alpha=0.6, s=100, label=str(year_2), edgecolors='black')
    axes[1].scatter(centroid_1_opt[0], centroid_1_opt[1],
                    c=COLOR_YEAR_1, s=300, marker='*', edgecolors='black', linewidth=2)
    axes[1].scatter(centroid_2_opt[0], centroid_2_opt[1],
                    c=COLOR_YEAR_2, s=300, marker='*', edgecolors='black', linewidth=2)

    # Линия между центроидами
    axes[1].plot([centroid_1_opt[0], centroid_2_opt[0]],
                 [centroid_1_opt[1], centroid_2_opt[1]],
                 'k--', linewidth=2, alpha=0.5)

    axes[1].set_xlabel(f'PC1 ({pca_opt.explained_variance_ratio_[0] * 100:.1f}%)')
    axes[1].set_ylabel(f'PC2 ({pca_opt.explained_variance_ratio_[1] * 100:.1f}%)')
    axes[1].set_title(f'После оптимизации ({len(hc_optimized)} УВ)\nCentroid distance: {centroid_dist_opt:.4f}',
                      fontsize=12, fontweight='bold')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    plt.suptitle(f'Сравнение PCA пространства до и после оптимизации\n{year_1} vs {year_2}', fontsize=14,
                 fontweight='bold')
    plt.tight_layout()

    full_path = os.path.join(output_dir, 'pca_comparison_before_after.png')
    plt.savefig(full_path, dpi=FIG_DPI, bbox_inches='tight')
    plt.close()
    print(f"Сохранено: {full_path}")

    # Возвращаем метрики для логирования
    return centroid_dist_orig, centroid_dist_opt


def plot_stable_hc_comparison_final(df, hc_optimized, consensus_df, year_1, year_2, output_dir,
                                    max_per_plot=MAX_HC_PER_PLOT_BOX):
    """Финальный boxplot сравнения для ВСЕХ оптимизированных УВ"""

    # Сортируем hc_optimized по consensus score (от высоких к низким)
    consensus_sorted = consensus_df.set_index('hydrocarbon').loc[hc_optimized].sort_values('consensus_score',
                                                                                           ascending=False)
    hc_sorted = consensus_sorted.index.tolist()

    n_hc = len(hc_sorted)
    n_plots = int(np.ceil(n_hc / max_per_plot))

    print(f"\nstable_hc_comparison_FINAL: {n_hc} УВ, {n_plots} график(ов) по {max_per_plot} УВ")

    for plot_idx in range(n_plots):
        start_idx = plot_idx * max_per_plot
        end_idx = min((plot_idx + 1) * max_per_plot, n_hc)
        plot_hc = hc_sorted[start_idx:end_idx]

        n_in_plot = len(plot_hc)
        n_rows = int(np.ceil(n_in_plot / 5))
        n_cols = min(5, n_in_plot)

        fig, axes = plt.subplots(n_rows, n_cols, figsize=(5 * n_cols, 4 * n_rows))
        if n_rows == 1 and n_cols == 1:
            axes = np.array([[axes]])
        elif n_rows == 1:
            axes = axes.reshape(1, -1)
        elif n_cols == 1:
            axes = axes.reshape(-1, 1)

        axes = axes.flatten()

        for i, hc in enumerate(plot_hc):
            data_year_1_all = df[df['year'] == year_1][hc_optimized]
            data_year_2_all = df[df['year'] == year_2][hc_optimized]

            props_1 = data_year_1_all.div(data_year_1_all.sum(axis=1), axis=0)[hc].values
            props_2 = data_year_2_all.div(data_year_2_all.sum(axis=1), axis=0)[hc].values

            axes[i].boxplot([props_1, props_2], labels=[str(year_1), str(year_2)], patch_artist=True,
                            boxprops=dict(facecolor='lightgreen', alpha=0.7),
                            medianprops=dict(color='red', linewidth=2))

            axes[i].scatter(np.random.normal(1, 0.05, len(props_1)), props_1, alpha=0.6, color=COLOR_YEAR_1, s=50)
            axes[i].scatter(np.random.normal(2, 0.05, len(props_2)), props_2, alpha=0.6, color=COLOR_YEAR_2, s=50)

            _, p_value = mannwhitneyu(props_1, props_2, alternative='two-sided')

            score = consensus_df.set_index('hydrocarbon').loc[hc, 'consensus_score']
            axes[i].set_title(f'{hc}\nscore={score:.2f}, p={p_value:.3f}', fontsize=8, fontweight='bold')
            axes[i].set_ylabel('Proportion')
            axes[i].grid(True, alpha=0.3)

        # Скрыть пустые subplot
        for j in range(i + 1, len(axes)):
            axes[j].set_visible(False)

        plt.suptitle(
            f'ФИНАЛ: Сравнение распределений УВ (ПОСЛЕ оптимизации) - Часть {plot_idx + 1}/{n_plots}\n{year_1} vs {year_2}',
            fontsize=14, fontweight='bold')
        plt.tight_layout()

        full_path = os.path.join(output_dir, f'stable_hc_comparison_FINAL_part{plot_idx + 1}.png')
        plt.savefig(full_path, dpi=FIG_DPI, bbox_inches='tight')
        plt.close()
        print(f"Сохранено: {full_path}")


def plot_parallel_coordinates_final(df, hc_optimized, consensus_df, year_1, year_2, output_dir):
    """Финальный parallel coordinates (с МЕДИАНОЙ вместо среднего)"""

    # Сортируем по consensus score
    consensus_sorted = consensus_df.set_index('hydrocarbon').loc[hc_optimized].sort_values('consensus_score',
                                                                                           ascending=False)
    hc_sorted = consensus_sorted.index.tolist()

    data_subset = df[hc_sorted + ['year']].copy()
    data_subset[hc_sorted] = data_subset[hc_sorted].div(data_subset[hc_sorted].sum(axis=1), axis=0)

    plt.figure(figsize=(16, 8))

    data_year_1 = data_subset[data_subset['year'] == year_1][hc_sorted]
    for idx in data_year_1.index:
        plt.plot(range(len(hc_sorted)), data_year_1.loc[idx].values,
                 color=COLOR_YEAR_1, alpha=0.3, linewidth=1, label=str(year_1) if idx == data_year_1.index[0] else "")

    data_year_2 = data_subset[data_subset['year'] == year_2][hc_sorted]
    for idx in data_year_2.index:
        plt.plot(range(len(hc_sorted)), data_year_2.loc[idx].values,
                 color=COLOR_OUTLIER, alpha=0.3, linewidth=1, label=str(year_2) if idx == data_year_2.index[0] else "")

    # МЕДИАНА вместо среднего
    median_year_1 = data_year_1.median()
    median_year_2 = data_year_2.median()
    plt.plot(range(len(hc_sorted)), median_year_1.values,
             color=COLOR_YEAR_1, linewidth=3, marker='o', markersize=8, label=f'Median {year_1}')
    plt.plot(range(len(hc_sorted)), median_year_2.values,
             color=COLOR_OUTLIER, linewidth=3, marker='s', markersize=8, label=f'Median {year_2}')

    plt.xticks(range(len(hc_sorted)), hc_sorted, rotation=45, ha='right', fontsize=7)
    plt.ylabel('Proportion (normalized to sum=1)', fontsize=12)
    plt.title(
        f'ФИНАЛ: Паттерны пропорций стабильных УВ (ПОСЛЕ оптимизации)\nМедиана вместо среднего (сортировка по consensus score)\n{year_1} vs {year_2}',
        fontsize=14, fontweight='bold')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    full_path = os.path.join(output_dir, 'parallel_coordinates_FINAL.png')
    plt.savefig(full_path, dpi=FIG_DPI, bbox_inches='tight')
    plt.close()
    print(f"Сохранено: {full_path}")


def plot_correlation_heatmap_stable_final(df, hc_optimized, year_1, year_2, output_dir):
    """Финальная heatmap корреляций для оптимизированного набора"""

    data_year_1 = df[df['year'] == year_1][hc_optimized]
    data_year_2 = df[df['year'] == year_2][hc_optimized]

    props_year_1 = data_year_1.div(data_year_1.sum(axis=1), axis=0)
    props_year_2 = data_year_2.div(data_year_2.sum(axis=1), axis=0)

    corr_year_1 = props_year_1.corr(method='spearman')
    corr_year_2 = props_year_2.corr(method='spearman')

    fig, axes = plt.subplots(1, 2, figsize=(16, 7))

    im0 = axes[0].imshow(corr_year_1, cmap='RdYlGn', vmin=-1, vmax=1)
    axes[0].set_title(f'{year_1} Correlation Matrix\n(оптимизированный набор)', fontsize=12, fontweight='bold')
    axes[0].set_xticks(range(len(hc_optimized)))
    axes[0].set_xticklabels(hc_optimized, rotation=45, ha='right', fontsize=6)
    axes[0].set_yticks(range(len(hc_optimized)))
    axes[0].set_yticklabels(hc_optimized, fontsize=6)
    plt.colorbar(im0, ax=axes[0])

    im1 = axes[1].imshow(corr_year_2, cmap='RdYlGn', vmin=-1, vmax=1)
    axes[1].set_title(f'{year_2} Correlation Matrix\n(оптимизированный набор)', fontsize=12, fontweight='bold')
    axes[1].set_xticks(range(len(hc_optimized)))
    axes[1].set_xticklabels(hc_optimized, rotation=45, ha='right', fontsize=6)
    axes[1].set_yticks(range(len(hc_optimized)))
    axes[1].set_yticklabels(hc_optimized, fontsize=6)
    plt.colorbar(im1, ax=axes[1])

    corr_diff = np.abs(corr_year_1.values - corr_year_2.values).mean()

    plt.suptitle(
        f'ФИНАЛ: Меж-УВ корреляции (ПОСЛЕ оптимизации)\nСреднее различие: {corr_diff:.3f}\n{year_1} vs {year_2}',
        fontsize=14, fontweight='bold')
    plt.tight_layout()

    full_path = os.path.join(output_dir, 'correlation_heatmap_stable_FINAL.png')
    plt.savefig(full_path, dpi=FIG_DPI, bbox_inches='tight')
    plt.close()
    print(f"Сохранено: {full_path}")


def plot_distribution_overlap_final(df, hc_optimized, consensus_df, year_1, year_2, output_dir,
                                    max_per_plot=MAX_HC_PER_PLOT_KDE):
    """Финальный KDE overlap для ВСЕХ оптимизированных УВ"""

    # Сортируем по consensus score
    consensus_sorted = consensus_df.set_index('hydrocarbon').loc[hc_optimized].sort_values('consensus_score',
                                                                                           ascending=False)
    hc_sorted = consensus_sorted.index.tolist()

    n_hc = len(hc_sorted)
    n_plots = int(np.ceil(n_hc / max_per_plot))

    print(f"\ndistribution_overlap_FINAL: {n_hc} УВ, {n_plots} график(ов) по {max_per_plot} УВ")

    for plot_idx in range(n_plots):
        start_idx = plot_idx * max_per_plot
        end_idx = min((plot_idx + 1) * max_per_plot, n_hc)
        plot_hc = hc_sorted[start_idx:end_idx]

        n_in_plot = len(plot_hc)
        n_rows = int(np.ceil(n_in_plot / 3))
        n_cols = min(3, n_in_plot)

        fig, axes = plt.subplots(n_rows, n_cols, figsize=(6 * n_cols, 4 * n_rows))
        if n_rows == 1 and n_cols == 1:
            axes = np.array([[axes]])
        elif n_rows == 1:
            axes = axes.reshape(1, -1)
        elif n_cols == 1:
            axes = axes.reshape(-1, 1)

        axes = axes.flatten()

        for i, hc in enumerate(plot_hc):
            data_year_1_all = df[df['year'] == year_1][hc_optimized]
            data_year_2_all = df[df['year'] == year_2][hc_optimized]

            props_1 = data_year_1_all.div(data_year_1_all.sum(axis=1), axis=0)[hc].values
            props_2 = data_year_2_all.div(data_year_2_all.sum(axis=1), axis=0)[hc].values

            y1 = np.log(props_1 + EPSILON)
            y2 = np.log(props_2 + EPSILON)

            kde_1 = gaussian_kde(y1)
            kde_2 = gaussian_kde(y2)

            x_range = np.linspace(min(y1.min(), y2.min()), max(y1.max(), y2.max()), 100)

            axes[i].fill_between(x_range, kde_1(x_range), alpha=0.4, color=COLOR_YEAR_1, label=str(year_1))
            axes[i].fill_between(x_range, kde_2(x_range), alpha=0.4, color=COLOR_YEAR_2, label=str(year_2))

            overlap = np.minimum(kde_1(x_range), kde_2(x_range)).sum() / len(x_range)

            score = consensus_df.set_index('hydrocarbon').loc[hc, 'consensus_score']
            axes[i].set_title(f'{hc}\nscore={score:.2f}, overlap={overlap:.2f}', fontsize=9, fontweight='bold')
            axes[i].set_xlabel('log(Proportion)')
            axes[i].set_ylabel('Density')
            axes[i].legend(fontsize=7)
            axes[i].grid(True, alpha=0.3)

        # Скрыть пустые subplot
        for j in range(i + 1, len(axes)):
            axes[j].set_visible(False)

        plt.suptitle(
            f'ФИНАЛ: Перекрытие распределений (KDE) ПОСЛЕ оптимизации - Часть {plot_idx + 1}/{n_plots}\n{year_1} vs {year_2}',
            fontsize=14, fontweight='bold')
        plt.tight_layout()

        full_path = os.path.join(output_dir, f'distribution_overlap_FINAL_part{plot_idx + 1}.png')
        plt.savefig(full_path, dpi=FIG_DPI, bbox_inches='tight')
        plt.close()
        print(f"Сохранено: {full_path}")


def plot_pca_biplot_final(proportions_year_1, proportions_year_2, hc_optimized, year_1, year_2, output_dir):
    """Финальный PCA biplot для оптимизированного набора (ИСПОЛЬЗУЕТ ЕДИНУЮ ПРЕДОБРАБОТКУ)"""

    # ==========================================================================
    # Пересчитываем CLR на оптимизированном наборе через единую функцию
    # ==========================================================================
    clr_1, clr_2 = preprocess_hydrocarbon_subset(proportions_year_1, proportions_year_2, hc_optimized)

    # Объединяем CLR данные для оптимизированного набора
    X_1 = clr_1
    X_2 = clr_2

    # ОБЪЕДИНЯЕМ для PCA (как в plot_pca_comparison_before_after)
    X_combined = np.vstack([X_1, X_2])

    scaler = StandardScaler()
    X_combined_scaled = scaler.fit_transform(X_combined)

    # PCA фитится на объединённых данных
    pca = PCA(n_components=2)
    pca_combined = pca.fit_transform(X_combined_scaled)

    # Разделяем обратно
    pca_1 = pca_combined[:len(X_1), :]
    pca_2 = pca_combined[len(X_1):, :]

    # Центроиды
    centroid_1 = np.mean(pca_1, axis=0)
    centroid_2 = np.mean(pca_2, axis=0)
    centroid_dist = np.sqrt(np.sum((centroid_1 - centroid_2) ** 2))

    plt.figure(figsize=(12, 10))

    plt.scatter(pca_1[:, 0], pca_1[:, 1],
                c=COLOR_YEAR_1, alpha=0.6, s=100, edgecolors='black', linewidth=1,
                label=f'{year_1} (n={len(pca_1)})')

    plt.scatter(pca_2[:, 0], pca_2[:, 1],
                c=COLOR_YEAR_2, alpha=0.6, s=100, edgecolors='black', linewidth=1,
                label=f'{year_2} (n={len(pca_2)})')

    plt.scatter(centroid_1[0], centroid_1[1],
                c=COLOR_YEAR_1, s=300, marker='*', edgecolors='black', linewidth=2, label=f'Centroid {year_1}')
    plt.scatter(centroid_2[0], centroid_2[1],
                c=COLOR_YEAR_2, s=300, marker='*', edgecolors='black', linewidth=2, label=f'Centroid {year_2}')

    # Линия между центроидами
    plt.plot([centroid_1[0], centroid_2[0]],
             [centroid_1[1], centroid_2[1]],
             'k--', linewidth=2, alpha=0.5, label=f'Distance={centroid_dist:.4f}')

    plt.xlabel(f'PC1 ({pca.explained_variance_ratio_[0] * 100:.1f}% variance)', fontsize=12)
    plt.ylabel(f'PC2 ({pca.explained_variance_ratio_[1] * 100:.1f}% variance)', fontsize=12)
    plt.title(
        f'ФИНАЛ: PCA Biplot (ПОСЛЕ оптимизации, {len(hc_optimized)} УВ)\nCentroid distance: {centroid_dist:.4f}\n{year_1} vs {year_2}',
        fontsize=14, fontweight='bold')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    full_path = os.path.join(output_dir, 'pca_biplot_stable_FINAL.png')
    plt.savefig(full_path, dpi=FIG_DPI, bbox_inches='tight')
    plt.close()
    print(f"Сохранено: {full_path}")

    return centroid_dist


# =============================================================================
# 19. ЭКСПОРТ РЕЗУЛЬТАТОВ (ДИНАМИЧЕСКИЙ)
# =============================================================================

def export_results(all_results, enabled_methods, output_dir, output_path=OUTPUT_FILENAME):
    """Экспорт всех результатов в Excel (только включённые методы)"""

    full_path = os.path.join(output_dir, output_path)

    # Маппинг ключей all_results к именам методов
    result_key_map = {
        'clr_df': 'clr',
        'ratio_df': 'ratio',
        'pattern_df': 'pattern',
        'importance_df': 'importance',
        'bootstrap_df': 'bootstrap',
        'loadings_df': 'pca',
        'cohens_d_df': 'cohens_d',
        'wasserstein_df': 'wasserstein',
        'pairwise_df': 'pairwise',
        'consensus_df': 'consensus'
    }

    with pd.ExcelWriter(full_path, engine='openpyxl') as writer:
        for result_key, method_name in result_key_map.items():
            # Проверяем, что метод включён и данные существуют
            if method_name == 'consensus':
                # Консенсус всегда экспортируем если есть
                if result_key in all_results and all_results[result_key] is not None:
                    all_results[result_key].to_excel(writer, sheet_name='Consensus_Full', index=False)
                    if len(all_results[result_key]) > EXPORT_SHEET_TOP_N:
                        all_results[result_key].head(EXPORT_SHEET_TOP_N).to_excel(writer, sheet_name='Consensus_Top10',
                                                                                  index=False)
            elif enabled_methods.get(method_name, False):
                if result_key in all_results and all_results[result_key] is not None:
                    sheet_name_full = f'{method_name.capitalize()}_Full'
                    all_results[result_key].to_excel(writer, sheet_name=sheet_name_full, index=False)

                    if len(all_results[result_key]) > EXPORT_SHEET_TOP_N:
                        sheet_name_top = f'{method_name.capitalize()}_Top{EXPORT_SHEET_TOP_N}'
                        all_results[result_key].head(EXPORT_SHEET_TOP_N).to_excel(writer, sheet_name=sheet_name_top,
                                                                                  index=False)

    print(f"\nРезультаты экспортированы в: {full_path}")

    # Вывод информации о том, что было экспортировано
    print(f"\nЭкспортированные листы:")
    for result_key, method_name in result_key_map.items():
        if method_name == 'consensus':
            if result_key in all_results and all_results[result_key] is not None:
                print(f"  ✅ Consensus_Full, Consensus_Top10")
        elif enabled_methods.get(method_name, False):
            if result_key in all_results and all_results[result_key] is not None:
                print(f"  ✅ {method_name.capitalize()}_Full, {method_name.capitalize()}_Top{EXPORT_SHEET_TOP_N}")
        else:
            if result_key in all_results:
                print(f"  ⏸️  {method_name.capitalize()} (пропущено - метод отключён)")


# =============================================================================
# 20. ГЛАВНАЯ ФУНКЦИЯ
# =============================================================================

# Глобальные переменные для годов (используются в функциях визуализации)
year_1 = None
year_2 = None


def main():
    """Основная функция анализа"""

    global year_1, year_2

    print("=" * 80)
    print("АНАЛИЗ СТАБИЛЬНОСТИ УГЛЕВОДОРОДОВ МЕЖДУ ИЗМЕРЕНИЯМИ РАЗНЫХ ГОДОВ")
    print("Версия 4.8: Исправление ошибки min_hc >= len(hc_columns)")
    print("=" * 80)

    filepath = INPUT_FILEPATH

    output_dir = os.path.dirname(os.path.abspath(filepath))
    print(f"\nПапка для сохранения результатов: {output_dir}")

    df = load_data(filepath)

    # ==========================================================================
    # ПОЛУЧЕНИЕ УНИКАЛЬНЫХ ГОДОВ ИЗ ДАННЫХ
    # ==========================================================================
    year_1, year_2 = get_unique_years(df)
    print(f"\n✅ Годы анализа: {year_1} и {year_2}")

    hc_columns = get_hydrocarbon_columns(df)
    print(f"\nНайдено {len(hc_columns)} углеводородов для анализа")

    data_year_1, data_year_2 = prepare_data_by_year(df, hc_columns, year_1, year_2)

    # ==========================================================================
    # НАСТРОЙКИ МЕТОДОВ
    # ==========================================================================
    print("\n" + "=" * 80)
    print("ВЫБРАННЫЕ МЕТОДЫ АНАЛИЗА")
    print("=" * 80)

    enabled_methods = {k: v for k, v in METHODS_CONFIG.items()}
    enabled_method_list = [k for k, v in METHODS_CONFIG.items() if v]
    disabled_method_list = [k for k, v in METHODS_CONFIG.items() if not v]

    print(f"\n✅ Включено ({len(enabled_method_list)}): {', '.join(enabled_method_list)}")
    print(f"⏸️  Отключено ({len(disabled_method_list)}): {', '.join(disabled_method_list)}")

    if len(enabled_method_list) < MIN_METHODS_FOR_CONSENSUS:
        print(f"\n⚠️  ВНИМАНИЕ: Включено меньше {MIN_METHODS_FOR_CONSENSUS} методов!")
        print("   Консенсусный рейтинг может быть ненадёжным.")

    # ==========================================================================
    # НАСТРОЙКИ ОПТИМИЗАЦИИ
    # ==========================================================================
    print(f"\nНастройки оптимизации:")
    print(f"  Алгоритм: {OPTIMIZATION_ALGORITHM}")
    print(f"  Минимум УВ: {MIN_HC}")
    print(f"  Максимум УВ: {MAX_HC}")
    print(f"  Макс итераций/поколений: {MAX_ITERATIONS}")
    print(f"  Порог consensus для кандидатов: {CONSENSUS_THRESHOLD}")
    print(f"\nНастройки жадного алгоритма:")
    print(f"  Макс итераций: {GREEDY_MAX_ITERATIONS}")
    print(f"  Варианты удаления УВ: {GREEDY_N_REMOVE_OPTIONS}")
    print(f"  Итераций в гибридном режиме: {GREEDY_HYBRID_ITERATIONS}")

    # ==========================================================================
    # ПОДГОТОВКА КОМПОЗИЦИОННЫХ ДАННЫХ
    # ==========================================================================
    proportions_year_1, proportions_year_2, clr_year_1, clr_year_2, log_proportions_year_1, log_proportions_year_2 = \
        prepare_compositional_data(data_year_1, data_year_2, hc_columns)

    all_results = {}
    results_for_consensus = {}

    # ==========================================================================
    # ОБНАРУЖЕНИЕ ВЫБРОСОВ
    # ==========================================================================
    print("\n" + "=" * 80)
    print("ОБНАРУЖЕНИЕ ВЫБРОСОВ")
    print("=" * 80)

    sample_outliers_year_1, scores_year_1, threshold_year_1 = detect_sample_outliers(
        clr_year_1, method=SAMPLE_OUTLIER_METHOD)
    sample_outliers_year_2, scores_year_2, threshold_year_2 = detect_sample_outliers(
        clr_year_2, method=SAMPLE_OUTLIER_METHOD)

    print(f"\nПробы-выбросы ({SAMPLE_OUTLIER_METHOD} на CLR):")
    print(
        f"  {year_1}: {sample_outliers_year_1.sum()} из {len(sample_outliers_year_1)} проб (порог={threshold_year_1:.2f})")
    print(
        f"  {year_2}: {sample_outliers_year_2.sum()} из {len(sample_outliers_year_2)} проб (порог={threshold_year_2:.2f})")

    hc_outliers_year_1, hc_outlier_summary_year_1 = detect_hydrocarbon_outliers(
        clr_year_1, method=HC_OUTLIER_METHOD, threshold=HC_OUTLIER_THRESHOLD)
    hc_outliers_year_2, hc_outlier_summary_year_2 = detect_hydrocarbon_outliers(
        clr_year_2, method=HC_OUTLIER_METHOD, threshold=HC_OUTLIER_THRESHOLD)

    total_outliers_year_1 = hc_outliers_year_1.values.sum()
    total_outliers_year_2 = hc_outliers_year_2.values.sum()

    print(f"\nУглеводороды-выбросы ({HC_OUTLIER_METHOD}, threshold={HC_OUTLIER_THRESHOLD}):")
    print(f"  {year_1}: {total_outliers_year_1} выбросов")
    print(f"  {year_2}: {total_outliers_year_2} выбросов")

    print(f"\nТоп-5 УВ с наибольшим числом выбросов ({year_1}):")
    print(hc_outlier_summary_year_1.head(5)[['hydrocarbon', 'n_outliers', 'outlier_ratio']].to_string(index=False))

    print(f"\nТоп-5 УВ с наибольшим числом выбросов ({year_2}):")
    print(hc_outlier_summary_year_2.head(5)[['hydrocarbon', 'n_outliers', 'outlier_ratio']].to_string(index=False))

    visualize_outliers(clr_year_1, clr_year_2, sample_outliers_year_1, sample_outliers_year_2,
                       hc_outliers_year_1, hc_outliers_year_2, year_1, year_2, output_dir)

    create_outlier_report(sample_outliers_year_1, sample_outliers_year_2,
                          hc_outliers_year_1, hc_outliers_year_2,
                          hc_outlier_summary_year_1, hc_outlier_summary_year_2,
                          year_1, year_2, output_dir)

    if EXCLUDE_SAMPLE_OUTLIERS:
        print("\n" + "=" * 80)
        print("ИСКЛЮЧЕНИЕ ПРОБ-ВЫБРОСОВ ИЗ АНАЛИЗА")
        print("=" * 80)

        clr_year_1_clean = clr_year_1[~sample_outliers_year_1].reset_index(drop=True)
        clr_year_2_clean = clr_year_2[~sample_outliers_year_2].reset_index(drop=True)
        proportions_year_1_clean = proportions_year_1[~sample_outliers_year_1].reset_index(drop=True)
        proportions_year_2_clean = proportions_year_2[~sample_outliers_year_2].reset_index(drop=True)
        log_proportions_year_1_clean = log_proportions_year_1[~sample_outliers_year_1].reset_index(drop=True)
        log_proportions_year_2_clean = log_proportions_year_2[~sample_outliers_year_2].reset_index(drop=True)

        print(f"  {year_1}: {len(clr_year_1)} → {len(clr_year_1_clean)} проб")
        print(f"  {year_2}: {len(clr_year_2)} → {len(clr_year_2_clean)} проб")

        clr_year_1, clr_year_2 = clr_year_1_clean, clr_year_2_clean
        proportions_year_1, proportions_year_2 = proportions_year_1_clean, proportions_year_2_clean
        log_proportions_year_1, log_proportions_year_2 = log_proportions_year_1_clean, log_proportions_year_2_clean
    else:
        print("\n⚠️  Пробы-выбросы НЕ исключаются (EXCLUDE_SAMPLE_OUTLIERS = False)")
        print("   Для исключения установите EXCLUDE_SAMPLE_OUTLIERS = True")

    # ==========================================================================
    # АНАЛИЗ СТАБИЛЬНОСТИ (ВЫБРАННЫЕ МЕТОДЫ)
    # ==========================================================================

    print("\n" + "=" * 80)
    print("ВЫПОЛНЕНИЕ АНАЛИЗА СТАБИЛЬНОСТИ")
    print("=" * 80)

    # Переменные для опциональных данных
    corr_year_1, corr_year_2 = None, None

    for method_name, enabled in METHODS_CONFIG.items():
        if not enabled:
            print(f"\n⏸️  {method_name.upper()}: ПРОПУЩЕНО")
            continue

        print(f"\n{'=' * 80}")
        print(f"МЕТОД: {method_name.upper()}")
        print(f"{'=' * 80}")

        if method_name == 'cohens_d':
            # Специальная обработка для Cohen's D
            clr_df_temp = calculate_clr_stability(clr_year_1, clr_year_2, hc_columns)
            cohens_d_results = clr_df_temp[['hydrocarbon', 'cohens_d']].copy()
            cohens_d_results['effect_size_class'] = cohens_d_results['cohens_d'].apply(interpret_cohens_d)
            cohens_d_results['cohens_d_stability'] = 1 / (1 + np.abs(cohens_d_results['cohens_d']))
            cohens_d_results = cohens_d_results.sort_values('cohens_d_stability', ascending=False)
            all_results['cohens_d_df'] = cohens_d_results
            results_for_consensus['cohens_d'] = cohens_d_results[['hydrocarbon', 'cohens_d_stability']].rename(
                columns={'cohens_d_stability': 'score'})
            print(f"Топ-5 стабильных (Cohen's d): {cohens_d_results.head(5)['hydrocarbon'].tolist()}")

        elif method_name == 'pattern':
            pattern_df, corr_year_1, corr_year_2 = correlation_pattern_stability(proportions_year_1, proportions_year_2,
                                                                                 hc_columns)
            all_results['pattern_df'] = pattern_df
            results_for_consensus['pattern'] = pattern_df[['hydrocarbon', 'pattern_stability_score']].rename(
                columns={'pattern_stability_score': 'score'})
            print(f"Топ-5 стабильных (паттерны): {pattern_df.head(5)['hydrocarbon'].tolist()}")

        elif method_name == 'importance':
            importance_df, rf_model = year_prediction_importance(log_proportions_year_1, log_proportions_year_2,
                                                                 hc_columns)
            all_results['importance_df'] = importance_df
            results_for_consensus['importance'] = importance_df[['hydrocarbon', 'stability_from_importance']].rename(
                columns={'stability_from_importance': 'score'})
            print(f"Топ-5 стабильных (importance): {importance_df.head(5)['hydrocarbon'].tolist()}")

        elif method_name == 'bootstrap':
            bootstrap_df = bootstrap_stability_ci(log_proportions_year_1, log_proportions_year_2, hc_columns,
                                                  n_iterations=BOOTSTRAP_ITERATIONS)
            all_results['bootstrap_df'] = bootstrap_df
            results_for_consensus['bootstrap'] = bootstrap_df[['hydrocarbon', 'ci_reliability']].rename(
                columns={'ci_reliability': 'score'})
            print(f"Топ-5 надёжных (bootstrap): {bootstrap_df.head(5)['hydrocarbon'].tolist()}")

        elif method_name == 'pca':
            loadings_df, loadings_corr, pca_1, pca_2 = pca_loadings_stability(clr_year_1, clr_year_2, hc_columns)
            all_results['loadings_df'] = loadings_df
            results_for_consensus['pca'] = loadings_df[['hydrocarbon', 'loadings_stability']].rename(
                columns={'loadings_stability': 'score'})
            print(f"Корреляция PCA loadings: {loadings_corr:.3f}")
            print(f"Топ-5 стабильных (PCA): {loadings_df.head(5)['hydrocarbon'].tolist()}")

        elif method_name == 'clr':
            clr_df = calculate_clr_stability(clr_year_1, clr_year_2, hc_columns)
            all_results['clr_df'] = clr_df
            results_for_consensus['clr'] = clr_df[['hydrocarbon', 'clr_stability_score']].rename(
                columns={'clr_stability_score': 'score'})
            print(f"Топ-5 стабильных (CLR): {clr_df.head(5)['hydrocarbon'].tolist()}")

        elif method_name == 'ratio':
            ratio_df = calculate_ratio_stability_metrics(proportions_year_1, proportions_year_2, hc_columns)
            all_results['ratio_df'] = ratio_df
            results_for_consensus['ratio'] = ratio_df[['hydrocarbon', 'ratio_stability_score']].rename(
                columns={'ratio_stability_score': 'score'})
            print(f"Топ-5 стабильных (пропорции): {ratio_df.head(5)['hydrocarbon'].tolist()}")

        elif method_name == 'wasserstein':
            wasserstein_df = calculate_wasserstein_stability(clr_year_1, clr_year_2, hc_columns)
            all_results['wasserstein_df'] = wasserstein_df
            results_for_consensus['wasserstein'] = wasserstein_df[
                ['hydrocarbon', 'wasserstein_stability_score']].rename(
                columns={'wasserstein_stability_score': 'score'})
            print(f"Топ-5 стабильных (Wasserstein): {wasserstein_df.head(5)['hydrocarbon'].tolist()}")

        elif method_name == 'pairwise':
            pairwise_df = calculate_pairwise_logratio_stability(proportions_year_1, proportions_year_2, hc_columns)
            all_results['pairwise_df'] = pairwise_df
            results_for_consensus['pairwise'] = pairwise_df[['hydrocarbon', 'pairwise_lr_mean_stability']].rename(
                columns={'pairwise_lr_mean_stability': 'score'})
            print(f"Топ-5 стабильных (pairwise LR): {pairwise_df.head(5)['hydrocarbon'].tolist()}")

    # ==========================================================================
    # CONSENSUS RANKING (выбранные методы)
    # ==========================================================================
    print("\n" + "=" * 80)
    print(f"CONSENSUS RANKING ({len(results_for_consensus)} методов)")
    print("=" * 80)

    if len(results_for_consensus) >= MIN_METHODS_FOR_CONSENSUS:
        consensus_df = consensus_ranking(results_for_consensus, enabled_method_list, hc_columns,
                                         use_variance_weighting=True)
        all_results['consensus_df'] = consensus_df

        print("\n" + "=" * 80)
        print(f"ТОП-10 НАИБОЛЕЕ СТАБИЛЬНЫХ УГЛЕВОДОРОДОВ (CONSENSUS)\n{year_1} vs {year_2}")
        print("=" * 80)
        print(consensus_df[['consensus_rank', 'hydrocarbon', 'consensus_score', 'consensus_class']].head(10).to_string(
            index=False))
    else:
        print(
            f"\n⚠️  Недостаточно методов для консенсусного рейтинга ({len(results_for_consensus)} < {MIN_METHODS_FOR_CONSENSUS})")
        consensus_df = None

    # ==========================================================================
    # ОПТИМИЗАЦИЯ НАБОРА УВ (3 метрики для перекрытия кластеров)
    # ==========================================================================
    if consensus_df is not None:
        print("\n" + "=" * 80)
        print(f"ОПТИМИЗАЦИЯ НАБОРА УВ (Алгоритм: {OPTIMIZATION_ALGORITHM.upper()})")
        print("Цель: максимальное перекрытие кластеров в PCA пространстве")
        print("=" * 80)

        # Фильтр: только УВ с consensus >= CONSENSUS_THRESHOLD
        candidate_hc = consensus_df[consensus_df['consensus_score'] >= CONSENSUS_THRESHOLD]['hydrocarbon'].tolist()
        print(f"\nКандидаты для оптимизации (consensus >= {CONSENSUS_THRESHOLD}): {len(candidate_hc)} УВ")

        start_time = time.time()

        # ВСЕ алгоритмы используют ЕДИНУЮ предобработку через evaluate_hydrocarbon_set
        # → preprocess_hydrocarbon_subset гарантирует одинаковую нормировку и CLR
        optimized_hc, optimization_history = optimize_hydrocarbon_set(
            proportions_year_1, proportions_year_2, candidate_hc, consensus_df,
            min_hc=MIN_HC, max_iterations=MAX_ITERATIONS,
            algorithm=OPTIMIZATION_ALGORITHM,
            pop_size=GA_POP_SIZE,
            mutation_rate=GA_MUTATION_RATE,
            max_hc=MAX_HC
        )

        elapsed = time.time() - start_time

        # Получаем финальные метрики
        final_metrics = evaluate_hydrocarbon_set(proportions_year_1, proportions_year_2, optimized_hc, consensus_df)

        print(f"\n{'=' * 80}")
        print(f"ОПТИМИЗАЦИЯ ЗАВЕРШЕНА за {elapsed:.1f} сек")
        print(f"{'=' * 80}")
        print(f"\n✅ Оптимальный набор: {len(optimized_hc)} углеводородов")
        print(f"   Удалено: {len(candidate_hc) - len(optimized_hc)} УВ")
        print(f"\nФинальные метрики (3 независимые):")
        print(f"   Centroid distance: {final_metrics['centroid_distance']:.4f}")
        print(f"   Variance ratio score: {final_metrics['variance_ratio_score']:.4f}")
        print(f"   Density similarity: {final_metrics['density_similarity']:.4f}")
        print(f"   Quality score: {final_metrics['quality_score']:.4f}")

        # Сохраняем список оптимальных УВ
        optimal_hc_df = pd.DataFrame({
            'hydrocarbon': optimized_hc,
            'included': True,
            'consensus_score': consensus_df.set_index('hydrocarbon').loc[optimized_hc, 'consensus_score'].values
        })
        optimal_hc_df.to_excel(os.path.join(output_dir, OPTIMAL_HC_FILENAME), index=False)

        # ==========================================================================
        # ВИЗУАЛИЗАЦИЯ ОПТИМИЗАЦИИ
        # ==========================================================================
        plot_optimization_history(optimization_history, output_dir)

        # ИСПОЛЬЗУЕТ ЕДИНУЮ ПРЕДОБРАБОТКУ (как и алгоритмы оптимизации)
        centroid_dist_before, centroid_dist_after = plot_pca_comparison_before_after(
            proportions_year_1, proportions_year_2, hc_columns, optimized_hc, year_1, year_2, output_dir)

        print(f"\n📊 PCA Centroid Distance:")
        print(f"   До оптимизации: {centroid_dist_before:.4f}")
        print(f"   После оптимизации: {centroid_dist_after:.4f}")
        if centroid_dist_before > 0:
            print(f"   Улучшение: {(1 - centroid_dist_after / centroid_dist_before) * 100:.1f}%")
    else:
        print("\n⚠️  Пропуск оптимизации: нет консенсусного рейтинга")
        optimized_hc = hc_columns
        optimization_history = []
        centroid_dist_before = 0
        centroid_dist_after = 0

    # ==========================================================================
    # ВИЗУАЛИЗАЦИЯ (ОСНОВНАЯ) - ДИНАМИЧЕСКАЯ
    # ==========================================================================
    print("\n" + "=" * 80)
    print("ГЕНЕРАЦИЯ ГРАФИКОВ (ОСНОВНАЯ)")
    print("=" * 80)

    all_scores_df = pd.DataFrame({'hydrocarbon': hc_columns})
    all_scores_df = all_scores_df.set_index('hydrocarbon')

    score_column_map = {
        'clr_df': ('clr_score', 'clr_stability_score'),
        'ratio_df': ('ratio_score', 'ratio_stability_score'),
        'pattern_df': ('pattern_score', 'pattern_stability_score'),
        'importance_df': ('importance_score', 'stability_from_importance'),
        'bootstrap_df': ('bootstrap_score', 'ci_reliability'),
        'loadings_df': ('pca_score', 'loadings_stability'),
        'cohens_d_df': ('cohens_d_score', 'cohens_d_stability'),
        'wasserstein_df': ('wasserstein_score', 'wasserstein_stability_score'),
        'pairwise_df': ('pairwise_score', 'pairwise_lr_mean_stability'),
    }

    for df_name, (new_col, orig_col) in score_column_map.items():
        if df_name in all_results:
            all_scores_df[new_col] = all_results[df_name].set_index('hydrocarbon')[orig_col].reindex(hc_columns).values

    all_scores_df = all_scores_df.fillna(0.5)
    all_scores_df = all_scores_df.reset_index()

    # Динамическая генерация графиков только для включённых методов
    plot_method_comparison(all_scores_df, enabled_methods, output_dir)

    if consensus_df is not None:
        plot_consensus_ranking(consensus_df, output_dir)

    if 'cohens_d_df' in all_results and METHODS_CONFIG.get('cohens_d', False):
        plot_cohens_d_distribution(all_results['cohens_d_df'], output_dir)

    if 'bootstrap_df' in all_results and METHODS_CONFIG.get('bootstrap', False):
        plot_bootstrap_ci(all_results['bootstrap_df'], output_dir)

    if 'importance_df' in all_results and METHODS_CONFIG.get('importance', False):
        plot_feature_importance(all_results['importance_df'], output_dir)

    if 'loadings_df' in all_results and METHODS_CONFIG.get('pca', False):
        plot_pca_loadings(all_results['loadings_df'], output_dir)

    if 'pattern_df' in all_results and METHODS_CONFIG.get('pattern', False) and corr_year_1 is not None:
        plot_correlation_matrices(corr_year_1, corr_year_2, year_1, year_2, output_dir)

    # ==========================================================================
    # ФИНАЛЬНЫЕ ГРАФИКИ ПОСЛЕ ОПТИМИЗАЦИИ
    # ==========================================================================
    print("\n" + "=" * 80)
    print("ФИНАЛЬНЫЕ ГРАФИКИ ПОСЛЕ ОПТИМИЗАЦИИ")
    print("=" * 80)

    if consensus_df is not None:
        plot_stable_hc_comparison_final(df, optimized_hc, consensus_df, year_1, year_2, output_dir,
                                        max_per_plot=MAX_HC_PER_PLOT_BOX)
        plot_parallel_coordinates_final(df, optimized_hc, consensus_df, year_1, year_2, output_dir)
        plot_correlation_heatmap_stable_final(df, optimized_hc, year_1, year_2, output_dir)
        plot_distribution_overlap_final(df, optimized_hc, consensus_df, year_1, year_2, output_dir,
                                        max_per_plot=MAX_HC_PER_PLOT_KDE)

        # ИСПОЛЬЗУЕТ ЕДИНУЮ ПРЕДОБРАБОТКУ
        centroid_dist_final = plot_pca_biplot_final(proportions_year_1, proportions_year_2, optimized_hc, year_1,
                                                    year_2, output_dir)

        print(f"\n📊 Финальный PCA Centroid Distance: {centroid_dist_final:.4f}")
        if centroid_dist_after > 0:
            print(
                f"   Сверка с pca_comparison_before_after: {abs(centroid_dist_final - centroid_dist_after):.6f} (должно быть ~0)")

    # ==========================================================================
    # ЭКСПОРТ (ДИНАМИЧЕСКИЙ)
    # ==========================================================================
    print("\n" + "=" * 80)
    print("ЭКСПОРТ РЕЗУЛЬТАТОВ")
    print("=" * 80)
    export_results(all_results, enabled_methods, output_dir)

    # ==========================================================================
    # ФИНАЛЬНЫЕ РЕКОМЕНДАЦИИ
    # ==========================================================================
    print("\n" + "=" * 80)
    print("ФИНАЛЬНЫЕ РЕКОМЕНДАЦИИ")
    print("=" * 80)

    print(f"\n✅ ОПТИМИЗИРОВАННЫЙ НАБОР ({len(optimized_hc)} УВ):")
    for i, hc in enumerate(optimized_hc, 1):
        if consensus_df is not None:
            score = consensus_df.set_index('hydrocarbon').loc[hc, 'consensus_score']
            print(f"   {i}. {hc} (score={score:.3f})")
        else:
            print(f"   {i}. {hc}")

    print("\n" + "=" * 80)
    print("АНАЛИЗ ЗАВЕРШЁН УСПЕШНО!")
    print("=" * 80)
    print(f"\nВсе файлы сохранены в: {output_dir}")
    print("=" * 80)

    return all_results, optimized_hc, optimization_history


# =============================================================================
# ЗАПУСК
# =============================================================================

if __name__ == "__main__":
    results, optimized_hc, history = main()