# coding: utf-8
"""
数据分析与报告生成服务

提供数据提取、分析、可视化、报告生成等功能
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from enum import Enum

import pandas as pd
import numpy as np

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

import config
from app.utils.db_utils import db_manager


# ==================== 报告类型枚举 ====================
class ReportType(Enum):
    """报告类型"""
    SALES = "sales"  # 销售报告
    USER_BEHAVIOR = "user_behavior"  # 用户行为报告
    PERFORMANCE = "performance"  # 性能报告
    FINANCIAL = "financial"  # 财务报告
    CUSTOM = "custom"  # 自定义报告


# ==================== 数据提取器 ====================
class DataExtractor:
    """数据提取器"""
    
    def __init__(self):
        """初始化数据提取器"""
        self.db = db_manager.get('zj3')
    
    def extract_from_database(
        self,
        query: str,
        params: Dict = None
    ) -> List[Dict]:
        """
        从数据库提取数据
        
        Args:
            query: SQL查询语句
            params: 查询参数
            
        Returns:
            数据列表
        """
        try:
            cursor = self.db.execute_sql(query, params or {})
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            print(f"数据库查询失败: {e}")
            return []
    
    def extract_from_file(
        self,
        file_path: str,
        file_type: str = None
    ) -> pd.DataFrame:
        """
        从文件提取数据
        
        Args:
            file_path: 文件路径
            file_type: 文件类型
            
        Returns:
            DataFrame
        """
        try:
            if file_type is None:
                if file_path.endswith('.csv'):
                    file_type = 'csv'
                elif file_path.endswith(('.xlsx', '.xls')):
                    file_type = 'excel'
                elif file_path.endswith('.json'):
                    file_type = 'json'
                else:
                    raise ValueError(f"不支持的文件类型: {file_path}")
            
            if file_type == 'csv':
                return pd.read_csv(file_path, encoding='utf-8')
            elif file_type == 'excel':
                return pd.read_excel(file_path)
            elif file_type == 'json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return pd.DataFrame(data)
            else:
                raise ValueError(f"不支持的文件类型: {file_type}")
        except Exception as e:
            print(f"文件读取失败: {e}")
            return pd.DataFrame()
    
    def generate_sample_data(
        self,
        data_type: str,
        rows: int = 100
    ) -> pd.DataFrame:
        """
        生成示例数据
        
        Args:
            data_type: 数据类型 (sales/users/performance)
            rows: 行数
            
        Returns:
            DataFrame
        """
        np.random.seed(42)
        
        if data_type == 'sales':
            dates = pd.date_range(
                start=datetime.now() - timedelta(days=rows),
                periods=rows,
                freq='D'
            )
            return pd.DataFrame({
                'date': dates,
                'product': np.random.choice(['产品A', '产品B', '产品C'], rows),
                'category': np.random.choice(['电子产品', '服装', '食品'], rows),
                'sales': np.random.randint(100, 10000, rows),
                'profit': np.random.randint(10, 3000, rows),
                'region': np.random.choice(['华东', '华南', '华北', '西部'], rows)
            })
        elif data_type == 'users':
            return pd.DataFrame({
                'user_id': range(1, rows + 1),
                'age': np.random.randint(18, 65, rows),
                'gender': np.random.choice(['男', '女'], rows),
                'city': np.random.choice(['北京', '上海', '广州', '深圳'], rows),
                'login_count': np.random.randint(1, 100, rows),
                'purchase_amount': np.random.uniform(0, 5000, rows)
            })
        elif data_type == 'performance':
            dates = pd.date_range(
                start=datetime.now() - timedelta(days=rows),
                periods=rows,
                freq='D'
            )
            return pd.DataFrame({
                'date': dates,
                'cpu_usage': np.random.uniform(10, 90, rows),
                'memory_usage': np.random.uniform(20, 80, rows),
                'response_time': np.random.uniform(100, 1000, rows),
                'error_rate': np.random.uniform(0, 5, rows)
            })
        else:
            return pd.DataFrame()


# ==================== 数据分析器 ====================
class DataAnalyzer:
    """数据分析器"""
    
    def __init__(self):
        """初始化数据分析器"""
        self.llm = self._create_llm()
    
    def _create_llm(self):
        """创建LLM实例"""
        llm_cfg = config.LLM.get('openai', config.LLM.get('modelscope', {}))
        return ChatOpenAI(
            model="gpt-4o",
            api_key=llm_cfg.get('api_key'),
            base_url=llm_cfg.get('base_url'),
            temperature=0.3
        )
    
    def calculate_statistics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        计算基本统计信息
        
        Args:
            df: DataFrame
            
        Returns:
            统计信息字典
        """
        stats = {
            'row_count': len(df),
            'column_count': len(df.columns),
            'columns': list(df.columns),
            'numeric_stats': {},
            'categorical_stats': {}
        }
        
        # 数值列统计
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            stats['numeric_stats'][col] = {
                'mean': float(df[col].mean()),
                'median': float(df[col].median()),
                'std': float(df[col].std()),
                'min': float(df[col].min()),
                'max': float(df[col].max()),
                'count': int(df[col].count())
            }
        
        # 分类列统计
        categorical_cols = df.select_dtypes(include=['object']).columns
        for col in categorical_cols:
            stats['categorical_stats'][col] = {
                'unique_count': int(df[col].nunique()),
                'top_values': df[col].value_counts().head(5).to_dict()
            }
        
        return stats
    
    def detect_anomalies(
        self,
        df: pd.DataFrame,
        column: str,
        method: str = 'iqr'
    ) -> List[Dict]:
        """
        检测异常值
        
        Args:
            df: DataFrame
            column: 列名
            method: 检测方法 (iqr/zscore)
            
        Returns:
            异常值列表
        """
        if column not in df.columns or not pd.api.types.is_numeric_dtype(df[column]):
            return []
        
        anomalies = []
        
        if method == 'iqr':
            Q1 = df[column].quantile(0.25)
            Q3 = df[column].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            anomalies_df = df[(df[column] < lower_bound) | (df[column] > upper_bound)]
            
            for idx, row in anomalies_df.iterrows():
                anomalies.append({
                    'index': int(idx),
                    'value': float(row[column]),
                    'type': 'outlier'
                })
        
        elif method == 'zscore':
            mean = df[column].mean()
            std = df[column].std()
            threshold = 3
            
            z_scores = np.abs((df[column] - mean) / std)
            anomalies_df = df[z_scores > threshold]
            
            for idx, row in anomalies_df.iterrows():
                anomalies.append({
                    'index': int(idx),
                    'value': float(row[column]),
                    'z_score': float(z_scores[idx]),
                    'type': 'outlier'
                })
        
        return anomalies
    
    def trend_analysis(
        self,
        df: pd.DataFrame,
        date_column: str,
        value_column: str,
        period: str = 'daily'
    ) -> Dict[str, Any]:
        """
        趋势分析
        
        Args:
            df: DataFrame
            date_column: 日期列名
            value_column: 数值列名
            period: 时间周期 (daily/weekly/monthly)
            
        Returns:
            趋势分析结果
        """
        if date_column not in df.columns or value_column not in df.columns:
            return {}
        
        df_copy = df.copy()
        df_copy[date_column] = pd.to_datetime(df_copy[date_column])
        
        if period == 'daily':
            df_copy['period'] = df_copy[date_column].dt.date
        elif period == 'weekly':
            df_copy['period'] = df_copy[date_column].dt.to_period('W').dt.start_time
        elif period == 'monthly':
            df_copy['period'] = df_copy[date_column].dt.to_period('M').dt.start_time
        
        grouped = df_copy.groupby('period')[value_column].agg(['mean', 'sum', 'count'])
        
        # 计算增长率
        grouped['growth_rate'] = grouped['mean'].pct_change() * 100
        
        return {
            'period': period,
            'trend_data': grouped.reset_index().to_dict('records'),
            'average_growth': grouped['growth_rate'].mean(),
            'total_sum': grouped['sum'].sum()
        }
    
    def generate_insights(
        self,
        df: pd.DataFrame,
        analysis_type: str = 'general'
    ) -> List[str]:
        """
        使用LLM生成数据洞察
        
        Args:
            df: DataFrame
            analysis_type: 分析类型
            
        Returns:
            洞察列表
        """
        # 获取数据摘要
        stats = self.calculate_statistics(df)
        data_summary = json.dumps(stats, ensure_ascii=False, indent=2)
        
        prompt = f"""基于以下数据统计信息，生成3-5条关键洞察。

数据类型：{analysis_type}
数据摘要：
{data_summary[:2000]}

请提供：
1. 数据的主要特征
2. 值得注意的趋势或模式
3. 潜在的问题或机会

每条洞察应该简洁明了，具有实际价值。"""
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            insights_text = response.content
            
            # 简单分割洞察
            insights = []
            for line in insights_text.split('\n'):
                line = line.strip()
                if line and (line.startswith('-') or line.startswith('•') or line.startswith('1.') or line.startswith('2.') or line.startswith('3.')):
                    insights.append(line.lstrip('-•0123456789. ').strip())
            
            if not insights:
                insights = [insights_text]
            
            return insights[:5]
        except Exception as e:
            print(f"生成洞察失败: {e}")
            return ["数据量充足，包含多个维度", "建议进一步分析特定维度的趋势"]


