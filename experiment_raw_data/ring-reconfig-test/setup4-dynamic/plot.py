import re
import matplotlib.pyplot as plt
import numpy as np

# 日志文件路径
log_path = 'traffic_gen_host1.stdout'

iterations = []
times = []


with open(log_path, 'r') as file:
    for line in file:
        match = re.search(r'Iter (\d+) time: ([\d.]+) ms', line)
        if match:
            iter_num = int(match.group(1))
            time_ms = float(match.group(2))
            if iter_num < 350:
                iterations.append(iter_num)
                times.append(time_ms)

# 转为 NumPy 数组
iterations = np.array(iterations)
times = np.array(times)

# 去除离群值（IQR 方法）
Q1 = np.percentile(times, 25)
Q3 = np.percentile(times, 75)
IQR = Q3 - Q1
lower = Q1 - 1.5 * IQR
upper = Q3 + 1.5 * IQR
mask = (times >= lower) & (times <= upper)
iterations = iterations[mask]
times = times[mask]

# 滑动平均
window_size = 21  # 你可以调整这个窗口大小
smoothed_times = np.convolve(times, np.ones(window_size)/window_size, mode='valid')
smoothed_iters = iterations[:len(smoothed_times)]  # 对齐

# 绘图
plt.figure(figsize=(10, 6))
plt.plot(iterations, times, marker='o', linestyle='', alpha=0.4, label='Raw Data')
plt.plot(smoothed_iters, smoothed_times, color='red', linewidth=2, label=f'Smoothed (window={window_size})')
plt.title('GPT AllReduce Execution Time')
plt.xlabel('Iteration')
plt.ylabel('Time (ms)')
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.savefig('iter_time_smoothed.png', dpi=300)
