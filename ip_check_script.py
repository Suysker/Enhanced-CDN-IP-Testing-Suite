import subprocess
import ipaddress

def get_subnets_24(subnet):
    network = ipaddress.ip_network(subnet, strict=False)
    for subnet in network.subnets(new_prefix=24):
        yield subnet

def is_ip_reachable(ip):
    # 使用tcptraceroute命令来检查IP的可达性
    result = subprocess.run(["tcptraceroute", "-f", "255", "-m", "255", "-q", "1", str(ip)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return "Destination unreachable" not in result.stdout.decode()

if __name__ == '__main__':
    with open('ip.txt', 'r') as file:
        subnets = file.readlines()

    all_subnets_24 = []
    for subnet in subnets:
        subnet = subnet.strip()
        for new_subnet in get_subnets_24(subnet):
            all_subnets_24.append(new_subnet)

    reachable_ips = []
    for subnet in sorted(all_subnets_24):
        ip = ipaddress.ip_network(subnet, strict=False).network_address
        if is_ip_reachable(ip):
            reachable_ips.append(subnet)

    with open('reachable_ips.txt', 'w') as file:
        for ip in reachable_ips:
            file.write(str(ip) + '\n')

    print("Done!")
