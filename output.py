import streamlit as st
import requests
import time
import os
from datetime import datetime
from typing import Optional, Dict, Any

# 应用配置
st.set_page_config(
    page_title="比特币价格追踪器",
    page_icon="₿",
    layout="centered"
)


class BitcoinPriceTracker:
    def __init__(self):
        self.api_url = os.getenv('COINGECKO_API_URL',
                                 "https://api.coingecko.com/api/v3/simple/price")
        self.timeout = int(os.getenv('REQUEST_TIMEOUT', '10'))
        self.params = {
            'ids': 'bitcoin',
            'vs_currencies': 'usd',
            'include_24hr_change': 'true',
            'include_24hr_vol': 'true',
            'include_last_updated_at': 'true'
        }

    def validate_bitcoin_data(self, data: Dict[str, Any]) -> bool:
        """验证比特币数据完整性"""
        required_fields = ['usd', 'usd_24h_change']
        for field in required_fields:
            if field not in data:
                st.error(f"数据验证失败: 缺少必要字段 '{field}'")
                return False

        # 验证价格数据合理性
        if data['usd'] <= 0:
            st.error("数据验证失败: 价格数据异常")
            return False

        return True

    def fetch_bitcoin_data(self) -> Optional[Dict[str, Any]]:
        """
        从 CoinGecko API 获取比特币数据
        返回: dict 包含价格和变化数据，或 None 如果失败
        """
        try:
            response = requests.get(self.api_url, params=self.params, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()
            bitcoin_data = data.get('bitcoin', {})

            if not bitcoin_data:
                raise ValueError("未找到比特币数据")

            # 数据验证
            if not self.validate_bitcoin_data(bitcoin_data):
                return None

            return bitcoin_data

        except requests.exceptions.Timeout:
            st.error("⏰ 请求超时，请检查网络连接")
            return None
        except requests.exceptions.ConnectionError:
            st.error("🌐 网络连接错误，请检查网络设置")
            return None
        except requests.exceptions.HTTPError as e:
            st.error(f"🔍 HTTP错误: {e.response.status_code if e.response else '未知'}")
            return None
        except requests.exceptions.RequestException as e:
            st.error(f"📡 网络请求错误: {str(e)}")
            return None
        except ValueError as e:
            st.error(f"📊 数据解析错误: {str(e)}")
            return None
        except Exception as e:
            st.error(f"❓ 未知错误: {str(e)}")
            return None

    @st.cache_data(ttl=30)  # 缓存30秒
    def fetch_bitcoin_data_cached(_self) -> Optional[Dict[str, Any]]:
        """带缓存的比特币数据获取"""
        return _self.fetch_bitcoin_data()

    def fetch_bitcoin_data_with_retry(self, max_retries: int = 3) -> Optional[Dict[str, Any]]:
        """带重试机制的数据获取"""
        for attempt in range(max_retries):
            st.info(f"尝试获取数据 ({attempt + 1}/{max_retries})...")
            data = self.fetch_bitcoin_data()
            if data:
                return data
            if attempt < max_retries - 1:
                time.sleep(2)  # 等待2秒后重试
        return None

    def format_price(self, price: float) -> str:
        """格式化价格显示"""
        return f"${price:,.2f}"

    def format_change(self, change_percent: float, change_amount: float) -> str:
        """格式化变化数据显示"""
        if change_percent > 0:
            color = "🟢"
            trend = "上涨"
        elif change_percent < 0:
            color = "🔴"
            trend = "下跌"
        else:
            color = "⚪"
            trend = "持平"

        return f"{color} {trend} {abs(change_percent):.2f}% (${abs(change_amount):.2f})"

    def calculate_previous_price(self, current_price: float, change_percent: float) -> float:
        """计算24小时前价格"""
        change_amount = (current_price * change_percent) / 100
        return current_price - change_amount

    def display_price_info(self, bitcoin_data: Dict[str, Any]):
        """显示价格信息"""
        current_price = bitcoin_data.get('usd', 0)
        change_percent = bitcoin_data.get('usd_24h_change', 0)
        change_amount = (current_price * change_percent) / 100
        previous_price = self.calculate_previous_price(current_price, change_percent)

        # 主价格显示区域
        col1, col2 = st.columns([2, 1])

        with col1:
            # 主价格显示
            st.markdown(f'<div class="price-display">{self.format_price(current_price)}</div>',
                        unsafe_allow_html=True)

            # 涨跌幅信息
            change_display = self.format_change(change_percent, change_amount)
            if change_percent > 0:
                st.success(change_display)
            elif change_percent < 0:
                st.error(change_display)
            else:
                st.info(change_display)

        with col2:
            # 更新时间
            last_updated = bitcoin_data.get('last_updated_at')
            if last_updated:
                update_time = datetime.fromtimestamp(last_updated)
                st.caption(f"🕒 {update_time.strftime('%Y-%m-%d %H:%M:%S')}")

        # 详细信息卡片
        st.markdown("---")

        col3, col4, col5 = st.columns(3)

        with col3:
            st.metric(
                label="当前价格",
                value=self.format_price(current_price),
                delta=f"{change_percent:.2f}%"
            )

        with col4:
            st.metric(
                label="24小时前价格",
                value=self.format_price(previous_price)
            )

        with col5:
            volume = bitcoin_data.get('usd_24h_vol', 0)
            st.metric(
                label="24小时交易量",
                value=f"${volume:,.0f}"
            )

        # 趋势分析
        st.markdown("### 📊 市场趋势分析")
        if change_percent > 5:
            st.success(f"🚀 强势上涨: 过去24小时大幅上涨 {change_percent:.2f}%")
        elif change_percent > 2:
            st.success(f"📈 稳步上涨: 过去24小时上涨 {change_percent:.2f}%")
        elif change_percent > 0:
            st.info(f"↗️ 小幅上涨: 过去24小时微涨 {change_percent:.2f}%")
        elif change_percent < -5:
            st.error(f"📉 大幅下跌: 过去24小时大幅下跌 {abs(change_percent):.2f}%")
        elif change_percent < -2:
            st.error(f"🔻 明显下跌: 过去24小时下跌 {abs(change_percent):.2f}%")
        elif change_percent < 0:
            st.warning(f"↘️ 小幅下跌: 过去24小时微跌 {abs(change_percent):.2f}%")
        else:
            st.info("➡️ 价格平稳: 过去24小时价格基本持平")

    def display_error_state(self):
        """统一的错误状态显示"""
        st.error("❌ 无法获取比特币价格数据")

        st.info("""
        🔍 **可能的原因：**
        - 网络连接问题
        - API 服务暂时不可用  
        - 请求频率过高
        - 服务器维护中

        💡 **解决方案：**
        - 检查网络连接
        - 稍后重试
        - 使用重试功能
        """)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 立即重试", use_container_width=True):
                st.rerun()
        with col2:
            if st.button("🔄 重试3次", use_container_width=True):
                st.session_state.retry_mode = True
                st.rerun()


def setup_auto_refresh(refresh_interval: int):
    """设置自动刷新功能"""
    if refresh_interval > 0:
        placeholder = st.empty()
        for i in range(refresh_interval, 0, -1):
            with placeholder:
                st.info(f"⏰ 下次自动刷新: {i}秒")
            time.sleep(1)
        placeholder.empty()
        st.rerun()


def main():
    """主应用函数"""
    # 应用标题
    st.markdown('<div class="main-header">₿ 比特币价格追踪器</div>',
                unsafe_allow_html=True)
    st.markdown("实时监控比特币价格走势和市场动态")

    # 初始化追踪器
    tracker = BitcoinPriceTracker()

    # 侧边栏设置
    with st.sidebar:
        st.header("⚙️ 设置")

        # 刷新设置
        auto_refresh = st.checkbox("启用自动刷新", value=False)
        refresh_interval = 30
        if auto_refresh:
            refresh_interval = st.slider("刷新间隔(秒)", 10, 300, 30)
            st.info(f"🔄 自动刷新已启用 - 每 {refresh_interval} 秒")

        st.markdown("---")
        st.header("ℹ️ 关于")
        st.info("""
        数据来源: CoinGecko API
        更新频率: 实时
        支持货币: USD
        """)

    # 控制按钮区域
    col1, col2, col3 = st.columns([2, 1, 1])

    with col2:
        if st.button("🔄 刷新数据", use_container_width=True, key="refresh_main"):
            st.rerun()

    with col3:
        if st.button("🔁 重试模式", use_container_width=True, key="retry_mode"):
            st.session_state.retry_mode = True
            st.rerun()

    # 数据获取和显示
    with st.spinner("🔄 正在获取最新的比特币价格数据..."):
        if st.session_state.get('retry_mode', False):
            bitcoin_data = tracker.fetch_bitcoin_data_with_retry()
            st.session_state.retry_mode = False
        else:
            bitcoin_data = tracker.fetch_bitcoin_data_cached()

    # 数据显示或错误处理
    if bitcoin_data:
        tracker.display_price_info(bitcoin_data)

        # 调试信息（可选）
        with st.expander("🔧 查看原始数据（调试）"):
            st.json(bitcoin_data)

            # 性能信息
            st.caption("💡 提示: 数据已缓存30秒以减少API调用")
    else:
        tracker.display_error_state()

    # 自动刷新逻辑（放在最后以避免阻塞）
    if auto_refresh:
        setup_auto_refresh(refresh_interval)


# 自定义CSS样式
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #F7931A;
        text-align: center;
        margin-bottom: 1rem;
        font-weight: bold;
    }
    .price-display {
        font-size: 3.5rem;
        font-weight: bold;
        text-align: center;
        color: #F7931A;
        margin: 1rem 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #F7931A;
        margin: 0.5rem 0;
    }
    .stButton button {
        border-radius: 8px;
        font-weight: bold;
    }
    .stAlert {
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

if __name__ == "__main__":
    # 初始化session state
    if 'retry_mode' not in st.session_state:
        st.session_state.retry_mode = False

    main()