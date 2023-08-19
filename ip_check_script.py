import subprocess
import ipaddress
from concurrent.futures import ThreadPoolExecutor, as_completed

def is_ip_reachable(ip):
    result = subprocess.run(["tcptraceroute", "-f", "255", "-m", "255", "-q", "1", str(ip)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return "Destination unreachable" not in result.stdout.decode()

def first_reachable_ip_in_subnet(subnet):
    for ip in ipaddress.ip_network(subnet, strict=False).hosts():
        if is_ip_reachable(ip):
            return ip
    return None

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

    with ThreadPoolExecutor(max_workers=128) as executor:
        future_to_subnet = {executor.submit(first_reachable_ip_in_subnet, subnet): subnet for subnet in sorted(all_subnets_24)}
        for future in as_completed(future_to_subnet):
            completed += 1
            subnet = future_to_subnet[future]
            result = future.result()
            if result:
                reachable_ips.append(result)
            print(f"Progress: {completed}/{total} subnets checked")

    with open('reachable_ips.txt', 'w') as file:
        for ip in reachable_ips:
            file.write(str(ip) + '\n')

    print("Done!")
