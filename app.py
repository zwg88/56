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


def parse_numbers(text):
    """把 "2 8 14 ..." 拆成合法号码（1-80）。

    历史数据里有个别格子少了空格（如 "1617" 其实是 16 和 17），
    这种 token 会被当成 1617 —— 直接忽略，避免它污染频率/遗漏/选号。
    """
    out = []
    for tok in str(text).split():
        if tok.isdigit():
            n = int(tok)
            if 1 <= n <= 80:
                out.append(n)
    return out


# 2. 提取每期的号码，展平用于统计频率
all_numbers_flat = []
for _text in df['numbers']:
    all_numbers_flat.extend(parse_numbers(_text))

# 3. 展示频率统计
freq_counter = Counter(all_numbers_flat)
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

# 初始化 Session State，用于保存历史记录和最近一次生成的号码（本批）
for _k, _v in (
    ("history_records", []),
    ("last_batch", []),
    ("last_batch_info", {}),
):
    if _k not in st.session_state:
        st.session_state[_k] = _v

# 用户设置
col1, col2, col3 = st.columns(3)
with col1:
    # 修改这里：将玩法改成“选四”到“选十”
    play_options = ["选四 (挑4个号码)", "选五 (挑5个号码)", "选六 (挑6个号码)", "选七 (挑7个号码)", "选八 (挑8个号码)", "选九 (挑9个号码)", "选十 (挑10个号码)"]
    play_type = st.selectbox("选择玩法：", play_options)
with col2:
    strategy = st.selectbox("选择选号策略：", ["冷热结合（推荐）", "随机生成（纯机选）"])
with col3:
    batch_count = int(
        st.number_input("一次生成几注", min_value=1, max_value=10, value=1, step=1)
    )

# 提取玩法对应的号码个数
play_map = {"选四": 4, "选五": 5, "选六": 6, "选七": 7, "选八": 8, "选九": 9, "选十": 10}
# 提取 play_type 的前两个字，例如 "选四 (挑4个号码)" -> "选四"
play_key = play_type[:2]
num_count = play_map.get(play_key, 10)  # 默认选十

# 计算冷热号（用于冷热结合策略）
recent_df = df.tail(30)
recent_numbers = []
for _text in recent_df['numbers']:
    recent_numbers.extend(parse_numbers(_text))
hot_counter = Counter(recent_numbers)
hot_nums = [num for num, count in hot_counter.most_common(15)]

# 计算遗漏（冷号）
def calc_omission_k8(df):
    last_seen = {i: -1 for i in range(1, 81)}
    for idx, row in df.iterrows():
        for n in parse_numbers(row['numbers']):
            last_seen[n] = idx
    total = len(df)
    omission = {n: (total if pos == -1 else total - 1 - pos) for n, pos in last_seen.items()}
    return omission

omission_dict = calc_omission_k8(df)
cold_nums = sorted(omission_dict, key=omission_dict.get, reverse=True)[:15]

def make_one_pick():
    """生成一注号码（个数 = num_count）。"""
    if strategy == "冷热结合（推荐）":
        picks = set()
        # 2 个热号 + 2 个冷号，不够 num_count 时再随机补足
        picks.update(random.sample(hot_nums, min(2, len(hot_nums))))
        picks.update(random.sample(cold_nums, min(2, len(cold_nums))))
        while len(picks) < num_count:
            picks.add(random.randint(1, 80))
        return sorted(picks)
    # 纯随机
    return sorted(random.sample(range(1, 81), num_count))


# 生成号码：一次生成 batch_count 注，合起来算“本批”
if st.button("生成号码"):
    batch = []
    seen = set()
    for _ in range(batch_count):
        for _try in range(50):  # 同一批里不出现重复的一注
            final_picks = make_one_pick()
            num_str = " ".join(f"{n:02d}" for n in final_picks)
            if num_str not in seen:
                break
        seen.add(num_str)
        batch.append({
            "玩法": play_key,
            "号码": num_str,
            "选号个数": num_count,
            "策略": strategy,
        })

    st.session_state.last_batch = batch
    st.session_state.last_batch_info = {
        "play": play_key,
        "count": num_count,
        "strategy": strategy,
        "n": len(batch),
        "saved": False,
    }

# 展示本批号码，并提供一键复制与保存
_batch = st.session_state.get("last_batch") or []
_info = st.session_state.get("last_batch_info") or {}

if _batch:
    if len(_batch) == 1:
        st.success(f"本次生成的【{_info['play']}】号码如下：")
    else:
        st.success(f"本次生成 {len(_batch)} 注【{_info['play']}】号码：")

    st.dataframe(pd.DataFrame(_batch), use_container_width=True, hide_index=True)

    _numbers = "\n".join(row["号码"] for row in _batch)
    st.markdown("**👇 本批号码（点右上角复制，只有号码）**")
    st.code(_numbers, language=None)
    st.caption(
        f"选号个数：{_info['count']} | 策略：{_info['strategy']} | 共 {len(_batch)} 注"
    )

    if _info.get("saved"):
        st.caption("✅ 本批已保存到下方历史记录。")
    elif st.button("💾 保存到历史记录"):
        # 整批一起存，每注补一个序号
        for row in _batch:
            record = dict(row)
            record["序号"] = len(st.session_state.history_records) + 1
            st.session_state.history_records.append(record)
        st.session_state.last_batch_info["saved"] = True
        st.rerun()  # 刷新页面，让历史记录立刻显示出来

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
        st.markdown("**👇 全部历史号码（点右上角复制，只有号码）**")
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
                st.session_state.last_batch = []
                st.session_state.last_batch_info = {}
                st.rerun()

st.caption("⚠️ 本工具仅供个人学习与娱乐，不构成任何购彩建议，请理性购彩。")
