# FRDM demo：PN5180 接在 P11 40-pin

這個接法只對 `configs/imx93frdm-demo/defconfig` 指定的
`imx93-11x11-frdm-waveshare-7inch-c-panel-p11.dtb` 生效。原始 FRDM DTS、
MISNET 的 DTS 與 U-Boot 設定不變。舊款 Waveshare 面板使用 P11 的
5 V、pin 3/5 的 I²C4 與 GND。先前接線紀錄是面板 5 V 接 pin 2；
使用者後續補充 pin 4 也被面板占用，接線前須按實物確認兩腳的空間。

## 接線

| PN5180 模組 | FRDM P11 實體 pin | SoC 訊號／用途 |
| --- | ---: | --- |
| NSS／CS | 24 | GPIO_IO08，LPSPI3 CS0（GPIO2 offset 8） |
| MISO | 21 | GPIO_IO09，LPSPI3 SIN |
| MOSI | 19 | GPIO_IO10，LPSPI3 SOUT |
| SCK | 23 | GPIO_IO11，LPSPI3 SCK |
| BUSY | 27 | GPIO_IO00，GPIO2 offset 0，輸入 |
| RESET_N | 28 | GPIO_IO01，GPIO2 offset 1，輸出 |
| 模組 3.3 V 輸入 | 17 | P11 的 `VRPi_3V3` |
| 模組 5 V 輸入 | 2 或 4；若均被占用則分接 | P11 的同一路 `VRPi_5V` |
| GND | 20 或 25 | GND |

依使用者提供的模組需求，同時接入 3.3 V 與 5 V 兩路電源。
P11 pin 2 與 pin 4 都是 5 V。若 pin 4 被面板占用而 pin 2 可接，
模組改接 pin 2；若兩腳都被占用，須從同一 5 V 電源線經合適的分接端子
分給面板和模組，不能把線硬塞進已占用的接點。
3.3 V 選 pin 17，與 SPI、BUSY、RESET_N 腳位接近。
P11 的 `VRPi_3V3` 與 `VRPi_5V` 分別由 DTS 中的 `reg_vexp_3v3`、
`reg_vexp_5v` 在開機時啟用並保持供電。
不要將 5 V 接到 3.3 V 邏輯腳；接線前須核對模組上的 3.3 V 腳
確實是**電源輸入**，並確認兩路電源與面板合計電流未超過板子供電能力。
PN5180 晶片的供電與 RF 驅動電源規格不同，模組的實際接法以其原理圖為準。
本接法使用 BUSY 與 RESET_N 兩條 GPIO，IRQ 暫未接。

P11 腳號依 [NXP FRDM-IMX93 使用手冊的 Table 22](https://community.nxp.com/pwmxy87654/attachments/pwmxy87654/imx-processors/240994/1/UM12181.pdf)。
PN5180 的 SPI、BUSY 與 RESET_N 定義依
[NXP PN5180 產品資料](https://www.nxp.com/products/PN5180) 與
[AN12650](https://www.nxp.com/docs/en/application-note/AN12650.pdf)。

## DTS 與建置

`patch/linux/0014-arm64-dts-imx93-frdm-demo-add-pn5180-p11.patch` 修改 P11
overlay：沿用基底 FRDM DTS 的 LPSPI3 與 GPIO CS，把 GPIO2 offset 0/1
指定給 BUSY／RESET_N，並命名為 `pn5180-busy`／
`pn5180-reset`。P11 的 `VEXP_3V3` 會在開機啟用並保持供電；
原本供應 Waveshare 面板的 `VEXP_5V` 已設定為開機啟用並保持供電，
PN5180 模組從 P11 pin 2／4 或其 5 V 分接線共用這一路。
FRDM 基底 DTS 的 `pinctrl-assert-gpios` 會啟用通往板載無線模組的
SPI3 電平轉換器；[NXP 工程師建議](https://community.nxp.com/t5/Other-NXP-Products/SPI-read-imx93/m-p/2132049)
外接 SPI 裝置時移除該設定。合成 overlay 的 `/delete-property/` 未能從
最終 DTB 移除基底屬性，因此本版改用 `GPIO_ACTIVE_LOW` 讓同一控制腳
輸出物理低電位，關閉該電平轉換器。使用板載無線模組的 SPI3 路徑時
須另行驗證；這項調整尚未經 FRDM 實板測試。
SPI 裝置的 `compatible` 由基底的測試裝置 `lwn,bk4` 改為
`nxp,pn5180`，初始最大速度 1 MHz。這個 DTS 沒有 PN5180 Kernel driver；
要在 userspace 讀卡，仍須用現有 PN5180 userspace 程式將該 SPI 裝置
綁定到 `spidev`，並透過 GPIO character device 控制 BUSY／RESET_N。
overlay 也指定 `spi3` alias 指向 LPSPI3（`/soc@0/bus@42000000/spi@42550000`）。
因此載入**新版** DTB 後，PN5180 的 SPI 裝置應為 `spi3.0`；
綁定 spidev 後，應用程式開啟 `/dev/spidev3.0`。

板端以 root shell 執行以下命令，確認裝置存在並綁定 spidev：

```sh
cat /proc/device-tree/aliases/spi3
ls /sys/bus/spi/devices/spi3.0
echo spidev > /sys/bus/spi/devices/spi3.0/driver_override
echo spi3.0 > /sys/bus/spi/drivers/spidev/bind
ls -l /dev/spidev3.0
```

此 sysfs 綁定只在本次開機有效；正式使用時需由 PN5180 應用或啟動腳本
重做。`imx_v8_defconfig` 已設 `CONFIG_SPI_SPIDEV=y`。BUSY 與 RESET_N
分別是 GPIO2 offset 0/1，line 名稱為 `pn5180-busy`／`pn5180-reset`；
實際 `/dev/gpiochipN` 編號仍需在板端查 `gpioinfo`。

在 Flexbuild Docker 內，已有 FRDM demo 設定時可執行 `make linux`。
若需重新選擇此版本，先確認目前 `.config` 可改寫，再執行：

```sh
make config CONFIG=configs/imx93frdm-demo/defconfig
make linux
```

板端更新時，先用 `findmnt /boot` 確認 `/boot` 是實際開機分割區，再將
新 DTB 覆蓋同名的 `/boot/imx93-11x11-frdm-waveshare-7inch-c-panel-p11.dtb`。
現有 `boot.scr` 已選用這個檔名，無須改 U-Boot `fdtfile`。更新後重開機，
檢查 `gpioinfo` 中的兩條命名 GPIO、SPI 裝置的 sysfs 路徑、面板顯示／觸控，
最後以 PN5180 應用讀取實卡。單獨換 DTB 不會更新既有 WIC 映像。

新增 patch 不會使已有 `.patchdone` 的 source 自動重套；若在另一份既有
source 建置，須先核對 patch 是否已套用。此版局部 DTB 編譯結果只證明
DTS 能合成，尚未在 FRDM 實板驗證 PN5180 的 SPI 波形或讀卡功能。