# ==================== 报告生成器 ====================
class ReportGenerator:
    """报告生成器"""
    
    def __init__(self):
        """初始化报告生成器"""
        self.llm = self._create_llm()
    
    def _create_llm(self):
        """创建LLM实例"""
        llm_cfg = config.LLM.get('openai', config.LLM.get('modelscope', {}))
        return ChatOpenAI(
            model="gpt-4o",
            api_key=llm_cfg.get('api_key'),
            base_url=llm_cfg.get('base_url'),
            temperature=0.5
        )
    
    def generate_text_report(
        self,
        data: pd.DataFrame,
        stats: Dict,
        insights: List[str],
        report_type: str = 'general'
    ) -> str:
        """
        生成文本报告
        
        Args:
            data: DataFrame
            stats: 统计信息
            insights: 洞察列表
            report_type: 报告类型
            
        Returns:
            报告文本
        """
        data_summary = json.dumps(stats, ensure_ascii=False, indent=2)
        insights_text = '\n'.join([f"- {insight}" for insight in insights])
        
        prompt = f"""生成一份专业的数据分析报告。

报告类型：{report_type}
生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

数据统计：
{data_summary[:1500]}

关键洞察：
{insights_text}

报告应包含：
1. 执行摘要
2. 数据概览
3. 关键发现
4. 详细分析
5. 建议

使用专业的商业语言，格式清晰，使用Markdown格式。"""
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            return response.content
        except Exception as e:
            print(f"生成报告失败: {e}")
            return f"报告生成失败: {str(e)}"
    
    def generate_summary(self, report: str, max_length: int = 300) -> str:
        """
        生成报告摘要
        
        Args:
            report: 完整报告
            max_length: 最大长度
            
        Returns:
            摘要文本
        """
        prompt = f"""为以下报告生成一个简洁的摘要（不超过{max_length}字）。

报告内容：
{report[:2000]}

摘要应该包含报告的核心结论和最重要的发现。"""
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            return response.content[:max_length]
        except Exception as e:
            print(f"生成摘要失败: {e}")
            return report[:max_length]


