#!/usr/bin/env python3
"""Check profiles in a temporary tree; run inside the Flexbuild container."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile

import kconfiglib


def run(args, cwd, env=None):
    result = subprocess.run(args, cwd=cwd, env=env, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return result.stdout


def main():
    root = Path(__file__).resolve().parents[2]
    with tempfile.TemporaryDirectory(prefix="misnet-profiles-") as directory:
        work = Path(directory)
        for name in ("configs", "include", "src", "tools"):
            shutil.copytree(root / name, work / name)
        shutil.copy(root / "Kconfig", work)
        shutil.copy(root / "Makefile", work)
        with (work / "Makefile").open("a") as stream:
            stream.write('\n.PHONY: profile-vars\nprofile-vars:\n'
                         '\t@echo "$(MACHINE)|$(SOCFAMILY)|$(FBOUTDIR)|'
                         '$(DTBSTR)|$(KOUTDIR)|$(DESTDIR)|$(RFSDIR)|$(uboot_cfg)"\n')
        mockbin = work / "mockbin"
        mockbin.mkdir()
        mkimage = mockbin / "mkimage"
        mkimage.write_text('#!/bin/bash\nset -eu\n'
                          'while [ "$1" != -d ]; do shift; done\n'
                          'cp "$2" "$3"\n')
        mkimage.chmod(0o755)
        os.chdir(work)
        outputs = set()
        for profile in ("dev", "demo", "production"):
            run(["python3", "tools/gen_config_from_file.py", "Kconfig",
                 f"configs/misnet-{profile}/defconfig"], work)
            run(["python3", "tools/kconfig_hooks.py"], work)
            conf = kconfiglib.Kconfig("Kconfig")
            conf.load_config(".config")
            assert conf.syms["SOC_IMX93"].str_value == "y"
            assert conf.syms["MISNET_PROFILE"].str_value == profile
            assert conf.syms["LINUX_EXTRA_CONFIG"].str_value == f"misnet-{profile}.config"
            dtb = ("imx93-11x11-evk-pn5180.dtb" if profile == "demo"
                   else "imx93-11x11-evk.dtb")
            values = run(["make", "-s", "profile-vars"], work).strip().split("|")
            machine, family, output, selected, kout, apps, rfs, uboot = values
            assert machine == "misnet-imx93-es001-reva"
            assert family == "IMX" and selected == dtb
            assert output.endswith(f"/{machine}/{profile}")
            assert all(path.startswith(output + "/") for path in (kout, apps, rfs))
            assert uboot == "imx93_11x11_evk_defconfig"
            outputs.add(output)
            env = dict(os.environ, FBDIR=str(work), FBOUTDIR=output,
                       SOCFAMILY=family, LINUX_DTB=selected, LOG_LEVEL="0",
                       PATH=str(mockbin) + ":" + os.environ["PATH"])
            run(["bash", "tools/flex-builder", "distroscr"], work, env)
            boot = Path(output, "boot/IMX_boot.scr").read_text()
            assert boot.startswith(f"setenv fdtfile {dtb}\nsetenv image Image\n")
            assert boot.endswith((work / "configs/board/IMX_boot.txt").read_text())
            print(f"PASS {profile}: config, output isolation, DTB staging selection, boot script source")
        assert len(outputs) == 3
        for board, uboot in (("imx93evk", "imx93_11x11_evk_defconfig"),
                             ("imx93frdm", "imx93_11x11_frdm_defconfig")):
            run(["python3", "tools/gen_config_from_file.py", "Kconfig",
                 f"configs/{board}/defconfig"], work)
            run(["python3", "tools/kconfig_hooks.py"], work)
            values = run(["make", "-s", "profile-vars"], work).strip().split("|")
            assert values[:4] == [board, "IMX", str(work / "build_lsdk2606" / board), "imx*.dtb"]
            assert values[7] == uboot
            assert all(path.startswith(values[2] + "/") for path in values[4:7])
            assert values[2] not in outputs
            outputs.add(values[2])
            env["FBOUTDIR"] = values[2]
            env["LINUX_DTB"] = ""
            run(["bash", "tools/flex-builder", "distroscr"], work, env)
            assert Path(values[2], "boot/IMX_boot.scr").read_text() == (work / "configs/board/IMX_boot.txt").read_text()
            print(f"PASS {board}: isolated output, U-Boot config, inherited fdtfile")
        assert len(outputs) == 5
        run(["python3", "tools/gen_defconfig.py", "Kconfig", machine], work)
        conf = kconfiglib.Kconfig("Kconfig")
        conf.load_config(".config")
        assert conf.syms["MISNET_PROFILE"].str_value == "dev"
        print("PASS MISNET board defconfig: defaults to dev")


if __name__ == "__main__":
    main()
