import subprocess
import ipaddress
from concurrent.futures import ThreadPoolExecutor, as_completed

urlprefix = ".ip"

def get_subnets_48(subnet):
    """Convert a subnet to multiple /48 subnets."""
    network = ipaddress.ip_network(subnet, strict=False)
    return list(network.subnets(new_prefix=48))

def is_ip_reachable(ip):
    try:
        result = subprocess.run(["curl", "--interface", "wgcf", "-o", "/dev/null", "-s", "-w", "%{http_code}", f"http://[{ip}]/cdn-cgi/trace"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=2)
        return result.stdout.decode().strip() == "200"
    except subprocess.TimeoutExpired:
        return False

def first_reachable_ip_in_subnet(subnet):
    ip = ipaddress.ip_address(subnet.network_address)
    return ip if is_ip_reachable(ip) else None

def generate_domain(ip_address):
    parts = str(ip_address).split(":")
    return '-'.join(parts) + urlprefix


if __name__ == '__main__':
    with open('ipv6_.txt', 'r') as file:
        base_subnets = file.readlines()

    all_subnets_48 = []
    for subnet in base_subnets:
        subnet = subnet.strip()
        all_subnets_48.extend(get_subnets_48(subnet))

    reachable_ips = []
    total = len(all_subnets_48)
    completed = 0

    with ThreadPoolExecutor(max_workers=2048) as executor:
        future_to_subnet = {executor.submit(first_reachable_ip_in_subnet, subnet): subnet for subnet in sorted(all_subnets_48)}
        for future in as_completed(future_to_subnet):
            completed += 1
            subnet = future_to_subnet[future]
            result = future.result()
            if result:
                reachable_ips.append(result)
            print(f"Progress: {completed}/{total} subnets checked")

    # Sort reachable IPs
    reachable_ips = sorted(reachable_ips)

    # Save selected IPs
    with open('ipv6.txt', 'w') as file:
        for ip in reachable_ips:
            file.write(str(ip) + '/48' + '\n')

    print("Done!")