# ==================== 数据分析服务主类 ====================
class DataAnalysisService:
    """数据分析服务主类"""
    
    def __init__(self):
        """初始化数据分析服务"""
        self.extractor = DataExtractor()
        self.analyzer = DataAnalyzer()
        self.generator = ReportGenerator()
    
    def analyze_report(
        self,
        data_source: str = None,
        data_type: str = 'sales',
        query: str = None,
        report_type: str = 'general'
    ) -> Dict[str, Any]:
        """
        执行完整的数据分析并生成报告
        
        Args:
            data_source: 数据源（文件路径或数据库查询）
            data_type: 数据类型
            query: SQL查询语句（如果从数据库提取）
            report_type: 报告类型
            
        Returns:
            分析结果和报告
        """
        # 1. 提取数据
        if data_source and data_source.endswith(('.csv', '.xlsx', '.xls', '.json')):
            df = self.extractor.extract_from_file(data_source)
        elif query:
            df = pd.DataFrame(self.extractor.extract_from_database(query))
        else:
            df = self.extractor.generate_sample_data(data_type)
        
        if df.empty:
            return {
                'success': False,
                'message': '数据提取失败或数据为空'
            }
        
        # 2. 计算统计信息
        stats = self.analyzer.calculate_statistics(df)
        
        # 3. 生成洞察
        insights = self.analyzer.generate_insights(df, data_type)
        
        # 4. 生成报告
        report = self.generator.generate_text_report(df, stats, insights, report_type)
        
        # 5. 生成摘要
        summary = self.generator.generate_summary(report)
        
        return {
            'success': True,
            'data_summary': {
                'row_count': stats['row_count'],
                'column_count': stats['column_count'],
                'columns': stats['columns']
            },
            'statistics': stats,
            'insights': insights,
            'report': report,
            'summary': summary,
            'generated_at': datetime.now().isoformat()
        }
    
    def quick_analysis(
        self,
        data_source: str,
        columns: List[str] = None
    ) -> Dict[str, Any]:
        """
        快速分析
        
        Args:
            data_source: 数据源
            columns: 要分析的列
            
        Returns:
            快速分析结果
        """
        df = self.extractor.extract_from_file(data_source)
        
        if columns:
            df = df[columns]
        
        stats = self.analyzer.calculate_statistics(df)
        insights = self.analyzer.generate_insights(df, 'quick')
        
        return {
            'success': True,
            'statistics': stats,
            'insights': insights
        }


