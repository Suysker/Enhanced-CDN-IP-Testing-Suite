import subprocess
import ipaddress
from concurrent.futures import ThreadPoolExecutor, as_completed

urlprefix = ".ip"

def get_subnets_24(subnet):
    """Convert a subnet to multiple /24 subnets."""
    network = ipaddress.ip_network(subnet, strict=False)
    return list(network.subnets(new_prefix=24))

def is_ip_reachable(ip):
    try:
        result = subprocess.run(["curl", "-o", "/dev/null", "-s", "-w", "%{http_code}", f"http://{ip}/"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=2)
        return result.stdout.decode().strip() == "403"
    except subprocess.TimeoutExpired:
        return False

def first_reachable_ip_in_subnet(subnet):
    ip = ipaddress.ip_address(subnet.network_address)
    return ip if is_ip_reachable(ip) else None

def generate_domain(ip_address):
    parts = str(ip_address).split(".")
    return "-".join(parts) + urlprefix

if __name__ == '__main__':
    with open('CloudFront/ip.txt', 'r') as file:
        ips = [ipaddress.ip_network(ip.strip()) for ip in file.readlines()]

    all_subnets_24 = [] # 存储所有/24网段

    for ip in ips:
        # 将所有网段扩展为/24
        if ip.prefixlen < 24:
            all_subnets_24 += list(ip.subnets(new_prefix=24))
        elif ip.prefixlen == 24:
            all_subnets_24.append(ip)
        else: # ip.prefixlen > 24
            base_ip = ip.network_address
            all_subnets_24.append(ipaddress.ip_network(f"{base_ip}/24", strict=False))

    reachable_ips = []
    total = len(all_subnets_24)
    completed = 0

    with ThreadPoolExecutor(max_workers=1024) as executor:
        future_to_subnet = {executor.submit(first_reachable_ip_in_subnet, subnet): subnet for subnet in sorted(all_subnets_24)}
        for future in as_completed(future_to_subnet):
            completed += 1
            subnet = future_to_subnet[future]
            result = future.result()
            if result:
                reachable_ips.append(result)
            print(f"Progress: {completed}/{total} subnets checked")

    # Save all subnets /24
    with open('CloudFront/whole_ips.txt', 'w') as file:
        for subnet in all_subnets_24:
            file.write(str(subnet.network_address) + '\n')

    with open('CloudFront/bind_config.txt', 'w') as file:
        for ip in all_subnets_24:
            domain = generate_domain(ip.network_address)
            file.write(f"{domain}. 1 IN A {ip.network_address}\n")

    # Sort reachable IPs
    reachable_ips = sorted(reachable_ips)

    # Save selected IPs
    with open('CloudFront/reachable_ips.txt', 'w') as file:
        for ip in reachable_ips:
            file.write(str(ip) + '\n')

    selected_ips = []
    while reachable_ips:
        first_ip = reachable_ips.pop(0)
        selected_ips.append(first_ip)
        subnet_20 = ipaddress.ip_network(first_ip).supernet(new_prefix=20)
        reachable_ips = [ip for ip in reachable_ips if not ipaddress.ip_network(ip).subnet_of(subnet_20)]

    with open('CloudFront/simple_reachable_ips.txt', 'w') as file:
        for ip in selected_ips:
            file.write(str(ip) + '\n')

    print("Done!")
