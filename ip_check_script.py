import subprocess
import ipaddress
from concurrent.futures import ThreadPoolExecutor, as_completed

urlprefix = ".ip.suyskser.top"

def get_subnets_24(subnet):
    """Convert a subnet to multiple /24 subnets."""
    network = ipaddress.ip_network(subnet, strict=False)
    return list(network.subnets(new_prefix=24))

def get_colo_if_reachable(ip):
    try:
        result = subprocess.run(["curl", "-s", f"http://{ip}/cdn-cgi/trace"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=2)
        response = result.stdout.decode().strip()
        
        if "200" in response:  # 基于HTTP 200状态码检查IP是否可访问
            for line in response.split("\n"):
                if line.startswith("colo="):
                    return ip, line.split("=")[1]
        return None, None
    except subprocess.TimeoutExpired:
        return None, None

def first_reachable_ip_in_subnet(subnet):
    consecutive_failures = 0
    for i in range(0, 256, 25):
        ip = ipaddress.ip_address(f"{subnet.network_address + i}")
        ip_result, colo = get_colo_if_reachable(ip)
        if ip_result:
            return ip_result, colo
        else:
            consecutive_failures += 1
            if consecutive_failures >= 10:
                break
    return None, None

def generate_domain(ip_address):
    parts = str(ip_address).split(".")
    parts[-1] = "0"  # 把最后一个部分替换为 "0"
    return "-".join(parts) + urlprefix

if __name__ == '__main__':
    with open('ip.txt', 'r') as file:
        subnets = file.readlines()

    all_subnets_24 = []
    for subnet in subnets:
        subnet = subnet.strip()
        for new_subnet in get_subnets_24(subnet):
            all_subnets_24.append(new_subnet)

    reachable_ips_colos = {}
    total = len(all_subnets_24)
    completed = 0

    with ThreadPoolExecutor(max_workers=256) as executor:
        future_to_subnet = {executor.submit(first_reachable_ip_in_subnet, subnet): subnet for subnet in sorted(all_subnets_24)}
        for future in as_completed(future_to_subnet):
            completed += 1
            subnet = future_to_subnet[future]
            ip, colo = future.result()
            if ip:
                reachable_ips_colos[ip] = colo
            print(f"Progress: {completed}/{total} subnets checked")

    # Save reachable IPs
    with open('reachable_ips.txt', 'w') as file:
        for ip, colo in reachable_ips_colos.items():
            file.write(f"{ip} - {colo}\n")
    
    # Save corresponding domain names with IPs
    with open('bind_config.txt', 'w') as file:
        for ip in reachable_ips_colos.keys():
            domain = generate_domain(ip)
            file.write(f"{domain}. 1 IN A {ip}\n")

    print("Done!")
