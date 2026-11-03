# i.MX93 Debian BSP 開發與建置參考

本文件於 2026-10-07 依本機 repository 分析。下列建置指令已核對腳本／Kbuild 定義，本次未執行 BSP 編譯、Docker 啟動或板端部署。現有產物僅證明檔案存在，不能作為本次測試 PASS 的證據。日後設定或版本改變時須重新核對。

## 1. 已確認基線與目錄

| 項目 | 本機證據與結果 |
| --- | --- |
| Flexbuild Git | branch `misnet-lsdk-26.06`；HEAD `fde434ad2a29386e6e97dec0c072308048951de5`；tag `LSDK-26.06_DEBIAN-13_LF-6.12.49` |
| Remotes | `nxp`: `https://github.com/nxp/flexbuild`；`origin`: `git@github.com:misnet/flexbuild.git` |
| 版本 | 根 `Makefile`: `lsdk2606`、Debian 13 / trixie、`DEFAULT_REPO_TAG=lf-6.12.49-2.2.0` |
| 目標 | `.config`: `CONFIG_SOC_IMX93EVK=y`、`CONFIG_MACHINE_NAME="imx93evk"`、IMX、8 jobs；OP-TEE 未啟用 |
| Kernel | `components_lsdk2606/linux/linux`，Makefile 版本 6.12.49；現有 output `include/config/kernel.release` 也是 `6.12.49` |
| Kernel 來源 | `configs/sdk.yml` 及生成的 `.sdk.cfg`: `https://github.com/nxp-imx/linux-imx.git`，無個別版本覆寫，依 downloader 使用預設 ref |
| U-Boot | `components_lsdk2606/bsp/uboot`，Makefile 版本 2025.04；來源 `https://github.com/nxp-imx/uboot-imx.git`，亦使用預設 ref |
| Git 限制 | Kernel、U-Boot 皆無 `.git`；`CONFIG_KEEP_GIT` 未啟用。不能核實本地 commit／checkout tag 或判定其 source 完全未改。`dl/` 有兩者 `lf-6.12.49-2.2.0` tarball，未做全 source 比對 |
| U-Boot 板型 | `configs/board/imx93evk.conf`: `imx93_11x11_evk_defconfig`，ATF `imx93` |

主要管理位置：

- `Makefile`、`Kconfig`：頂層命令、版本、路徑與功能選項。
- `configs/board/`：板型選單、各板 `.conf`、`IMX_boot.txt`；`configs/linux/`：Kernel fragments、ITS；`configs/debian/`：RootFS 套件與後處理。
- `configs/sdk.yml`：元件來源；可用 `CONFIG_CUSTOM_SDK_CONFIG` 指向 `configs/` 下的自訂 YAML。`tools/parse_yaml.py` 產生 `.sdk.cfg`，不直接修改生成檔。
- `src/linux/`、`src/bsp/`、`src/apps/`：Kernel/modules、韌體及各類應用的 recipes；`src/system/`：板端服務與系統檔案。
- `include/`：download、patch、頂層 helper targets；`tools/`：Docker、RootFS、boot、image 與部署工具。
- `patch/<component>/`：可追蹤補丁；`components_lsdk2606/`：下載／解壓的 source；`build_lsdk2606/`：output、staging、RootFS 與映像；`dl/`：下載快取；`logs/`：日誌與 locks。

這不是 Yocto layer 專案；本次沒有辨識到獨立的客製硬體板型設定。不要直接套用其他專案的 machine 名稱或 BitBake 指令。

## 2. Docker 與設定入口

依據：`Makefile`、`include/func.mk`、`tools/flex-builder` 的 `flexbuild_launch_docker`、`docker/debian/{Dockerfile,Makefile}`。

```sh
# 主機，Flexbuild 根目錄
make docker
# 以下在該容器的 Flexbuild 根目錄執行
make help
make list
# 僅首次或已確認要重設設定時擇一
make imx93evk_defconfig
make menuconfig
make config CONFIG=<已存在的受追蹤設定檔>
```

- 實際預設是 Debian trixie image，含 arm64 GCC/G++ cross compiler、QEMU/binfmt、Kconfig 等依賴；`docker/ubuntu/` 存在但不由此入口使用。
- image 名為 `fbdebian:13-<Dockerfile MD5 前8碼>`，container 名含使用者、版本、Dockerfile hash 與工作路徑 hash。不存在則 build/run，已停止則 start/attach，執行中則 exec bash。
- 容器使用 `--privileged --net=host`，掛載使用者 HOME、專案原路徑、`/lib/modules`、`/dev`，工作目錄是專案根目錄。這些掛載會影響主機，尤其不能自行執行燒錄命令。
- 除 `docker/help/list` 外，頂層 Makefile 要求 `/.dockerenv`。註解與條件不一致時以條件為準。`make docker` wrapper 有 `|| true`，需看實際訊息，不能只依 exit code 判定成功。
- 設定入口會跑 `kconfig_hooks.py`、`parse-sdk-config`、`host-dep`，可能下載／安裝工具。手改來源 YAML 後可用 `make parse-sdk-config` 重生 `.sdk.cfg`。
- `make config` 的 parser 先跳過 `#` 行，因此保存明確停用選項時使用 `CONFIG_FOO=n`，不要依賴 `# CONFIG_FOO is not set` 被該入口重現。

