import argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--towers", type=int, default=1)
parser.add_argument("--clients", type=int, default=1)
args = parser.parse_args()

if args.towers < 1:
    raise SystemExit("Need at least 1 tower")

if args.clients < 1:
    raise SystemExit("Need at least 1 client")

out = Path("generated")
out.mkdir(exist_ok=True)

lines = []

lines.append("services:")
lines.append("")
lines.append("  epc:")
lines.append("    build:")
lines.append("      context: ..")
lines.append("    container_name: lte-epc")
lines.append("    command: >")
lines.append("      srsepc")
lines.append("      /etc/srsran/epc.conf")
lines.append("      --mme.mme_bind_addr=10.10.10.10")
lines.append("      --spgw.gtpu_bind_addr=10.10.10.10")
lines.append("    privileged: true")
lines.append("    cap_add:")
lines.append("      - NET_ADMIN")
lines.append("      - SYS_NICE")
lines.append("    devices:")
lines.append("      - /dev/net/tun:/dev/net/tun")
lines.append("    networks:")
lines.append("      lte-net:")
lines.append("        ipv4_address: 10.10.10.10")
lines.append("")

clients_per_tower = (args.clients + args.towers - 1) // args.towers

client_number = 1

for tower_number in range(1, args.towers + 1):

    tower_ip = f"10.10.10.{20 + tower_number - 1}"

    # First version: each tower gets one ZMQ pair.
    tx_port = 2000 + ((tower_number - 1) * 100)
    rx_port = tx_port + 1

    tower_name = f"tower{tower_number}"
    client_name = f"client{client_number}"

    lines.append(f"  {tower_name}:")
    lines.append("    build:")
    lines.append("      context: ..")
    lines.append(f"    container_name: lte-{tower_name}")
    lines.append("    privileged: true")
    lines.append("    depends_on:")
    lines.append("      - epc")
    lines.append("    command: >")
    lines.append("      srsenb")
    lines.append("      /etc/srsran/enb.conf")
    lines.append("      --enb.mme_addr=10.10.10.10")
    lines.append(f"      --enb.gtp_bind_addr={tower_ip}")
    lines.append(f"      --enb.s1c_bind_addr={tower_ip}")
    lines.append("      --rf.device_name=zmq")
    lines.append(
        f"      --rf.device_args=fail_on_disconnect=true,"
        f"tx_port=tcp://*:{tx_port},"
        f"rx_port=tcp://{client_name}:{rx_port},"
        f"id=enb{tower_number},"
        f"base_srate=23.04e6"
    )
    lines.append("    cap_add:")
    lines.append("      - SYS_NICE")
    lines.append("    ulimits:")
    lines.append("      rtprio:")
    lines.append("        soft: 99")
    lines.append("        hard: 99")
    lines.append("    networks:")
    lines.append("      lte-net:")
    lines.append(f"        ipv4_address: {tower_ip}")
    lines.append("")

    if client_number <= args.clients:

        lines.append(f"  {client_name}:")
        lines.append("    build:")
        lines.append("      context: ..")
        lines.append(f"    container_name: lte-{client_name}")
        lines.append("    privileged: true")
        lines.append("    depends_on:")
        lines.append(f"      - {tower_name}")
        lines.append("    command: >")
        lines.append("      srsue")
        lines.append("      /etc/srsran/ue.conf")
        lines.append("      --rf.device_name=zmq")
        lines.append(
            f"      --rf.device_args="
            f"tx_port=tcp://*:{rx_port},"
            f"rx_port=tcp://{tower_name}:{tx_port},"
            f"id=ue{client_number},"
            f"base_srate=23.04e6"
        )
        lines.append("    cap_add:")
        lines.append("      - NET_ADMIN")
        lines.append("      - SYS_NICE")
        lines.append("    ulimits:")
        lines.append("      rtprio:")
        lines.append("        soft: 99")
        lines.append("        hard: 99")
        lines.append("    devices:")
        lines.append("      - /dev/net/tun:/dev/net/tun")
        lines.append("    networks:")
        lines.append("      - lte-net")
        lines.append("")

        client_number += 1

lines.append("networks:")
lines.append("  lte-net:")
lines.append("    driver: bridge")
lines.append("    ipam:")
lines.append("      config:")
lines.append("        - subnet: 10.10.10.0/24")

compose_path = out / "docker-compose.generated.yml"
compose_path.write_text("\n".join(lines))

print()
print("Generated:")
print(compose_path)
print()
print(f"Towers:  {args.towers}")
print(f"Clients: {min(args.clients, args.towers)}")
print()
print("Run:")
print("docker compose -f generated/docker-compose.generated.yml up -d --build")