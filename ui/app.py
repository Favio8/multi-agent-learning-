"""
Streamlit Frontend Application - Performance Optimized
User interface for the Multi-Agent Learning System
"""

import streamlit as st
import requests
import json
from pathlib import Path
import sys
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
from collections import Counter
from functools import lru_cache

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Configuration
API_BASE_URL = "http://localhost:8000"

# Page configuration
st.set_page_config(
    page_title="知卡学伴",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS - 现代化美化样式（参考豆包、GPT等优秀设计）
st.markdown("""
<style>
    /* ========== 全局样式 ========== */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }
    
    /* 主容器背景 */
    .main {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 20%, #f5f7fa 40%, #e8eef5 60%, #f5f7fa 100%);
        background-size: 400% 400%;
        animation: gradientShift 15s ease infinite;
    }
    
    @keyframes gradientShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    /* ========== 标题样式 ========== */
    .main-header {
        font-size: 3rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        text-align: center;
        margin-bottom: 2rem;
        padding: 1.5rem 0;
        letter-spacing: -0.02em;
        animation: titleFadeIn 0.8s ease-out;
    }
    
    @keyframes titleFadeIn {
        from {
            opacity: 0;
            transform: translateY(-20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    /* ========== 玻璃拟态卡片 ========== */
    .glass-card {
        background: rgba(255, 255, 255, 0.9);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.5);
        border-radius: 24px;
        padding: 32px;
        margin: 24px 0;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .glass-card:hover {
        transform: translateY(-8px);
        box-shadow: 0 16px 48px rgba(0, 0, 0, 0.12);
        border-color: rgba(102, 126, 234, 0.3);
    }
    
    /* ========== 题目卡片样式 ========== */
    .card-box {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        border-radius: 24px;
        padding: 36px;
        margin: 24px 0;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.06);
        border: 1px solid rgba(0, 0, 0, 0.04);
        position: relative;
        overflow: hidden;
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .card-box::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, #667eea, #764ba2, #f093fb);
        background-size: 200% 100%;
        animation: shimmer 3s linear infinite;
    }
    
    @keyframes shimmer {
        0% { background-position: -200% 0; }
        100% { background-position: 200% 0; }
    }
    
    .card-box:hover {
        transform: translateY(-4px) scale(1.01);
        box-shadow: 0 20px 60px rgba(102, 126, 234, 0.15);
    }
    
    /* ========== 不同题型的卡片样式 ========== */
    .knowledge-card {
        background: linear-gradient(135deg, #fff5f5 0%, #ffe5e5 100%);
        border-left: 4px solid #ff6b6b;
    }
    
    .cloze-card {
        background: linear-gradient(135deg, #f0f4ff 0%, #e5edff 100%);
        border-left: 4px solid #667eea;
    }
    
    .mcq-card {
        background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
        border-left: 4px solid #10b981;
    }
    
    /* ========== 答案区域 ========== */
    .answer-box {
        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
        border-radius: 16px;
        padding: 24px;
        margin: 20px 0;
        border-left: 4px solid #3b82f6;
        position: relative;
        overflow: hidden;
    }
    
    .answer-box::before {
        content: '';
        position: absolute;
        top: 0;
        right: 0;
        width: 100px;
        height: 100px;
        background: radial-gradient(circle, rgba(59, 130, 246, 0.1) 0%, transparent 70%);
    }
    
    /* ========== 正确/错误答案样式 ========== */
    .correct {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        font-weight: 600;
        font-size: 1.1rem;
        padding: 12px 24px;
        border-radius: 12px;
        display: inline-block;
        margin: 12px 0;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
        animation: successPulse 0.6s ease-out;
    }
    
    @keyframes successPulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.05); }
    }
    
    .incorrect {
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
        color: white;
        font-weight: 600;
        font-size: 1.1rem;
        padding: 12px 24px;
        border-radius: 12px;
        display: inline-block;
        margin: 12px 0;
        box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
        animation: errorShake 0.5s ease-out;
    }
    
    @keyframes errorShake {
        0%, 100% { transform: translateX(0); }
        25% { transform: translateX(-8px); }
        75% { transform: translateX(8px); }
    }
    
    /* ========== 进度条优化 ========== */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
    }
    
    /* ========== 题目文字 ========== */
    .question-text {
        font-size: 1.35rem;
        line-height: 1.8;
        color: #1e293b;
        margin: 20px 0;
        font-weight: 500;
        letter-spacing: -0.01em;
    }
    
    /* ========== 提示框 ========== */
    .hint-box {
        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
        border-radius: 16px;
        padding: 20px;
        margin: 16px 0;
        border-left: 4px solid #f59e0b;
        box-shadow: 0 4px 12px rgba(245, 158, 11, 0.15);
    }
    
    /* ========== 统计卡片 ========== */
    .stat-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        border-radius: 20px;
        padding: 28px;
        text-align: center;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
        border: 1px solid rgba(0, 0, 0, 0.04);
        transition: all 0.3s ease;
    }
    
    .stat-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 32px rgba(0, 0, 0, 0.12);
    }
    
    /* ========== 按钮美化 ========== */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 12px 28px;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
    }
    
    /* ========== 输入框美化 ========== */
    .stTextInput > div > div > input {
        border-radius: 12px;
        border: 2px solid #e2e8f0;
        padding: 12px 16px;
        font-size: 1rem;
        transition: all 0.3s ease;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
    
    /* ========== 文本框美化 ========== */
    .stTextArea > div > div > textarea {
        border-radius: 12px;
        border: 2px solid #e2e8f0;
        padding: 16px;
        font-size: 1rem;
        transition: all 0.3s ease;
    }
    
    .stTextArea > div > div > textarea:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
    
    /* ========== 收藏按钮 ========== */
    .favorite-btn {
        font-size: 1.8rem;
        cursor: pointer;
        transition: all 0.3s ease;
        filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
    }
    
    .favorite-btn:hover {
        transform: scale(1.2) rotate(15deg);
    }
    
    /* ========== 选项按钮（MCQ） ========== */
    .choice-button {
        background: white;
        border: 2px solid #e2e8f0;
        border-radius: 16px;
        padding: 16px 20px;
        margin: 8px 0;
        cursor: pointer;
        transition: all 0.3s ease;
        font-size: 1.05rem;
        display: block;
        width: 100%;
        text-align: left;
    }
    
    .choice-button:hover {
        border-color: #667eea;
        background: linear-gradient(135deg, #f0f4ff 0%, #e5edff 100%);
        transform: translateX(8px);
    }
    
    /* ========== 信息提示框 ========== */
    .stAlert {
        border-radius: 16px;
        border: none;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    }
    
    /* ========== 侧边栏美化 ========== */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
    }
    
    section[data-testid="stSidebar"] * {
        color: white !important;
    }
    
    section[data-testid="stSidebar"] .stRadio > label {
        background: rgba(255, 255, 255, 0.1);
        padding: 12px;
        border-radius: 12px;
        margin: 4px 0;
        transition: all 0.3s ease;
    }
    
    section[data-testid="stSidebar"] .stRadio > label:hover {
        background: rgba(255, 255, 255, 0.2);
        transform: translateX(4px);
    }
    
    /* ========== Expander美化 ========== */
    .streamlit-expanderHeader {
        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .streamlit-expanderHeader:hover {
        background: linear-gradient(135deg, #e2e8f0 0%, #cbd5e1 100%);
    }
</style>
""", unsafe_allow_html=True)


# ==================== 优化的API调用函数 ====================

@st.cache_data(ttl=30, show_spinner=False)  # 缓存30秒
def check_api_health():
    """检查API健康状态（带缓存）"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=1)
        return response.status_code == 200
    except:
        return False


@st.cache_data(ttl=300, show_spinner=False)  # 缓存5分钟
def fetch_cards(doc_id=None, limit=100):
    """获取卡片列表（带缓存）"""
    try:
        url = f"{API_BASE_URL}/cards"
        response = requests.get(url, params={"doc_id": doc_id, "limit": limit}, timeout=5)
        response.raise_for_status()
        return response.json()
    except:
        return None


def call_api(endpoint: str, method: str = "GET", data: dict = None, files: dict = None):
    """Helper function to call API"""
    url = f"{API_BASE_URL}{endpoint}"
    
    try:
        # 根据endpoint调整超时时间
        if "/build/" in endpoint:
            timeout = 300  # 构建流水线5分钟超时
        elif files:
            timeout = 120  # 文件上传2分钟超时
        else:
            timeout = 30  # 其他操作30秒超时
        
        if method == "GET":
            response = requests.get(url, params=data, timeout=timeout)
        elif method == "POST":
            if files:
                response = requests.post(url, files=files, data=data, timeout=timeout)
            else:
                response = requests.post(url, json=data, timeout=timeout)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.ConnectionError:
        st.error("⚠️ 无法连接到后端服务器。请确保API服务器正在运行。")
        st.code("运行命令: python api/app.py", language="bash")
        return None
    except requests.exceptions.HTTPError as e:
        st.error(f"API错误: {e}")
        return None
    except requests.exceptions.Timeout:
        st.error("⚠️ 请求超时，请稍后重试")
        return None
    except Exception as e:
        st.error(f"请求失败: {e}")
        return None


# ==================== 优化的可视化函数 ====================

@st.cache_data(ttl=300, show_spinner=False)  # 缓存5分钟
def show_card_stats(cards_tuple):
    """显示卡片统计可视化（使用缓存）"""
    # 将tuple of tuples转回list of dicts
    cards = [dict(card) for card in cards_tuple]
    
    if not cards:
        return
    
    # 统计卡片类型
    card_types = [card['type'] for card in cards]
    type_counts = Counter(card_types)
    
    # 类型映射
    type_names = {
        'knowledge': '📚 知识卡片',
        'cloze': '📝 填空题',
        'mcq': '🎯 选择题',
        'short': '✍️ 简答题'
    }
    
    # 颜色映射
    type_colors = {
        'knowledge': '#fcb69f',
        'cloze': '#8ec5fc',
        'mcq': '#a8edea',
        'short': '#f093fb'
    }
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 饼图 - 卡片类型分布
        st.markdown("### 📊 卡片类型分布")
        
        labels = [type_names.get(t, t) for t in type_counts.keys()]
        values = list(type_counts.values())
        colors = [type_colors.get(t, '#999') for t in type_counts.keys()]
        
        fig_pie = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.4,
            marker=dict(colors=colors),
            textinfo='label+percent',
            textfont=dict(size=14)
        )])
        
        fig_pie.update_layout(
            showlegend=True,
            height=350,
            margin=dict(t=20, b=20, l=20, r=20)
        )
        
        st.plotly_chart(fig_pie, use_container_width=True, key=f"pie_{len(cards)}")
    
    with col2:
        # 柱状图 - 卡片数量
        st.markdown("### 📈 卡片数量统计")
        
        fig_bar = go.Figure(data=[go.Bar(
            x=labels,
            y=values,
            marker=dict(color=colors),
            text=values,
            textposition='auto',
        )])
        
        fig_bar.update_layout(
            showlegend=False,
            height=350,
            margin=dict(t=20, b=60, l=40, r=20),
            xaxis_title="卡片类型",
            yaxis_title="数量"
        )
        
        st.plotly_chart(fig_bar, use_container_width=True, key=f"bar_{len(cards)}")


@st.cache_data(ttl=60, show_spinner=False)  # 缓存1分钟（进度变化快）
def show_progress_stats(total, current_idx):
    """显示学习进度可视化（使用缓存）"""
    completed = current_idx
    remaining = total - completed
    progress_pct = (completed / total * 100) if total > 0 else 0
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # 环形进度图
        fig_progress = go.Figure(data=[go.Pie(
            values=[completed, remaining],
            labels=['已完成', '未完成'],
            hole=0.7,
            marker=dict(colors=['#667eea', '#e0e0e0']),
            textinfo='none',
            hoverinfo='label+value'
        )])
        
        fig_progress.add_annotation(
            text=f"{progress_pct:.0f}%",
            x=0.5, y=0.5,
            font=dict(size=32, color="#667eea"),
            showarrow=False
        )
        
        fig_progress.update_layout(
            showlegend=False,
            height=200,
            margin=dict(t=0, b=0, l=0, r=0)
        )
        
        st.plotly_chart(fig_progress, use_container_width=True)
        st.markdown(f"<p style='text-align: center; color: #667eea; font-weight: bold;'>完成进度</p>", 
                   unsafe_allow_html=True)
    
    with col2:
        st.metric(
            label="📝 已完成",
            value=f"{completed}",
            delta=f"还剩 {remaining} 题"
        )
    
    with col3:
        # 预估剩余时间（假设每题30秒）
        est_time = remaining * 0.5  # 分钟
        st.metric(
            label="⏱️ 预估剩余",
            value=f"{est_time:.0f} 分钟",
            delta="按30秒/题计算"
        )


# ==================== 初始化Session State ====================

def init_session_state():
    """初始化所有session state变量"""
    if 'user_id' not in st.session_state:
        st.session_state['user_id'] = "demo_user"
    
    if 'favorites' not in st.session_state:
        st.session_state['favorites'] = set()
    
    if 'answer_start_time' not in st.session_state:
        st.session_state['answer_start_time'] = datetime.now()
    
    if 'show_knowledge_answer' not in st.session_state:
        st.session_state['show_knowledge_answer'] = False
    
    if 'knowledge_assessment' not in st.session_state:
        st.session_state['knowledge_assessment'] = None
    
    # 恢复学习进度
    if 'progress_restored' not in st.session_state:
        restore_learning_progress()
        st.session_state['progress_restored'] = True


def restore_learning_progress():
    """从数据库恢复学习进度（优化版 - 使用缓存）"""
    try:
        import requests
        user_id = st.session_state.get('user_id', 'demo_user')
        
        # 获取最近的学习进度（减少超时时间）
        response = requests.get(f"{API_BASE_URL}/progress/{user_id}", timeout=2)
        
        if response.status_code == 200:
            progress = response.json()
            if progress and isinstance(progress, dict) and 'doc_id' in progress:
                st.session_state['last_doc_id'] = progress.get('doc_id')
                st.session_state['current_card_idx'] = progress.get('current_card_idx', 0)
                # 显示恢复提示（只显示一次）
                if 'progress_message' not in st.session_state:
                    doc_title = progress.get('doc_title', '未知文档')
                    st.session_state['progress_message'] = f"已恢复上次学习进度：{doc_title}"
    except:
        # 失败时静默处理，不影响页面加载速度
        pass
    finally:
        # 确保有默认值
        if 'current_card_idx' not in st.session_state:
            st.session_state['current_card_idx'] = 0


def save_progress(user_id: str, doc_id: str, current_idx: int, total_cards: int):
    """保存学习进度到数据库"""
    try:
        import requests
        requests.post(f"{API_BASE_URL}/progress/save", json={
            'user_id': user_id,
            'doc_id': doc_id,
            'current_card_idx': current_idx,
            'total_cards': total_cards
        }, timeout=3)
    except:
        pass  # 静默失败，不影响用户体验


# ==================== 页面函数 ====================

def page_upload():
    """Document upload page"""
    st.markdown('<h1 class="main-header">📤 上传学习资料</h1>', unsafe_allow_html=True)
    
    st.markdown("""
    <div style='text-align: center; margin-bottom: 2rem;'>
        <p style='font-size: 1.1rem; color: #666;'>
            上传PDF、HTML或文本文件，AI智能体将自动分析并生成学习卡片
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        uploaded_file = st.file_uploader(
            "选择文件",
            type=['pdf', 'txt', 'html', 'htm'],
            help="支持PDF、文本和HTML格式"
        )
        
        if uploaded_file is not None:
            st.success(f"✅ 已选择文件: {uploaded_file.name}")
            
            # Show file info
            file_details = {
                "文件名": uploaded_file.name,
                "文件类型": uploaded_file.type,
                "文件大小": f"{uploaded_file.size / 1024:.2f} KB"
            }
            st.json(file_details)
            
            if st.button("🚀 上传并开始处理", type="primary", use_container_width=True):
                with st.spinner("正在上传文件..."):
                    # Upload file
                    files = {"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
                    result = call_api("/ingest", method="POST", files=files)
                    
                    if result:
                        st.success(f"✅ {result['message']}")
                        doc_id = result['doc_id']
                        
                        # Store doc_id in session and reset card index
                        st.session_state['last_doc_id'] = doc_id
                        st.session_state['current_card_idx'] = 0  # 重置为第一题
                        
                        # Start pipeline
                        with st.spinner("正在处理文档，生成卡片..."):
                            build_result = call_api(f"/build/{doc_id}", method="POST")
                            
                            if build_result:
                                st.success("✅ 卡片生成完成！")
                                
                                # 清除卡片缓存以便重新加载
                                fetch_cards.clear()
                                
                                # Show summary with beautiful cards
                                summary = build_result['summary']
                                
                                st.markdown("### 📊 生成统计")
                                col_a, col_b, col_c = st.columns(3)
                                
                                with col_a:
                                    st.markdown("""
                                    <div class="stat-card">
                                        <h2 style="color: #667eea; margin: 0;">📄</h2>
                                        <h3 style="margin: 10px 0;">{}</h3>
                                        <p style="color: #888; margin: 0;">段落数</p>
                                    </div>
                                    """.format(summary['total_sections']), unsafe_allow_html=True)
                                
                                with col_b:
                                    st.markdown("""
                                    <div class="stat-card">
                                        <h2 style="color: #48c6ef; margin: 0;">💡</h2>
                                        <h3 style="margin: 10px 0;">{}</h3>
                                        <p style="color: #888; margin: 0;">概念数</p>
                                    </div>
                                    """.format(summary['total_concepts']), unsafe_allow_html=True)
                                
                                with col_c:
                                    st.markdown("""
                                    <div class="stat-card">
                                        <h2 style="color: #f093fb; margin: 0;">📝</h2>
                                        <h3 style="margin: 10px 0;">{}</h3>
                                        <p style="color: #888; margin: 0;">卡片数</p>
                                    </div>
                                    """.format(summary['total_cards']), unsafe_allow_html=True)
                                
                                st.info("💡 现在可以在左侧菜单中选择'练习卡片'开始学习！")
    
    with col2:
        st.info("""
        ### 📖 使用说明
        
        1. 📤 选择要上传的文件
        2. 🚀 点击"上传并开始处理"
        3. ⏳ AI智能体协同分析（约1-3分钟）
        4. ✅ 开始智能学习！
        
        ### 🤖 AI智能体工作流
        
        - **ContentAgent** - 内容解析与分段
        - **ConceptAgent** - 概念提取与关系构建
        - **QuizAgent** - 多题型卡片生成
        - **EvalAgent** - 智能评测与反馈
        - **ScheduleAgent** - 复习计划优化
        """)
        
        # 添加支持的文件类型提示
        st.success("""
        ✅ **支持格式:** PDF, TXT, HTML  
        📊 **最佳效果:** 5-50页文档  
        ⚡ **处理速度:** 约每10页1分钟
        """)


def page_practice():
    """Practice page - 性能优化版本"""
    st.markdown('<h1 class="main-header">✍️ 练习卡片</h1>', unsafe_allow_html=True)
    
    # 添加页面说明
    st.markdown("""
    <div style='text-align: center; margin-bottom: 1rem;'>
        <p style='font-size: 1rem; color: #666;'>
            🤖 AI智能体已为你准备好学习卡片，开始高效学习吧！
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    user_id = st.session_state['user_id']
    doc_id = st.session_state.get('last_doc_id')
    
    # 显示进度恢复提示
    if 'progress_message' in st.session_state and st.session_state['progress_message']:
        st.success(f"📖 {st.session_state['progress_message']}")
        st.session_state['progress_message'] = None  # 只显示一次
    
    # 使用优化的缓存API调用
    cards_data = fetch_cards(doc_id, 100)
    
    if not cards_data or not cards_data.get('cards'):
        st.warning("⚠️ 还没有可用的卡片。请先上传文档生成卡片。")
        return
    
    cards = cards_data['cards']
    
    # 显示卡片统计（使用缓存）
    with st.expander("📊 查看卡片统计", expanded=False):
        cards_tuple = tuple(tuple(sorted(card.items())) for card in cards)
        show_card_stats(cards_tuple)
    
    st.write(f"共有 **{len(cards)}** 张卡片可供练习 | 已收藏 **{len(st.session_state['favorites'])}** 张")
    
    current_idx = st.session_state['current_card_idx']
    
    if current_idx >= len(cards):
        st.success("🎉 恭喜！你已经完成了所有卡片！")
        if st.button("🔄 重新开始", use_container_width=True):
            st.session_state['current_card_idx'] = 0
            st.rerun()
        return
    
    card = cards[current_idx]
    
    # 显示进度统计可视化（使用缓存）
    with st.expander("📈 查看学习进度", expanded=False):
        show_progress_stats(len(cards), current_idx)
    
    # Progress bar
    progress = (current_idx + 1) / len(cards)
    prog_col1, prog_col2, prog_col3 = st.columns([2, 1, 1])
    with prog_col1:
        st.progress(progress)
    with prog_col2:
        st.metric("当前进度", f"{current_idx + 1}/{len(cards)}")
    with prog_col3:
        st.metric("完成度", f"{int(progress*100)}%")
    
    # 收藏按钮（优化：使用回调避免rerun）
    is_favorited = card['card_id'] in st.session_state['favorites']
    
    def toggle_favorite():
        """收藏切换回调"""
        card_id = card['card_id']
        if card_id in st.session_state['favorites']:
            st.session_state['favorites'].discard(card_id)
        else:
            st.session_state['favorites'].add(card_id)
    
    fav_col1, fav_col2 = st.columns([6, 1])
    with fav_col2:
        fav_icon = "⭐" if is_favorited else "☆"
        fav_text = "已收藏" if is_favorited else "收藏"
        st.button(f"{fav_icon} {fav_text}", 
                 key=f"fav_{current_idx}",
                 on_click=toggle_favorite,
                 use_container_width=True)
    
    # Display card based on type
    if card['type'] == 'knowledge':
        # Knowledge card
        st.markdown(f"""
        <div class="card-box knowledge-card">
            <h3 style="color: #ff6b6b; margin-bottom: 20px;">📚 KNOWLEDGE - 知识记忆卡</h3>
            <p class="question-text" style="text-align: center; padding: 30px; font-size: 1.6rem; font-weight: 500;">
                {card['stem']}
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # 使用回调优化翻转
        def flip_card():
            st.session_state['show_knowledge_answer'] = not st.session_state.get('show_knowledge_answer', False)
        
        col_k1, col_k2 = st.columns(2)
        with col_k1:
            st.button("🔄 翻转查看答案", 
                     key=f"flip_{current_idx}",
                     on_click=flip_card,
                     use_container_width=True)
        
        if st.session_state.get('show_knowledge_answer', False):
            st.markdown(f"""
            <div class="answer-box">
                <h4 style="color: #4facfe; margin-bottom: 15px;">💡 答案</h4>
                <p class="question-text">{card['answer']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            if card.get('explanation'):
                with st.expander("📖 提示与例子"):
                    st.write(card['explanation'])
            
            # Self-assessment with callbacks
            st.write("**自我评估：你记住了吗？**")
            
            def remember_callback():
                st.session_state['knowledge_assessment'] = True
            
            def forgot_callback():
                st.session_state['knowledge_assessment'] = False
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.button("✅ 记住了", 
                         type="primary", 
                         key=f"remember_{current_idx}",
                         on_click=remember_callback,
                         use_container_width=True)
            with col_b:
                st.button("❌ 还不熟", 
                         key=f"forgot_{current_idx}",
                         on_click=forgot_callback,
                         use_container_width=True)
        
        user_answer = st.session_state.get('knowledge_assessment', None)
        if user_answer is not None:
            user_answer = "correct" if user_answer else "incorrect"
    
    else:
        # Other card types
        card_class = ""
        card_color = "#667eea"
        card_icon = "📋"
        
        if card['type'] == 'cloze':
            card_class = "cloze-card"
            card_color = "#667eea"
            card_icon = "📝"
        elif card['type'] == 'mcq':
            card_class = "mcq-card"
            card_color = "#48c6ef"
            card_icon = "🎯"
        elif card['type'] == 'short':
            card_class = "card-box"
            card_color = "#f093fb"
            card_icon = "✍️"
        
        st.markdown(f"""
        <div class="card-box {card_class}">
            <h3 style="color: {card_color}; margin-bottom: 20px;">{card_icon} {card['type'].upper()} 题型</h3>
            <p class="question-text"><strong>题目：</strong>{card['stem']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Answer input
        user_answer = None
        
        if card['type'] == 'mcq':
            choices = card['choices']
            user_answer = st.radio("**请选择答案：**", choices, key=f"answer_{current_idx}")
        
        elif card['type'] in ['cloze', 'short']:
            placeholder = "请输入填空答案..." if card['type'] == 'cloze' else "请输入你的答案..."
            user_answer = st.text_input(
                "**请输入答案：**", 
                key=f"answer_{current_idx}",
                placeholder=placeholder
            )
    
    # 回调函数定义
    def next_card():
        """下一题回调"""
        st.session_state['current_card_idx'] += 1
        st.session_state['answer_start_time'] = datetime.now()
        st.session_state['show_knowledge_answer'] = False
        st.session_state['knowledge_assessment'] = None
        
        # 保存学习进度
        save_progress(user_id, doc_id, st.session_state['current_card_idx'], len(cards))
    
    def jump_to_card():
        """跳转回调"""
        jump_idx = st.session_state.get(f'jump_input_{current_idx}', 1) - 1
        if 0 <= jump_idx < len(cards):
            st.session_state['current_card_idx'] = jump_idx
            st.session_state['show_knowledge_answer'] = False
            st.session_state['knowledge_assessment'] = None
    
    # 现代化按钮布局区域
    st.markdown("---")
    st.markdown("""
    <div style='margin: 2rem 0 1rem 0;'>
        <p style='text-align: center; color: #64748b; font-size: 0.9rem; margin-bottom: 1.5rem;'>
            💡 提示：输入答案后点击提交，或直接跳到下一题
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # 主操作区（提交答案） - 居中大按钮
    if card['type'] == 'knowledge':
        # Knowledge卡片：确认并继续
        if user_answer:
            submit_col1, submit_col2, submit_col3 = st.columns([1, 2, 1])
            with submit_col2:
                st.button("✅ 确认并继续", 
                         type="primary", 
                         key=f"submit_{current_idx}",
                         on_click=next_card,
                         use_container_width=True)
    else:
        # 其他类型：提交答案
        has_answer = user_answer and len(str(user_answer).strip()) > 0
        
        submit_col1, submit_col2, submit_col3 = st.columns([1, 2, 1])
        with submit_col2:
            if st.button("✅ 提交答案", 
                        type="primary", 
                        key=f"submit_{current_idx}",
                        disabled=not has_answer,
                        use_container_width=True):
                
                latency = int((datetime.now() - st.session_state['answer_start_time']).total_seconds() * 1000)
                
                answer_data = {
                    "user_id": user_id,
                    "card_id": card['card_id'],
                    "response": user_answer,
                    "latency_ms": latency
                }
                
                result = call_api("/answer", method="POST", data=answer_data)
                
                if result:
                    evaluation = result['evaluation']
                    
                    if evaluation['is_correct']:
                        st.markdown(f'<p class="correct">✅ {evaluation["feedback"]}</p>', 
                                  unsafe_allow_html=True)
                        st.balloons()
                    else:
                        st.markdown(f'<p class="incorrect">❌ {evaluation["feedback"]}</p>', 
                                  unsafe_allow_html=True)
                    
                    if not evaluation['is_correct'] and card.get('answer'):
                        st.markdown(f"""
                        <div class="hint-box">
                            <strong>💡 正确答案：</strong>{card['answer']}
                        </div>
                        """, unsafe_allow_html=True)
                    
                    if card.get('explanation'):
                        with st.expander("📖 查看详细解析", expanded=not evaluation['is_correct']):
                            st.markdown(f"<p class='question-text'>{card['explanation']}</p>", unsafe_allow_html=True)
                    
                    if result.get('schedule'):
                        schedule = result['schedule']
                        next_due = datetime.fromisoformat(schedule['next_due']).strftime("%Y-%m-%d %H:%M")
                        st.success(f"📅 下次复习时间: {next_due} (间隔 {schedule['interval_days']} 天)")
    
    # 次要操作区（下一题 + 快速跳转） - 卡片式布局
    st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)
    
    action_col1, action_col2 = st.columns([1, 1])
    
    with action_col1:
        st.markdown("""
        <div style='background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%); 
                    border-radius: 12px; padding: 1rem; margin-bottom: 0.5rem;
                    border-left: 4px solid #667eea;'>
            <p style='font-size: 0.85rem; color: #475569; margin: 0; font-weight: 600;'>
                ⏭️ 下一题
            </p>
        </div>
        """, unsafe_allow_html=True)
        st.button("继续下一题", 
                 key=f"next_{current_idx}",
                 on_click=next_card,
                 use_container_width=True)
    
    with action_col2:
        st.markdown("""
        <div style='background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%); 
                    border-radius: 12px; padding: 1rem; margin-bottom: 0.5rem;
                    border-left: 4px solid #10b981;'>
            <p style='font-size: 0.85rem; color: #475569; margin: 0; font-weight: 600;'>
                🚀 快速跳转
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        jump_col1, jump_col2 = st.columns([3, 2])
        with jump_col1:
            st.number_input(
                "题号", 
                min_value=1, 
                max_value=len(cards), 
                value=current_idx+1, 
                key=f"jump_input_{current_idx}",
                label_visibility="collapsed"
            )
        with jump_col2:
            st.button("跳转", 
                     key=f"jump_btn_{current_idx}",
                     on_click=jump_to_card,
                     use_container_width=True)


def page_review():
    """Review plan page"""
    st.markdown('<h1 class="main-header">📅 今日复习</h1>', unsafe_allow_html=True)
    
    user_id = st.session_state['user_id']
    
    with st.spinner("正在加载复习计划..."):
        plan = call_api("/review_plan", data={"user_id": user_id})
    
    if not plan:
        return
    
    if plan['due_today'] == 0:
        st.success("🎉 今天没有需要复习的卡片！")
        return
    
    # Show summary
    col1, col2 = st.columns(2)
    with col1:
        st.metric("📝 待复习", plan['due_today'])
    with col2:
        st.metric("⚠️ 逾期", plan['overdue'])
    
    # Show cards
    st.write("### 待复习卡片")
    
    for card in plan['cards'][:10]:
        with st.expander(f"📋 {card['type'].upper()} - {card['stem'][:50]}..."):
            st.write(f"**题目:** {card['stem']}")
            st.write(f"**难度:** {card['difficulty']}")
            st.write(f"**来源:** {card.get('source_ref', 'N/A')}")


def page_favorites():
    """Favorites page - 收藏的卡片"""
    st.markdown('<h1 class="main-header">⭐ 我的收藏</h1>', unsafe_allow_html=True)
    
    if not st.session_state['favorites']:
        st.info("📝 还没有收藏任何卡片。在练习时点击'收藏'按钮收藏重要的知识卡片吧！")
        return
    
    # Get cards from cache
    doc_id = st.session_state.get('last_doc_id')
    cards_data = fetch_cards(doc_id, 100)
    
    if not cards_data or not cards_data.get('cards'):
        st.warning("⚠️ 请先上传文档并生成卡片")
        return
    
    all_cards = cards_data['cards']
    favorited_cards = [card for card in all_cards if card['card_id'] in st.session_state['favorites']]
    
    st.write(f"共收藏了 **{len(favorited_cards)}** 张卡片")
    
    # 显示收藏卡片的统计
    if favorited_cards:
        with st.expander("📊 收藏统计", expanded=True):
            fav_cards_tuple = tuple(tuple(sorted(card.items())) for card in favorited_cards)
            show_card_stats(fav_cards_tuple)
    
    # 筛选选项
    type_names = {
        'knowledge': '📚 知识卡片',
        'cloze': '📝 填空题',
        'mcq': '🎯 选择题',
        'short': '✍️ 简答题'
    }
    
    card_types = list(set([card['type'] for card in favorited_cards]))
    filter_type = st.selectbox(
        "筛选卡片类型",
        ['全部'] + [type_names.get(t, t) for t in card_types]
    )
    
    # Apply filter
    display_cards = favorited_cards
    if filter_type != '全部':
        type_map = {v: k for k, v in type_names.items()}
        selected_type = type_map.get(filter_type, filter_type)
        display_cards = [card for card in favorited_cards if card['type'] == selected_type]
    
    st.write(f"显示 **{len(display_cards)}** 张卡片")
    
    # Display cards
    for idx, card in enumerate(display_cards):
        with st.expander(f"{type_names.get(card['type'], card['type'])} - {card['stem'][:50]}...", expanded=False):
            col1, col2 = st.columns([5, 1])
            
            with col1:
                st.markdown(f"**题目：** {card['stem']}")
                st.markdown(f"**答案：** {card['answer']}")
                
                if card.get('choices'):
                    st.markdown("**选项：**")
                    for choice in card['choices']:
                        st.write(f"  - {choice}")
                
                if card.get('explanation'):
                    st.markdown(f"**解析：** {card['explanation']}")
            
            with col2:
                def remove_favorite(card_id):
                    st.session_state['favorites'].discard(card_id)
                
                st.button("🗑️ 移除", 
                         key=f"remove_fav_{idx}",
                         on_click=remove_favorite,
                         args=(card['card_id'],))


def page_report():
    """Learning report page"""
    st.markdown('<h1 class="main-header">📊 学习报告</h1>', unsafe_allow_html=True)
    
    user_id = st.session_state['user_id']
    
    # 添加tab切换
    tab1, tab2 = st.tabs(["📈 学习统计", "📚 学习历史"])
    
    with tab1:
        with st.spinner("正在加载学习报告..."):
            report = call_api("/report", data={"user_id": user_id})
        
        if not report:
            return
        
        if report.get('total_reviews', 0) == 0:
            st.info("📝 还没有练习记录，快去练习吧！")
            return
        
        # Show metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📊 总练习数", report['total_reviews'])
        with col2:
            st.metric("✅ 正确数", report['correct_count'])
        with col3:
            st.metric("📈 正确率", f"{report['accuracy']*100:.1f}%")
        with col4:
            st.metric("⏱️ 平均响应", f"{report['avg_latency_ms']/1000:.1f}秒")
        
        # Error distribution
        if report.get('error_distribution'):
            st.write("### 错误类型分布")
            error_data = report['error_distribution']
            st.bar_chart(error_data)
    
    with tab2:
        st.markdown("### 📚 我的学习历史")
        
        # 获取学习历史
        response = call_api(f"/progress/{user_id}/all")
        
        if not response or response.get('total', 0) == 0:
            st.info("📝 还没有学习历史记录")
            return
        
        progress_list = response['progress']
        
        st.write(f"共有 **{len(progress_list)}** 个文档的学习记录")
        
        for idx, prog in enumerate(progress_list):
            with st.expander(f"📄 {prog['doc_title']} ({prog['doc_type'].upper()})", expanded=(idx==0)):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("学习进度", f"{prog['current_card_idx']}/{prog['total_cards']}")
                
                with col2:
                    progress_pct = (prog['current_card_idx'] / prog['total_cards'] * 100) if prog['total_cards'] > 0 else 0
                    st.metric("完成度", f"{progress_pct:.1f}%")
                
                with col3:
                    last_updated = datetime.fromisoformat(prog['last_updated']).strftime("%m-%d %H:%M")
                    st.write(f"**最后学习:** {last_updated}")
                
                # 继续学习按钮
                if st.button("📖 继续学习", key=f"continue_{idx}"):
                    st.session_state['last_doc_id'] = prog['doc_id']
                    st.session_state['current_card_idx'] = prog['current_card_idx']
                    st.success(f"✅ 已切换到：{prog['doc_title']}")
                    st.info("💡 请前往'练习卡片'页面继续学习")


# ==================== 优化的Sidebar ====================

def render_sidebar():
    """渲染侧边栏（性能优化版）"""
    st.sidebar.title("📚 知卡学伴")
    st.sidebar.markdown("---")
    
    # Navigation
    page = st.sidebar.radio(
        "导航菜单",
        ["📤 上传资料", "✍️ 练习卡片", "⭐ 我的收藏", "📅 今日复习", "📊 学习报告"],
        key="main_navigation"
    )
    
    st.sidebar.markdown("---")
    
    # User info
    st.sidebar.write(f"👤 用户: {st.session_state['user_id']}")
    
    # API status check（带缓存，30秒刷新一次）
    api_status = check_api_health()
    if api_status:
        st.sidebar.success("✅ API 已连接")
    else:
        st.sidebar.error("❌ API 未连接")
    
    st.sidebar.markdown("---")
    
    # 系统信息（默认折叠，减少渲染开销）
    with st.sidebar.expander("ℹ️ 关于系统", expanded=False):
        st.markdown("""
        ### 🎓 多智能体协同学习系统
        
        **核心架构:**
        - 🤖 6个专业AI智能体协作
        - 📊 智能内容分析与提取
        - 🎯 多题型自动生成
        - 🧠 SM-2间隔重复算法
        
        **版本:** v0.8.5  
        **技术栈:** Multi-Agent + DeepSeek AI
        """)
    
    st.sidebar.markdown("---")
    st.sidebar.caption("💡 Powered by Multi-Agent System")
    
    return page


# ==================== Main App ====================

def main():
    """Main application - 性能优化版"""
    
    # 初始化session state
    init_session_state()
    
    # Render sidebar and get selected page
    page = render_sidebar()
    
    # Route to pages
    if page == "📤 上传资料":
        page_upload()
    elif page == "✍️ 练习卡片":
        page_practice()
    elif page == "⭐ 我的收藏":
        page_favorites()
    elif page == "📅 今日复习":
        page_review()
    elif page == "📊 学习报告":
        page_report()


if __name__ == "__main__":
    main()