## 3. Kernel、DTB 與 modules

依據：`src/linux/linux.mk`、`src/linux/Makefile`、本地 Kernel `Makefile`、`arch/arm64/Makefile` 及 DTS Makefile。

以下 shell 變數僅供本章範例，從容器內專案根目錄設定；版本或平台改變後需更新：

```sh
FB_ROOT="$PWD"
KSRC="$FB_ROOT/components_lsdk2606/linux/linux"
KOUT="$FB_ROOT/build_lsdk2606/linux/linux/arm64/IMX/output/lf-6.12.49-2.2.0"
KSTAGE="$FB_ROOT/build_lsdk2606/linux/linux/arm64/IMX"
APP_STAGE="$FB_ROOT/build_lsdk2606/apps/apps_debian_imx93evk"
RFS="$FB_ROOT/build_lsdk2606/rfs/rootfs_lsdk2606_debian_imx93evk"
```

### 完整 Kernel recipe 與設定

```sh
make dl-kernel          # dl-linux 為別名；下載、patch、首次 config
make linux-menuconfig  # kernel-menuconfig 為別名
make linux
make linux-headers
make linux-modules
```

`dl-kernel` 採 `imx_v8_defconfig`，並將 `CONFIG_LINUX_EXTRA_CONFIG` 指定的 `configs/linux/` 檔案複製至 source `arch/arm64/configs/`。只有 output `.config` 不存在才執行初始 config targets。新增 fragment 不會自動改既有 config；保存差異並審查後再決定如何套用，不能任意刪 build 目錄。

`make linux` 依序執行下載／patch／config、Kbuild `all`、`zinstall`、複製 `Image*`、`modules`、`modules_install INSTALL_MOD_PATH=<APP_STAGE>`、移除 staging 中該 release 的 `build` link，並複製 `freescale/imx*.dtb` 到 KSTAGE。這不是單純 Image target，也不是只有 imx93 的 DTB。`build_lsdk2606/linux/kernel` 會建立為 `linux` symlink。

`make linux-headers` 安裝 UAPI headers 到 `<APP_STAGE>/usr/include`。`make linux-modules` 聚合所選外部 modules；目前設定啟用 `cryptodev_linux` 與 `nxp_wlan_bt`。`make linux-deb` 存在，但會先建置 linux，且 recipe 會修改 Kernel `scripts/package/mkdebian`，不是無副作用的打包檢查。

### 只編譯 DTB

EVK 範例來源為 `arch/arm64/boot/dts/freescale/imx93-11x11-evk.dts`，共用 SoC 定義及 pin function 在同目錄。先檢查 include 鏈、binding 及原理圖，再執行：

```sh
# 前提：KSRC/KOUT 已初始化且版本、config 正確
make -C "$KSRC" O="$KOUT" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- freescale/imx93-11x11-evk.dtb
# 需要全部已配置的 DTB 時
make -C "$KSRC" O="$KOUT" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- dtbs
# 選用：需要已安裝相容的 dtschema 等工具，新增 binding 時也檢查 dt_binding_check
make -C "$KSRC" O="$KOUT" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- dtbs_check
# 經確認後同步本機 staging，再重新產生 boot archive
cp "$KOUT/arch/arm64/boot/dts/freescale/imx93-11x11-evk.dtb" "$KSTAGE/"
make boot
```

根目錄沒有單獨 `dtbs` wrapper。局部編譯不會自動複製到 KSTAGE；不要拿舊 staging 打包。`dtbs_check` 是額外驗證，不保證現有整棵 vendor tree 無警告，應區分既有與新增問題。

### Image／Driver／Module 局部工作

```sh
make -C "$KSRC" O="$KOUT" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j8 Image
make -C "$KSRC" O="$KOUT" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j8 modules
make -C "$KSRC" O="$KOUT" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- modules_install INSTALL_MOD_PATH="$APP_STAGE"
```

