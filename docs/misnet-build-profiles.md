# MISNET ES001 RevA 建置設定

硬體名稱固定為 `misnet-imx93-es001-reva`，使用獨立板型 Kconfig symbol，
並歸入 i.MX93 / IMX family。依使用者指定，初版 BSP、U-Boot 與 Kernel 設定
沿用 `imx93evk` 基線；這不表示 EVK 的 pinmux、DDR 或周邊設定已在 ES001 RevA 驗證。
維持 LSDK 26.06、Debian 13 trixie、arm64 與 `lf-6.12.49-2.2.0`。

| 設定檔 | profile | Kernel fragment | DTB |
| --- | --- | --- | --- |
| `configs/misnet-dev/defconfig` | dev | `configs/linux/misnet-dev.config` | `imx93-11x11-misnet-es001-reva-dev.dtb` |
| `configs/misnet-demo/defconfig` | demo | `configs/linux/misnet-demo.config` | `imx93-11x11-evk-pn5180.dtb` |
| `configs/misnet-production/defconfig` | production | `configs/linux/misnet-production.config` | `imx93-11x11-misnet-es001-reva-product.dtb` |

三組 defconfig 的 component selection 保存本次修改前 `.config` 的選項。
production 目前只代表獨立建置設定，尚未做套件裁減或出貨設定調整。
Kernel fragments 目前只有註解，沒有額外 Kernel 選項；DTB 由 `CONFIG_LINUX_DTB` 選擇。
三組 profile 共用同一份 Kernel source 與 `patch/linux/` 補丁；profile 差異由
各自的 defconfig 選擇 DTB。dev 與 production 的獨立 DTS 由
`patch/linux/0012-arm64-dts-imx93-add-misnet-es001-reva-dev-product.patch`
保存，目前只 include `imx93-11x11-evk.dts`，沒有增刪硬體節點或改動屬性；
後續各 profile 的硬體設定可分別加在其 DTS。兩者目前仍沿用 EVK 的
`model` 與 `compatible`，上板前須依 ES001 RevA 硬體核對。
風扇 PWM 設定只位於 demo 使用的 PN5180 DTS，
不在 dev／production 使用的 DTS 中。
`src/linux/linux.mk` 的 `dl-kernel` 對共用 source 依檔名順序套用全部
`patch/linux/*.patch`，不依 profile 過濾；`0006` 新增 demo DTS，
`0007`、`0008` 與 `0009` 只修改該 DTS。demo 的 `CONFIG_LINUX_DTB` 選 PN5180 DTB，
dev／production 各選對應的 MISNET DTB；8GB／16GB 映像容量不影響這項選擇。
既有 source 的 `.patchdone` 不會因新增補丁而重套；更新該 source 時
必須先核對內容，不能刪除標記後盲目套用全部補丁。

## 設定入口與產物隔離

主機執行 `make docker`，進入容器後依需求擇一：

```sh
make config CONFIG=configs/misnet-dev/defconfig
make config CONFIG=configs/misnet-demo/defconfig
make config CONFIG=configs/misnet-production/defconfig
```

以上每條都會改寫 `.config`，並執行 SDK 解析與依賴準備。
`make misnet-imx93-es001-reva_defconfig` 也可選板，但會使用 Kconfig 預設選項
與 dev profile，不等同於載入已保存的 dev defconfig。

所有板型的 `FBOUTDIR` 都以 machine 分開；MISNET 再以 profile 分開：

```text
build_lsdk2606/imx93evk/
build_lsdk2606/imx93frdm/
build_lsdk2606/misnet-imx93-es001-reva/dev/
build_lsdk2606/misnet-imx93-es001-reva/demo/
build_lsdk2606/misnet-imx93-es001-reva/production/
```

