import subprocess
import ipaddress
from concurrent.futures import ThreadPoolExecutor, as_completed

def get_subnets_24(subnet):
    """Convert a subnet to multiple /24 subnets."""
    network = ipaddress.ip_network(subnet, strict=False)
    return list(network.subnets(new_prefix=24))

def is_ip_reachable(ip):
    try:
        result = subprocess.run(["curl", "-o", "/dev/null", "-s", "-w", "%{http_code}", f"http://{ip}/cdn-cgi/trace"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=2)
        return result.stdout.decode().strip() == "200"
    except subprocess.TimeoutExpired:
        return False

def first_reachable_ip_in_subnet(subnet):
    consecutive_failures = 0
    for i in range(0, 256, 25):
        ip = ipaddress.ip_address(f"{subnet.network_address + i}")
        if is_ip_reachable(ip):
            return ip
        else:
            consecutive_failures += 1
            if consecutive_failures >= 10:
                break
    return None

def generate_domain(ip_address):
    parts = str(ip_address).split(".")
    parts[-1] = "0"  # 把最后一个部分替换为 "0"
    return "-".join(parts) + ".ip.hangover.tk"

if __name__ == '__main__':
    with open('ip.txt', 'r') as file:
        subnets = file.readlines()

    all_subnets_24 = []
    for subnet in subnets:
        subnet = subnet.strip()
        for new_subnet in get_subnets_24(subnet):
            all_subnets_24.append(new_subnet)

    reachable_ips = []
    total = len(all_subnets_24)
    completed = 0

    with ThreadPoolExecutor(max_workers=256) as executor:
        future_to_subnet = {executor.submit(first_reachable_ip_in_subnet, subnet): subnet for subnet in sorted(all_subnets_24)}
        for future in as_completed(future_to_subnet):
            completed += 1
            subnet = future_to_subnet[future]
            result = future.result()
            if result:
                reachable_ips.append(result)
            print(f"Progress: {completed}/{total} subnets checked")

    # Save reachable IPs
    with open('reachable_ips.txt', 'w') as file:
        for ip in reachable_ips:
            file.write(str(ip) + '\n')
    
    # Save corresponding domain names with IPs
    with open('bind_config.txt', 'w') as file:
        for ip in reachable_ips:
            domain = generate_domain(ip)
            file.write(f"{domain}. 1 IN A {ip}\n")

    print("Done!")
