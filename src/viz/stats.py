"""Amostrador de CPU/RAM do processo — usado pelo painel da janela do cérebro."""
import os
import time
from collections import deque
import psutil
from src import config

HISTORY_SECONDS = 45  # janela do gráfico (curta = mais precisa)


class StatsSampler:
    def __init__(self):
        self.proc = psutil.Process(os.getpid())
        self.proc.cpu_percent(interval=None)  # primeira leitura calibra
        self.cpu_count = psutil.cpu_count() or 1

        self.interval = config.STATS_SAMPLE_INTERVAL
        capacity = max(2, int(HISTORY_SECONDS / self.interval) + 1)
        self.cpu_hist: deque[float] = deque(maxlen=capacity)
        self.ram_hist: deque[float] = deque(maxlen=capacity)
        self.last_sample = 0.0
        self.last_cpu = 0.0
        self.last_ram_mb = 0.0
        self.last_ram_pct = 0.0

    def sample(self):
        now = time.time()
        if now - self.last_sample < self.interval:
            return
        self.last_sample = now
        cpu = self.proc.cpu_percent(interval=None) / self.cpu_count
        mem = self.proc.memory_info().rss
        sys_mem = psutil.virtual_memory().total
        self.last_cpu = cpu
        self.last_ram_mb = mem / (1024 * 1024)
        self.last_ram_pct = (mem / sys_mem) * 100 if sys_mem else 0.0
        self.cpu_hist.append(cpu)
        self.ram_hist.append(self.last_ram_pct)
