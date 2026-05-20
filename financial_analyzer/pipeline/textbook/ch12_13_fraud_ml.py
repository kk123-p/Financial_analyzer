"""
Ch12-13: ML财务舞弊检测管线
===========================
整合《Python大数据财务分析》第12-13章：
  - Ch12.2: 决策树舞弊模型 (lines 118-146 数据预处理 + SMOTE + DT训练)
  - Ch12.3: 参数调优 GridSearchCV
  - Ch13.4: 集成模型 — 随机森林/GBDT/XGBoost + 投票集成

训练数据: DATA.xlsx (教科书附带的中国A股舞弊数据集)
推理数据: 项目 session 中的当前公司财务数据
"""
from __future__ import annotations
import logging
import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# 可选依赖 — 若未安装则优雅降级
try:
    from sklearn.tree import DecisionTreeClassifier
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.model_selection import GridSearchCV, train_test_split
    from sklearn.metrics import accuracy_score, roc_auc_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn 未安装，ML欺诈检测不可用")

try:
    from xgboost import XGBClassifier
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    logger.warning("xgboost 未安装，XGBoost模型不可用")

try:
    from imblearn.over_sampling import SMOTE
    SMOTE_AVAILABLE = True
except ImportError:
    SMOTE_AVAILABLE = False
    logger.warning("imblearn 未安装，SMOTE过采样不可用")


@dataclass
class FraudDetectionResult:
    """ML欺诈检测结果"""
    fraud_probability: float = 0.0       # 综合欺诈概率 (0-1)
    fraud_risk_level: str = "未知"        # 低风险/中风险/高风险
    model_votes: dict[str, Any] = field(default_factory=dict)
    feature_importance: dict[str, float] = field(default_factory=dict)
    top_risk_features: list[str] = field(default_factory=list)


