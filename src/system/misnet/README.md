# MISNET system integration

此目錄保存 MISNET 客製服務、腳本與系統設定。目前沿用 NXP 系統檔案，尚無新增服務。

先保持單層目錄；只有實際出現版本差異才增加子目錄。新增檔案需透過
`configs/debian/debian_post_config.sh` 或明確的 app install recipe 安裝；
此目錄不會自動複製到 RootFS。
