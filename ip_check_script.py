import subprocess
import ipaddress
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

def get_subnets_24(subnet):
    """Convert a subnet to multiple /24 subnets."""
    network = ipaddress.ip_network(subnet, strict=False)
    return list(network.subnets(new_prefix=24))

def is_ip_reachable(ip):
    result = subprocess.run(["ping", "-c", "1", "-W", "1", str(ip)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return result.returncode == 0

def first_reachable_ip_in_subnet(subnet):
    for ip in ipaddress.ip_network(subnet, strict=False).hosts():
        if is_ip_reachable(ip):
            return ip
    return None

counter = 0
counter_lock = threading.Lock()

def worker_function(subnet):
    global counter
    result = first_reachable_ip_in_subnet(subnet)
    with counter_lock:
        counter += 1
        print(f"Progress: {counter}/{total} subnets checked")
    return result

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

    with ThreadPoolExecutor(max_workers=50) as executor:
        results = list(executor.map(worker_function, sorted(all_subnets_24)))

    for ip in results:
        if ip:
            reachable_ips.append(ip)

    with open('reachable_ips.txt', 'w') as file:
        for ip in reachable_ips:
            file.write(str(ip) + '\n')

    print("Done!")