樹內 driver：修改對應 `drivers/` 或 subsystem，接入其 Kconfig/Makefile；`=y` 需更新 Image，`=m` 需更新 `.ko`。外部 module：參考 `src/linux/cryptodev_linux.mk` 的 Kernel source、O= 與 staging 傳遞，並接入 `src/linux/{Kconfig,Makefile}`。符合 Kbuild 的新外部 module 可用以下形式，`MODULE_SRC` 必須先設為真實、含 Kbuild/Makefile 的絕對路徑：

```sh
make -C "$KSRC" O="$KOUT" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- M="$MODULE_SRC" modules
make -C "$KSRC" O="$KOUT" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- M="$MODULE_SRC" modules_install INSTALL_MOD_PATH="$APP_STAGE"
```

需要正確 `.config`、generated headers，使用 symbol versioning 時亦需完整建置的 `Module.symvers`；`modules_prepare` 本身不代替完整符號產物。上述 Image 局部命令不執行 `zinstall`／staging，正式 boot 打包前用 `make linux` 同步整套產物，或明確處理所有受影響檔案，避免混用新舊 release。

### 各產物的部署與驗證責任

| 產物 | 本機安裝／打包 | 板端驗證（部署需遵守批准規則） |
| --- | --- | --- |
| Image | KOUT 的 `arch/arm64/boot/Image` → KSTAGE → `make boot` | 核對 boot script 的 `${image}`、載入媒體／分割區、hash 與 `uname -r`／boot log |
| DTB | KOUT 的 `arch/arm64/boot/dts/freescale/*.dtb` → KSTAGE → `make boot` | 核對 `${fdtfile}`、DT model/compatible、實際裝置節點與 probe log |
| Module | APP_STAGE 的 `lib/modules/<kernel.release>/` → `make merge-apps` → `make packrfs` | 比對 `uname -r`、`modinfo` vermagic、依賴索引與 `modprobe`/`dmesg`；需時於目標執行 `depmod -a <release>` |

`configs/board/IMX_boot.txt` 使用 U-Boot 的 `image/fdtfile` 載入，不從檔名自動辨識板型；預設 boot partition 1、root partition 2、mmcdev 1，但 environment 可覆寫。U-Boot defconfig 預設 `imx93-11x11-evk.dtb`，不代表實板目前 environment 必然相同。板端掛載點及媒體待確認，故此處不提供猜測的 scp／dd／燒錄命令。

## 4. U-Boot、RootFS 與完整 image

```sh
make uboot       # u-boot 為別名
make flash.bin   # 建立本機 i.MX 複合 boot image，並非燒錄
make rfs
make apps
make merge-apps
make boot
make packrfs
# 或既有設定下執行完整流程
make all
# 在 boot/rootfs archive 與 flash.bin 都備妥後，另建磁碟映像
make wic
```

- U-Boot recipe 每次套 `imx93_11x11_evk_defconfig` 再建置；output 為 `build_lsdk2606/bsp/u-boot/imx93evk/output/imx93_11x11_evk_defconfig/`。暫時改 output `.config` 可能被覆蓋，長期設定需保存為 source patch。
- `flash.bin` 依賴 uboot、atf、firmware_imx、mcore_demo；i.MX93 recipe 加入 SPL/U-Boot、ATF BL31、ELE AHAB 與 DDR firmware，呼叫 imx-mkimage `SOC=iMX93 flash_singleboot`，輸出 `images/imx93evk-sd-flash.bin`。它會清理 imx-mkimage 生成檔；先保存對該目錄的客製修改。建置不等於允許寫入 boot media。
- `make rfs` → `tools/distro_debian` → `configs/debian/debian_server_arm64.sh`，使用 **mmdebstrap** 建立 arm64 trixie。i.MX93 使用 `extra_packages_list` 的 `ls_pkgs` 與 `imx_pkgs`，之後執行 `debian_post_config.sh`。一般流程將套件傳入 mmdebstrap；另有 gradual 分支用 chroot apt-get。
- RootFS `etc/buildinfo` 存在就直接退出，不會因套件清單或 service 修改自動更新；不存在時會 `rm -rf` 該 RootFS。重建既有資料須先批准；本次不刪標記或執行重建。
- `make merge-apps` 複製 APP_STAGE 到 RFS 並在 chroot 執行 ldconfig；`make packrfs` 卸載相關 mount 後 tar+zstd 打包。不要平行操作同一 RootFS。
- `make all` 順序為 rfs → linux → linux-headers → linux-modules → apps → flash.bin（IMX）→ boot → merge-apps → packrfs；不包括 wic。
- `make wic` 呼叫 `flex-installer -i mkwic`，使用檔案及 loop device 建立分割區／檔案系統，會覆寫同名 image；本次未執行。它與把 image 寫入實體 SD/eMMC 不同，使用前仍須檢查 loop backing file 與現有資料。

### 產物位置

