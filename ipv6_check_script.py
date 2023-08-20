import subprocess
import ipaddress
from concurrent.futures import ThreadPoolExecutor, as_completed

urlprefix = ".ip"

def get_subnets_56(subnet):
    """Convert a subnet to multiple /56 subnets."""
    network = ipaddress.ip_network(subnet, strict=False)
    return list(network.subnets(new_prefix=56))

def is_ip_reachable(ip):
    try:
        result = subprocess.run(["curl", "-o", "/dev/null", "-s", "-w", "%{http_code}", f"http://[{ip}]/cdn-cgi/trace"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=2)
        return result.stdout.decode().strip() == "200"
    except subprocess.TimeoutExpired:
        return False

def first_reachable_ip_in_subnet(subnet):
    ip = ipaddress.ip_address(subnet.network_address)
    return ip if is_ip_reachable(ip) else None

def generate_domain(ip_address):
    parts = str(ip_address).split(":")
    return '-'.join(parts[::-1]) + urlprefix

def hierarchical_query(subnet):
    base_subnet = ipaddress.ip_network(subnet, strict=False)
    current_prefix = base_subnet.prefixlen

    subnets_to_check = [base_subnet]
    while current_prefix < 56:
        current_prefix += 8
        new_subnets = []
        for s in subnets_to_check:
            new_subnets.extend(list(s.subnets(new_prefix=current_prefix)))

        print(f"Checking subnet: {new_subnets[0]}")  # Add this line for debugging

        if is_ip_reachable(new_subnets[0].network_address):
            print(f"Subnet {new_subnets[0]} is reachable")  # Add this line for debugging
            if current_prefix == 56:
                return new_subnets
            subnets_to_check = new_subnets
        else:
            print(f"Subnet {new_subnets[0]} is NOT reachable, stopping search")  # Add this line for debugging
            return []
    return []


if __name__ == '__main__':
    with open('ipv6.txt', 'r') as file:
        base_subnets = file.readlines()

    all_subnets_56 = []
    for subnet in base_subnets:
        subnet = subnet.strip()
        all_subnets_56.extend(hierarchical_query(subnet))

    reachable_ips = []
    total = len(all_subnets_56)
    completed = 0

    with ThreadPoolExecutor(max_workers=256) as executor:
        future_to_subnet = {executor.submit(first_reachable_ip_in_subnet, subnet): subnet for subnet in sorted(all_subnets_56)}
        for future in as_completed(future_to_subnet):
            completed += 1
            subnet = future_to_subnet[future]
            result = future.result()
            if result:
                reachable_ips.append(result)
            print(f"Progress: {completed}/{total} subnets checked")

    # Save all subnets /56
    with open('ipv6_whole_ips.txt', 'w') as file:
        for subnet in all_subnets_56:
            file.write(str(subnet.network_address) + '\n')

    with open('ipv6_bind_config.txt', 'w') as file:
        for ip in all_subnets_56:
            domain = generate_domain(ip.network_address)
            file.write(f"{domain}. 1 IN AAAA {ip.network_address}\n")

    # Sort reachable IPs
    reachable_ips = sorted(reachable_ips)

    # Save selected IPs
    with open('ipv6_reachable_ips.txt', 'w') as file:
        for ip in reachable_ips:
            file.write(str(ip) + '\n')

    selected_ips = []
    while reachable_ips:
        first_ip = reachable_ips.pop(0)
        selected_ips.append(first_ip)
        subnet_52 = ipaddress.ip_network(first_ip).supernet(new_prefix=52)
        reachable_ips = [ip for ip in reachable_ips if not ipaddress.ip_network(ip).subnet_of(subnet_52)]

    with open('ipv6_simple_reachable_ips.txt', 'w') as file:
        for ip in selected_ips:
            file.write(str(ip) + '\n')

    print("Done!")
