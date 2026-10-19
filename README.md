# Otomasi Lab MikroTik CHR via Docker

## Cara Penggunaan (Quick Start)

1. Pastikan seluruh file (`docker-compose.yml`, `deploy.sh`, dan `auto_config_chr.py`) berada pada direktori yang sama di server Ubuntu Anda.
2. Berikan hak akses eksekusi pada berkas *bash script*:
   ```bash
   chmod +x deploy.sh auto_config_chr.py
   ```
3. Jalankan proses otomatisasi:
    ```bash
    ./deploy.sh
    ```


---
Di terminal baru, bisa memantau proses.

`docker attach chr1`
<p align="center">
  <img width="460" height="300" src="/Users/kube/work/mikrotik-lab/auto-chr-lab-main/capture/chr1_v01.png">
</p>



..
....

`docker attach chr5`
<p align="center">
  <img width="460" height="300" src="/Users/kube/work/mikrotik-lab/auto-chr-lab-main/capture/chr5_v02.png">
</p>


---

## 1. Arsitektur Jaringan

* **Subnet Internal (Docker Bridge):** `172.20.0.0/24`
* **Gateway:** `172.20.0.1`
* **Daftar Instance Container:**
  * `chr1`: IP `172.20.0.10` | Winbox Port `8291` | SSH Port `2201`
  * `chr2`: IP `172.20.0.11` | Winbox Port `8292` | SSH Port `2202`
  * `chr3`: IP `172.20.0.12` | Winbox Port `8293` | SSH Port `2203`
  * `chr4`: IP `172.20.0.13` | Winbox Port `8294` | SSH Port `2204`
  * `chr5`: IP `172.20.0.14` | Winbox Port `8295` | SSH Port `2205`

---

## 2. Berkas Konfigurasi Utama

### A. `docker-compose.yml`
Digunakan untuk mendefinisikan topologi 5 container CHR dengan mode *privileged* agar QEMU di dalamnya dapat mengelola antarmuka jaringan dalam mode *promiscuous*, serta melakukan *port mapping* port manajemen ke *host*.

```yaml
networks:
  chr_net:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/24

services:
  chr1:
    image: mikrotik/chr:latest
    container_name: chr1
    privileged: true
    tty: true
    stdin_open: true
    restart: always
    command: sh -c "(sleep 3 && ifconfig eth0 promisc && ifconfig br0 promisc) & /start.sh"
    ports:
      - "8291:8291"
      - "2201:22"
      - "8081:80"
    networks:
      chr_net:
        ipv4_address: 172.20.0.10

  chr2:
    image: mikrotik/chr:latest
    container_name: chr2
    privileged: true
    tty: true
    stdin_open: true
    restart: always
    command: sh -c "(sleep 3 && ifconfig eth0 promisc && ifconfig br0 promisc) & /start.sh"
    ports:
      - "8292:8291"
      - "2202:22"
      - "8082:80"
    networks:
      chr_net:
        ipv4_address: 172.20.0.11

  chr3:
    image: mikrotik/chr:latest
    container_name: chr3
    privileged: true
    tty: true
    stdin_open: true
    restart: always
    command: sh -c "(sleep 3 && ifconfig eth0 promisc && ifconfig br0 promisc) & /start.sh"
    ports:
      - "8293:8291"
      - "2203:22"
      - "8083:80"
    networks:
      chr_net:
        ipv4_address: 172.20.0.12

  chr4:
    image: mikrotik/chr:latest
    container_name: chr4
    privileged: true
    tty: true
    stdin_open: true
    restart: always
    command: sh -c "(sleep 3 && ifconfig eth0 promisc && ifconfig br0 promisc) & /start.sh"
    ports:
      - "8294:8291"
      - "2204:22"
      - "8084:80"
    networks:
      chr_net:
        ipv4_address: 172.20.0.13

  chr5:
    image: mikrotik/chr:latest
    container_name: chr5
    privileged: true
    tty: true
    stdin_open: true
    restart: always
    command: sh -c "(sleep 3 && ifconfig eth0 promisc && ifconfig br0 promisc) & /start.sh"
    ports:
      - "8295:8291"
      - "2205:22"
      - "8085:80"
    networks:
      chr_net:
        ipv4_address: 172.20.0.14
```

### B. `deploy.sh` (Orkestrator Sekuensial)
Skrip otomatisasi bash yang bertugas membersihkan state lama, menginstal dependensi `pexpect`, menjalankan *deployment* secara **sekuensial** (satu per satu untuk mencegah *CPU throttling* saat QEMU *booting*), serta melakukan pengujian *Ping Sweep* akhir.

```bash
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
```[cite: 4]

### C. `auto_config_chr.py` (Skrip Otomasi Pexpect)
Skrip Python untuk menempel (*attach*) ke TTY container, menangani layar lisensi EULA, memperbarui kredensial, serta menginjeksikan konfigurasi IP, Gateway, dan DNS.

