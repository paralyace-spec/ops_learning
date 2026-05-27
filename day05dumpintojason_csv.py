# -*- coding: utf-8 -*-
# owner: paralyace-spec@gmail.com
#   date: 2023-04-05
#  desc: 正则表达式示例

## IP提取
#ips = re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", log_text)

#### 提取 nginx 日志中的 ip, method, url, status

# m = re.search(
#     r'^(\d+\.\d+\.\d+\.\d+) .*?"(\w+) (.+?) HTTP.*?" (\d{3})',
#     line
# )
# ip, method, url, status = m.groups()

#### 解析键值对 port = 8080  海象运算符 防崩
#if m := re.match(r"^(\w+)\s*=\s*(.+)$", line):
#    key, value = m.groups()


from concurrent.futures import ThreadPoolExecutor, as_completed
import subprocess
import csv
import json
import logging
from pathlib import Path
from datetime import datetime
from collections import Counter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def run_cmd(cmd):
    try:
        r = subprocess.run(cmd, shell=False, capture_output=True, text=True, timeout=5)
        return r.returncode == 0, r.stdout.strip()
    except Exception as e:
        return False, str(e)

def ping_host(ip):
    ok, msg = run_cmd(["ping", "-c", "1", "-W", "2", ip])
    rtt = "0ms"
    if ok:
        import re
        m = re.search(r"time=(\d+\.?\d*)\s*ms", msg)
        rtt = m.group(1) + "ms" if m else "0ms"
    return {"ip": ip, "alive": ok, "rtt": rtt}

def scan_and_save(ips, json_file, csv_file):
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["ip","alive","rtt","timestamp"])
        writer.writeheader()

        with ThreadPoolExecutor(max_workers=30) as executor:
            futures = [executor.submit(ping_host, ip) for ip in ips]
            for future in as_completed(futures):
                try:
                    row = future.result(timeout=5)
                    row["timestamp"] = datetime.now().isoformat()
                    writer.writerow(row)
                except Exception:
                    continue

    logging.info(f"CSV 已写入: {csv_file}")

    # JSON 可选（如果需要）
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        data = list(reader)

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    logging.info(f"JSON 已写入: {json_file}")

if __name__ == "__main__":
    ips = Path("hosts.txt").read_text().strip().splitlines()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    scan_and_save(ips, f"scan_{ts}.json"， f"scan_{ts}.csv")
