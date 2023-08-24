import ipaddress
from concurrent.futures import ThreadPoolExecutor
import subprocess

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
    with open('/Gcore/ip.txt', 'r') as file:
        ips = [ipaddress.ip_network(ip.strip()) for ip in file.readlines()]

    # 合并 /32 到 /24 网段
    subnets_24 = ipaddress.collapse_addresses(ips)
    whole_ips = [subnet for subnet in subnets_24 if subnet.prefixlen == 24]

    # 生成 whole_ips.txt 和 bind_config.txt 文件
    with open('whole_ips.txt', 'w') as file_whole_ips, open('bind_config.txt', 'w') as file_bind_config:
        for subnet in whole_ips:
            file_whole_ips.write(str(subnet.network_address) + '\n')
            domain = generate_domain(subnet.network_address)
            file_bind_config.write(f"{domain}. 1 IN A {subnet.network_address}\n")

    # 测试每个 /24 网段的可用性
    reachable_ips = []
    with ThreadPoolExecutor(max_workers=256) as executor:
        futures = [executor.submit(is_ip_reachable, str(ip)) for subnet in whole_ips for ip in subnet.hosts()]
        for i, future in enumerate(futures):
            if future.result():
                reachable_ips.append(str(whole_ips[i//256].network_address))

    # 生成 reachable_ips.txt 和 simple_reachable_ips.txt 文件
    with open('reachable_ips.txt', 'w') as file_reachable_ips, open('simple_reachable_ips.txt', 'w') as file_simple_reachable_ips:
        for ip in reachable_ips:
            file_reachable_ips.write(ip + '\n')
            file_simple_reachable_ips.write(ip.split('.')[0] + '.' + ip.split('.')[1] + '.' + ip.split('.')[2] + '.1/32\n')

    print("Done!")
