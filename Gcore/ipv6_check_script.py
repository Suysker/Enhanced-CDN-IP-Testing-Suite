import ipaddress
from collections import defaultdict

urlprefix = ".ip"

def generate_domain(ip_address):
    parts = str(ip_address).split(":")
    return "-".join(parts) + urlprefix

if __name__ == '__main__':
    with open('Gcore/ipv6.txt', 'r') as file:
        ipv6_addresses = [ip.strip().split('/')[0] for ip in file.readlines()] # 移除/128后缀

    # 生成 whole_ips.txt 和 bind_config.txt 文件
    with open('Gcore/ipv6_whole_ips.txt', 'w') as file_whole_ips, open('Gcore/ipv6_bind_config.txt', 'w') as file_bind_config:
        for ip in ipv6_addresses:
            file_whole_ips.write(ip + '\n')
            domain = generate_domain(ip)
            file_bind_config.write(f"{domain}. 1 IN AAAA {ip}\n")

    # 由于IPv6不需要进行可用性测试，直接复制 whole_ips.txt 至 reachable_ips.txt
    with open('Gcore/whole_ips.txt', 'r') as file_whole_ips, open('Gcore/ipv6_reachable_ips.txt', 'w') as file_reachable_ips:
        for line in file_whole_ips:
            file_reachable_ips.write(line)

    # 生成 simple_reachable_ips.txt 文件，包含每个/64段的第一个IP
    with open('Gcore/ipv6_reachable_ips.txt', 'r') as file_reachable_ips, open('Gcore/ipv6_simple_reachable_ips.txt', 'w') as file_simple_reachable_ips:
        recorded_subnets = set() # 用于记录已经处理过的/64网段

        for ip in file_reachable_ips:
            ip = ip.strip()
            subnet = ip.rsplit(':', 4)[0] # 获取IP地址的前几个数字，即/64网段
            if subnet not in recorded_subnets:
                recorded_subnets.add(subnet)
                file_simple_reachable_ips.write(ip + '\n') # 以/64格式写入该网段的第一个IP

    print("Done!")