EVK／FRDM 可分別以 `make config CONFIG=configs/imx93evk/defconfig` 和
`make config CONFIG=configs/imx93frdm/defconfig` 載入受追蹤設定；這兩份設定
沿用 Kconfig 的 component 預設值，未聲稱與舊版 EVK `.config` 完全相同。
設定入口會改寫根目錄 `.config` 並執行依賴準備；主機先用 `make docker`。
載入設定後可在容器內執行 `make all`；需要 WIC 映像時另執行 `make wic`。
EVK／FRDM 沒有設定 `CONFIG_LINUX_DTB`，boot script 沿用 U-Boot 的
`fdtfile`，須核對板端 environment 及 boot partition 中的 DTB 檔名。
各目錄包含 Kernel output/staging、apps/modules、RootFS、BSP 與 images。
元件 source、下載快取及 `.patchdone` 仍共用；不能同時在同一 checkout
切換 `.config` 或並行建置不同板型／profile。舊的 `build_lsdk2606/` 頂層
EVK 產物不會自動搬移，新建置使用 `build_lsdk2606/imx93evk/`。
既有 Kernel output `.config` 不會自動重套修改後的 fragment。

未來新增 MISNET 硬體 revision 時，需依實際硬體建立獨立的 machine、板型設定
及 defconfig，並擴充 MISNET profile 的 Kconfig 適用條件；同一 revision 的用途
差異再用 profile。新增板型後，上述路徑規則會自動使用新的 machine 名稱，
不須另改 Makefile。

## 待辦：8GB eMMC 映像設定

- 在 `make menuconfig` 加入 MISNET WIC 容量選項，供 dev、demo、production
  共用；預設維持現有標準設定（10 GiB WIC，供 16GB eMMC 使用）。
- 8GB 選項只調整 WIC 製作，不複製 Kernel、應用程式或 RootFS 建置設定；
  將選項由 Kconfig／Makefile 傳至 `tools/flex-builder` 與 `tools/flex-installer`。
- 8GB WIC 使用獨立檔名，避免覆寫標準 WIC；製圖前檢查分割區配置、
  RootFS 解包容量及目標映像大小，容量不足時明確失敗。
- 先以 7.25 GiB 作為候選映像大小；定稿前用 8GB 實板的 `lsblk -b`
  確認 eMMC 實際容量，並保留映像與裝置間的容量餘量。現有 16GB
  板端 `/` 已用約 5.03 GiB，估算縮至該大小後約剩 1 GiB，
  須以新映像及實板重新量測。
- 驗證三種 profile 的選項、預設行為、兩種 WIC 的檔名、解壓後大小、
  分割表與檔案系統空間；另在 8GB 板確認開機及實際剩餘空間。
  製作映像與燒錄實體 eMMC 分開處理，燒錄前另取得明確批准。

## Demo 預裝開發套件

`configs/debian/extra_packages_list` 的 `misnet_demo_pkgs` 保存下列套件：

```text
build-essential cmake
libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev
```

`tools/distro_debian` 只在 `MACHINE=misnet-imx93-es001-reva` 且
`MISNET_PROFILE=demo` 的非 base RootFS 建置中追加此清單，適用一般 mmdebstrap
與 gradual 安裝路徑；不會替 dev、production 或 EVK 追加套件。
現有 imx93evk RootFS 的 dpkg 紀錄顯示 `libwayland-dev`、`libwayland-bin`、
`wayland-protocols`、`libxkbcommon-dev`、`gstreamer1.0-plugins-base`、
`gstreamer1.0-plugins-good` 已安裝；`pkgconf` 提供 `pkg-config` 命令。
`weston` 由現有 graphics recipe 建置及併入 RootFS，因此未再加入 Debian
套件清單。上述四個 demo 專用項目在該 RootFS 的 dpkg 紀錄中未安裝。

容器內使用 `make config CONFIG=configs/misnet-demo/defconfig` 後，
`make rfs` 建立含套件的 RootFS，或用 `make all` 完成整套建置與打包。
`make linux` 不安裝 RootFS 套件。既有 RootFS 的 `etc/buildinfo` 會使 `make rfs`
跳過；需保存客製資料並取得明確批准後才清理及重建，不刪標記強制重建。

