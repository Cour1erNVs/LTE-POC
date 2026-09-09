# LTE-POC

A Dockerized LTE lab using **srsRAN** and **ZeroMQ**.

LTE-POC allows you to quickly deploy an emulated LTE environment containing:

- EPC
- LTE Towers (eNodeBs)
- LTE Clients (UEs)
- ZeroMQ RF connections between towers and clients

The deployment generator automatically creates the requested tower/client topology and configures the ZeroMQ connections.

---

# Windows Setup

## Requirements

- Windows 10/11
- WSL2
- Docker Desktop
- Git
- Python 3
- 8 GB+ RAM recommended for multiple towers/clients

---

## 1. Install WSL2

Open **PowerShell as Administrator**:

```powershell
wsl --install
```

Restart the computer if requested.

Verify:

```powershell
wsl -l -v
```

---

## 2. Install Docker Desktop

Install Docker Desktop and make sure the Docker Engine is running.

Verify:

```powershell
docker --version
```

Then:

```powershell
docker version
```

---

## 3. Clone LTE-POC

```powershell
git clone https://github.com/Cour1erNVs/LTE-POC
```

Enter the framework directory:

```powershell
cd LTE-POC\framework
```

---

## 4. Build

```powershell
docker compose build
```

The first build can take several minutes because srsRAN is compiled inside the Docker image.

---

## 5. Generate a Lab

Example with **2 towers and 2 clients**:

```powershell
py .\generate.py --towers 2 --clients 2
```

This creates:

```text
generated\
└── docker-compose.generated.yml
```

---

# Windows - Start Lab

Start the generated environment:

```powershell
docker compose -f .\generated\docker-compose.generated.yml up -d
```

Wait for the LTE network to initialize:

```powershell
Start-Sleep -Seconds 20
```

Check the containers:

```powershell
docker compose -f .\generated\docker-compose.generated.yml ps -a
```

Check whether the clients successfully attached:

```powershell
docker logs lte-client1 | Select-String "Network attach successful"
docker logs lte-client2 | Select-String "Network attach successful"
```

A successful client should show:

```text
Network attach successful. IP: 172.16.0.2
```

Check the LTE interfaces:

```powershell
docker exec lte-client1 ip -4 addr show tun_srsue
docker exec lte-client2 ip -4 addr show tun_srsue
```

Test connectivity using an assigned UE IP:

```powershell
docker exec -it lte-epc ping 172.16.0.2
```

Press `Ctrl+C` to stop the ping.

---

# Windows - Restart / Clear Lab

Stop and remove the current lab:

```powershell
docker compose -f .\generated\docker-compose.generated.yml down --remove-orphans
```

Generate the topology again if needed:

```powershell
py .\generate.py --towers 2 --clients 2
```

Start it:

```powershell
docker compose -f .\generated\docker-compose.generated.yml up -d
```

Wait:

```powershell
Start-Sleep -Seconds 20
```

Verify:

```powershell
docker compose -f .\generated\docker-compose.generated.yml ps -a
```

---

# Windows - WSL Memory

Running multiple srsRAN towers and clients can require a significant amount of RAM.

If a container exits with:

```text
Exited (137)
```

check whether it was killed because of insufficient memory:

```powershell
docker inspect lte-client1 --format="Exit={{.State.ExitCode}} OOMKilled={{.State.OOMKilled}}"
```

If you get:

```text
Exit=137 OOMKilled=true
```

open your WSL configuration:

```powershell
notepad $env:USERPROFILE\.wslconfig
```

Example configuration:

```ini
[wsl2]
memory=8GB
processors=4
swap=4GB
```

Save the file and run:

```powershell
wsl --shutdown
```

Restart Docker Desktop.

Verify the available memory:

```powershell
docker run --rm alpine free -h
```

---

# Linux Setup

## Requirements

- Linux
- Docker Engine
- Docker Compose plugin
- Git
- Python 3
- 8 GB+ RAM recommended for multiple towers/clients

> WSL is **not required** on Linux.

The following example uses Ubuntu/Debian.

---

## 1. Install Required Packages

```bash
sudo apt update
sudo apt install -y git python3
```

Install Docker using the appropriate installation method for your Linux distribution.

Verify Docker:

