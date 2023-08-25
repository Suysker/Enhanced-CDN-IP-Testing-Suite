import subprocess
import ipaddress
from concurrent.futures import ThreadPoolExecutor, as_completed

urlprefix = ".ip"

def is_ip_reachable(ip):
    try:
        result = subprocess.run(["curl", "-I", "-s",  f"http://{ip}/"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=2)
        response = result.stdout.decode('utf-8')
        if "CloudFront" in response:
            geo_code = response.split('X-Amz-Cf-Pop: ')[1][:3]
            return ip, geo_code
        else:
            return None, None
    except subprocess.TimeoutExpired:
        return None, None

def first_reachable_ip_in_subnet(subnet):
    ip = ipaddress.ip_address(subnet.network_address)
    return is_ip_reachable(ip)

def generate_domain(ip_address):
    parts = str(ip_address).split(".")
    return "-".join(parts) + urlprefix

if __name__ == '__main__':
    with open('CloudFront/ip.txt', 'r') as file:
        ips = [ipaddress.ip_network(ip.strip()) for ip in file.readlines()]

    all_subnets_22 = [] # Store all /22 subnets

    for ip in ips:
        # Expand all networks to /22
        if ip.prefixlen < 22:
            all_subnets_22 += list(ip.subnets(new_prefix=22))
        elif ip.prefixlen == 22:
            all_subnets_22.append(ip)
        else: # ip.prefixlen > 22
            base_ip = ip.network_address
            all_subnets_22.append(ipaddress.ip_network(f"{base_ip}/22", strict=False))

    reachable_ips = []
    geo_reachable_ips = []
    simple_reachable_ips = []
    geo_simple_reachable_ips = []

    total = len(all_subnets_22)
    completed = 0

    with ThreadPoolExecutor(max_workers=1024) as executor:
        future_to_subnet = {executor.submit(first_reachable_ip_in_subnet, subnet): subnet for subnet in sorted(all_subnets_22)}
        for future in as_completed(future_to_subnet):
            completed += 1
            subnet = future_to_subnet[future]
            result, geo_code = future.result()
            if result:
                reachable_ips.append(result)
                if geo_code:
                    geo_reachable_ips.append((result, geo_code))
            print(f"Progress: {completed}/{total} subnets checked")

    # Other logic to save subnets, domains, and reachable IPs

    # Save reachable IPs
    with open('CloudFront/reachable_ips.txt', 'w') as file:
        for ip in reachable_ips:
            file.write(str(ip) + '\n')

    # Save geo information for reachable IPs
    with open('CloudFront/geo_reachable_ips.txt', 'w') as file:
        for ip, geo_code in geo_reachable_ips:
            file.write(str(ip) + ' ' + geo_code + '\n')

    # Save simple reachable IPs
    with open('CloudFront/simple_reachable_ips.txt', 'w') as file:
        for ip in simple_reachable_ips:
            file.write(str(ip) + '\n')

    # Save geo information for simple reachable IPs
    with open('CloudFront/geo_simple_reachable_ips.txt', 'w') as file:
        for ip, geo_code in geo_simple_reachable_ips:
            file.write(str(ip) + ' ' + geo_code + '\n')

    print("Done!")
