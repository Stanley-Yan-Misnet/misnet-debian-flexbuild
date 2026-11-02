# FRDM i.MX93：舊款 Waveshare 7 吋面板（P11 I²C4）

## 狀態與範圍

2026-11-02 記錄：使用者回報，上週以 NXP 原始
`imx93-11x11-frdm-waveshare-7inch-c-panel` 設定為基礎、將 I²C 改接
FRDM P11 後，舊款 7 吋面板已能正常工作。本文件記錄該已用過的接線版本；
本次提交未重新在板端量測或開機驗證。較早的新版
7-DSI-TOUCH-C 驅動／診斷實驗仍暫停，保存在
`patch/linux/paused-waveshare/`，不屬於此 DTB。

## 可重現的 DTS

`patch/linux/0011-arm64-dts-imx93-frdm-waveshare-7inch-c-p11-i2c4.patch`
新增獨立的 `imx93-11x11-frdm-waveshare-7inch-c-panel-p11.dtso`，
由 Kernel DTS Makefile 與原始 `imx93-11x11-frdm.dtb` 合成
`imx93-11x11-frdm-waveshare-7inch-c-panel-p11.dtb`。NXP 原有的
P12／LPI2C1 面板 DTB 保持可用。

新 overlay 保留 NXP 原始面板時序、DSI graph、橋接器 `0x45` 與
GT911 觸控 `0x14`。P11 pin 3／5 的 GPIO_IO02／GPIO_IO03 分別設定為
LPI2C4 SDA／SCL，I²C 設為 400 kHz；面板與橋接器由 `reg_vexp_5v`
供電，並使 P11 5V 在開機時維持啟用。這些是本版相對原始 overlay 的
接線差異，不引入暫停實驗中的新驅動或診斷設定。

## 再次建置與選用

在既有設定可被改寫的前提下，從專案根目錄執行 `make docker` 進入
Flexbuild 容器，然後使用：

```sh
make config CONFIG=configs/imx93frdm-waveshare-7inch-c-p11/defconfig
make linux
make boot
```

這組設定選用 FRDM board 與新的 P11 DTB；`make linux` 將 DTB 放入
Kernel staging，`make boot` 依 `CONFIG_LINUX_DTB` 產生指向該檔名的
boot script。切換設定前先保存目前 `.config` 與既有產物資訊；以上命令
會改寫設定並執行建置。建置映像不等於燒錄實體媒體。

既有 Kernel source 的 `.patchdone` 不會因 0011 補丁新增而重套；
若該 source 尚未含 P11 overlay，須先核對 source 與補丁，再在隔離
環境重建或個別套用。不要直接刪除 `.patchdone` 盲目重套整組補丁。

板端實際載入檔案仍應核對 U-Boot `fdtfile`、boot script、DTB 內容及
I²C／顯示／觸控 probe 記錄；本文件的正常工作狀態來自使用者回報。

## 本次檢查（2026-11-02）

- 已執行 0011 補丁的反向套用、正向 dry-run 與重播；重播後的 Makefile
  和 DT overlay 與現有 source 逐位元組相同。
- 已在 `fbdebian:13-3a518191` 容器中解析新設定：machine 為
  `imx93frdm`，選用 P11 DTB；原 FRDM 設定的 `CONFIG_LINUX_DTB`
  仍為空字串。
- 已在同一容器，以唯讀掛載 source、獨立 `/tmp` output 與
  `imx_v8_defconfig` 局部編譯 P11 合成 DTB，產物 62,240 bytes。
- 已執行 `scripts/checkpatch.pl --no-tree --no-signoff` 檢查 0011 補丁：
  0 errors、0 warnings。

未執行完整 `make linux`、`make boot`、DT binding/schema 檢查或本次
板端重測。局部 DTB 編譯成功不證明實際部署的 Image、DTB 與 boot script
彼此一致。
