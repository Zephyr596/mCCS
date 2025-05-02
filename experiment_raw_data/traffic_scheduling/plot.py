import os
import re
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter

BASE_DIR = './'
WITH_QOS = 'setup5-real-normal-1/setup5-real-qosv2'
WITHOUT_QOS = 'setup5-real-woEnforce-1/setup5-real-qosv2'

# 提取 iteration time 列表
def extract_iter_times(file_path):
    pattern = re.compile(r'Iter \d+ time: ([\d.]+) ms')
    times = []
    with open(file_path, 'r') as f:
        for line in f:
            match = pattern.search(line)
            if match:
                times.append(float(match.group(1)))
    return times

# 使用 Savitzky-Golay 滤波平滑
def smooth(data, window=301, poly=3):
    if len(data) < window:
        return data
    return savgol_filter(data, window_length=window, polyorder=poly)

def main():
    # 日志路径
    with_gpt1 = os.path.join(BASE_DIR, WITH_QOS, 'traffic_gen_host1.stdout')
    with_gpt2 = os.path.join(BASE_DIR, WITH_QOS, 'traffic_gen_host3.stdout')
    without_gpt1 = os.path.join(BASE_DIR, WITHOUT_QOS, 'traffic_gen_host1.stdout')
    without_gpt2 = os.path.join(BASE_DIR, WITHOUT_QOS, 'traffic_gen_host3.stdout')

    # 提取并平滑数据
    data_with = {
        'GPT1 (With QoS)': smooth(extract_iter_times(with_gpt1)),
        'GPT2 (With QoS)': smooth(extract_iter_times(with_gpt2)),
    }
    data_without = {
        'GPT1 (Without QoS)': smooth(extract_iter_times(without_gpt1)),
        'GPT2 (Without QoS)': smooth(extract_iter_times(without_gpt2)),
    }

    # 统一裁剪长度
    min_len = min(*(len(v) for v in list(data_with.values()) + list(data_without.values())))
    start_idx = 200
    x = list(range(start_idx, min_len))

    for k in data_with:
        data_with[k] = data_with[k][start_idx:min_len]
    for k in data_without:
        data_without[k] = data_without[k][start_idx:min_len]

    # 颜色样式设定
    color_map = {
        'GPT1': 'blue',
        'GPT2': 'orange'
    }

    # 开始绘图（两个子图）
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), sharey=True)

    # 子图 1：With QoS
    ax = axes[0]
    for label, y in data_with.items():
        gpt = 'GPT1' if 'GPT1' in label else 'GPT2'
        ax.plot(x, y, label=label, color=color_map[gpt], linestyle='-')
    ax.set_title('With QoS')
    ax.set_xlabel('Iteration')
    ax.set_ylabel('Time (ms)')
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.legend()

    # 子图 2：Without QoS
    ax = axes[1]
    for label, y in data_without.items():
        gpt = 'GPT1' if 'GPT1' in label else 'GPT2'
        ax.plot(x, y, label=label, color=color_map[gpt], linestyle='--')
    ax.set_title('Without QoS')
    ax.set_xlabel('Iteration')
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.legend()

    # 总体布局
    fig.suptitle('Smoothed AllReduce Iteration Time', fontsize=14)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig('qos_subplots_from_iter200.png', dpi=300)
    plt.show()

if __name__ == '__main__':
    main()
