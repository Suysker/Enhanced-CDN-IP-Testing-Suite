import ipaddress
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed # 必须导入这个
import subprocess
from collections import defaultdict

def is_ip_reachable(ip):
    try:
        result = subprocess.run(["curl", "-o", "/dev/null", "-s", "-I", f"http://{ip}"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=2)
        return "Empty reply from server" in result.stderr.decode()
    except subprocess.TimeoutExpired:
        return False

def generate_domain(ip_address):
    parts = str(ip_address).split(".")
    return "-".join(parts) + ".ip"

if __name__ == '__main__':
    with open('Gcore/ip.txt', 'r') as file:
        ips = [ipaddress.ip_network(ip.strip()) for ip in file.readlines()]

    # 合并 /32 到 /24 网段
    subnets_24 = defaultdict(list)
    
    for ip in ips:
        network_address = ip.network_address
        parts = str(network_address).split('.')[:-1]
        network_24_address_str = '.'.join(parts) + '.0/24'
        network_24 = ipaddress.ip_network(network_24_address_str, strict=False)
        subnets_24[network_24].append(ip)

    whole_ips = []
    for subnet in subnets_24.keys():
        for host in subnet.hosts():
            whole_ips.append(str(host))

    # 生成 whole_ips.txt 和 bind_config.txt 文件
    with open('Gcore/whole_ips.txt', 'w') as file_whole_ips, open('Gcore/bind_config.txt', 'w') as file_bind_config:
        for ip in whole_ips:
            file_whole_ips.write(ip + '\n')
            domain = generate_domain(ip)
            file_bind_config.write(f"{domain}. 1 IN A {ip}\n")

    # 测试每个 /32 IP的可用性
    reachable_ips = []
    total = len(whole_ips)
    completed = 0
    with ThreadPoolExecutor(max_workers=256) as executor:
        future_to_ip = {executor.submit(is_ip_reachable, ip): ip for ip in whole_ips}
        for future in as_completed(future_to_ip):
            completed += 1
            ip = future_to_ip[future]
            result = future.result()
            if result:
                reachable_ips.append(ip)
            progress = (completed * 100) // total # 根据整体任务数量计算进度百分比
            print(f"Progress: {progress}% ({completed}/{total} IPs checked)")

    # 生成 reachable_ips.txt 和 simple_reachable_ips.txt 文件
    with open('Gcore/reachable_ips.txt', 'w') as file_reachable_ips, open('Gcore/simple_reachable_ips.txt', 'w') as file_simple_reachable_ips:
        for ip in reachable_ips:
            file_reachable_ips.write(ip + '\n')
            file_simple_reachable_ips.write(ip.split('.')[0] + '.' + ip.split('.')[1] + '.' + ip.split('.')[2] + '.1/32\n')

    print("Done!")
