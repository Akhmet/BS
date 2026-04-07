"""
Hydrocarbon Profile Comparison Tool
Сравнение профилей углеводородов за разные годы
"""

import pandas as pd
import numpy as np
from scipy import stats
from scipy.spatial.distance import braycurtis, cosine
from sklearn.decomposition import PCA
from sklearn.covariance import EmpiricalCovariance
from sklearn.ensemble import IsolationForest
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Tuple, List, Dict, Optional
import warnings
warnings.filterwarnings('ignore')


class HydrocarbonComparator:
    """Основной класс для сравнения профилей углеводородов"""
    
    def __init__(self, similarity_threshold: float = 0.85):
        """
        Инициализация
        
        Parameters:
        -----------
        similarity_threshold : float
            Минимальный порог схожести (0-1). Чем выше, тем строже отбор.
        """
        self.similarity_threshold = similarity_threshold
        self.data_2009 = None
        self.data_2010 = None
        self.relative_2009 = None
        self.relative_2010 = None
        self.selected_hydrocarbons = None
        self.outlier_samples = {'2009': [], '2010': []}
        self.outlier_compounds = {'2009': [], '2010': []}
        
    def load_data(self, filepath: str, sample_col: str = 'номер пробы', 
                  year_col: str = 'год') -> None:
        """
        Загрузка данных из Excel файла
        
        Parameters:
        -----------
        filepath : str
            Путь к Excel файлу
        sample_col : str
            Название столбца с номерами проб
        year_col : str
            Название столбца с годами
        """
        df = pd.read_excel(filepath)
        
        # Разделение по годам
        self.data_2009 = df[df[year_col] == 2009].copy()
        self.data_2010 = df[df[year_col] == 2010].copy()
        
        # Сохранение идентификаторов проб
        self.sample_ids_2009 = self.data_2009[sample_col].values
        self.sample_ids_2010 = self.data_2010[sample_col].values
        
        # Удаление служебных столбцов
        hydrocarbon_cols = [col for col in df.columns if col not in [sample_col, year_col]]
        self.hydrocarbon_columns = hydrocarbon_cols
        
        print(f"Загружено {len(self.data_2009)} проб за 2009 год")
        print(f"Загружено {len(self.data_2010)} проб за 2010 год")
        print(f"Количество углеводородов: {len(hydrocarbon_cols)}")
        
    def convert_to_relative(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Перевод абсолютных концентраций в относительные (нормировка по сумме)
        
        Parameters:
        -----------
        data : pd.DataFrame
            DataFrame с абсолютными концентрациями
            
        Returns:
        --------
        pd.DataFrame
            DataFrame с относительными концентрациями (в долях единицы)
        """
        hydrocarbon_data = data[self.hydrocarbon_columns]
        
        # Замена нулей и отрицательных значений на малое положительное число
        hydrocarbon_data = hydrocarbon_data.clip(lower=1e-10)
        
        # Нормировка по сумме в каждой пробе
        sums = hydrocarbon_data.sum(axis=1)
        relative_data = hydrocarbon_data.div(sums, axis=0)
        
        return relative_data
    
    def prepare_data(self) -> None:
        """Подготовка данных: конвертация в относительные концентрации"""
        self.relative_2009 = self.convert_to_relative(self.data_2009)
        self.relative_2010 = self.convert_to_relative(self.data_2010)
        print("Данные конвертированы в относительные концентрации")
    
    def detect_sample_outliers(self, method: str = 'mahalanobis', 
                               contamination: float = 0.1) -> Dict:
        """
        Обнаружение выбросов среди проб
        
        Parameters:
        -----------
        method : str
            'mahalanobis' - расстояние Махаланобиса
            'isolation_forest' - изолирующий лес
            'iqr' - межквартильный размах
        contamination : float
            Ожидаемая доля выбросов (для isolation forest)
            
        Returns:
        --------
        Dict
            Словарь с выбросами по годам
        """
        outlier_results = {'2009': [], '2010': []}
        
        for year, data in [('2009', self.relative_2009), ('2010', self.relative_2010)]:
            if len(data) < 3:
                continue
                
            if method == 'mahalanobis':
                # Расстояние Махаланобиса
                try:
                    mean = data.mean().values.copy()
                    cov = data.cov().values.copy()
                    
                    # Регуляризация ковариационной матрицы
                    cov += np.eye(len(cov)) * 1e-6
                    
                    cov_inv = np.linalg.inv(cov)
                    
                    distances = []
                    for idx, row in data.iterrows():
                        diff = row.values - mean
                        d = np.sqrt(diff @ cov_inv @ diff)
                        distances.append(d)
                    
                    # Порог: среднее + 3*std
                    threshold = np.mean(distances) + 3 * np.std(distances)
                    outliers_idx = [i for i, d in enumerate(distances) if d > threshold]
                    sample_ids = self.sample_ids_2009 if year == '2009' else self.sample_ids_2010
                    outlier_results[year] = [sample_ids[i] for i in outliers_idx]
                    
                except Exception as e:
                    print(f"Ошибка при расчете расстояния Махаланобиса для {year}: {e}")
                    outlier_results[year] = []
                    
            elif method == 'isolation_forest':
                iso_forest = IsolationForest(contamination=contamination, random_state=42)
                predictions = iso_forest.fit_predict(data)
                outliers_idx = np.where(predictions == -1)[0]
                sample_ids = self.sample_ids_2009 if year == '2009' else self.sample_ids_2010
                outlier_results[year] = [sample_ids[i] for i in outliers_idx]
                                        
            elif method == 'iqr':
                Q1 = data.quantile(0.25)
                Q3 = data.quantile(0.75)
                IQR = Q3 - Q1
                
                # Выбросы если хотя бы один компонент за пределами 1.5*IQR
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                outlier_mask = ((data < lower_bound) | (data > upper_bound)).any(axis=1)
                outliers_idx = np.where(outlier_mask)[0]
                sample_ids = self.sample_ids_2009 if year == '2009' else self.sample_ids_2010
                outlier_results[year] = [sample_ids[i] for i in outliers_idx]
        
        self.outlier_samples = outlier_results
        
        print(f"\nВыбросы среди проб (метод: {method}):")
        print(f"2009: {outlier_results['2009']}")
        print(f"2010: {outlier_results['2010']}")
        
        return outlier_results
    
    def detect_compound_outliers(self, method: str = 'iqr') -> Dict:
        """
        Обнаружение выбросов среди углеводородов
        
        Parameters:
        -----------
        method : str
            'iqr' - межквартильный размах
            'zscore' - Z-оценка
            
        Returns:
        --------
        Dict
            Словарь с выбросами по годам
        """
        outlier_results = {'2009': [], '2010': []}
        
        for year, data in [('2009', self.relative_2009), ('2010', self.relative_2010)]:
            if method == 'iqr':
                Q1 = data.quantile(0.25)
                Q3 = data.quantile(0.75)
                IQR = Q3 - Q1
                
                lower_bound = Q1 - 3 * IQR  # Более строгий порог для компонентов
                upper_bound = Q3 + 3 * IQR
                
                # Компонент считается выбросом если много проб выходят за границы
                outlier_mask = ((data < lower_bound) | (data > upper_bound)).sum(axis=0) > len(data) * 0.3
                outlier_results[year] = data.columns[outlier_mask].tolist()
                
            elif method == 'zscore':
                z_scores = np.abs(stats.zscore(data))
                # Компонент с большим количеством экстремальных Z-оценок
                outlier_mask = (z_scores > 3).sum(axis=0) > len(data) * 0.3
                outlier_results[year] = data.columns[outlier_mask].tolist()
        
        self.outlier_compounds = outlier_results
        
        print(f"\nВыбросы среди углеводородов (метод: {method}):")
        print(f"2009: {outlier_results['2009']}")
        print(f"2010: {outlier_results['2010']}")
        
        return outlier_results
    
    def calculate_similarity_metrics(self, compounds: List[str]) -> Dict:
        """
        Расчет метрик схожести для заданного списка углеводородов
        
        Parameters:
        -----------
        compounds : List[str]
            Список названий углеводородов
            
        Returns:
        --------
        Dict
            Словарь с метриками схожести
        """
        data_09 = self.relative_2009[compounds]
        data_10 = self.relative_2010[compounds]
        
        # Медианные профили
        median_09 = data_09.median()
        median_10 = data_10.median()
        
        # 1. Косинусное сходство медианных профилей
        cos_sim = 1 - cosine(median_09.values, median_10.values)
        
        # 2. Расстояние Брея-Кертиса между медианами (преобразуем в схожесть)
        bc_dist = braycurtis(median_09.values, median_10.values)
        bc_sim = 1 - bc_dist
        
        # 3. Корреляция Спирмена между медианными профилями
        spearman_corr, _ = stats.spearmanr(median_09.values, median_10.values)
        
        # 4. PCA анализ - расстояние между центроидами
        combined_data = pd.concat([data_09, data_10], ignore_index=True)
        n_components = min(3, len(compounds), len(combined_data) - 1)
        
        if n_components >= 1:
            pca = PCA(n_components=n_components)
            pca_result = pca.fit_transform(combined_data)
            
            centroid_09 = pca_result[:len(data_09)].mean(axis=0)
            centroid_10 = pca_result[len(data_09):].mean(axis=0)
            
            pca_distance = np.linalg.norm(centroid_09 - centroid_10)
            # Преобразуем расстояние в схожесть (экспоненциальное затухание)
            pca_sim = np.exp(-pca_distance)
        else:
            pca_distance = np.inf
            pca_sim = 0
        
        # 5. Сравнение вариативности (отношение дисперсий)
        var_ratio_09 = data_09.var().mean()
        var_ratio_10 = data_10.var().mean()
        var_similarity = 1 - abs(var_ratio_09 - var_ratio_10) / max(var_ratio_09, var_ratio_10, 1e-10)
        
        # 6. Средняя попарная корреляция между пробами разных лет
        pairwise_corrs = []
        for idx_09 in range(len(data_09)):
            for idx_10 in range(len(data_10)):
                corr, _ = stats.spearmanr(data_09.iloc[idx_09].values, 
                                         data_10.iloc[idx_10].values)
                pairwise_corrs.append(corr)
        avg_pairwise_corr = np.mean(pairwise_corrs)
        
        # Общая интегральная метрика (взвешенное среднее)
        overall_similarity = (
            0.25 * cos_sim + 
            0.20 * bc_sim + 
            0.20 * spearman_corr + 
            0.20 * pca_sim + 
            0.15 * var_similarity
        )
        
        return {
            'cosine_similarity': cos_sim,
            'bray_curtis_similarity': bc_sim,
            'spearman_correlation': spearman_corr,
            'pca_centroid_distance': pca_distance,
            'pca_similarity': pca_sim,
            'variance_similarity': var_similarity,
            'avg_pairwise_correlation': avg_pairwise_corr,
            'overall_similarity': overall_similarity,
            'n_compounds': len(compounds)
        }
    
    def select_optimal_compounds(self, exclude_outliers: bool = True) -> List[str]:
        """
        Итеративный подбор оптимального списка углеводородов
        
        Алгоритм:
        1. Исключаем компоненты-выбросы
        2. Сортируем компоненты по индивидуальной схожести
        3. Жадно добавляем компоненты, пока общая схожесть не упадет ниже порога
        
        Parameters:
        -----------
        exclude_outliers : bool
            Исключать ли компоненты-выбросы
            
        Returns:
        --------
        List[str]
            Оптимальный список углеводородов
        """
        # Начальный список компонентов
        if exclude_outliers:
            all_compounds = set(self.hydrocarbon_columns) - \
                           set(self.outlier_compounds['2009']) - \
                           set(self.outlier_compounds['2010'])
        else:
            all_compounds = set(self.hydrocarbon_columns)
        
        all_compounds = list(all_compounds)
        
        # Расчет индивидуальной схожести для каждого компонента
        compound_scores = {}
        for comp in all_compounds:
            metrics = self.calculate_similarity_metrics([comp])
            compound_scores[comp] = metrics['overall_similarity']
        
        # Сортировка по убыванию схожести
        sorted_compounds = sorted(compound_scores.keys(), 
                                 key=lambda x: compound_scores[x], 
                                 reverse=True)
        
        print(f"\nНачинаем отбор из {len(sorted_compounds)} компонентов...")
        print(f"Порог схожести: {self.similarity_threshold}")
        
        # Жадный алгоритм подбора
        selected = []
        best_overall_sim = 0
        
        for comp in sorted_compounds:
            test_list = selected + [comp]
            metrics = self.calculate_similarity_metrics(test_list)
            
            if metrics['overall_similarity'] >= self.similarity_threshold:
                selected.append(comp)
                best_overall_sim = metrics['overall_similarity']
                print(f"Добавлен {comp}: общая схожесть = {best_overall_sim:.3f}, "
                      f"кол-во компонентов = {len(selected)}")
            else:
                # Если еще ничего не добавлено, пробуем добавить компонент anyway
                if len(selected) == 0:
                    selected.append(comp)
                    best_overall_sim = metrics['overall_similarity']
                    print(f"Добавлен первый компонент {comp}: схожесть = {best_overall_sim:.3f}")
                # Пробуем добавить следующий по списку
                continue
        
        self.selected_hydrocarbons = selected
        
        print(f"\n=== ИТОГ ===")
        print(f"Отобрано компонентов: {len(selected)} из {len(all_compounds)}")
        print(f"Итоговая схожесть: {best_overall_sim:.3f}")
        print(f"Список: {selected}")
        
        return selected
    
    def get_final_metrics(self) -> Dict:
        """Получить финальные метрики для отобранных компонентов"""
        if self.selected_hydrocarbons is None:
            raise ValueError("Сначала выполните select_optimal_compounds()")
        
        return self.calculate_similarity_metrics(self.selected_hydrocarbons)
    
    def visualize_results(self, save_dir: str = './results') -> None:
        """
        Визуализация результатов сравнения
        
        Parameters:
        -----------
        save_dir : str
            Директория для сохранения графиков
        """
        import os
        os.makedirs(save_dir, exist_ok=True)
        
        if self.selected_hydrocarbons is None:
            raise ValueError("Сначала выполните select_optimal_compounds()")
        
        compounds = self.selected_hydrocarbons
        data_09 = self.relative_2009[compounds]
        data_10 = self.relative_2010[compounds]
        
        # Настройка стиля
        plt.style.use('seaborn-v0_8-whitegrid')
        
        # 1. Heatmap медианных профилей
        fig, ax = plt.subplots(figsize=(12, 6))
        
        if len(compounds) == 0:
            print("Нет отобранных компонентов для визуализации")
            return
        
        median_df = pd.DataFrame({
            '2009': data_09.median(),
            '2010': data_10.median()
        })
        
        # Логарифмическая шкала для лучшей визуализации
        median_df_log = np.log10(median_df + 1e-10)
        
        sns.heatmap(median_df_log.T, annot=False, cmap='RdYlBu_r', ax=ax,
                   cbar_kws={'label': 'log10(относительная концентрация)'})
        ax.set_title('Heatmap медианных профилей (логарифмическая шкала)', fontsize=14)
        plt.tight_layout()
        plt.savefig(f'{save_dir}/heatmap_medians.png', dpi=300)
        plt.close()
        
        # 2. Scatter plot: 2009 vs 2010 для медиан
        fig, ax = plt.subplots(figsize=(8, 8))
        ax.scatter(median_df['2009'], median_df['2010'], s=100, alpha=0.7, 
                  edgecolors='black', linewidth=1)
        
        # Линия y=x
        min_val = min(median_df.min().min(), 1e-6)
        max_val = max(median_df.max().max(), 1e-3)
        ax.plot([min_val, max_val], [min_val, max_val], 'r--', label='y=x')
        
        ax.set_xscale('log')
        ax.set_yscale('log')
        ax.set_xlabel('2009 (медиана)', fontsize=12)
        ax.set_ylabel('2010 (медиана)', fontsize=12)
        ax.set_title('Сравнение медианных концентраций', fontsize=14)
        ax.legend()
        plt.tight_layout()
        plt.savefig(f'{save_dir}/scatter_medians.png', dpi=300)
        plt.close()
        
        # 3. Box plots для ключевых компонентов
        n_show = min(12, len(compounds))
        top_compounds = compounds[:n_show]
        
        fig, axes = plt.subplots(3, 4, figsize=(20, 15))
        axes = axes.flatten()
        
        for idx, comp in enumerate(top_compounds):
            data_to_plot = [data_09[comp].values, data_10[comp].values]
            bp = axes[idx].boxplot(data_to_plot, patch_artist=True, labels=['2009', '2010'])
            
            # Раскраска
            colors = ['#1f77b4', '#ff7f0e']
            for patch, color in zip(bp['boxes'], colors):
                patch.set_facecolor(color)
                patch.set_alpha(0.7)
            
            axes[idx].set_title(comp, fontsize=10)
            axes[idx].set_ylabel('Относит. конц.')
            axes[idx].set_yscale('log')
        
        plt.suptitle('Распределения относительных концентраций (топ-12 компонентов)', 
                    fontsize=16, y=0.995)
        plt.tight_layout()
        plt.savefig(f'{save_dir}/boxplots_top.png', dpi=300)
        plt.close()
        
        # 4. PCA biplot
        combined_data = pd.concat([data_09, data_10], ignore_index=True)
        labels = [0] * len(data_09) + [1] * len(data_10)
        label_names = ['2009', '2010']
        
        n_pca = min(3, len(compounds), len(combined_data) - 1)
        if n_pca >= 2:
            pca = PCA(n_components=2)
            pca_result = pca.fit_transform(combined_data)
            
            fig, ax = plt.subplots(figsize=(10, 8))
            
            # Точки проб
            scatter = ax.scatter(pca_result[:, 0], pca_result[:, 1], 
                               c=labels, cmap='Set1', s=100, alpha=0.7,
                               edgecolors='black', linewidth=1)
            
            # Легенда с правильными метками
            legend_elements = [plt.Line2D([0], [0], marker='o', color='w', 
                                          markerfacecolor=color, markersize=10,
                                          label=name, linestyle='None') 
                              for color, name in zip(['#1f77b4', '#ff7f0e'], label_names)]
            ax.legend(handles=legend_elements, title='Год')
            
            ax.set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]*100:.1f}%)', fontsize=12)
            ax.set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]*100:.1f}%)', fontsize=12)
            ax.set_title('PCA: Проекция проб на первые две компоненты', fontsize=14)
            plt.tight_layout()
            plt.savefig(f'{save_dir}/pca_biplot.png', dpi=300)
            plt.close()
        
        # 5. Parallel coordinates
        if len(compounds) <= 15:
            fig, ax = plt.subplots(figsize=(14, 8))
            
            # Нормировка для лучшей визуализации
            data_09_norm = (data_09 - data_09.min()) / (data_09.max() - data_09.min() + 1e-10)
            data_10_norm = (data_10 - data_10.min()) / (data_10.max() - data_10.min() + 1e-10)
            
            for idx in range(len(data_09_norm)):
                ax.plot(range(len(compounds)), data_09_norm.iloc[idx].values, 
                       'b-', alpha=0.3, linewidth=1)
            
            for idx in range(len(data_10_norm)):
                ax.plot(range(len(compounds)), data_10_norm.iloc[idx].values, 
                       'r-', alpha=0.3, linewidth=1)
            
            # Медианы
            ax.plot(range(len(compounds)), 
                   (median_df['2009'] - median_df['2009'].min()) / 
                   (median_df['2009'].max() - median_df['2009'].min() + 1e-10),
                   'b-', linewidth=3, label='2009 медиана')
            ax.plot(range(len(compounds)), 
                   (median_df['2010'] - median_df['2010'].min()) / 
                   (median_df['2010'].max() - median_df['2010'].min() + 1e-10),
                   'r-', linewidth=3, label='2010 медиана')
            
            ax.set_xticks(range(len(compounds)))
            ax.set_xticklabels(compounds, rotation=45, ha='right')
            ax.set_xlabel('Углеводороды', fontsize=12)
            ax.set_ylabel('Нормированная относительная концентрация', fontsize=12)
            ax.set_title('Parallel Coordinates Plot', fontsize=14)
            ax.legend()
            plt.tight_layout()
            plt.savefig(f'{save_dir}/parallel_coords.png', dpi=300)
            plt.close()
        
        # 6. Bar chart метрик схожести
        metrics = self.get_final_metrics()
        metric_names = {
            'cosine_similarity': 'Косинусное сходство',
            'bray_curtis_similarity': 'Брей-Кертис',
            'spearman_correlation': 'Корреляция Спирмена',
            'pca_similarity': 'PCA схожесть',
            'variance_similarity': 'Схожесть вариативности',
            'avg_pairwise_correlation': 'Средняя попарная корр.',
            'overall_similarity': 'Общая схожесть'
        }
        
        fig, ax = plt.subplots(figsize=(10, 6))
        values = [metrics[k] for k in metric_names.keys()]
        names = list(metric_names.values())
        
        colors = ['#2ecc71' if v >= self.similarity_threshold else '#e74c3c' 
                 for v in values]
        
        bars = ax.bar(names, values, color=colors, alpha=0.8, edgecolor='black')
        ax.axhline(y=self.similarity_threshold, color='red', linestyle='--', 
                  linewidth=2, label=f'Порог ({self.similarity_threshold})')
        
        ax.set_ylim(0, 1.1)
        ax.set_ylabel('Значение', fontsize=12)
        ax.set_title('Метрики схожести профилей', fontsize=14)
        ax.legend()
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(f'{save_dir}/similarity_metrics.png', dpi=300)
        plt.close()
        
        print(f"\nГрафики сохранены в директорию: {save_dir}")
    
    def save_results(self, output_path: str) -> None:
        """
        Сохранение результатов в Excel файл
        
        Parameters:
        -----------
        output_path : str
            Путь к выходному Excel файлу
        """
        if self.selected_hydrocarbons is None:
            raise ValueError("Сначала выполните select_optimal_compounds()")
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # 1. Список отобранных углеводородов
            df_compounds = pd.DataFrame({
                'Углеводород': self.selected_hydrocarbons,
                'Индекс': range(len(self.selected_hydrocarbons))
            })
            df_compounds.to_excel(writer, sheet_name='Отобранные_компоненты', index=False)
            
            # 2. Метрики схожести
            metrics = self.get_final_metrics()
            df_metrics = pd.DataFrame({
                'Метрика': list(metrics.keys()),
                'Значение': list(metrics.values())
            })
            df_metrics.to_excel(writer, sheet_name='Метрики_схожести', index=False)
            
            # 3. Относительные концентрации 2009
            df_2009 = self.relative_2009[self.selected_hydrocarbons].copy()
            df_2009.insert(0, 'Номер_пробы', self.sample_ids_2009)
            df_2009.to_excel(writer, sheet_name='Данные_2009', index=False)
            
            # 4. Относительные концентрации 2010
            df_2010 = self.relative_2010[self.selected_hydrocarbons].copy()
            df_2010.insert(0, 'Номер_пробы', self.sample_ids_2010)
            df_2010.to_excel(writer, sheet_name='Данные_2010', index=False)
            
            # 5. Выбросы
            df_outliers = pd.DataFrame({
                'Тип': ['Пробы_2009', 'Пробы_2010', 'Компоненты_2009', 'Компоненты_2010'],
                'Выбросы': [
                    ', '.join(map(str, self.outlier_samples['2009'])),
                    ', '.join(map(str, self.outlier_samples['2010'])),
                    ', '.join(self.outlier_compounds['2009']),
                    ', '.join(self.outlier_compounds['2010'])
                ]
            })
            df_outliers.to_excel(writer, sheet_name='Выбросы', index=False)
            
            # 6. Статистика по компонентам
            stats_data = []
            for comp in self.selected_hydrocarbons:
                stats_data.append({
                    'Компонент': comp,
                    'Медиана_2009': self.relative_2009[comp].median(),
                    'Медиана_2010': self.relative_2010[comp].median(),
                    'IQR_2009': self.relative_2009[comp].quantile(0.75) - 
                               self.relative_2009[comp].quantile(0.25),
                    'IQR_2010': self.relative_2010[comp].quantile(0.75) - 
                               self.relative_2010[comp].quantile(0.25),
                    'Индив_схожесть': self.calculate_similarity_metrics([comp])['overall_similarity']
                })
            
            df_stats = pd.DataFrame(stats_data)
            df_stats.to_excel(writer, sheet_name='Статистика_компонентов', index=False)
        
        print(f"\nРезультаты сохранены в файл: {output_path}")


# Пример использования
if __name__ == '__main__':
    # Инициализация с порогом схожести
    comparator = HydrocarbonComparator(similarity_threshold=0.85)
    
    # Загрузка данных
    # ЗАМЕНИТЕ 'your_data.xlsx' НА ПУТЬ К ВАШЕМУ ФАЙЛУ
    comparator.load_data('your_data.xlsx', sample_col='номер пробы', year_col='год')
    
    # Подготовка данных
    comparator.prepare_data()
    
    # Поиск выбросов
    comparator.detect_sample_outliers(method='mahalanobis')
    comparator.detect_compound_outliers(method='iqr')
    
    # Подбор оптимального списка
    selected = comparator.select_optimal_compounds(exclude_outliers=True)
    
    # Визуализация
    comparator.visualize_results(save_dir='./results')
    
    # Сохранение результатов
    comparator.save_results('results.xlsx')
    
    print("\n=== Все шаги выполнены успешно ===")
