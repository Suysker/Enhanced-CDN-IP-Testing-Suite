import subprocess
import ipaddress
from concurrent.futures import ThreadPoolExecutor, as_completed

urlprefix = ".ip"

def get_subnets_52(subnet):
    """Convert a subnet to multiple /52 subnets."""
    network = ipaddress.ip_network(subnet, strict=False)
    return list(network.subnets(new_prefix=52))

def is_ip_reachable(ip):
    try:
        result = subprocess.run(["curl", "--interface", "wgcf", "-o", "/dev/null", "-s", "-w", "%{http_code}", "--retry", "2", f"http://[{ip}]/cdn-cgi/trace"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3)
        return result.stdout.decode().strip() == "200"
    except subprocess.TimeoutExpired:
        return False

def first_reachable_ip_in_subnet(subnet):
    ip = ipaddress.ip_address(subnet.network_address)
    return ip if is_ip_reachable(ip) else None

def generate_domain(ip_address):
    address_str = str(ip_address)
    # 检测双冒号并进行处理
    if "::" in address_str:
        address_str = address_str.replace("::", ":")
        parts = address_str.rstrip(":").split(":")
    else:
        parts = address_str.split(":")
    # 过滤掉空字符串
    return '-'.join(parts) + urlprefix

if __name__ == '__main__':
    with open('Cloudflare/ipv6.txt', 'r') as file:
        base_subnets = file.readlines()

    all_subnets_52 = []
    for subnet in base_subnets:
        subnet = subnet.strip()
        all_subnets_52.extend(get_subnets_52(subnet))

    reachable_ips = []
    total = len(all_subnets_52)
    completed = 0

    with ThreadPoolExecutor(max_workers=1024) as executor:
        future_to_subnet = {executor.submit(first_reachable_ip_in_subnet, subnet): subnet for subnet in sorted(all_subnets_52)}
        for future in as_completed(future_to_subnet):
            completed += 1
            subnet = future_to_subnet[future]
            result = future.result()
            if result:
                reachable_ips.append(result)
            print(f"Progress: {completed}/{total} subnets checked")

    # Save all subnets /52
    with open('ipv6_whole_ips.txt', 'w') as file:
        for subnet in all_subnets_52:
            file.write(str(subnet.network_address) + '\n')

    with open('Cloudflare/ipv6_bind_config.txt', 'w') as file:
        for ip in all_subnets_52:
            domain = generate_domain(ip.network_address)
            file.write(f"{domain}. 1 IN AAAA {ip.network_address}\n")

    # Sort reachable IPs
    reachable_ips = sorted(reachable_ips)

    # Save selected IPs
    with open('Cloudflare/ipv6_reachable_ips.txt', 'w') as file:
        for ip in reachable_ips:
            file.write(str(ip) + '\n')

    selected_ips = []
    while reachable_ips:
        first_ip = reachable_ips.pop(0)
        selected_ips.append(first_ip)
        subnet_48 = ipaddress.ip_network(first_ip).supernet(new_prefix=48)
        reachable_ips = [ip for ip in reachable_ips if not ipaddress.ip_network(ip).subnet_of(subnet_48)]

    with open('Cloudflare/ipv6_simple_reachable_ips.txt', 'w') as file:
        for ip in selected_ips:
            file.write(str(ip) + '\n')

    print("Done!")