```python
#!/usr/bin/env python3
import pexpect
import sys
import time

if len(sys.argv) != 2:
    print("Penggunaan: ./auto_config_chr.py <nama_container>")
    sys.exit(1)

target_container = sys.argv[1]

chrs = {
    "chr1": "172.20.0.10",
    "chr2": "172.20.0.11",
    "chr3": "172.20.0.12",
    "chr4": "172.20.0.13",
    "chr5": "172.20.0.14"
}

if target_container not in chrs:
    print(f"[!] Container {target_container} tidak dikenali.")
    sys.exit(1)

ip = chrs[target_container]
gw = "172.20.0.1"
password = "x"

print(f"\n==========================================")
print(f"Memproses {target_container} ({ip})...")
print(f"==========================================")

child = None
try:
    child = pexpect.spawn(f"docker attach {target_container}", encoding='latin-1', timeout=30)
    child.logfile_read = sys.stdout

    # Jeda awal dan pancing TTY
    time.sleep(2)
    child.send("\r\n")

    # 1. Menunggu prompt Login:
    print(f"[*] {target_container}: Menunggu prompt Login...")
    child.expect(r"[Ll]ogin:\s*", timeout=20)
    child.sendline("admin")

    # 2. Menunggu prompt Password:
    print(f"[*] {target_container}: Menunggu prompt Password...")
    child.expect(r"[Pp]assword:\s*", timeout=15)
    child.send("\r") # Kirim Enter murni untuk password kosong

    # 3. Menangani Layar Lisensi EULA atau Langsung ke Password Baru
    print(f"[*] {target_container}: Memeriksa lisensi EULA / Password baru...")
    idx = child.expect([
        r"Do you want to see the software license\? \[Y/n\]:\s*", # 0
        r"press Enter \(q to abort\)\s*",                     # 1
        r"new password>\s*"                                      # 2
    ], timeout=20)

    if idx == 0:
        print(f"[*] {target_container}: Menolak lisensi dengan 'n'...")
        child.sendline("n")
        # Setelah menolak lisensi, tunggu prompt password baru
        child.expect(r"new password>\s*", timeout=10)
    elif idx == 1:
        print(f"[*] {target_container}: Keluar dari pager lisensi...")
        child.send("q")
        child.expect(r"new password>\s*", timeout=10)

    # 4. Memasukkan Password Baru ('x') secara sinkron
    print(f"[*] {target_container}: Mengatur password baru...")
    child.sendline(password)
    
    print(f"[*] {target_container}: Mengonfirmasi ulangi password baru...")
    child.expect(r"repeat new password>\s*", timeout=10)
    child.sendline(password)

    # 5. Menunggu sampai benar-benar masuk ke CLI Prompt '>'
    print(f"[*] {target_container}: Menunggu CLI prompt...")
    child.expect(r">\s*", timeout=15)
    print(f"[+] {target_container}: Berhasil masuk ke CLI prompt!")

    # Jeda mikro agar buffer stabil
    time.sleep(1)

    # 6. Injeksi Konfigurasi Jaringan Secara Berurutan & Aman
    print(f"[*] {target_container}: Menghapus IP lama...")
    child.sendline("/ip address remove [find]")
    child.expect(r">\s*", timeout=10)

    print(f"[*] {target_container}: Memasang IP {ip}/24...")
    child.sendline(f"/ip address add address={ip}/24 interface=ether1")
    child.expect(r">\s*", timeout=10)

    print(f"[*] {target_container}: Memasang Gateway {gw}...")
    child.sendline(f"/ip route add gateway={gw}")
    child.expect(r">\s*", timeout=10)

    print(f"[*] {target_container}: Menyetel DNS server...")
    child.sendline("/ip dns set servers=8.8.8.8,1.1.1.1")
    child.expect(r">\s*", timeout=10)

    print(f"\n[OK] {target_container} ({ip}) BERHASIL DIKONFIGURASI!")

except pexpect.TIMEOUT:
    print(f"\n[FATAL ERROR] {target_container}: Timeout tercapai pada state machine!")
    sys.exit(1)
except Exception as e:
    print(f"\n[FATAL ERROR] {target_container}: Terjadi kesalahan - {e}")
    sys.exit(1)
finally:
    if child:
        try:
            # Detach aman (Ctrl+P Ctrl+Q)
            child.send("\x10\x11")
            time.sleep(1)
            child.close(force=True)
        except:
            pass
```

---

## 3. Kendala Kritis yang Diatasi & Solusinya

1. **Crash Encoding Byte QEMU & TTY ANSI Escape:**
   * **Masalah:** Emulator QEMU mengirimkan karakter mentah serta *ANSI escape sequence* (seperti `\x1b[26;3R`) ke terminal, menyebabkan `pexpect` standar UTF-8 mengalami *crash* atau salah membaca *prompt*.
   * **Solusi:** Menambahkan argumen `encoding='latin-1'` pada modul `pexpect.spawn` agar seluruh byte mentah aman dibaca.
2. **Keterlambatan Booting & QEMU CPU Contention:**
   * **Masalah:** Ketika kelima CHR dinyalakan secara serentak (`docker compose up -d`), instance `chr3` hingga `chr5` mengalami *timeout* karena CPU *host* mengalami *bottleneck* saat instance QEMU bersamaan melakukan *booting* dan *generate* kunci SSH.
   * **Solusi:** Menerapkan pendekatan **Deployment Sekuensial** pada `deploy.sh`. Container dinyalakan satu per satu dengan jeda penantian *booting* selama 20 detik sebelum skrip Python mengeksekusi konfigurasinya.
3. **Penanganan EULA yang Menjebak:**
   * **Masalah:** Jika pertanyaan lisensi dijawab dengan menekan *Enter* kosong, RouterOS menganggapnya "Yes" sehingga TTY terkunci dalam pager teks GNU/GPL yang sangat panjang.
   * **Solusi:** Skrip diprogram untuk secara presisi mendeteksi teks lisensi dan meresponsnya secara eksplisit dengan huruf `"n"`.

---

