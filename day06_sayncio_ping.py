#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 06：异步高并发 Ping 扫描器（生产级）
1、日志配置（工程级）
2、配置分离 yaml
3、异步：
  3.1、定义异步函数：async def async_ping(ip, timeout=3)
  3.2、异常处理：try except
  3.3、 创建异步进程 proc = await asyncio.create_subprocess_exec（）
  3.4、列表推导式：tasks = [async_ping(ip, timeout) for ip in ips]
  3.5 、并发执行，逐个处理 for coro in asyncio.as_completed(tasks):

异步核心概念：
async     → 声明异步函数（协程函数）
await     → 等待异步操作完成
asyncio.run()     → 启动事件循环
asyncio.gather()  → 并发执行多个任务



async def main():
    tasks = [async_ping(ip) for ip in ips]  # ← 这里只是创建任务对象
    results = await asyncio.gather(*tasks)  # ← 这里才开始并发执行
"""

import asyncio
import csv
import logging
import os
import yaml
from datetime import datetime
from pathlib import Path

# =========================
# 日志配置（工程级）
# =========================
def setup_logging():
    """初始化日志系统"""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(f"{log_dir}/scan.log", encoding="utf-8"),
            logging.StreamHandler()
        ]
    )

# =========================
# 配置加载
# =========================
def load_config(path="config.yaml"):
    """加载 YAML 配置"""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

# =========================
# 异步 Ping 核心
# =========================
async def async_ping(ip, timeout=3):
    """
    异步 Ping 单个 IP
    返回: (ip, alive, rtt)
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            "ping",
            "-c", "1",
            "-W", str(timeout),
            ip,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, _ = await proc.communicate()

        if proc.returncode == 0:
            # 提取 RTT
            import re
            m = re.search(r"time=(\d+\.?\d*)\s*ms", stdout.decode())
            rtt = m.group(1) + "ms" if m else "0ms"
            return ip, True, rtt
        else:
            return ip, False, "0ms"

    except asyncio.TimeoutError:
        logging.warning(f"{ip} 超时")
        return ip, False, "timeout"
    except Exception as e:
        logging.error(f"{ip} 异常: {e}")
        return ip, False, "error"

# =========================
# 主函数（流式写入）
# =========================
async def main():
    setup_logging()
    config = load_config()

    ips = config["targets"]
    timeout = config["scan"]["timeout"]
    output_dir = config["scan"]["output_dir"]

    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"{output_dir}/scan_{timestamp}.csv"

    logging.info(f"开始扫描，共 {len(ips)} 个目标")

    # 流式写入 CSV
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["IP", "状态", "RTT", "时间"])

        # 创建所有任务
        tasks = [async_ping(ip, timeout) for ip in ips]

        # 并发执行，逐个处理
        for coro in asyncio.as_completed(tasks):
            ip, alive, rtt = await coro
            status = "✅ 存活" if alive else "❌ 失联"
            now = datetime.now().strftime("%H:%M:%S")

            writer.writerow([ip, status, rtt, now])
            logging.info(f"{ip} {status} ({rtt})")

    logging.info(f"扫描完成，结果已保存: {output_file}")

# =========================
# 入口
# =========================
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.warning("用户中断扫描")
    except Exception as e:
        logging.critical(f"程序崩溃: {e}", exc_info=True)
