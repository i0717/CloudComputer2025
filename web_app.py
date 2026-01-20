import streamlit as st
import requests
import json
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import os
import time
import base64
from typing import Dict, List, Any
import io

# 页面配置
st.set_page_config(
    page_title="PPT内容扩展智能体",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API配置
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8010")

# 自定义CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #374151;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
    }
    .success-box {
        background-color: #D1FAE5;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #10B981;
        margin: 1rem 0;
    }
    .info-box {
        background-color: #DBEAFE;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #3B82F6;
        margin: 1rem 0;
    }
    .warning-box {
        background-color: #FEF3C7;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #F59E0B;
        margin: 1rem 0;
    }
    .slide-card {
        background-color: #F9FAFB;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #E5E7EB;
        margin-bottom: 1rem;
        transition: all 0.3s ease;
    }
    .slide-card:hover {
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        transform: translateY(-2px);
    }
    .expanded-content {
        background-color: #FEFCE8;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #EAB308;
        margin: 1rem 0;
    }
    .stButton > button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)


def check_api_health():
    """检查API健康状态"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=60)
        return response.status_code == 200
    except:
        return False


def call_api(endpoint: str, method: str = "GET", data: Dict = None, files: Dict = None):
    """调用API"""
    url = f"{API_BASE_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=180)
        elif method == "POST":
            if files:
                response = requests.post(url, files=files, data=data, timeout=180)
            else:
                response = requests.post(url, json=data, timeout=180)
        else:
            return {"error": f"不支持的HTTP方法: {method}"}

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 408:  # 超时错误
            return {"error": "请求超时，请稍后重试"}
        else:
            return {"error": f"API错误 ({response.status_code})", "details": response.text}

    except requests.exceptions.Timeout:
        return {"error": "请求超时，请检查网络连接或稍后重试"}
    except requests.exceptions.RequestException as e:
        return {"error": f"网络错误: {str(e)}"}


def show_header():
    """显示页面标题"""
    st.markdown('<h1 class="main-header">📚 PPT内容扩展智能体</h1>', unsafe_allow_html=True)
    st.markdown("""
    <div style="text-align: center; color: #6B7280; margin-bottom: 2rem;">
    基于云原生和LLM技术，自动扩展PPT内容，提供详细解释、代码示例和学习资源
    </div>
    """, unsafe_allow_html=True)


def show_sidebar():
    """显示侧边栏"""
    with st.sidebar:
        st.markdown("### 🎯 导航")
        page = st.radio(
            "选择功能",
            ["🏠 首页", "📤 上传PPT", "📋 文件管理", "🔍 内容扩展", "📚 学习模式", "⚙️ 设置"],
            label_visibility="collapsed"
        )

        st.markdown("---")
        st.markdown("### 📊 系统状态")

        # 显示API状态
        if check_api_health():
            st.success("✅ API连接正常")
        else:
            st.error("❌ API连接失败")
            st.info("请确保API服务已启动：`python main.py --mode api`")

        st.markdown("---")
        st.markdown("### 📈 统计信息")

        # 获取文件统计
        files_response = call_api("/api/files")
        if "files" in files_response:
            total_files = len(files_response["files"])
            total_slides = sum(f.get("total_slides", 0) for f in files_response["files"])

            col1, col2 = st.columns(2)
            with col1:
                st.metric("总文件数", total_files)
            with col2:
                st.metric("总幻灯片数", total_slides)

        st.markdown("---")
        st.markdown("### ℹ️ 快速开始")
        with st.expander("查看指南"):
            st.markdown("""
            1. **上传PPT文件** → 选择PPT/PPTX文件
            2. **查看解析结果** → 自动分析PPT结构
            3. **智能扩展** → AI生成详细内容
            4. **导出学习材料** → 支持多种格式

            **功能特点**：
            - 🧠 智能内容扩展
            - 💻 代码示例生成
            - 📖 学习资源推荐
            - ❓ 自测问题生成
            - 📊 学习进度跟踪
            """)

        return page


def home_page():
    """首页"""
    st.markdown('<h2 class="sub-header">🏠 欢迎使用PPT内容扩展智能体</h2>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div class="info-box">
        <h3>🎯 核心功能</h3>
        <ul>
        <li><b>智能解析</b>：自动分析PPT结构</li>
        <li><b>知识扩展</b>：AI生成详细解释</li>
        <li><b>代码示例</b>：自动生成相关代码</li>
        <li><b>资源推荐</b>：提供学习参考资料</li>
        <li><b>测验生成</b>：创建自测问题</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="info-box">
        <h3>🚀 快速开始</h3>
        <ol>
        <li>点击左侧"上传PPT"</li>
        <li>选择你的PPT文件</li>
        <li>查看解析结果</li>
        <li>选择要扩展的内容</li>
        <li>下载学习材料</li>
        </ol>
        </div>
        """, unsafe_allow_html=True)

    # 使用指南
    st.markdown("---")
    st.markdown('<h3>📖 使用指南</h3>', unsafe_allow_html=True)

    guide_cols = st.columns(3)

    with guide_cols[0]:
        st.markdown("""
        ### 1. 上传文件
        - 支持PPT/PPTX格式
        - 最大100MB
        - 自动解析结构
        - 保存历史记录
        """)

    with guide_cols[1]:
        st.markdown("""
        ### 2. 智能扩展
        - 选择特定幻灯片
        - 多种扩展类型
        - 实时进度显示
        - 批量处理支持
        """)

    with guide_cols[2]:
        st.markdown("""
        ### 3. 学习工具
        - Markdown导出
        - 测验自测
        - 进度跟踪
        - 搜索功能
        """)

    # 系统要求
    st.markdown("---")
    st.markdown('<h3>⚙️ 系统要求</h3>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        **运行环境**：
        - Python 3.8+
        - 4GB以上内存
        - 网络连接

        **API要求**：
        - 硅基流动API密钥
        - FastAPI服务
        """)

    with col2:
        st.markdown("""
        **依赖库**：
        - FastAPI / Streamlit
        - LangChain
        - python-pptx
        - ChromaDB

        **浏览器**：
        - Chrome 90+
        - Firefox 88+
        - Edge 90+
        """)


def upload_page():
    """上传页面"""
    st.markdown('<h2 class="sub-header">📤 上传PPT文件</h2>', unsafe_allow_html=True)

    # 上传区域
    uploaded_file = st.file_uploader(
        "选择PPT文件",
        type=['pptx', 'ppt'],
        help="支持PPT和PPTX格式，最大100MB"
    )

    if uploaded_file is not None:
        # 显示文件信息
        file_size = uploaded_file.size / 1024 / 1024  # MB
        file_info = {
            "filename": uploaded_file.name,
            "size": f"{file_size:.2f} MB",
            "type": uploaded_file.type
        }

        st.markdown(f"""
        <div class="info-box">
        <h4>📄 文件信息</h4>
        <p><b>文件名</b>: {file_info['filename']}</p>
        <p><b>文件大小</b>: {file_info['size']}</p>
        <p><b>文件类型</b>: {file_info['type']}</p>
        </div>
        """, unsafe_allow_html=True)

        # 文件描述
        description = st.text_area(
            "文件描述（可选）",
            placeholder="请输入PPT的主要内容、课程名称或用途...",
            height=80,
            help="描述将帮助AI更好地理解内容"
        )

        # 扩展选项
        st.markdown("### ⚙️ 扩展选项")

        col1, col2 = st.columns(2)

        with col1:
            expand_explanations = st.checkbox("详细解释", value=True,
                                              help="为每个概念生成详细解释")
            expand_examples = st.checkbox("代码示例", value=True,
                                          help="为技术内容生成代码示例")

        with col2:
            expand_references = st.checkbox("参考资源", value=True,
                                            help="推荐学习资源")
            expand_quiz = st.checkbox("测验问题", value=True,
                                      help="生成自测问题")

        # 上传按钮
        if st.button("🚀 开始上传和处理", type="primary", use_container_width=True):
            with st.spinner("正在上传和处理文件..."):
                # 创建进度显示
                progress_bar = st.progress(0)
                status_text = st.empty()

                # 上传文件
                status_text.text("📤 上传文件中...")
                files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
                data = {"description": description}

                progress_bar.progress(25)

                # 调用上传API
                response = call_api("/api/upload", "POST", data=data, files=files)

                if "error" in response:
                    st.error(f"上传失败: {response['error']}")
                    if "details" in response:
                        with st.expander("查看错误详情"):
                            st.code(response["details"])
                else:
                    progress_bar.progress(50)
                    status_text.text("🔍 解析PPT内容...")

                    # 显示结果
                    progress_bar.progress(75)
                    status_text.text("✅ 处理完成！")

                    st.markdown(f"""
                    <div class="success-box">
                    <h4>✅ 文件上传成功！</h4>
                    <p><b>文件ID</b>: {response.get('file_id', 'N/A')}</p>
                    <p><b>幻灯片数量</b>: {response.get('total_slides', 0)}</p>
                    <p><b>处理状态</b>: 已完成</p>
                    </div>
                    """, unsafe_allow_html=True)

                    # 显示大纲预览
                    if "outline" in response and response["outline"]:
                        with st.expander("📑 查看PPT大纲", expanded=True):
                            for item in response["outline"]:
                                st.write(item)

                    # 保存文件ID到session state
                    st.session_state.current_file_id = response.get('file_id')
                    st.session_state.expansion_options = {
                        "explanations": expand_explanations,
                        "examples": expand_examples,
                        "references": expand_references,
                        "quiz": expand_quiz
                    }

                    progress_bar.progress(100)
                    time.sleep(0.5)
                    progress_bar.empty()
                    status_text.empty()

                    st.success("✅ 文件处理完成！请在'内容扩展'页面继续操作。")


def file_management_page():
    """文件管理页面"""
    st.markdown('<h2 class="sub-header">📋 文件管理</h2>', unsafe_allow_html=True)

    # 刷新按钮
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("🔄 刷新列表", use_container_width=True):
            st.rerun()

    # 获取文件列表
    files_response = call_api("/api/files")

    if "files" in files_response and files_response["files"]:
        files = files_response["files"]

        # 文件统计
        st.markdown("### 📊 文件统计")
        stat_cols = st.columns(4)

        with stat_cols[0]:
            st.metric("总文件数", len(files))
        with stat_cols[1]:
            total_slides = sum(f.get("total_slides", 0) for f in files)
            st.metric("总幻灯片数", total_slides)
        with stat_cols[2]:
            avg_slides = total_slides // max(len(files), 1)
            st.metric("平均幻灯片", avg_slides)
        with stat_cols[3]:
            latest_file = files[0]["filename"] if files else "无"
            st.metric("最近上传", latest_file[:15] + "..." if len(latest_file) > 15 else latest_file)

        # 文件列表
        st.markdown("### 📄 文件列表")

        for file_info in files:
            with st.container():
                st.markdown(f'<div class="slide-card">', unsafe_allow_html=True)

                cols = st.columns([3, 1, 1, 1])

                with cols[0]:
                    st.write(f"**{file_info['filename']}**")
                    st.caption(f"📅 上传时间: {file_info['uploaded_at'][:16]}")
                    if file_info.get('description'):
                        st.info(f"📝 {file_info['description']}")

                with cols[1]:
                    st.metric("幻灯片", file_info.get('total_slides', 0))

                with cols[2]:
                    if st.button("选择", key=f"select_{file_info['file_id']}", use_container_width=True):
                        st.session_state.current_file_id = file_info['file_id']
                        st.success(f"已选择: {file_info['filename']}")
                        st.rerun()

                with cols[3]:
                    if st.button("删除", key=f"delete_{file_info['file_id']}",
                                 use_container_width=True, type="secondary"):
                        # 这里应该调用删除API
                        st.warning("删除功能开发中...")

                st.markdown('</div>', unsafe_allow_html=True)

        # 显示当前选中文件的详细信息
        if 'current_file_id' in st.session_state and st.session_state.current_file_id:
            st.markdown("---")
            show_file_details(st.session_state.current_file_id)

    else:
        st.markdown("""
        <div class="warning-box">
        <h4>📭 还没有上传任何文件</h4>
        <p>请先前往<strong>上传PPT</strong>页面上传你的PPT文件。</p>
        </div>
        """, unsafe_allow_html=True)


def show_file_details(file_id: str):
    """显示文件详情"""
    st.markdown(f"### 📄 文件详情")

    file_response = call_api(f"/api/file/{file_id}")

    if "error" in file_response:
        st.error(f"获取文件详情失败: {file_response['error']}")
        return

    file_info = file_response

    # 基本信息
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("文件大小", f"{file_info.get('file_size', 0) / 1024:.1f} KB")
    with col2:
        st.metric("幻灯片数", file_info.get('structure', {}).get('total_slides', 0))
    with col3:
        st.metric("关键词数", len(file_info.get('structure', {}).get('keywords', [])))
    with col4:
        st.metric("解析状态", "✅ 完成")

    # 标签页
    tab1, tab2, tab3, tab4 = st.tabs(["📑 幻灯片预览", "🗺️ 大纲视图", "🔑 关键词", "📊 统计图表"])

    with tab1:
        slides_preview = file_info.get('slides_preview', [])
        for slide in slides_preview:
            with st.expander(f"幻灯片 {slide['slide_number'] + 1}: {slide['title']}"):
                st.write(f"**层级**: {'#' * slide.get('level', 1)}")
                st.write(f"**内容预览**: {slide.get('content_preview', '无内容')}")

                # 查看详情按钮
                if st.button("查看完整内容", key=f"view_slide_{slide['slide_number']}"):
                    slide_detail = call_api(f"/api/file/{file_id}/slide/{slide['slide_number']}")
                    if "error" not in slide_detail:
                        st.json(slide_detail)

    with tab2:
        outline = file_info.get('structure', {}).get('outline', [])
        if outline:
            for item in outline:
                st.write(item)
        else:
            st.info("暂无大纲信息")

    with tab3:
        keywords = file_info.get('structure', {}).get('keywords', [])
        if keywords:
            keyword_text = " ".join([f"`{kw}`" for kw in keywords])
            st.markdown(keyword_text)
        else:
            st.info("暂无关键词")

    with tab4:
        # 生成统计图表
        slides_preview = file_info.get('slides_preview', [])
        if slides_preview:
            # 层级分布
            levels = [s.get('level', 1) for s in slides_preview]
            level_counts = pd.Series(levels).value_counts().sort_index()

            fig1 = go.Figure(data=[
                go.Bar(
                    x=[f"层级 {i}" for i in level_counts.index],
                    y=level_counts.values,
                    marker_color='#3B82F6'
                )
            ])
            fig1.update_layout(
                title="幻灯片层级分布",
                xaxis_title="层级",
                yaxis_title="数量",
                height=300
            )
            st.plotly_chart(fig1, use_container_width=True)

            # 标题长度分布
            title_lengths = [len(s.get('title', '')) for s in slides_preview]
            fig2 = go.Figure(data=[
                go.Histogram(
                    x=title_lengths,
                    nbinsx=10,
                    marker_color='#10B981'
                )
            ])
            fig2.update_layout(
                title="标题长度分布",
                xaxis_title="标题长度（字符）",
                yaxis_title="数量",
                height=300
            )
            st.plotly_chart(fig2, use_container_width=True)


def expansion_page():
    """内容扩展页面"""
    st.markdown('<h2 class="sub-header">🔍 内容扩展</h2>', unsafe_allow_html=True)

    if 'current_file_id' not in st.session_state or not st.session_state.current_file_id:
        st.warning("⚠️ 请先在文件管理页面选择一个文件")
        return

    file_id = st.session_state.current_file_id

    # 获取文件详情
    file_response = call_api(f"/api/file/{file_id}")
    if "error" in file_response:
        st.error(f"获取文件失败: {file_response['error']}")
        return

    file_info = file_response
    total_slides = file_info.get('structure', {}).get('total_slides', 0)

    if total_slides == 0:
        st.error("该文件没有幻灯片")
        return

    st.markdown(f"### 📄 当前文件: {file_info.get('filename', '未知文件')}")

    # 幻灯片选择
    st.markdown("### 🎯 选择要扩展的幻灯片")

    col1, col2 = st.columns(2)

    with col1:
        # 选择模式
        selection_mode = st.radio(
            "选择模式",
            ["全部幻灯片", "指定范围", "手动选择"],
            horizontal=True
        )

    with col2:
        # 扩展选项
        st.markdown("**扩展内容**")
        expand_types = []

        col_a, col_b = st.columns(2)
        with col_a:
            if st.checkbox("详细解释", value=True):
                expand_types.append("explanation")
            if st.checkbox("参考资源", value=True):
                expand_types.append("references")
        with col_b:
            if st.checkbox("代码示例", value=True):
                expand_types.append("examples")
            if st.checkbox("测验问题", value=True):
                expand_types.append("quiz")

    # 根据选择模式确定幻灯片
    slide_numbers = []

    if selection_mode == "全部幻灯片":
        slide_numbers = list(range(total_slides))
        st.info(f"将扩展全部 {total_slides} 张幻灯片")

    elif selection_mode == "指定范围":
        col1, col2 = st.columns(2)
        with col1:
            start_slide = st.number_input("起始幻灯片", min_value=1, max_value=total_slides, value=1)
        with col2:
            end_slide = st.number_input("结束幻灯片", min_value=1, max_value=total_slides, value=min(5, total_slides))

        if start_slide <= end_slide:
            slide_numbers = list(range(start_slide - 1, end_slide))
            st.info(f"将扩展第 {start_slide} 到第 {end_slide} 张幻灯片，共 {len(slide_numbers)} 张")
        else:
            st.error("起始幻灯片不能大于结束幻灯片")

    else:  # 手动选择
        slides_preview = file_info.get('slides_preview', [])
        for slide in slides_preview:
            if st.checkbox(f"幻灯片 {slide['slide_number'] + 1}: {slide['title']}",
                           value=False, key=f"slide_{slide['slide_number']}"):
                slide_numbers.append(slide['slide_number'])

        if slide_numbers:
            st.info(f"已选择 {len(slide_numbers)} 张幻灯片")
        else:
            st.warning("请至少选择一张幻灯片")

    # 扩展按钮
    if slide_numbers and expand_types:
        if st.button("🚀 开始智能扩展", type="primary", use_container_width=True):
            with st.spinner("正在使用AI扩展内容..."):
                # 准备请求数据
                request_data = {
                    "slide_numbers": slide_numbers,
                    "expansion_types": expand_types
                }

                # 显示进度
                progress_bar = st.progress(0)
                status_text = st.empty()

                status_text.text("📤 发送扩展请求...")
                progress_bar.progress(10)

                # 调用扩展API
                response = call_api(f"/api/expand/{file_id}", "POST", data=request_data)

                if "error" in response:
                    st.error(f"扩展失败: {response['error']}")
                else:
                    progress_bar.progress(50)
                    status_text.text("🧠 AI正在处理内容...")

                    # 等待处理完成（轮询结果）
                    result_id = response.get('result_id')
                    if result_id:
                        # 简单轮询
                        for i in range(10):
                            time.sleep(2)
                            result_response = call_api(f"/api/expansion/{result_id}")

                            if "error" not in result_response:
                                progress_bar.progress(70 + (i * 3))

                                if result_response.get('total_slides', 0) > 0:
                                    progress_bar.progress(100)
                                    status_text.text("✅ 扩展完成！")

                                    st.markdown(f"""
                                    <div class="success-box">
                                    <h4>✅ 内容扩展完成！</h4>
                                    <p><b>扩展结果ID</b>: {result_id}</p>
                                    <p><b>处理幻灯片</b>: {response.get('total_expanded', 0)} 张</p>
                                    <p><b>完成时间</b>: {datetime.now().strftime('%H:%M:%S')}</p>
                                    </div>
                                    """, unsafe_allow_html=True)

                                    # 显示预览
                                    show_expansion_preview(result_response)

                                    # 下载选项
                                    # 在 expansion_page() 函数中
                                    st.markdown("### 📥 下载扩展内容")
                                    col1, col2 = st.columns(2)

                                    with col1:
                                        # 创建下载链接
                                        download_url = f"{API_BASE_URL}/api/download/{file_id}?format=markdown"
                                        st.markdown(
                                            f'<a href="{download_url}" target="_blank" style="text-decoration: none;">'
                                            f'<button style="width: 100%; padding: 10px; background-color: #4CAF50; color: white; border: none; border-radius: 5px; cursor: pointer;">'
                                            f'📄 下载Markdown'
                                            f'</button>'
                                            f'</a>',
                                            unsafe_allow_html=True
                                        )

                                    with col2:
                                        download_url = f"{API_BASE_URL}/api/download/{file_id}?format=json"
                                        st.markdown(
                                            f'<a href="{download_url}" target="_blank" style="text-decoration: none;">'
                                            f'<button style="width: 100%; padding: 10px; background-color: #2196F3; color: white; border: none; border-radius: 5px; cursor: pointer;">'
                                            f'📊 下载JSON'
                                            f'</button>'
                                            f'</a>',
                                            unsafe_allow_html=True
                                        )

                                    break

                    progress_bar.empty()
                    status_text.empty()
    elif not slide_numbers:
        st.warning("请选择要扩展的幻灯片")
    elif not expand_types:
        st.warning("请选择至少一种扩展类型")


def show_expansion_preview(expansion_result: Dict[str, Any]):
    """显示扩展内容预览"""
    slides = expansion_result.get('slides', [])

    if not slides:
        st.info("暂无扩展内容")
        return

    st.markdown("### 📝 扩展内容预览")

    for slide_result in slides[:3]:  # 只显示前3张
        if "error" in slide_result:
            continue

        with st.expander(f"幻灯片 {slide_result['slide_number'] + 1}: {slide_result['title']}", expanded=False):
            st.markdown('<div class="expanded-content">', unsafe_allow_html=True)

            # 显示详细解释
            if "explanations" in slide_result and slide_result["explanations"]:
                st.markdown("**📚 详细解释**")
                for exp in slide_result["explanations"][:2]:  # 只显示前2个
                    st.markdown(f"**{exp.get('concept', '概念')}**")
                    st.write(exp.get('explanation', '')[:200] + "...")
                    st.markdown("---")

            # 显示代码示例
            if "examples" in slide_result and slide_result["examples"]:
                st.markdown("**💻 代码示例**")
                for exp in slide_result["examples"]:
                    st.code(exp.get('code_example', '')[:300] + "...",
                            language=exp.get('language', 'python'))

            # 显示参考资源
            if "references" in slide_result and slide_result["references"]:
                st.markdown("**📖 参考资源**")
                for ref in slide_result["references"][:3]:  # 只显示前3个
                    st.write(f"- **{ref.get('title', '资源')}**: {ref.get('description', '')[:100]}...")

            # 显示测验问题
            if "quiz_questions" in slide_result and slide_result["quiz_questions"]:
                st.markdown("**❓ 测验问题**")
                for quiz in slide_result["quiz_questions"]:
                    st.write(f"**问题**: {quiz.get('question', '')}")
                    st.write(f"**答案**: {quiz.get('answer', '')}")

            st.markdown('</div>', unsafe_allow_html=True)

    if len(slides) > 3:
        st.info(f"还有 {len(slides) - 3} 张幻灯片的扩展内容未显示...")


def learning_mode_page():
    """学习模式页面"""
    st.markdown('<h2 class="sub-header">📚 学习模式</h2>', unsafe_allow_html=True)

    st.markdown("""
    <div class="info-box">
    <h4>🎯 学习模式功能</h4>
    <p>利用AI生成的扩展内容，提供个性化的学习体验。</p>
    </div>
    """, unsafe_allow_html=True)

    # 搜索功能
    st.markdown("### 🔍 搜索学习内容")

    search_query = st.text_input("输入搜索关键词", placeholder="例如：机器学习、算法、数据库...")

    if search_query:
        if st.button("开始搜索", type="primary"):
            with st.spinner("正在搜索..."):
                search_data = {"query": search_query, "limit": 10}
                search_response = call_api("/api/search", "POST", data=search_data)

                if "error" in search_response:
                    st.error(f"搜索失败: {search_response['error']}")
                else:
                    results = search_response.get("results", [])
                    total_results = search_response.get("total_results", 0)

                    st.success(f"找到 {total_results} 个相关结果")

                    for result in results:
                        with st.container():
                            st.markdown(f"**文件**: {result['filename']}")
                            st.markdown(f"**幻灯片 {result['slide_number'] + 1}**: {result['title']}")
                            st.markdown(f"**内容预览**: {result['content_preview']}")
                            st.markdown(f"**相关度**: {'⭐' * min(result['relevance'], 5)}")
                            st.markdown("---")

    # 测验模式
    st.markdown("### ❓ 知识测验")

    if 'current_file_id' in st.session_state and st.session_state.current_file_id:
        file_id = st.session_state.current_file_id

        if st.button("生成学习测验", use_container_width=True):
            # 这里应该调用API生成测验
            st.info("测验生成功能开发中...")
    else:
        st.warning("请先选择一个文件来生成测验")


def settings_page():
    """设置页面"""
    st.markdown('<h2 class="sub-header">⚙️ 系统设置</h2>', unsafe_allow_html=True)

    # API设置
    st.markdown("### 🔧 API设置")

    api_key = st.text_input(
        "硅基流动API密钥",
        value=os.getenv("SILICONFLOW_API_KEY", ""),
        type="password",
        help="从 https://cloud.siliconflow.cn/ 获取"
    )

    api_base_url = st.text_input(
        "API基础URL",
        value=os.getenv("API_BASE_URL", "http://localhost:8000"),
        help="后端API服务的地址"
    )

    # 模型设置
    st.markdown("### 🧠 AI模型设置")

    model_name = st.selectbox(
        "选择模型",
        ["deepseek-ai/DeepSeek-V3.2-Exp", "deepseek-ai/DeepSeek-V2", "其他模型"],
        help="选择要使用的AI模型"
    )

    temperature = st.slider(
        "创造性 (Temperature)",
        min_value=0.0,
        max_value=1.0,
        value=0.7,
        step=0.1,
        help="值越高，生成的内容越有创造性"
    )

    # 文件设置
    st.markdown("### 📁 文件设置")

    max_file_size = st.slider(
        "最大文件大小 (MB)",
        min_value=10,
        max_value=500,
        value=100,
        step=10,
        help="允许上传的最大文件大小"
    )

    # 保存设置
    if st.button("💾 保存设置", type="primary", use_container_width=True):
        # 这里应该保存设置到配置文件
        st.success("设置已保存！")

        # 更新环境变量
        os.environ["SILICONFLOW_API_KEY"] = api_key
        os.environ["API_BASE_URL"] = api_base_url

        st.info("部分设置需要重启应用才能生效")


def main():
    """主函数"""
    show_header()

    # 检查API连接
    if not check_api_health():
        st.markdown("""
        <div class="warning-box">
        <h4>⚠️ API服务未连接</h4>
        <p>请确保API服务已启动，可以执行以下命令：</p>
        <pre><code>python main.py --mode api</code></pre>
        <p>或者</p>
        <pre><code>uvicorn api:app --host 0.0.0.0 --port 8000</code></pre>
        </div>
        """, unsafe_allow_html=True)

    # 显示侧边栏并获取当前页面
    page = show_sidebar()

    # 根据页面路由
    if page == "🏠 首页":
        home_page()
    elif page == "📤 上传PPT":
        upload_page()
    elif page == "📋 文件管理":
        file_management_page()
    elif page == "🔍 内容扩展":
        expansion_page()
    elif page == "📚 学习模式":
        learning_mode_page()
    elif page == "⚙️ 设置":
        settings_page()


if __name__ == "__main__":
    # 初始化session state
    if 'current_file_id' not in st.session_state:
        st.session_state.current_file_id = None
    if 'expansion_options' not in st.session_state:
        st.session_state.expansion_options = {}

    main()