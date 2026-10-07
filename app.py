import streamlit as st
import pandas as pd
from collections import Counter
import random

st.set_page_config(page_title="快乐8分析", page_icon="🎱", layout="wide")
st.title("体彩快乐8历史分析")

# 1. 读取数据
@st.cache_data
def load_data():
    try:
        df = pd.read_excel('data/k8.xlsx')
        df['numbers'] = df['numbers'].fillna('').astype(str)
        # 新增：只保留我们需要的那三列
        df = df[['issue', 'date', 'numbers']]
        return df
    except Exception as e:
        st.error(f"读取数据失败，请确认 data/k8.xlsx 是否存在！错误：{e}")
        st.stop()

df = load_data()
# 把空行直接丢掉，防止后面处理时崩溃
df = df.dropna(subset=['numbers'])
df['numbers'] = df['numbers'].astype(str)  # 确保都是字符串
# 2. 提取每期的20个号码
all_draws = df['numbers'].astype(str).str.split(' ').tolist()
# 展平所有号码，用于统计频率
all_numbers_flat = []
for draw in all_draws:
    if isinstance(draw, list):  # 确保它是列表才遍历，过滤掉空值（float）
        for num in draw:
            if num and str(num).isdigit(): # 确保是数字才转换
                all_numbers_flat.append(int(num))

# 原来的第27行保留
freq_counter = Counter(all_numbers_flat)
# 3. 展示频率统计
st.header("📊 号码频率统计 (1-80)")
freq_data = [{"号码": i, "出现次数": freq_counter.get(i, 0)} for i in range(1, 81)]
freq_df = pd.DataFrame(freq_data)
st.bar_chart(freq_df.set_index("号码"))

# 4. 展示最新几期数据
st.header("📋 最新开奖数据")
st.dataframe(df.tail(10), use_container_width=True)

# ==========================================
# 5. 智能选号与历史记录（支持选四到选十）
# ==========================================
st.markdown("---")
st.header("🎯 智能选号辅助 (仅供娱乐)")
st.caption("注意：彩票开奖是独立随机事件，以下号码仅由历史数据统计生成，不代表预测结果，请理性对待。")

# 初始化 Session State，用于保存历史记录和当前生成的号码
if 'history_records' not in st.session_state:
    st.session_state.history_records = []
if 'current_pick' not in st.session_state:
    st.session_state.current_pick = None

# 用户设置
col1, col2 = st.columns(2)
with col1:
    # 修改这里：将玩法改成“选四”到“选十”
    play_options = ["选四 (挑4个号码)", "选五 (挑5个号码)", "选六 (挑6个号码)", "选七 (挑7个号码)", "选八 (挑8个号码)", "选九 (挑9个号码)", "选十 (挑10个号码)"]
    play_type = st.selectbox("选择玩法：", play_options)
with col2:
    strategy = st.selectbox("选择选号策略：", ["冷热结合（推荐）", "随机生成（纯机选）"])

# 提取玩法对应的号码个数
play_map = {"选四": 4, "选五": 5, "选六": 6, "选七": 7, "选八": 8, "选九": 9, "选十": 10}
# 提取 play_type 的前两个字，例如 "选四 (挑4个号码)" -> "选四"
play_key = play_type[:2]
num_count = play_map.get(play_key, 10)  # 默认选十

# 计算冷热号（用于冷热结合策略）
recent_df = df.tail(30)
recent_numbers = [int(num) for draw in recent_df['numbers'].astype(str).str.split(' ') for num in draw if num.isdigit()]
hot_counter = Counter(recent_numbers)
hot_nums = [num for num, count in hot_counter.most_common(15)]

# 计算遗漏（冷号）
def calc_omission_k8(df):
    last_seen = {i: -1 for i in range(1, 81)}
    for idx, row in df.iterrows():
        nums = [int(n) for n in str(row['numbers']).split(' ') if n.isdigit()]
        for n in nums:
            last_seen[n] = idx
    total = len(df)
    omission = {n: (total if pos == -1 else total - 1 - pos) for n, pos in last_seen.items()}
    return omission

omission_dict = calc_omission_k8(df)
cold_nums = sorted(omission_dict, key=omission_dict.get, reverse=True)[:15]

# 生成单注号码的逻辑
if st.button("生成一注号码"):
    if strategy == "冷热结合（推荐）":
        picks = set()
        # 如果是选四，正好2热2冷；如果选五以上，再随机补足
        picks.update(random.sample(hot_nums, min(2, len(hot_nums))))
        picks.update(random.sample(cold_nums, min(2, len(cold_nums))))
        while len(picks) < num_count:
            picks.add(random.randint(1, 80))
        final_picks = sorted(list(picks))
    else:
        # 纯随机
        final_picks = sorted(random.sample(range(1, 81), num_count))
        
    num_str = " ".join(f"{n:02d}" for n in final_picks)
    
    # 暂存当前生成的号码
    st.session_state.current_pick = {
        "玩法": play_key,
        "号码": num_str,
        "选号个数": num_count,
        "策略": strategy
    }

# 展示当前生成的号码，并提供保存按钮
if st.session_state.current_pick:
    st.success(f"当前生成的【{st.session_state.current_pick['玩法']}】号码如下：")
    st.code(st.session_state.current_pick["号码"], language=None)
    st.caption(f"选号个数：{st.session_state.current_pick['选号个数']} | 策略：{st.session_state.current_pick['策略']}")
    
    if st.button("💾 保存到历史记录"):
        # 补充一个编号
        record = st.session_state.current_pick.copy()
        record["序号"] = len(st.session_state.history_records) + 1
        st.session_state.history_records.append(record)
        st.session_state.current_pick = None # 保存后清空暂存，防止重复保存
        st.rerun() # 刷新页面，让历史记录立刻显示出来

# 6. 展示历史生成记录
if st.session_state.history_records:
    st.markdown("---")
    st.subheader("📋 历史生成记录")
    
    hist_df = pd.DataFrame(st.session_state.history_records)
    # 调整列顺序，把序号、玩法放前面
    cols = ['序号', '玩法', '号码', '选号个数', '策略']
    hist_df = hist_df[[c for c in cols if c in hist_df.columns]]
    
    tab1, tab2 = st.tabs(["当前历史列表", "下载/清空"])
    
    with tab1:
        st.dataframe(hist_df, use_container_width=True, hide_index=True)
        
        all_numbers = "\n".join(hist_df['号码'].astype(str).tolist())
        st.markdown("**👇 长按下方文本框，即可一键复制全部历史号码：**")
        st.code(all_numbers, language=None)
        
    with tab2:
        col_a, col_b = st.columns(2)
        with col_a:
            csv_data = hist_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 下载历史记录为 CSV",
                data=csv_data,
                file_name="k8_generated_history.csv",
                mime="text/csv"
            )
        with col_b:
            if st.button("🗑️ 清空历史记录"):
                st.session_state.history_records = []
                st.session_state.current_pick = None
                st.rerun()

st.caption("⚠️ 本工具仅供个人学习与娱乐，不构成任何购彩建议，请理性购彩。")