# ==================== 使用示例 ====================
if __name__ == "__main__":
    # 创建数据分析服务
    service = DataAnalysisService()
    
    print("=" * 60)
    print("数据分析与报告生成示例")
    print("=" * 60)
    
    # 示例1：生成销售数据报告
    print("\n正在生成销售数据分析报告...")
    result1 = service.analyze_report(
        data_type='sales',
        report_type='销售分析'
    )
    
    if result1['success']:
        print(f"\n数据摘要:")
        print(f"  - 行数: {result1['data_summary']['row_count']}")
        print(f"  - 列数: {result1['data_summary']['column_count']}")
        
        print(f"\n关键洞察:")
        for insight in result1['insights']:
            print(f"  - {insight}")
        
        print(f"\n报告摘要:")
        print(f"  {result1['summary']}")
        
        print(f"\n完整报告:")
        print(result1['report'][:500] + "...")
    
    # 示例2：快速分析
    print("\n" + "=" * 60)
    print("快速分析示例")
    print("=" * 60)
    
    # 生成示例文件
    sample_file = "sample_data.csv"
    sample_df = service.extractor.generate_sample_data('users', 50)
    sample_df.to_csv(sample_file, index=False, encoding='utf-8')
    
    print(f"\n已生成示例文件: {sample_file}")
    
    quick_result = service.quick_analysis(sample_file, columns=['age', 'city', 'purchase_amount'])
    
    if quick_result['success']:
        print(f"\n统计信息:")
        for col, col_stats in quick_result['statistics']['numeric_stats'].items():
            print(f"  {col}:")
            print(f"    平均值: {col_stats['mean']:.2f}")
            print(f"    最小值: {col_stats['min']:.2f}")
            print(f"    最大值: {col_stats['max']:.2f}")
        
        print(f"\n快速洞察:")
        for insight in quick_result['insights']:
            print(f"  - {insight}")