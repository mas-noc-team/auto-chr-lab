#!/bin/bash
set -e

echo "=== 1. Bersihkan Container Lama Secara Total ==="
reset 2>/dev/null || true
docker compose down --remove-orphans -v

echo "=== 2. Memastikan Pexpect Terinstal ==="
sudo apt-get update -qq && sudo apt-get install -y -qq python3-pexpect >/dev/null
chmod +x auto_config_chr.py

echo "=== 3. Deploy & Konfigurasi Sekuensial (Satu per Satu) ==="
# Hanya menyalakan bridge network tanpa menyalakan container
docker compose up -d --no-start

for i in {1..5}; do
    CONTAINER="chr$i"
    echo -e "\n>>> Menyalakan $CONTAINER..."
    docker compose start $CONTAINER
    
    echo ">>> Menunggu $CONTAINER selesai booting (20 detik)..."
    sleep 20
    
    echo ">>> Mengeksekusi konfigurasi otomatis untuk $CONTAINER..."
    ./auto_config_chr.py $CONTAINER
    
    echo ">>> Jeda 2 detik sebelum lanjut ke container berikutnya..."
    sleep 2
done

echo -e "\n=== 4. Pengujian Akhir Ping Sweep 5 CHR ==="
for ip in 172.20.0.10 172.20.0.11 172.20.0.12 172.20.0.13 172.20.0.14; do
  ping -c 1 -W 1 $ip >/dev/null 2>&1 && echo "IP $ip: REACHABLE [OK]" || { echo "IP $ip: UNREACHABLE [FAILED]"; exit 1; }
done

echo "=== DEPLOYMENT SELESAI DAN VALID ==="
