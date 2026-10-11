# SunXBrowser บน GitHub Actions

ระบบ build อยู่ที่ `.github/workflows/sunxbrowser-build.yml` ใน repository root
รันเองผ่าน **Actions → SunXBrowser cloud installers → Run workflow** เท่านั้น ไม่เริ่ม compile Chromium อัตโนมัติทุกครั้งที่ push

ตรวจ workflow ด้วย actionlint ผ่านแล้ว และ unit tests ของ tooling ผ่าน 10 รายการ (runtime payload, uninstall manifest, disk/architecture preflight, ownership ของ cleanup) ไม่ใช่ผลการ compile หรือการติดตั้ง browser จริง

## สถานะ

เตรียม workflow, bootstrap เครื่องมือ, build, headless smoke test, Windows NSIS installer, macOS DMG, SHA-256, log และการล้าง checkout หลังจบแล้ว ยังไม่ได้รัน full Chromium build บน cloud และยังไม่มีไฟล์ติดตั้งจริงที่ยืนยันแล้ว ต้องเชื่อม repository และ runner ก่อน

ผล build เป็น **development installer**: Windows `.exe` ยังไม่มี Authenticode; macOS `.dmg` ยังไม่มี Developer ID signing/notarization จึงอาจเจอ SmartScreen/Gatekeeper ไม่ได้ปิดระบบป้องกันของ OS ในสคริปต์ การไม่ต้องกด Allow ที่ตั้งไว้หมายถึง DNS ภายในเบราว์เซอร์เท่านั้น

## 1. GitHub repository

นำโฟลเดอร์ `SunXBrowser/` และ `.github/` ขึ้น repository โดยต้องวาง `.github` ที่ root มี workflow build และ workflow ทดสอบ tooling ขนาดเล็กบน Ubuntu อย่าอัปโหลดโฟลเดอร์ build ของแอป iOS, Chromium checkout หรือไฟล์ token

ใช้ private repository หรือควบคุมสิทธิ์ผู้ที่แก้ workflow ได้ เพราะ workflow นี้รันบนเครื่อง cloud ของคุณ ไม่เปิดใช้งาน pull_request จากภายนอก และ GitHub token มีเพียง `contents: read`

## 2. เตรียม cloud runner

workflow ใช้ **self-hosted runner บน cloud** ซึ่งหมายถึงเช่าเครื่อง cloud แล้วติดตั้ง GitHub Actions runner บนนั้น ไม่ใช่เครื่อง Mac ปัจจุบันของคุณ และ workflow ไม่ได้สร้างหรือจ่ายค่าเช่า VM ให้อัตโนมัติ

| ระบบ | label ที่ runner ต้องมี | เครื่องมือ |
|---|---|---|
| Windows x64 | `self-hosted`, `Windows`, `X64`, `sunx-build` | Git, Python 3.12, Visual Studio 2026 C++/ATL/MFC, Windows SDK, NSIS 3 |
| macOS Apple Silicon | `self-hosted`, `macOS`, `ARM64`, `sunx-build` | Git, Python 3.12, Xcode 27, macOS SDK 27, accepted Xcode license |
| macOS Intel (เลือก X64 ตอนรัน) | `self-hosted`, `macOS`, `X64`, `sunx-build` | เครื่องมือ macOS ตามรุ่นที่ Chromium revision นี้รองรับ |

แนะนำ RAM อย่างน้อย 32 GB และดิสก์ 300–500 GB มีพื้นที่ว่าง **อย่างน้อย 200 GiB** ก่อน build สคริปต์จะหยุดก่อนดาวน์โหลดถ้าพื้นที่ไม่พอ Windows checkout ต้องอยู่บน NTFS; Mac checkout บน APFS และ path ต้องไม่มีช่องว่าง

