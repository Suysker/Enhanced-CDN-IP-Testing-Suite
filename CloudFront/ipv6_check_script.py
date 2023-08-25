import subprocess
import ipaddress
from concurrent.futures import ThreadPoolExecutor, as_completed

urlprefix = ".ip"

def is_ip_reachable(ip):
    try:
        result = subprocess.run(["curl", "-I", "-s", f"http://[{ip}]/"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=2)
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
    parts = str(ip_address).split(":")
    return "-".join(parts) + urlprefix

if __name__ == '__main__':
    with open('CloudFront/ipv6.txt', 'r') as file:
        ips = [ipaddress.ip_network(ip.strip()) for ip in file.readlines()]

    all_subnets_48 = []

    for ip in ips:
        if ip.prefixlen < 48:
            all_subnets_48 += list(ip.subnets(new_prefix=48))
        elif ip.prefixlen == 48:
            all_subnets_48.append(ip)
        else: # ip.prefixlen > 48
            base_ip = ip.network_address
            all_subnets_48.append(ipaddress.ip_network(f"{base_ip}/48", strict=False))
    
    reachable_ips = []
    geo_reachable_ips = []

    total = len(all_subnets_48)
    completed = 0

    with ThreadPoolExecutor(max_workers=1024) as executor:
        future_to_subnet = {executor.submit(first_reachable_ip_in_subnet, subnet): subnet for subnet in sorted(all_subnets_48)}
        for future in as_completed(future_to_subnet):
            completed += 1
            subnet = future_to_subnet[future]
            result, geo_code = future.result()
            if result:
                reachable_ips.append(result)
                if geo_code:
                    geo_reachable_ips.append((result, geo_code))
            print(f"Progress: {completed}/{total} subnets checked")

    # Save all subnets /48
    with open('CloudFront/ipv6_whole_ips.txt', 'w') as file:
        for subnet in all_subnets_48:
            file.write(str(subnet.network_address) + '\n')
    
    with open('CloudFront/ipv6_bind_config.txt', 'w') as file:
        for ip in all_subnets_48:
            domain = generate_domain(ip.network_address)
            file.write(f"{domain}. 1 IN AAAA {ip.network_address}\n")

      # Sort reachable IPs
    reachable_ips = sorted(reachable_ips)

    # Save selected IPs
    with open('CloudFront/ipv6_reachable_ips.txt', 'w') as file:
        for ip in reachable_ips:
            file.write(str(ip) + '\n')

    selected_ips = []
    while reachable_ips:
        first_ip = reachable_ips.pop(0)
        selected_ips.append(first_ip)
        subnet_44 = ipaddress.ip_network(first_ip).supernet(new_prefix=44)
        reachable_ips = [ip for ip in reachable_ips if not ipaddress.ip_network(ip).subnet_of(subnet_44)]

    simple_reachable_ips = selected_ips

    with open('CloudFront/ipv6_simple_reachable_ips.txt', 'w') as file:
        for ip in simple_reachable_ips:
            file.write(str(ip) + '\n')

    # Get geo information for simple reachable IPs
    geo_simple_reachable_ips = [item for item in geo_reachable_ips if item[0] in simple_reachable_ips]

    with open('CloudFront/ipv6_geo_simple_reachable_ips.txt', 'w') as file:
        for ip, geo_code in geo_simple_reachable_ips:
            file.write(str(ip) + ' ' + geo_code + '\n')

    print("Done!")
