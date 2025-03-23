import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import re

# 设置页面配置
st.set_page_config(
    page_title="脑电数据分析工具",
    page_icon="🧠",
    layout="wide"
)

# 应用标题
st.title("脑电数据分析工具")
st.markdown("上传并分析您的脑电数据，适合初学者使用的简易工具")

# 定义EEG数据解析函数
def parse_eeg_data(text_data):
    # 初始化数据列表
    data_points = []
    
    # 将文本分割成行
    lines = text_data.strip().split('\n')
    
    # 正则表达式匹配十六进制字节
    hex_pattern = r'([0-9A-F]{2})'
    
    for line in lines:
        # 尝试提取所有十六进制字节
        hex_bytes = re.findall(hex_pattern, line)
        
        if len(hex_bytes) < 10:  # 跳过过短的行
            continue
            
        # 尝试找到AA AA同步字节的位置
        for i in range(len(hex_bytes) - 1):
            if hex_bytes[i] == 'AA' and hex_bytes[i+1] == 'AA':
                # 找到潜在的数据包起始点
                if i + 4 < len(hex_bytes):  # 确保有足够的数据
                    try:
                        # 提取数据包长度
                        payload_length = int(hex_bytes[i+2], 16)
                        
                        # 检查是否有完整数据包
                        if i + payload_length + 4 <= len(hex_bytes):
                            # 解析数据点
                            data_point = {}
                            
                            # 检查是否包含注意力值和放松度值
                            for j in range(i, i+payload_length):
                                if j + 1 < len(hex_bytes):
                                    if hex_bytes[j] == '04':  # 注意力代码
                                        data_point['attention'] = int(hex_bytes[j+1], 16)
                                    
                                    if hex_bytes[j] == '05':  # 放松度代码
                                        data_point['meditation'] = int(hex_bytes[j+1], 16)
                                        
                                    if hex_bytes[j] == '02':  # 信号质量代码
                                        data_point['signal_quality'] = int(hex_bytes[j+1], 16)
                            
                            if data_point:  # 如果解析出有效数据点
                                data_points.append(data_point)
                    except:
                        continue  # 解析错误，继续尝试下一个位置
    
    return data_points

# 创建侧边栏
st.sidebar.title("功能导航")
page = st.sidebar.radio("选择功能", ["数据上传与解析", "数据可视化", "学习资源"])

# 数据上传与解析页面
if page == "数据上传与解析":
    st.header("数据上传与解析")
    
    # 文件上传
    uploaded_file = st.file_uploader("上传脑电数据文件", type=["txt"])
    
    if uploaded_file is not None:
        # 读取上传的文件
        raw_data = uploaded_file.getvalue().decode("utf-8")
        
        # 显示原始数据预览
        with st.expander("查看原始数据预览"):
            st.text(raw_data[:1000] + "..." if len(raw_data) > 1000 else raw_data)
        
        # 解析数据
        with st.spinner('正在解析数据...'):
            data_points = parse_eeg_data(raw_data)
        
        # 将数据转换为DataFrame以便分析
        if data_points:
            df = pd.DataFrame(data_points)
            st.session_state['eeg_data'] = df
            
            # 显示解析结果
            st.success(f"成功解析 {len(data_points)} 个数据点")
            
            # 显示数据预览
            st.subheader("数据预览")
            st.dataframe(df.head(10))
            
            # 显示数据统计
            st.subheader("数据统计")
            
            # 创建两列布局
            col1, col2 = st.columns(2)
            
            with col1:
                if 'attention' in df.columns:
                    st.metric("平均注意力", f"{df['attention'].mean():.2f}")
                if 'meditation' in df.columns:
                    st.metric("平均放松度", f"{df['meditation'].mean():.2f}")
            
            with col2:
                if 'signal_quality' in df.columns:
                    bad_signals = [0x1D, 0x36, 0x37, 0x38, 0x50, 0x51, 0x52, 0x6B, 0xC8]
                    bad_signal_count = sum(df['signal_quality'].isin(bad_signals))
                    bad_signal_pct = (bad_signal_count / len(df)) * 100 if len(df) > 0 else 0
                    st.metric("数据质量", f"{100 - bad_signal_pct:.1f}% 良好")
        else:
            st.error("无法解析数据。请确保文件格式正确。")
            st.info("数据应包含以十六进制格式表示的EEG数据包，如 'AA AA 20 02 50 83 18...'")