demo 仍啟用 `CONFIG_GFX_WESTON=y` 與 GStreamer source recipes；
`make merge-apps` 會將建置產物併入 RootFS。新增 Debian GStreamer 開發套件
可能與 source 版本的 headers／library 共存，需在板端檢查實際
`pkg-config` 解析的版本與路徑；預裝套件不代表已通過執行測試。

## DTB 的建置、打包與載入

`make linux` 沿用 NXP Kbuild all 流程，但只複製 `CONFIG_LINUX_DTB` 指定的 DTB
到當前 profile 的 Kernel staging。下載與 patch 後會檢查對應 DTS 是否存在。
`make boot` 產生的 boot script 會在共用 IMX boot script 前加入：

```text
setenv fdtfile <本版選用的 DTB>
setenv image Image
```

這只設定當次 boot script 的變數，不執行 `saveenv`。因此 demo 不會因既有
U-Boot `fdtfile` 指向預設 EVK 而選錯 DTB。仍需確認板端實際執行的是本版 `boot.scr`。
`flex-installer` 加入新 machine 名稱，DTB 清理前綴使用 `imx93`；本次不執行安裝或燒錄。

## Demo AHT21B 的舊 I²C 接線（2026-10-20）

以下記錄舊設定；現行 BME280 設定見本文末的 2026-11-03 紀錄。

demo 使用的 `imx93-11x11-evk-pn5180.dtb` 現在將 LPI2C4 設為 100 kHz，
並把 GPIO_IO02／GPIO_IO03 分別 mux 成 SDA／SCL；NXP EVK J1001 的對應
接腳是 pin 3／5。修改由 `patch/linux/0008-arm64-dts-imx93-evk-pn5180-enable-aht21b-i2c.patch`
保存，dev／production 的 DTB 不受影響。`imx93.dtsi` 將 LPI2C4 alias 為
`i2c3`，因此載入新版 DTB 後預期出現 `/dev/i2c-3`；實際板端仍須核對。

感測器型號已確認為 AHT21B_v10，而非 DHT11。AHT21B 是 I²C 裝置，
資料表使用 7-bit 位址 `0x38`；目前 Kernel 的 `aht10` hwmon 驅動只明列
AHT10／AHT20，故本次只啟用 I²C bus，不宣稱已有 AHT21B 的 kernel
sensor driver，也不建立未驗證的相容裝置節點。既有 `imx_v8_defconfig`
已啟用 `CONFIG_I2C_IMX_LPI2C` 與 `CONFIG_I2C_CHARDEV`，可供後續
userspace 通訊驗證。

MISNET ES001 RevA 仍須按實板原理圖確認 40-pin 接腳走線、感測器供電、
SDA／SCL 上拉電壓與阻值；不可直接把 5V 上拉接到未確認的 SoC I/O。
尚未在 8GB／16GB 實板上驗證 I²C ACK、量測值或開機載入的 DTB。

## 保存現有 PN5180 DTS

本地 Kernel source 沒有 `.git`，不能確認其 commit 或全部既有差異。
快取 `dl/linux_lf-6.12.49-2.2.0.tar.gz` 中沒有 PN5180 DTS。
`patch/linux/0006-arm64-dts-imx93-evk-pn5180-demo.patch` 保存現有
`imx93-11x11-evk-pn5180.dts` 的完整內容，並在基線 DTS Makefile 註冊 DTB，
接續既有 0001–0005 補丁。

`0007-arm64-dts-imx93-evk-pn5180-enable-tpm4-fan-pwm.patch` 只修改 demo DTS：
原先啟用 TPM4，將 J1001 pin 33 的 GPIO_IO13 mux 為 TPM4_CH2，pad 設定沿用
NXP FRDM DTS 的 `0x02`。`0009` 已將風扇 PWM 改至 TPM5_CH2／pin 12。
目前未新增 `pwm-fan` consumer，也未設定 PWM 頻率、極性或風扇供電，
因此開機時不會由此設定自動讓風扇運轉。這些項目需依實際風扇規格及
ES001 RevA 線路確認。

