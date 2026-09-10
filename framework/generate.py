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

if args.clients > args.towers:
    raise SystemExit(
        "Current ZMQ design supports one client per tower. "
        "Clients cannot exceed towers."
    )

if args.towers > 230:
    raise SystemExit(
        "Too many towers for the current 10.10.10.0/24 network"
    )


out = Path("generated")
out.mkdir(exist_ok=True)


def generate_imsi(client_number):
    mcc = "001"
    mnc = "01"
    msin = f"{client_number:010d}"
    return f"{mcc}{mnc}{msin}"


AUTH = "xor"
KEY = "00112233445566778899aabbccddeeff"
OP_TYPE = "opc"
OPC = "63bfa50ee6523365ff14c1f45f88737d"
AMF = "9001"
SQN = "000000001234"
QCI = "7"
IP_ALLOC = "dynamic"


#
# Generate HSS subscriber database
#

user_db_lines = [
    "#",
    "# .csv to store UE's information in HSS",
    '# Kept in the following format: "Name,Auth,IMSI,Key,OP_Type,OP/OPc,AMF,SQN,QCI,IP_alloc"',
    "#",
    "# Name:     Human readable name to help distinguish UE's. Ignored by the HSS",
    "# Auth:     Authentication algorithm used by the UE. Valid algorithms are XOR",
    "#           (xor) and MILENAGE (mil)",
    "# IMSI:     UE's IMSI value",
    "# Key:      UE's key, where other keys are derived from. Stored in hexadecimal",
    "# OP_Type:  Operator's code type, either OP or OPc",
    "# OP/OPc:   Operator Code/Cyphered Operator Code, stored in hexadecimal",
    "# AMF:      Authentication management field, stored in hexadecimal",
    "# SQN:      UE's Sequence number for freshness of the authentication",
    "# QCI:      QoS Class Identifier for the UE's default bearer.",
    "# IP_alloc: IP allocation stratagy for the SPGW.",
    "#           With 'dynamic' the SPGW will automatically allocate IPs",
    "#           With a valid IPv4 the UE will have a statically assigned IP.",
    "#",
    "# Note: Lines starting by '#' are ignored and will be overwritten",
]


for client_number in range(1, args.clients + 1):

    imsi = generate_imsi(client_number)

    user_db_lines.append(
        f"ue{client_number},"
        f"{AUTH},"
        f"{imsi},"
        f"{KEY},"
        f"{OP_TYPE},"
        f"{OPC},"
        f"{AMF},"
        f"{SQN},"
        f"{QCI},"
        f"{IP_ALLOC}"
    )


user_db_path = out / "user_db.generated.csv"

with user_db_path.open(
    "w",
    encoding="utf-8",
    newline="\n"
) as f:

    f.write("\n".join(user_db_lines) + "\n")


#
# Generate Docker Compose file
#

lines = []

lines.append("services:")
lines.append("")


#
# EPC
#

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

lines.append("    sysctls:")
lines.append("      net.ipv4.ip_forward: 1")
lines.append("      net.ipv4.conf.all.send_redirects: 0")
lines.append("      net.ipv4.conf.default.send_redirects: 0")

lines.append("    devices:")
lines.append("      - /dev/net/tun:/dev/net/tun")

lines.append("    volumes:")
lines.append(
    "      - ./user_db.generated.csv:/etc/srsran/user_db.csv"
)

lines.append("    networks:")
lines.append("      lte-net:")
lines.append("        ipv4_address: 10.10.10.10")

lines.append("")


#
# Towers
#

for tower_number in range(1, args.towers + 1):

    tower_ip = f"10.10.10.{20 + tower_number - 1}"

    tx_port = 2000 + ((tower_number - 1) * 100)
    rx_port = tx_port + 1

    tower_name = f"tower{tower_number}"

    lines.append(f"  {tower_name}:")

    lines.append("    build:")
    lines.append("      context: ..")

    lines.append(
        f"    container_name: lte-{tower_name}"
    )

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

    if tower_number <= args.clients:

        client_name = f"client{tower_number}"

        lines.append(
            f"      --rf.device_args="
            f"fail_on_disconnect=true,"
            f"tx_port=tcp://*:{tx_port},"
            f"rx_port=tcp://{client_name}:{rx_port},"
            f"id=enb{tower_number},"
            f"base_srate=23.04e6"
        )

    else:

        lines.append(
            f"      --rf.device_args="
            f"fail_on_disconnect=false,"
            f"tx_port=tcp://*:{tx_port},"
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


#
# Clients
#

for client_number in range(1, args.clients + 1):

    tower_number = client_number
    tower_name = f"tower{tower_number}"
    client_name = f"client{client_number}"

    tx_port = 2000 + ((tower_number - 1) * 100)
    rx_port = tx_port + 1

    imsi = generate_imsi(client_number)

    lines.append(f"  {client_name}:")

    lines.append("    build:")
    lines.append("      context: ..")

    lines.append(
        f"    container_name: lte-{client_name}"
    )

    lines.append("    privileged: true")

    lines.append("    depends_on:")
    lines.append(f"      - {tower_name}")

    lines.append("    command: >")
    lines.append("      srsue")
    lines.append("      /etc/srsran/ue.conf")
    lines.append(f"      --usim.imsi={imsi}")
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


#
# Docker network
#

lines.append("networks:")
lines.append("  lte-net:")
lines.append("    driver: bridge")
lines.append("    ipam:")
lines.append("      config:")
lines.append("        - subnet: 10.10.10.0/24")


compose_path = out / "docker-compose.generated.yml"

with compose_path.open(
    "w",
    encoding="utf-8",
    newline="\n"
) as f:

    f.write("\n".join(lines) + "\n")


#
# Output
#

print()

print("Generated:")
print(f"  {compose_path}")
print(f"  {user_db_path}")

print()

print(f"Towers:  {args.towers}")
print(f"Clients: {args.clients}")

print()

print("LTE topology:")
print()

for tower_number in range(1, args.towers + 1):

    if tower_number <= args.clients:

        imsi = generate_imsi(tower_number)

        print(
            f"  client{tower_number}"
            f" -> tower{tower_number}"
            f" -> EPC"
            f" | IMSI {imsi}"
        )

    else:

        print(
            f"  tower{tower_number}"
            f" -> EPC"
            f" | no client"
        )

print()

print("Run:")
print(
    "docker compose "
    "-f generated/docker-compose.generated.yml "
    "up -d --build"
)