```bash
docker --version
```

Verify Docker Compose:

```bash
docker compose version
```

---

## 2. Clone LTE-POC

```bash
git clone https://github.com/Cour1erNVs/LTE-POC
```

Enter the framework directory:

```bash
cd LTE-POC/framework
```

---

## 3. Build

```bash
docker compose build
```

The first build can take several minutes because srsRAN is compiled inside the Docker image.

---

## 4. Generate a Lab

Example with **2 towers and 2 clients**:

```bash
python3 ./generate.py --towers 2 --clients 2
```

This creates:

```text
generated/
└── docker-compose.generated.yml
```

---

# Linux - Start Lab

Start the generated environment:

```bash
docker compose -f ./generated/docker-compose.generated.yml up -d
```

Wait for the LTE network to initialize:

```bash
sleep 20
```

Check the containers:

```bash
docker compose -f ./generated/docker-compose.generated.yml ps -a
```

Check whether the clients successfully attached:

```bash
docker logs lte-client1 | grep "Network attach successful"
docker logs lte-client2 | grep "Network attach successful"
```

A successful client should show:

```text
Network attach successful. IP: 172.16.0.2
```

Check the LTE interfaces:

```bash
docker exec lte-client1 ip -4 addr show tun_srsue
docker exec lte-client2 ip -4 addr show tun_srsue
```

Test connectivity:

```bash
docker exec -it lte-epc ping 172.16.0.2
```

Press `Ctrl+C` to stop the ping.

---

# Linux - Restart / Clear Lab

Stop and remove the current lab:

```bash
docker compose -f ./generated/docker-compose.generated.yml down --remove-orphans
```

Generate the topology again if needed:

```bash
python3 ./generate.py --towers 2 --clients 2
```

Start it:

```bash
docker compose -f ./generated/docker-compose.generated.yml up -d
```

Wait:

```bash
sleep 20
```

Verify:

```bash
docker compose -f ./generated/docker-compose.generated.yml ps -a
```

---

# Architecture

```text
                   EPC
                    |
            +-------+-------+
            |               |
         Tower 1          Tower 2
            |               |
          ZeroMQ          ZeroMQ
            |               |
         Client 1        Client 2
```

ZeroMQ emulates the RF connection between each srsRAN eNodeB and UE, allowing the LTE environment to run without physical SDR hardware.

---

# Quick Demo - Windows

```powershell
cd LTE-POC\framework

py .\generate.py --towers 2 --clients 2

docker compose -f .\generated\docker-compose.generated.yml up -d

Start-Sleep -Seconds 20

docker compose -f .\generated\docker-compose.generated.yml ps -a

docker logs lte-client1 | Select-String "Network attach successful"

docker logs lte-client2 | Select-String "Network attach successful"
```

Then test an assigned UE IP:

```powershell
docker exec -it lte-epc ping 172.16.0.2
```

---

# Quick Demo - Linux

```bash
cd LTE-POC/framework

python3 ./generate.py --towers 2 --clients 2

docker compose -f ./generated/docker-compose.generated.yml up -d

sleep 20

docker compose -f ./generated/docker-compose.generated.yml ps -a

docker logs lte-client1 | grep "Network attach successful"

docker logs lte-client2 | grep "Network attach successful"
```

Then test an assigned UE IP:

```bash
docker exec -it lte-epc ping 172.16.0.2
```

---

# Useful Commands

## Check Containers

Windows:

```powershell
docker compose -f .\generated\docker-compose.generated.yml ps -a
```

Linux:

```bash
docker compose -f ./generated/docker-compose.generated.yml ps -a
```

## Check Resource Usage

```bash
docker stats
```

## EPC Logs

```bash
docker logs lte-epc
```

## Tower Logs

```bash
docker logs lte-tower1
docker logs lte-tower2
```

## Client Logs

```bash
docker logs lte-client1
docker logs lte-client2
```

---

# Project Goal

LTE-POC is designed to make an emulated LTE network quickly deployable for lab and educational environments.

Instead of manually configuring each EPC, tower, UE, and ZeroMQ connection, the deployment generator creates the required Docker topology automatically.

The goal is to make deploying an LTE lab as simple as:

```text
Clone → Build → Generate → Start → Test
```