現有 source 已有 `.patchdone` 且已含此 DTS/DTB 項目，因此新增補丁不會自動重套，
也不應刪除標記後重套所有補丁。新 source 依正常 patch 流程套用。
若其他已有 `.patchdone` 的環境缺少 PN5180 DTS，需先核對差異再個別套用。

現有 DTS 使用 `nxp,pn5180`，註解描述以 userspace/spidev bring-up；
保存 DTS 不等於加入 PN5180 Kernel driver、binding 或 userspace 應用。
其中外部 `gas_demo/nfc/bind-pn5180-spidev.sh` 與 README 引用未由這版整合。

`0010-arm64-dts-imx93-evk-pn5180-use-lpspi7.patch` 將 demo 的 PN5180
改至 LPSPI7，並把 ADP5585 的 EXP_SEL（R4）設為 output-low，以選擇
CAN2 通往板載收發器及 J1101 的路徑；PN5180 使用 J1001 的 IO04–07。
依
[NXP EVK 手冊的 J1001 腳位表](https://community.nxp.com/pwmxy87654/attachments/pwmxy87654/imx-processors/215888/1/MCIMX93EVKUM.pdf)，
接線須改為 CS=pin 7（GPIO_IO04／gpio2 offset 4）、
MISO=pin 29（GPIO_IO05）、MOSI=pin 31（GPIO_IO06）、SCK=pin 26
（GPIO_IO07）、BUSY=pin 27（GPIO_IO00／gpio2 offset 0）、RESET_N=pin 28
（GPIO_IO01／gpio2 offset 1）。DTS 指定 `spi7` alias；板端應核對
`/dev/spidev7.0` 與實際 GPIO chip，並同步更新外部 PN5180 應用的裝置路徑
及 BUSY／RESET_N offset。原來連至 J1001 pin 24／21／19／23／29／31
的線不能沿用舊定義。此改動只影響 demo DTB，尚未在實板驗證 NFC 通訊。
同一補丁也啟用 CAN2；SoC 端的 TX／RX pinmux 使用 GPIO_IO25／GPIO_IO27，
與 PN5180 的 pinmux 無衝突。外部 CAN 匯流排應接板上的 **J1101 CAN 接頭**，
經板載 U1101 收發器轉成差動訊號：pin 2 為 CAN_H、pin 3 為 CAN_L、
pin 4 為 GND；pin 1 是 5 V 供電。J1001 上的 GPIO_IO25／GPIO_IO27
不是 CAN_H／CAN_L 接線端。現有 Kernel 設定為 `CONFIG_CAN_FLEXCAN=m`，
板端仍須確認 FlexCAN module 載入、CAN 網路介面、收發器待機控制及實際通訊。

## Demo RS485 Modbus 接線（2026-10-28）

`0009-arm64-dts-imx93-evk-pn5180-add-rs485-uart8.patch` 在 demo DTB 啟用
LPUART8，將 J1001 pin 32／33／10 分別設為 TX／RX／RTS，並啟用 Linux
開機時的 RS485 半雙工方向控制。pin 33 原本供 TPM4_CH2 風扇 PWM 使用，
因此同一補丁改以 J1001 pin 12 的 GPIO_IO18／TPM5_CH2 輸出風扇 PWM。
風扇控制線須實際從 pin 33 改接至 pin 12；UART 預期為 `/dev/ttyLP7`，
仍需由板端確認。

UART 訊號須經合適 I/O 電壓的 RS485 收發器轉為 A／B 差動線。RTS_B 與
收發器 DE／RE 的有效極性、終端電阻、偏壓、接地與 Modbus 參數需依
實際模組及線路核對；目前未驗證板端通訊或風扇輸出。

## Git 管理與驗證

板型、defconfig、Kernel fragments、補丁、建置腳本與本文件由根目錄 Git 管理。
生成的 `.config`、`configs/.sdk.cfg`、source 與 build 仍維持 ignored。
`src/system/misnet/README.md` 記錄系統檔案的安裝規則，先不分類 dev/demo/production。

安全的設定流程檢查，在容器內執行：

```sh
python3 tools/tests/check_misnet_profiles.py
```

此檢查在暫存目錄驗證 Kconfig、Makefile 產物路徑、DTB 選擇與 boot script 原文，
使用 mock mkimage，不代表實際 boot.scr 格式、Kernel 或板端測試通過。
完整建置使用既有 `make linux` / `make boot` / `make all` 入口；
RootFS 重建、WIC 與燒錄仍須遵守根目錄 AGENTS.md 的資料與批准要求。

## 本版實際驗證（2026-10-13）

使用現有 `fbdebian:13-3a518191` Docker 映像，以 `--network=none` 與唯讀專案掛載
執行；所有測試輸出留在容器或主機暫存目錄，沒有改寫現有 `.config`、source 或 BSP output。

- 當時已執行 `python3 tools/tests/check_misnet_profiles.py`：三版設定、獨立產物路徑、
  DTB staging 選擇、boot script 原文、原有 EVK 行為與新板預設 dev 均通過。
- 已執行 `bash -n tools/flex-builder tools/flex-installer src/system/board_id.sh src/system/distroplatcfg`
  與 Python AST 語法檢查：通過。板型辨識函式的 MISNET / EVK 輸入結果符合預期。
- 已從快取 tarball 取出補丁涉及的原始檔，在暫存目錄依序執行
  `patch --batch -p1 -d <暫存目錄> -i <補丁絕對路徑>`：0001–0006 全部套用成功，
  新 DTS 與現有 PN5180 DTS 位元組相同。
- 已把現有 Kernel output `.config` 複製到容器 `/tmp/misnet-kout/.config`，執行
  `make -s -C <Kernel source> O=/tmp/misnet-kout ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig`，
  再執行同參數的 `make -j8 freescale/imx93-11x11-evk.dtb freescale/imx93-11x11-evk-pn5180.dtb`：
  兩個 DTB 編譯成功，大小分別為 64595 / 50998 bytes，未出現編譯警告。
- 已對兩種 DTB 執行 `bash tools/flex-builder distroscr`，再以實際 `mkimage -l` 與
  `dumpimage -T script -p 0` 檢查產物：可生成及辨識，內含正確的 DTB / Image 選擇。
- 已執行 `perl components_lsdk2606/linux/linux/scripts/checkpatch.pl --no-tree --no-signoff patch/linux/0006-arm64-dts-imx93-evk-pn5180-demo.patch`：
  **未通過**，6 errors 是保存的原有註解區塊使用空白縮排；5 warnings 包含
  4 個原有區塊註解格式與 1 個新增檔案的 MAINTAINERS 提示。
  這版保留現有 DTS 原文，不宣稱補丁符合全部 Kernel style。
- 已執行 `git diff --check`：通過。

未執行完整 `make linux`、U-Boot、RootFS、WIC、DT binding/schema 檢查或板端開機／
PN5180 通訊測試。局部 DTB 編譯成功不代表 ES001 RevA 硬體相容或 PN5180 可正常通訊。

## 跨板型輸出目錄驗證（2026-10-14）

已使用同一 Docker 映像與唯讀專案掛載，在暫存目錄執行
`python3 tools/tests/check_misnet_profiles.py`：MISNET 三個 profile、EVK、FRDM
的輸出目錄彼此不同，U-Boot 設定及 boot script 原文檢查通過。
已執行 `git diff --check`。未執行完整映像建置、WIC 或板端驗證。

## 無新版面板實驗的五組基線（2026-10-19）

此版只包含原始 FRDM、EVK，以及 MISNET dev、demo、production 的設定入口。
新版 Waveshare 7-DSI-TOUCH-C 的驅動、DTB 與診斷補丁不在啟用中的
`patch/linux/*.patch`；三種板型的這五組 defconfig 均未選用該面板設定。
先前面板實驗未納入此版提交。

本次重新執行：

- Docker 唯讀掛載專案，執行 `python3 tools/tests/check_misnet_profiles.py`：
  MISNET 三版與 EVK、FRDM 的設定、輸出目錄及 boot script 檢查通過。
- 使用獨立 `/tmp` Kernel output 與 `imx_v8_defconfig`，局部編譯
  `imx93-11x11-evk.dtb`、`imx93-11x11-evk-pn5180.dtb`、
  `imx93-11x11-frdm.dtb`：三個目標均成功。
- 在重播 0001–0006 補丁的暫存 Kernel source 上，執行
  `make imx_v8_defconfig misnet-demo.config`：設定合併成功。
- `bash -n` 檢查五個修改過的 Shell 檔案、`git diff --check` 均通過。

沒有執行完整 `make linux`、RootFS、WIC 或五種實機啟動驗證。

## MISNET dev／product DTS 基線（2026-11-03）

`misnet-dev` 使用 `imx93-11x11-misnet-es001-reva-dev.dtb`，
`misnet-production` 使用 `imx93-11x11-misnet-es001-reva-product.dtb`。
`0012` 補丁新增兩份獨立 DTS 與 Kbuild 項目；兩份 DTS 目前都直接 include
NXP 的 `imx93-11x11-evk.dts`。現有 Kernel source 有 `.patchdone`，
本次先以 `patch --dry-run` 確認，再單獨套用 `0012`，沒有重套舊補丁。

已在既有 `fbdebian:13-3a518191` 容器，以獨立 `/tmp` output 與
`imx_v8_defconfig` 局部編譯 EVK、dev、product 三個 DTB，並執行
`python3 tools/tests/check_misnet_profiles.py`：均通過。反編譯比對顯示
dev／product 的節點與屬性和 EVK 相同；EVK DTB 另含編譯產生的
`__symbols__` 與部分未被引用的 `phandle`，故檔案大小不同。
`checkpatch.pl` 對 `0012` 回報 0 error、1 個 MAINTAINERS 提示 warning；
`git diff --check` 通過。尚未執行完整 `make linux`、映像打包或實板開機驗證。

## Demo BME280 取代 AHT21B（2026-11-03）

沿用 J1001 pin 3（GPIO_IO02／LPI2C4 SDA）與 pin 5（GPIO_IO03／LPI2C4 SCL）、
100 kHz bus 設定，將感測器改為 I²C 位址 `0x76` 的 BME280。
`patch/linux/0013-arm64-dts-imx93-evk-pn5180-add-bme280.patch` 在 demo DTS
加入 `bosch,bme280`、`pressure@76`、`reg = <0x76>`，並把 AHT21B 專用的
pinctrl 名稱改為 BME280。感測器 VCC 已確認接 J1001 的 3.3 V 腳；DTS
以固定 `VRPi_3V3` regulator 表示該供電，供 `vddd-supply` 與 `vdda-supply`
引用。`configs/linux/misnet-demo.config` 啟用 Kernel 內建 `CONFIG_BMP280=y`，
此選項會選取 I²C 介面驅動；dev／production DTB 不受影響。

Bosch BME280 的 SDO 接 GND 才是 `0x76`，接 VDDIO 則為 `0x77`；CSB
需拉高以啟用 I²C。GY 模組的實際接法及晶片 ID 尚待板端核對。
既有 demo Kernel output `.config` 不會自動重套新的 fragment；本次已先備份，
再針對該 output 執行 `scripts/config -e BMP280` 與 `olddefconfig`。
與備份相比只新增 `CONFIG_BMP280=y`、`CONFIG_BMP280_I2C=y`、
`CONFIG_BMP280_SPI=y`；後者由目前啟用的 SPI master 自動選取。

已用獨立 `/tmp` output 和 `imx_v8_defconfig` 加 `CONFIG_BMP280=y` 局部編譯
demo DTB 與 `drivers/iio/pressure/`，三個 BMP280 相關物件均進入
`built-in.a`。反查 DTB 確認 `pressure@76`、`bosch,bme280`、3.3 V
供電及 `vddd-supply`／`vdda-supply`。`0013` 補丁反向與正向重播成功，
`checkpatch.pl` 為 0 error、0 warning，`git diff --check` 通過。
容器沒有 `dt-validate`；尚未執行完整 `make linux`、boot 打包或實板 probe。