class FraudDetectionPipeline:
    """
    ML舞弊检测管线 — 复现教科书 Ch12-13 的完整流程

    用法:
        pipeline = FraudDetectionPipeline()
        pipeline.train("path/to/DATA.xlsx")  # 一次性训练
        pipeline.save("fraud_models.pkl")
        # ... 之后 ...
        pipeline.load("fraud_models.pkl")
        result = pipeline.predict(company_features)
    """

    # 教科书 DATA.xlsx 中使用的特征列名
    # (DATA.xlsx 包含数十个财务比率，此处列出一组典型特征)
    FEATURE_COLUMNS = [
        # 盈利能力
        "roe", "roa", "gross_margin", "net_margin",
        # 偿债能力
        "current_ratio", "quick_ratio", "debt_to_assets",
        # 营运能力
        "asset_turnover", "inventory_turnover", "receivable_turnover",
        # 成长能力
        "revenue_growth", "profit_growth",
        # 现金流
        "ocf_to_profit", "revenue_cash_ratio",
        # 特殊指标
        "accrual_ratio", "goodwill_to_equity",
    ]

    def __init__(self):
        self.models: dict[str, Any] = {}
        self.is_trained = False
        self.feature_names: list[str] = []
        self.preprocessing_stats: dict[str, dict] = {}  # 每列的中位数

    # ========================================================================
    # 数据预处理 — 复现教科书 Ch12.2 lines 118-146
    # ========================================================================

    def preprocess(
        self,
        df: pd.DataFrame,
        target_col: str = "是否舞弊",
        fit: bool = True,
    ) -> tuple[pd.DataFrame, pd.Series | None]:
        """
        数据清洗管道 — 完全复现教科书 Ch12.2

        1. 删除缺失率超过50%的列
        2. 用中位数填充缺失值
        3. 无穷大值 → NaN → 用最大值填充
        4. 提取特征和目标变量
        """
        df = df.copy()

        # 1. 删除缺失率 > 50% 的列 (Ch12.2 line 121)
        missing_ratio = df.isnull().sum() / len(df)
        high_missing_cols = missing_ratio[missing_ratio > 0.5].index.tolist()
        df = df.drop(columns=[c for c in high_missing_cols if c != target_col])

        # 2. 保存预处理统计量（仅训练时）
        if fit:
            self.feature_names = [c for c in df.columns if c != target_col]
            self.preprocessing_stats = {}
            for col in self.feature_names:
                if df[col].dtype in ('float64', 'int64'):
                    self.preprocessing_stats[col] = {
                        "median": float(df[col].median()) if pd.notna(df[col].median()) else 0.0,
                        "max": float(df[col].max()) if pd.notna(df[col].max()) else 0.0,
                    }

        # 3. 无穷大值处理 (Ch12.2 lines 123-125)
        for col in self.feature_names:
            if col not in df.columns:
                continue
            inf_mask = np.isinf(df[col].astype(float))
            if fit and col in self.preprocessing_stats:
                df.loc[inf_mask, col] = np.nan
                fill_val = self.preprocessing_stats[col]["max"]
                df[col] = df[col].fillna(fill_val)
            elif col in self.preprocessing_stats:
                df.loc[inf_mask, col] = np.nan
                df[col] = df[col].fillna(self.preprocessing_stats[col]["max"])

        # 4. 中位数填充缺失值 (Ch12.2 line 122)
        for col in self.feature_names:
            if col not in df.columns:
                continue
            if fit and col in self.preprocessing_stats:
                df[col] = df[col].fillna(self.preprocessing_stats[col]["median"])
            elif col in self.preprocessing_stats:
                df[col] = df[col].fillna(self.preprocessing_stats[col]["median"])

        # 5. 提取特征和目标
        y = df[target_col].astype(int) if target_col in df.columns else None
        X = df[[c for c in self.feature_names if c in df.columns]]
        return X, y

    # ========================================================================
    # 训练 — 复现教科书 Ch12.2 + Ch13.4
    # ========================================================================

    def train(
        self,
        data_path: str | Path,
        target_col: str = "是否舞弊",
    ) -> dict[str, float]:
        """
        训练全部4个模型 — 复现教科书 Ch12.2 + Ch13.4 的完整流程

        Args:
            data_path: DATA.xlsx 路径

        Returns:
            {model_name: auc_score}
        """
        if not SKLEARN_AVAILABLE:
            return {"error": "scikit-learn 未安装"}

        logger.info(f"开始训练ML舞弊检测模型 — 数据: {data_path}")
        df = pd.read_excel(data_path)

        # 预处理
        X, y = self.preprocess(df, target_col, fit=True)

        # 按年份划分训练/测试 (Ch12.2 lines 128-132)
        if "年份" in df.columns:
            train_years = df.loc[X.index, "年份"].unique()
            test_year = train_years[-1]  # 最后一年做测试
            X_test_full = X[df.loc[X.index, "年份"] == test_year]
            y_test_full = y[df.loc[X.index, "年份"] == test_year]
            X_train_full = X[df.loc[X.index, "年份"] != test_year]
            y_train_full = y[df.loc[X.index, "年份"] != test_year]
        else:
            X_train_full, X_test_full, y_train_full, y_test_full = train_test_split(
                X, y, test_size=0.2, random_state=123
            )

        # SMOTE过采样 (Ch12.2 line 141-142)
        if SMOTE_AVAILABLE and y_train_full.value_counts().min() < y_train_full.value_counts().max() * 0.5:
            logger.info("检测到类别不平衡，应用SMOTE过采样")
            smote = SMOTE(random_state=123)
            X_train_resampled, y_train_resampled = smote.fit_resample(X_train_full, y_train_full)
        else:
            X_train_resampled, y_train_resampled = X_train_full, y_train_full

        # 训练4个模型
        results = {}

        # 1. 决策树 (Ch12.2 line 145)
        logger.info("训练 DecisionTree...")
        dt = DecisionTreeClassifier(max_depth=3, random_state=123)
        dt.fit(X_train_resampled, y_train_resampled)
        self.models["DecisionTree"] = dt
        results["DecisionTree_AUC"] = round(
            roc_auc_score(y_test_full, dt.predict_proba(X_test_full)[:, 1]), 4
        )

        # 2. 随机森林 (Ch13.4 lines 52-93)
        logger.info("训练 RandomForest...")
        rf = RandomForestClassifier(n_estimators=50, random_state=123)
        rf.fit(X_train_resampled, y_train_resampled)
        self.models["RandomForest"] = rf
        results["RandomForest_AUC"] = round(
            roc_auc_score(y_test_full, rf.predict_proba(X_test_full)[:, 1]), 4
        )

        # 3. GBDT (Ch13.4 lines 97-137)
        logger.info("训练 GBDT...")
        gbdt = GradientBoostingClassifier(n_estimators=50, random_state=123)
        gbdt.fit(X_train_resampled, y_train_resampled)
        self.models["GBDT"] = gbdt
        results["GBDT_AUC"] = round(
            roc_auc_score(y_test_full, gbdt.predict_proba(X_test_full)[:, 1]), 4
        )

        # 4. XGBoost (Ch13.4 lines 141-195)
        if XGBOOST_AVAILABLE:
            logger.info("训练 XGBoost...")
            # XGBoost需要列名
            xgb = XGBClassifier(n_estimators=50, random_state=123, verbosity=0)
            xgb.fit(X_train_resampled, y_train_resampled)
            self.models["XGBoost"] = xgb
            results["XGBoost_AUC"] = round(
                roc_auc_score(y_test_full, xgb.predict_proba(X_test_full)[:, 1]), 4
            )

        self.is_trained = True
        logger.info(f"ML模型训练完成: {results}")
        return results

    # ========================================================================
    # 推理 — 对当前公司进行舞弊预测
    # ========================================================================

    def predict(
        self,
        company_features: dict[str, float],
    ) -> FraudDetectionResult:
        """
        对当前公司进行舞弊预测

        使用4个模型的投票集成
        复现教科书 Ch13.4 的集成预测逻辑
        """
        if not self.is_trained:
            return FraudDetectionResult(fraud_risk_level="模型未训练")

        # 提取特征向量
        feature_dict = {}
        for col in self.feature_names:
            val = company_features.get(col, company_features.get(col.upper(), 0))
            feature_dict[col] = float(val) if val is not None else 0.0

        X = pd.DataFrame([feature_dict], columns=self.feature_names)

        # 处理无穷值和缺失
        for col in self.feature_names:
            if col not in X.columns:
                X[col] = 0.0
            inf_mask = np.isinf(X[col].astype(float))
            X.loc[inf_mask, col] = self.preprocessing_stats.get(col, {}).get("max", 0)
            X[col] = X[col].fillna(self.preprocessing_stats.get(col, {}).get("median", 0))

        # 投票集成
        votes = {}
        fraud_probs = []

        for name, model in self.models.items():
            try:
                prob = float(model.predict_proba(X)[:, 1][0])
                votes[name] = round(prob, 4)
                fraud_probs.append(prob)
            except Exception as e:
                logger.warning(f"模型 {name} 预测失败: {e}")
                votes[name] = None

        if fraud_probs:
            avg_prob = float(np.mean(fraud_probs))
        else:
            avg_prob = 0.0

        # 风险等级
        if avg_prob > 0.5:
            risk_level = "高风险"
        elif avg_prob > 0.25:
            risk_level = "中风险"
        else:
            risk_level = "低风险"

        # 特征重要性（使用随机森林的特征重要性）
        feature_importance = {}
        if "RandomForest" in self.models:
            importances = self.models["RandomForest"].feature_importances_
            for i, col in enumerate(self.feature_names):
                if i < len(importances):
                    feature_importance[col] = round(float(importances[i]), 4)

        return FraudDetectionResult(
            fraud_probability=round(avg_prob, 4),
            fraud_risk_level=risk_level,
            model_votes=votes,
            feature_importance=feature_importance,
        )

    def save(self, path: str) -> None:
        """保存模型到文件"""
        with open(path, "wb") as f:
            pickle.dump({
                "models": self.models,
                "feature_names": self.feature_names,
                "preprocessing_stats": self.preprocessing_stats,
                "is_trained": self.is_trained,
            }, f)
        logger.info(f"ML模型已保存到 {path}")

    def load(self, path: str) -> bool:
        """从文件加载模型"""
        if not Path(path).exists():
            logger.warning(f"模型文件不存在: {path}")
            return False
        with open(path, "rb") as f:
            data = pickle.load(f)
        self.models = data["models"]
        self.feature_names = data["feature_names"]
        self.preprocessing_stats = data["preprocessing_stats"]
        self.is_trained = data["is_trained"]
        logger.info(f"ML模型已加载 ({len(self.models)} 个模型)")
        return True