# 数据可视化页面
elif page == "数据可视化":
    st.header("数据可视化")
    
    if 'eeg_data' not in st.session_state:
        st.warning("请先上传并解析数据")
    else:
        df = st.session_state['eeg_data']
        
        # 创建时间轴数据
        df['time'] = np.arange(len(df)) / 10.0  # 假设采样率为10Hz
        
        # 注意力和放松度
        if 'attention' in df.columns and 'meditation' in df.columns:
            st.subheader("注意力和放松度")
            
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.plot(df['time'], df['attention'], 'r-', label='注意力')
            ax.plot(df['time'], df['meditation'], 'b-', label='放松度')
            ax.set_xlabel('时间 (秒)')
            ax.set_ylabel('值 (0-100)')
            ax.set_ylim(0, 100)
            ax.legend()
            ax.grid(True)
            
            st.pyplot(fig)
            
            # 添加简单分析
            avg_attention = df['attention'].mean()
            avg_meditation = df['meditation'].mean()
            
            st.subheader("数据解读")
            
            if avg_attention > 60:
                st.info("您的平均注意力水平较高，表明您在记录期间保持了良好的专注状态。")
            elif avg_attention < 40:
                st.info("您的平均注意力水平较低，可能表明您在记录期间比较放松或分心。")
            else:
                st.info("您的平均注意力水平处于中等水平。")
                
            if avg_meditation > 60:
                st.info("您的平均放松度较高，表明您在记录期间处于较为放松的状态。")
            elif avg_meditation < 40:
                st.info("您的平均放松度较低，可能表明您在记录期间比较紧张或警觉。")
            else:
                st.info("您的平均放松度处于中等水平。")
                
            if avg_attention > 60 and avg_meditation > 60:
                st.success("您同时保持了较高的注意力和放松度，这是一种理想的'放松而专注'的状态，常见于冥想和高效学习时。")

# 学习资源页面
elif page == "学习资源":
    st.header("EEG学习资源")
    
    st.subheader("脑电波频段基础知识")
    
    # 使用表格展示频段信息
    freq_info = {
        "频段": ["Delta", "Theta", "Alpha", "Beta", "Gamma"],
        "频率范围": ["1-3 Hz", "4-7 Hz", "8-12 Hz", "13-30 Hz", ">30 Hz"],
        "主要相关状态": ["深度睡眠、恢复过程", "冥想、记忆处理、创造性思维", "放松但清醒、闭眼状态", "警觉、注意力集中、积极思考", "高级认知处理、感觉整合"]
    }
    
    st.table(pd.DataFrame(freq_info))
    
    # 添加学习资源链接
    st.subheader("推荐学习资源")
    
    st.markdown("""
    1. **入门教程**
       - [EEG/ERP分析导论](https://sccn.ucsd.edu/wiki/EEGLAB_Wiki)
       - [MNE-Python教程](https://mne.tools/stable/auto_tutorials/index.html)
    
    2. **学术资源**
       - Klimesch, W. (2012). Alpha-band oscillations, attention, and controlled access to stored information.
       - Cohen, M. X. (2014). Analyzing neural time series data: theory and practice.
    
    3. **实践工具**
       - [Emotiv社区](https://www.emotiv.com/documentation/)
       - [NeuroSky开发者资源](http://developer.neurosky.com/)
    """)
    
    st.subheader("常见问题")
    
    with st.expander("EEG数据中常见的伪影是什么？"):
        st.write("""
        EEG数据中常见的伪影包括：
        - **眨眼伪影**：眨眼时产生的大幅波动，主要影响前额区域
        - **肌电伪影**：由肌肉活动产生，通常是高频信号
        - **电源线干扰**：50Hz或60Hz的规律性噪声，取决于所在国家的电网频率
        - **电极移动伪影**：电极松动或移动导致的突然跳变
        
        这些伪影可以通过ICA（独立成分分析）、滤波和人工检查等方法去除。
        """)
    
    with st.expander("如何提高EEG数据质量？"):
        st.write("""
        提高EEG数据质量的方法：
        1. 确保电极与头皮良好接触，可使用导电凝胶
        2. 要求被试保持静止，减少眨眼和面部肌肉活动
        3. 在电磁干扰较小的环境中记录数据
        4. 使用屏蔽线缆和适当的接地
        5. 定期检查设备校准情况
        """)
    
    with st.expander("如何解读注意力和放松度数值？"):
        st.write("""
        注意力和放松度数值通常在0-100之间：
        
        **注意力指标**:
        - 0-20: 非常分心或注意力非常低
        - 20-40: 轻度注意
        - 40-60: 中等注意力水平
        - 60-80: 较高注意力水平
        - 80-100: 非常专注
        
        **放松度指标**:
        - 0-20: 紧张或焦虑状态
        - 20-40: 轻度放松
        - 40-60: 中等放松状态
        - 60-80: 较为放松
        - 80-100: 深度放松状态
        
        这些值是通过专有算法从原始脑电数据中计算得出的，可用作相对参考，但不应作为绝对医学指标。
        """)

# 添加页脚
st.markdown("---")
st.markdown("脑电数据分析工具 | 专为初学者设计 | ©2023")
