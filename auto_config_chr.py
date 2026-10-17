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
