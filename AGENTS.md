# NXP Debian Flexbuild 開發規範

## 適用範圍與依據

- 本文件適用於本專案的 BSP、Kernel、Device Tree、Driver、應用程式與系統整合。修改子目錄前，另讀其適用的 `AGENTS.md`／`AGENTS.override.md`。
- 以實際原始碼、設定及腳本為準。建置前閱讀 [BSP 開發與建置參考](docs/bsp-development.md) 的相關章節；該文件記錄指令來源、產物及待確認事項，不代表指令已通過實機測試。
- 已查核基線：LSDK 26.06、Debian 13 trixie、arm64、`imx93evk`；預設來源 ref 為 `lf-6.12.49-2.2.0`。每次仍須核對，不自行升版或更換板型。

## 開始工作與 Git

- 先讀根目錄 `git status --short`、`git diff`、`.config`、`configs/board/<machine>.conf`，確認硬體型號／revision、任務範圍與既有修改。涉及 Kernel 時確認原始碼版本、實際 output `.config`、`kernel.release` 及板端版本（可連線時）。
- 根目錄 Git 不追蹤 `components_lsdk*`、`build_lsdk*`、`.config*`、`configs/.sdk.cfg`。不能用根目錄乾淨來推斷 Kernel／U-Boot 沒有修改。先確認元件自己的 `.git` 與 `git rev-parse --show-toplevel`，避免誤讀父層 Git。
- 目前 Kernel／U-Boot 是沒有 `.git` 的 source tree。保留其 NXP 來源 URL、ref、patch 順序；無法確認 commit 或既有差異時明說，不虛構 branch／tag checkout 狀態。
- 長期修改須留在可追蹤的 `patch/<component>/`、`configs/`、`src/`，或有明確版本紀錄的客製 source repository；不得只留在 ignored source、output `.config` 或 RootFS。保留原始 BSP tag 與版本資訊。
- 不任意 `git reset`、`git clean`、restore／checkout 覆蓋未提交內容；未經確認不切換 Kernel tag／branch。保留使用者的無關變更，不為修一項功能而重構其他模組。
- Patch 由 `.patchdone` 控制；新增 patch 不會自動重套。先確認既有套用狀態，不直接刪標記後盲目重套。啟用 `CONFIG_KEEP_GIT` 也不會替現有 source 或快取補回 `.git`。

## 建置入口

- 主機從根目錄執行 `make docker`；容器內使用 Makefile 入口。`source setup.env` 已棄用。不要假設主機有相同工具鏈，亦不要繞過 Docker 檢查。
- 新設定可用 `make imx93evk_defconfig`、`make menuconfig` 或 `make config CONFIG=<已追蹤設定檔>`；它們會改寫設定並執行依賴準備。已有設定時不要為了建置而重新套用預設。
- 已核對 targets：`make linux`、`make linux-menuconfig`、`make linux-headers`、`make linux-modules`、`make uboot`、`make flash.bin`、`make rfs`、`make apps`、`make boot`、`make merge-apps`、`make packrfs`、`make packapps`、`make all`、`make wic`。詳細前提／副作用見參考文件；不要猜測 `make dtbs` 等根目錄未定義 target。
- `make linux` 包含 Image、DTB、樹內 modules 與 staging；`make linux-modules` 是所選外部 modules。局部 DTB／Driver 使用參考文件中已核對的 Kernel Kbuild 指令。
- `make all` 不含 WIC。`make rfs` 遇 `etc/buildinfo` 會跳過，否則會刪除既有 RootFS 後重建。執行前確認資料與授權；不靠刪除 buildinfo 強制重建。
- 不把 `make -n` 當成絕對無副作用的檢查：本專案有 parse-time `$(shell ...)` 和 recursive make。

## Kernel、Device Tree 與 Driver

- 優先沿用 NXP driver、DTS/DTSI、subsystem 與既有 driver model。新增 driver 同步處理 Kconfig、Makefile、相依設定、probe/remove、錯誤清理及需要的 PM；遵循該 Kernel 的 `Documentation/process/coding-style.rst`。
- DTS 修改先查 include 鏈、`Documentation/devicetree/bindings/`、compatible、pinctrl／pinmux、clock、reset、regulator、interrupt 及硬體原理圖。新板優先建立板級 DTS，避免任意更動共用 SoC DTSI。
- Kernel 設定以 `imx_v8_defconfig` 加受追蹤的 `configs/linux/` fragment 管理；`linux-menuconfig` 只改 output 設定，需另保存可重現變更。既有 output `.config` 不會自動重套新的 fragment。
- 分別確認 Image、DTB、module 的 output、staging、打包及板端實際載入位置。單獨 Kbuild 不會自動更新 Flexbuild staging。Module 須匹配目標 `kernel.release`、config、符號／vermagic；不可拿 UAPI headers 代替完整 Kernel build tree。
- 修改後檢查 diff、相關編譯錯誤及新增警告；依變更執行 `scripts/checkpatch.pl`、DT binding／DTB 檢查及必要測試，說明缺少的工具或硬體。編譯成功不等於 probe、通訊或開機成功。

## 應用程式與系統整合

- C/C++、Python、Shell 沿用既有 `src/apps/<category>/*.mk`、Kconfig 與安裝方式。C/C++ 使用 arm64 工具鏈及目標 RootFS sysroot；避免混用 host headers／libraries。新 recipe／套件來源／選項須接入現有聚合 Makefile。
- Debian 套件在 `configs/debian/extra_packages_list` 與相關建置腳本管理；systemd、udev、板型辨識等檔案在 `src/system/`，透過 `debian_post_config.sh` 或明確的 app install recipe 安裝，不只手改生成的 RootFS。
- Python／Shell 使用既有 interpreter、依賴與風格，執行適當的語法檢查及既有測試。systemd 驗證 unit、安裝路徑、依賴、啟用方式與板端 journal；不要在開發主機啟用目標板服務。
- I2C、SPI、UART、GPIO、CAN、Ethernet 先確認 bus／pin／電壓／位址與驅動介面；相機先確認 media graph、V4L2 format、sensor/CSI 與 GStreamer plugin/caps。不要用盲目 bus write、pin 切換或服務重啟作為無風險測試。
- 測試依影響範圍選擇編譯、單元／語法檢查與板端整合驗證；無硬體時明列尚未驗證項目。

## 必須明確批准的操作

- 燒錄 eMMC、SD Card、SPI Flash；更新 Bootloader／U-Boot Environment；覆寫 partition table；刪除大量 source／build 資料；其他可能使目標板無法啟動的操作，執行前必須取得使用者明確批准。
- 批准前列明目標裝置、映像版本、影響範圍及復原方式。Docker 使用 privileged 並掛載 `/dev`，不構成免除批准的理由。`distclean`、大範圍 `clean-*` 及重建既有 RootFS 同樣先檢查上述要求。
- 一般分析、source 修改與安全的局部編譯按正常流程執行。建置映像檔與寫入實體媒體分開；WIC 會使用 loop device，需核對 backing file，不能誤操作實體磁碟。

## 每次交付

說明：修改檔案清單、目的與主要內容、實際使用的編譯／測試指令、結果、尚未驗證項目及風險。清楚區分「腳本已核對」「已執行」「未執行」；未執行不得宣稱 PASS。僅文件修改不需完整 BSP rebuild，但須檢查 diff 與文件中的路徑／指令依據。