以下皆相對 `build_lsdk2606/`；版本／板型／時間不同時檔名隨之變化：

| 類別 | 路徑 |
| --- | --- |
| Kernel output/config | `linux/linux/arm64/IMX/output/lf-6.12.49-2.2.0/`（含 `.config`、`vmlinux`、`Module.symvers`） |
| Kernel/DTB staging | `linux/linux/arm64/IMX/`（`Image*`、`imx*.dtb`、`config-<release>`、`vmlinuz-<release>`） |
| 應用與 module staging | `apps/apps_debian_imx93evk/` |
| RootFS | `rfs/rootfs_lsdk2606_debian_imx93evk/` |
| Boot archive | `images/boot_IMX_arm64_lts_6.12.49.tar.zst` → 時間戳版本；同名無副檔名目錄保存內容 |
| RootFS archive | `images/rootfs_lsdk2606_debian_imx93evk.tar.zst` → 時間戳版本 |
| Boot firmware | `images/imx93evk-sd-flash.bin` |
| 應用 deb | `make packapps` → `images/nxp_apps_debian_lsdk2606_imx93evk.deb` → 時間戳版本 |
| WIC | `make wic` 預期 `images/rootfs_lsdk2606_debian_imx93evk.wic.zst`（本次目錄未見） |

## 5. 應用程式與客製 BSP 保存

現有 C/C++ recipes 使用 `aarch64-linux-gnu-gcc/g++ --sysroot=<RFS>`，並加入 APP_STAGE headers/libs。參考 `src/apps/networking/tsntool.mk`（Make）與 `src/apps/gopoint/imx_camera_rotation.mk`（CMake）；不要把不同元件的專用 CMake 參數套用到所有程式。

```sh
make show-enabled-apps
make list-all-apps
make tsntool      # 目前設定已有啟用的實際 C 元件範例
make apps        # 全部所選元件，含相依建置
make merge-apps
make packrfs
make packapps    # 選用：封裝整個應用 staging，不是每個程式各一個 deb
```

新 C/C++ 程式接入現有類別 Makefile、Kconfig、recipe 與必要的 `sdk.yml` 來源；依其原生 Make/CMake/Meson system 編譯並安裝至 APP_STAGE，再合併／打包。Python 與 Shell 亦用 recipe 保存程式、依賴、權限與服務，不直接在生成 RootFS 留下唯一版本。部署透過已確認的 RootFS／deb／目標目錄流程；目標板連線、服務重啟與實際路徑須先核對，不臆造通用 deploy target。

元件是 downloader 管理的 archive／個別 repo，不是根 repo 的 Git submodule。`CONFIG_KEEP_GIT=y` 僅影響需要下載時的流程；既有 tar cache 與已解壓 source 會繼續使用。要追蹤既有修改，先備份並與已知基線比較，再以可追蹤 patch 或固定 commit 的客製來源保存，不直接刪除 source 重抓。

`include/patch_apply.mk` 依 `patch/<name>/*.patch` 檔名順序套用：有 `.git` 用 `git am`，否則 `patch -p1`，並寫入 `.patchdone`。新增／更新 patch 的重現測試宜用獨立乾淨 tree；不要在有使用者修改的 tree 強制重套。

新增硬體板型需一併檢查 `configs/board/Kconfig`、根 `Kconfig` 的 SoC family 與 `MACHINE_NAME` 對應、板 `.conf`、Kernel/U-Boot DTS/config、`src/system/board_id.sh`、boot script 與所需 image recipe。維持 NXP 共用定義，客製內容使用清楚板名；不能只新增 `.conf` 就假設全流程支援。

## 6. 待確認與驗證紀錄原則

- 實板 revision、DDR/PMIC、外接周邊、原理圖、目前開機媒體、U-Boot environment、DTB、Kernel release 及可用復原流程。
- Kernel/U-Boot 目前 source 的精確 commit、既有手動修改與 patch 完整性；客製 upstream／branch 保存策略。
- Docker 實際 image、compiler 版本、依賴可用性；本次僅核對 Dockerfile／launcher，未啟動容器。
- 現有 boot/rootfs/flash 產物與目前 source 是否一致；未重新建置、未確認可啟動。
- 本次新增文件後應執行 `git diff --check` 及未追蹤新檔的 whitespace／連結檢查；不以文件檢查取代 Kernel、RootFS 或實機測試。

根 `AGENTS.md` 保留跨任務規則，本文件保存詳細證據與操作。此安排依 [OpenAI 官方 AGENTS.md 指引](https://learn.chatgpt.com/docs/agent-configuration/agents-md)：專案指令由根目錄向工作子目錄累積、同層 override 優先，並受合併大小限制；新增文件後可在新 Codex session 確認載入。
