"""
Token 管理器 - 处理多数据源的 Token 管理
安全存储：优先 keyring，回退环境变量，禁止明文持久化
"""
import os

from ..logging_config import get_logger

logger = get_logger(__name__)

# 条件导入
try:
    import tushare as ts
    HAS_TUSHARE = True
except ImportError:
    HAS_TUSHARE = False

try:
    import keyring
    HAS_KEYRING = True
except ImportError:
    HAS_KEYRING = False

# keyring 服务名
_KEYRING_SERVICE = "financial_analyzer"

# 环境变量名映射
_ENV_VAR_MAP = {
    "tushare": "TUSHARE_TOKEN",
    "yfinance": "YFINANCE_TOKEN",
    "akshare": "AKSHARE_TOKEN",
}


class TokenManager:
    """Token 管理器 - 安全存储与读取"""

    def __init__(self):
        self.tokens: dict[str, str | None] = {
            "tushare": None,
            "yfinance": None,
            "akshare": None,
        }
        self.token_status: dict[str, str] = {
            "tushare": "未设置",
            "yfinance": "无需设置",
            "akshare": "无需设置",
        }
        # 启动时自动从安全存储加载
        self._load_from_secure_storage()

    def _load_from_secure_storage(self):
        """从 keyring 或环境变量加载已保存的 token"""
        for source in self.tokens:
            token = self._read_secure(source)
            if token:
                self.tokens[source] = token
                self.token_status[source] = "已加载"
                logger.info(f"从安全存储加载 {source} Token")

    @staticmethod
    def _read_secure(source: str) -> str | None:
        """从 keyring 读取，回退环境变量"""
        # 1. 优先 keyring
        if HAS_KEYRING:
            try:
                token = keyring.get_password(_KEYRING_SERVICE, source)
                if token:
                    return token
            except Exception as e:
                logger.debug(f"keyring 读取 {source} 失败: {e}")

        # 2. 回退环境变量
        env_var = _ENV_VAR_MAP.get(source)
        if env_var:
            token = os.environ.get(env_var)
            if token:
                return token.strip()

        return None

    @staticmethod
    def _write_secure(source: str, token: str) -> bool:
        """写入 keyring"""
        if not HAS_KEYRING:
            logger.warning("keyring 未安装，token 仅在本次会话有效。安装: pip install keyring")
            return False
        try:
            keyring.set_password(_KEYRING_SERVICE, source, token)
            return True
        except Exception as e:
            logger.error(f"keyring 写入 {source} 失败: {e}")
            return False

    @staticmethod
    def _delete_secure(source: str) -> bool:
        """从 keyring 删除"""
        if not HAS_KEYRING:
            return False
        try:
            keyring.delete_password(_KEYRING_SERVICE, source)
            return True
        except Exception:
            return False

    def set_token(self, source: str, token: str) -> bool:
        """设置特定数据源的 Token（同时持久化到安全存储）"""
        if source not in self.tokens:
            return False

        token = token.strip() if token else None
        self.tokens[source] = token

        if token:
            saved = self._write_secure(source, token)
            if saved:
                self.token_status[source] = "已保存"
                logger.info(f"{source} Token 已安全存储")
            else:
                self.token_status[source] = "仅本次会话"
        else:
            self._delete_secure(source)
            self.token_status[source] = "未设置"

        return True

    def get_token(self, source: str) -> str | None:
        """获取特定数据源的 Token"""
        return self.tokens.get(source)

    def get_masked_token(self, source: str) -> str:
        """获取遮蔽后的 Token（用于显示）"""
        token = self.tokens.get(source)
        if not token:
            return "未设置"
        if len(token) <= 8:
            return "****" + token[-4:] if len(token) > 4 else "****"
        return token[:4] + "****" + token[-4:]

    def validate_tushare_token(self, token: str) -> tuple[bool, str]:
        """验证 Tushare Token 有效性"""
        if not token:
            self.token_status["tushare"] = "未设置"
            return False, "Token 未设置"

        if not HAS_TUSHARE:
            self.token_status["tushare"] = "tushare 未安装"
            return False, "tushare 未安装，请运行: pip install tushare"

        try:
            pro = ts.pro_api(token)
            df = pro.daily(ts_code="600519.SH", start_date="20240101", end_date="20240105")
            if not df.empty:
                self.tokens["tushare"] = token
                self._write_secure("tushare", token)
                self.token_status["tushare"] = "已验证"
                logger.info("Tushare Token 验证成功")
                return True, "Token 验证成功"
            else:
                self.token_status["tushare"] = "验证失败"
                return False, "Token 验证失败：无法获取数据"
        except Exception as e:
            self.token_status["tushare"] = "验证失败"
            error_msg = str(e)
            if "每小时最多" in error_msg:
                return False, "API 限流中，请稍后再试"
            elif "token" in error_msg.lower() or "权限" in error_msg:
                return False, "Token 无效或无权限"
            else:
                return False, f"验证失败: {error_msg[:50]}"

    def get_all_status(self) -> dict:
        """获取所有 Token 状态"""
        return self.token_status.copy()

    def clear_token(self, source: str) -> bool:
        """清空特定数据源的 Token"""
        if source in self.tokens:
            self.tokens[source] = None
            self._delete_secure(source)
            self.token_status[source] = "未设置"
            logger.info(f"已清除 {source} Token")
            return True
        return False
