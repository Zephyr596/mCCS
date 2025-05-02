import os
import re
import matplotlib.pyplot as plt

BASE_DIR = './'
WITH_QOS = 'setup5-real-normal-1/setup5-real-qosv2'
WITHOUT_QOS = 'setup5-real-woEnforce-1/setup5-real-qosv2'

# 提取 mean time
def extract_mean_time(file_path):
    pattern = re.compile(r'\(mean, median, min, max\) = \(([\d.]+)ms,')
    with open(file_path, 'r') as f:
        for line in f:
            match = pattern.search(line)
            if match:
                return float(match.group(1))
    return None

# 归一化函数
def normalize(times):
    max_val = max(times)
    return [t / max_val for t in times]

def main():
    # 获取日志路径
    with_gpt1 = os.path.join(BASE_DIR, WITH_QOS, 'traffic_gen_host1.stdout')
    with_gpt2 = os.path.join(BASE_DIR, WITH_QOS, 'traffic_gen_host3.stdout')
    without_gpt1 = os.path.join(BASE_DIR, WITHOUT_QOS, 'traffic_gen_host1.stdout')
    without_gpt2 = os.path.join(BASE_DIR, WITHOUT_QOS, 'traffic_gen_host3.stdout')

    # 提取 mean time
    with_means = [extract_mean_time(with_gpt1), extract_mean_time(with_gpt2)]
    without_means = [extract_mean_time(without_gpt1), extract_mean_time(without_gpt2)]

    # 分别归一化
    with_norm = normalize(with_means)
    without_norm = normalize(without_means)

    # 设置绘图参数
    labels = ['With QoS', 'Without QoS']
    x = [0, 1]  # 每组的中心点
    width = 0.35

    fig, ax = plt.subplots(figsize=(8, 6))

    # 画柱子：每组中 GPT1 在左，GPT2 在右
    ax.bar([i - width/2 for i in x], [with_norm[0], without_norm[0]], width, label='GPT1')
    ax.bar([i + width/2 for i in x], [with_norm[1], without_norm[1]], width, label='GPT2')

    # 标注和装饰
    ax.set_ylabel('AllReduce Execution Mean Time')
    ax.set_title('QoS Impact on GPT AllReduce Mean Time')
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.legend()
    ax.grid(True, axis='y', linestyle='--', alpha=0.6)

    # 标注数值（原始 mean time）
    for i in range(len(x)):
        # 标注柱子数值（上面显示原始 mean）
        # Group 1: With QoS
        ax.text(x[0] - width/2, with_norm[0] + 0.01, f"{with_means[0]:.1f}ms", ha='center', fontsize=9)
        ax.text(x[0] + width/2, with_norm[1] + 0.01, f"{with_means[1]:.1f}ms", ha='center', fontsize=9)

        # Group 2: Without QoS
        ax.text(x[1] - width/2, without_norm[0] + 0.01, f"{without_means[0]:.1f}ms", ha='center', fontsize=9)
        ax.text(x[1] + width/2, without_norm[1] + 0.01, f"{without_means[1]:.1f}ms", ha='center', fontsize=9)


    plt.tight_layout()
    plt.savefig('qos_mean_comparison_by_group.png', dpi=300)
    plt.show()

if __name__ == '__main__':
    main()
