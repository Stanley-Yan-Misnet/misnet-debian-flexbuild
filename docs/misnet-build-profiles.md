# MISNET ES001 RevA 建置設定

硬體名稱固定為 `misnet-imx93-es001-reva`，使用獨立板型 Kconfig symbol，
並歸入 i.MX93 / IMX family。依使用者指定，初版 BSP、U-Boot 與 Kernel 設定
沿用 `imx93evk` 基線；這不表示 EVK 的 pinmux、DDR 或周邊設定已在 ES001 RevA 驗證。
維持 LSDK 26.06、Debian 13 trixie、arm64 與 `lf-6.12.49-2.2.0`。

| 設定檔 | profile | Kernel fragment | DTB |
| --- | --- | --- | --- |
| `configs/misnet-dev/defconfig` | dev | `configs/linux/misnet-dev.config` | `imx93-11x11-evk.dtb` |
| `configs/misnet-demo/defconfig` | demo | `configs/linux/misnet-demo.config` | `imx93-11x11-evk-pn5180.dtb` |
| `configs/misnet-production/defconfig` | production | `configs/linux/misnet-production.config` | `imx93-11x11-evk.dtb` |

三組 defconfig 的 component selection 保存本次修改前 `.config` 的選項。
production 目前只代表獨立建置設定，尚未做套件裁減或出貨設定調整。
Kernel fragments 目前只有註解，沒有額外 Kernel 選項；DTB 由 `CONFIG_LINUX_DTB` 選擇。

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

## 保存現有 PN5180 DTS

本地 Kernel source 沒有 `.git`，不能確認其 commit 或全部既有差異。
快取 `dl/linux_lf-6.12.49-2.2.0.tar.gz` 中沒有 PN5180 DTS。
`patch/linux/0006-arm64-dts-imx93-evk-pn5180-demo.patch` 保存現有
`imx93-11x11-evk-pn5180.dts` 的完整內容，並在基線 DTS Makefile 註冊 DTB，
接續既有 0001–0005 補丁。沒有更改目前 source 的 DTS 或 Makefile。

現有 source 已有 `.patchdone` 且已含此 DTS/DTB 項目，因此新增補丁不會自動重套，
也不應刪除標記後重套所有補丁。新 source 依正常 patch 流程套用。
若其他已有 `.patchdone` 的環境缺少 PN5180 DTS，需先核對差異再個別套用。

現有 DTS 使用 `nxp,pn5180`，註解描述以 userspace/spidev bring-up；
保存 DTS 不等於加入 PN5180 Kernel driver、binding 或 userspace 應用。
其中外部 `gas_demo/nfc/bind-pn5180-spidev.sh` 與 README 引用未由這版整合。

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