Windows ต้องมี Windows 11 SDK และ SDK Debugging Tools 10.0.26100.3323 ขึ้นไปตาม [ข้อกำหนดของ Chromium revision ที่ใช้](https://chromium.googlesource.com/chromium/src/+/4afca57b57f531a92ffc15af0ffb5cf0038fb273/docs/windows_build_instructions.md) ติดตั้ง Desktop development with C++ และ ATL/MFC ใน Visual Studio Installer เพิ่มโฟลเดอร์ NSIS ที่มี `makensis.exe` ลง PATH ของบัญชีที่รัน runner แล้ว restart runner service

ใน GitHub เปิด **Settings → Actions → Runners → New self-hosted runner** เลือก OS/architecture และทำตามคำสั่งที่ GitHub แสดงบนเครื่อง cloud เพิ่ม custom label `sunx-build` อย่าเก็บ registration token ใน repository เปิด runner เป็น service ตามคู่มือที่ GitHub แสดง

ดู [GitHub self-hosted runners](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/add-runners) และ [Chromium macOS build requirements](https://chromium.googlesource.com/chromium/src/+/4afca57b57f531a92ffc15af0ffb5cf0038fb273/docs/mac_build_instructions.md)

workflow นี้ไม่ใช้ GitHub macOS hosted runner เพราะดิสก์ที่ระบุใน [runner specifications](https://docs.github.com/en/actions/reference/runners/larger-runners) ไม่พอสำหรับ full Chromium build

## 3. เลือกไดรฟ์ build บน cloud

ตั้ง repository variables ใน **Settings → Secrets and variables → Actions → Variables**:

- `SUNX_WINDOWS_BUILD_ROOT`: เช่น `D:\sunx-builds`
- `SUNX_MACOS_BUILD_ROOT`: เช่น `/Volumes/BuildDisk/sunx-builds`

ถ้าไม่ตั้ง จะใช้ `$RUNNER_TEMP/sunx-builds` บน cloud runner ไดรฟ์นั้นต้องมีพื้นที่พอ สคริปต์สร้าง subdirectory ของแต่ละ run พร้อม ownership marker แล้วลบเฉพาะ directory ของ run นั้นหลัง upload ไม่ลบ checkout อื่น ไม่ cache ซอร์ส Chromium บนเครื่องนี้

## 4. Build และดาวน์โหลด

เลือก platform `both`, `windows` หรือ `macos`; สำหรับ Mac เลือก ARM64 หรือ X64 ให้ตรงเครื่อง runner ค่าเริ่มต้นคือ Apple Silicon ไม่ใช่ universal binary ถ้าต้องการ Intel เพิ่ม ให้รัน macos/X64 อีกครั้งบน Intel runner

เมื่อเสร็จ เปิดหน้า workflow run → **Artifacts**:

- `SunXBrowser-windows-x64-…`: `SunXBrowser-<version>-windows-x64-unsigned-setup.exe`
- `SunXBrowser-macos-ARM64-…`: `SunXBrowser-<version>-macos-arm64-unsigned.dmg`
- แต่ละชุดมี `.sha256`, `build-info.json`, `build.log`, `smoke.log`

artifact เก็บ 14 วัน ถ้า build ล้มเหลว artifact จะมี diagnostics แต่ไม่มี installer อย่าตีความว่า upload artifact สำเร็จแปลว่า build สำเร็จ ดู job conclusion และไฟล์ผลลัพธ์ประกอบ หาก job อยู่ Queued แสดงว่ายังไม่มี runner ที่ online และตรง labels

Windows installer ใช้ NSIS และ runtime dependency manifest จาก GN ติดตั้งใน `%LOCALAPPDATA%\Programs\SunXBrowser` มี Start Menu/Desktop shortcut และตัวถอนการติดตั้ง ไม่ขอ administrator เพื่อติดตั้ง และไม่ลงทะเบียน COM/default browser ผ่าน Chromium mini_installer จึงไม่เอา COM GUID เดิมไปลงทับ Chromium ที่มีอยู่ ข้อมูลผู้ใช้แยกจากไฟล์โปรแกรมและไม่ถูกลบเมื่อถอนการติดตั้ง ต้องปิด SunXBrowser ก่อนติดตั้งทับ/ถอนการติดตั้ง

macOS DMG มี `SunXBrowser.app` กับลิงก์ Applications สำหรับลากไปติดตั้ง ตรวจ bundle ID และ development code signature ก่อนสร้าง image และใช้ `hdiutil verify` หลังสร้าง ไม่ได้แอบอ้างว่าเป็นไฟล์ notarized

## การทดสอบและการแจกจ่าย

workflow จะเปิด binary ที่ build จริงแบบ headless แล้วให้ renderer โหลด HTML ทดสอบ โดยยังเปิด sandbox ตามค่า Chromium ปกติ นี่ตรวจการเริ่มต้น/renderer ไม่ใช่การทดสอบ DNS ครบทุกเครือข่ายหรือ installer end-to-end

ก่อนแจกจ่ายต้องลองติดตั้ง/ถอนการติดตั้งบน Windows และเปิดแอปจาก DMG บน Mac จริง ตรวจ Secure DNS จาก `chrome://settings/security` และ `https://1.1.1.1/help`, เว็บไซต์, restart และ private tabs รุ่น upstream ที่ pin เป็น development revision ต้องอัปเดตด้านความปลอดภัยและทดสอบก่อนออก release

ระบบนี้ยังไม่ผูก certificate/secrets สำหรับ Authenticode หรือ Apple Developer ID หากต้องการไฟล์ที่ระบบเชื่อถือ ต้องเพิ่มขั้นตอน signing/notarization พร้อม certificate ของผู้พัฒนาจริงก่อน publish
