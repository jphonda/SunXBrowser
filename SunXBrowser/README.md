# SunXBrowser — Chromium desktop source overlay

สถานะ: เตรียม patch ของ Chromium, GitHub Actions cloud build และสคริปต์สร้าง development installer สำหรับ Windows/macOS แล้ว
**ยังไม่มีไฟล์ติดตั้งหรือ browser binary ที่ผ่านการทดสอบ** เครื่องที่เตรียมโปรเจกต์นี้มีพื้นที่ว่างประมาณ 14 GiB จึงไม่ได้ checkout และ compile Chromium ทั้งหมด

สำหรับ build บน cloud โดยไม่ใช้พื้นที่เครื่องนี้ ดู [CLOUD_BUILD.md](CLOUD_BUILD.md) ต้องเชื่อม GitHub repository และ self-hosted cloud runners ก่อนจึงจะสั่ง build และดาวน์โหลด `.exe`/`.dmg` ได้

## สิ่งที่แก้ในซอร์ส

- ชื่อผลิตภัณฑ์และชื่อสั้น: SunXBrowser
- macOS bundle ID: `app.sunxbrowser.browser`
- แยกโฟลเดอร์ข้อมูลผู้ใช้ Windows/macOS ออกจาก Chromium
- ใช้ไอคอน S สีน้ำเงินจากแอปเดิมในโปรเจกต์ มีไฟล์ ICO, ICNS และ PNG ตามขนาดที่ Chromium ใช้
- ค่าเริ่มต้น Secure DNS: `secure` กับ endpoint `https://1.1.1.1/dns-query` ตั้งทั้งตอน register preferences และตอน constructor ตั้ง defaults เพื่อไม่ให้โค้ดต้นทางเปลี่ยนกลับเป็น automatic
- ไม่ต้องติดตั้ง DNS profile, VPN หรือกด Allow เพื่อเปิด DNS ของเบราว์เซอร
เป็นค่าเริ่มต้นสำหรับโปรไฟล์ใหม่ ผู้ใช้ยังเปลี่ยนใน settings ได้ และ enterprise policy/parental controls ของ Chromium ยังมีผลตามเดิม ไม่ได้เขียนทับค่าที่ผู้ใช้บันทึกไว้ ไม่ได้เปลี่ยน DNS ของระบบหรือแอปอื่น สิทธิ์เว็บไซต์ เช่น กล้อง ไมค์ และตำแหน่ง ยังคงทำงานตาม Chromium

โหมด secure ไม่ย้อนกลับไป DNS ปกติหาก endpoint ใช้งานไม่ได้ ดังนั้นเว็บอาจเปิดไม่ได้บนเครือข่ายที่บล็อก Cloudflare DoH

## Build

ใช้ Python 3 และติดตั้ง [depot_tools](https://chromium.googlesource.com/chromium/tools/depot_tools.git) โดยเพิ่มลง PATH
ต้อง build บนระบบปลายทาง: Windows สำหรับ Windows และ macOS สำหรับ macOS
ติดตั้งเครื่องมือตาม [Windows build instructions](https://chromium.googlesource.com/chromium/src/+/main/docs/windows_build_instructions.md) หรือ [macOS build instructions](https://chromium.googlesource.com/chromium/src/+/main/docs/mac_build_instructions.md)
สคริปต์ตรวจพื้นที่ว่างอย่างน้อย 150 GiB ก่อนเริ่ม fetch; เป็นเกณฑ์ขั้นต่ำของโปรเจกต์นี้ ไม่ใช่การรับประกันว่าจะพอสำหรับทุก configuration

macOS (checkout path ต้องไม่มีช่องว่าง):

```sh
python3 scripts/build.py /Volumes/BuildDisk/sunx-chromium --fetch
```

Windows บน Developer Command Prompt ที่มี depot_tools ใน PATH:

```bat
py scripts\build.py D:\sunx-chromium --fetch
```

กรณีมี checkout ที่ sync dependencies กับ revision ใน `upstream.json` แล้ว:

```sh
python3 scripts/build.py /path/to/sunx-chromium
```

ใช้ `--apply-only` หากต้องการลง source overlay โดยไม่ compile สคริปต์ตรวจ revision และ patch context ก่อนแก้ไฟล์ และรันซ้ำได้โดยไม่ลง patch ซ้ำ

ผล build target `chrome` อยู่ใน `src/out/SunXBrowser`: Windows ใช้ `chrome.exe`; macOS คาดว่าจะได้ `SunXBrowser.app` จาก BRANDING ที่แก้ไว้ ต้องยืนยันชื่อและการเปิดใช้งานหลัง compile จริง

## การตรวจสอบที่ทำแล้ว / ยังต้องทำ

ตรวจว่า patch ใช้ได้กับไฟล์ซอร์สจริงที่โหลดจาก pinned revision, ตรวจ XML ของ GRD/Info.plist หลังลง patch, ตรวจ DNS defaults และรูปแบบไอคอนแล้ว ไม่มีการทดสอบ compile C++ หรือทดสอบ DNS ภายใน Chromium ที่รันจริง

หลัง build ให้ใช้โปรไฟล์ใหม่ เปิด `chrome://settings/security` ตรวจ Cloudflare Secure DNS และเปิด `https://1.1.1.1/help` ตรวจ DoH จาก browser จริง ทดสอบเปิดเว็บ, private tabs, restart, DNS unavailable, โฟลเดอร์โปรไฟล์และไอคอนบนทั้งสองระบบ ใช้ network capture/net-export เพิ่มเติมเพื่อยืนยันว่าการ resolve โดเมนทดสอบส่งไป endpoint ที่กำหนด

นี่เป็น development overlay ใช้ NSIS แบบ per-user สำหรับ Windows และ DMG สำหรับ Mac ตามคู่มือ cloud build; ไม่ใช้ Chromium mini_installer และไม่ติดตั้ง COM registration เดิม ยังต้องทำ branding ของข้อความ/คำแปลที่เหลือ, signing/notarization, ทดสอบ installer บนระบบจริง และระบบอัปเดตความปลอดภัยก่อนแจกจ่าย ข้อความลิขสิทธิ์ของ Chromium คงอยู่

## Upstream

Revision อยู่ใน `upstream.json` เพื่อให้ source overlay ตรวจซ้ำได้ เป็น revision สำหรับพัฒนา ไม่ได้ผ่านการรับรองเป็น release ของ SunXBrowser เมื่ออัปเดต Chromium ต้องตรวจ patch และทดสอบใหม่ อย่าใช้ binary รุ่นที่ไม่ได้รับ security updates เป็นเบราว์เซอร์หลัก

