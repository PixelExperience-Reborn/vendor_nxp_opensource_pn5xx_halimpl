#!/usr/bin/env python3
"""AOSP17 PE-Reborn row 170: pinned PN5xx legacy HAL vs modern AIDL.

Only historical source/ABI/manifest evidence. No Soong/VINTF/device runtime.
"""
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

LEGACY = "36cf9d4af781d5aaa673227e5c06cf3e34ffa647"
LEGACY_TREE = "56d5e2b919750d354443a1052977e5f70fe2b0ad"
AOSP17 = "68931d93d3b2ccfc71553cb03088fe5d6fb5dd30"
AOSP17_TREE = "8386a3c67e07f5fe492c92d1888c256bbc37d48b"
NXP17 = "debec247cea5570d259db3138124201e3769a728"
NXP17_TREE = "31be748946aaf58dcf86034804db69c53a4ac3a7"


def require(ok, msg):
    if not ok:
        raise RuntimeError(msg)


def git(repo, *args):
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], text=True,
        stderr=subprocess.PIPE).strip()


def check_pin(repo, ref, sha, tree, description):
    actual = git(repo, "rev-parse", f"{ref}^{{commit}}")
    require(actual == sha, f"{description} SHA changed: {actual}")
    got = git(repo, "rev-parse", f"{actual}^{{tree}}")
    require(got == tree, f"{description} tree changed: {got}")
    return actual


def show(repo, sha, file):
    return git(repo, "show", f"{sha}:{file}")


def historical_hal(repo):
    sha = check_pin(repo, "refs/remotes/origin/seventeen",
                    LEGACY, LEGACY_TREE, "archived 2021 PN5xx HAL")
    bp = show(repo, sha, "Android.bp")
    native = show(repo, sha, "halimpl/src/halLibnfc/src/Android.bp")
    v1 = ET.fromstring(show(repo, sha, "extns/intf/nxpnfc/2.0/manifest.xml"))
    v2 = ET.fromstring(show(repo, sha, "extns/intf/nxpnfclegacy/1.0/manifest.xml"))
    config = show(repo, sha, "halimpl/libnfc-nxp-PN81T_example.conf")
    nfc_cpp = show(repo, sha, "1.2/Nfc.cpp")
    readme = show(repo, sha, "README.md")

    for name in ("nfc_nci.nqx.default.hw", "se_nq_extn_client",
                 "jcos_nq_client", "ls_nq_client"):
        require(f'name: "{name}"' in bp,
                f"archived PN5xx Soong module changed: {name}")
    for dependency in ("android.hardware.nfc@1.0",
                       "android.hardware.nfc@1.1",
                       "android.hardware.nfc@1.2",
                       "android.hardware.secure_element@1.0",
                       "vendor.nxp.hardware.nfc@2.0",
                       "vendor.nxp.nxpnfclegacy@1.0",
                       "hal_libnfc"):
        require(f'"{dependency}"' in bp,
                f"archived HIDL HAL dependency changed: {dependency}")
    require("defaults: [\"hidl_defaults\"]" in bp
            and "vendor: true" in bp,
            "archived HAL partition/defaults changed")
    require('name: "hal_libnfc"' in native
            and '"libchrome"' in native
            and '"libhidlbase"' in native,
            "archived separate NFA/NCI HAL layer changed")
    require("phNxpNciHal_getVendorConfig_1_2" in nfc_cpp
            and "hidl_vec" in nfc_cpp,
            "archived HIDL 1.2 entrypoints changed")
    h1 = {(h.findtext("name"), h.findtext("version"))
          for h in v1.findall("hal")}
    h2 = {(h.findtext("name"), h.findtext("version"))
          for h in v2.findall("hal")}
    require(("android.hardware.nfc", "1.2") in h1
            and ("vendor.nxp.nxpnfc", "2.0") in h1,
            "archived NXPNFC 2.0 HIDL VINTF changed")
    require(("android.hardware.nfc", "1.2") in h2
            and ("vendor.nxp.nxpnfclegacy", "1.0") in h2,
            "archived legacy HIDL VINTF changed")
    for setting in ('NXP_NFC_CHIP=0x08',
                    'NXP_NFC_DEV_NODE="/dev/pn553"',
                    'NXP_FW_NAME="libpn557_fw.so"'):
        require(setting in config,
                "archived PN81T example setting changed: " + setting)
    require("android-10.0.0_r2" in readme
            and "PN81T" in readme,
            "archived PN5xx firmware/release identity changed")
    print("PASS: pinned 2021 PN5xx HIDL 1.2 + NXP extensions/JCOP/loader modules")
    print("PASS: example PN81T config and eSE service HIDL declarations detected")
    print("DECISION: no PN81T config or proprietary eSE firmware in AOSP17 ROM")


def official_aosp17(repo):
    sha = check_pin(repo, "refs/tags/android-17.0.0_r1",
                    AOSP17, AOSP17_TREE, "official Android17 NXP HAL")
    bp = show(repo, sha, "snxxx/Android.bp")
    aidl = show(repo, sha, "intf/nxpnfc/aidl/Android.bp")
    vendor_api = show(repo, sha,
                      "intf/nxpnfc/aidl/vendor/nxp/nxpnfc_aidl/INxpNfc.aidl")
    require('name: "android.hardware.nfc-service.nxp"' in bp,
            "AOSP17 official native HAL module changed")
    require('name: "vendor.nxp.nxpnfc_aidl"' in aidl
            and 'stability: "vintf"' in aidl
            and "ndk: {" in aidl,
            "AOSP17 NXP vendor stable AIDL module changed")
    for api in ("getVendorParam(", "setVendorParam(", "resetEse(",
                "setNxpTransitConfig("):
        require(api in vendor_api,
                f"AOSP17 vendor NXP API no longer provides {api}")
    print("PASS: pinned official Android17 NXP AIDL service and NXP vendor VINTF AIDL")
    print("DECISION: official AOSP17 already supplies the required modern interface")


def modern_nxp17(repo):
    sha = check_pin(repo, "refs/remotes/origin/br_ar_17_aosp_mainline",
                    NXP17, NXP17_TREE, "official NXP 17.07.00 candidate")
    bp = show(repo, sha, "snxxx/Android.bp")
    vintf = ET.fromstring(show(repo, sha, "snxxx/aidl/2.0/nfc2-service-nxp.xml"))
    readme = show(repo, sha, "README.md")
    main = show(repo, sha, "snxxx/aidl/2.0/main.cpp")
    for symbol in ('name: "android.hardware.nfc2-service.nxp"',
                   '"android.hardware.nfc-V2-ndk"',
                   '"vendor.nxp.nxpnfc_aidl-V1-ndk"',
                   'vintf_fragments: ["aidl/2.0/nfc2-service-nxp.xml"]'):
        require(symbol in bp, f"newer NXP AIDL service changed: {symbol}")
    actual = {(h.findtext("name"), h.findtext("version"),
               h.findtext("fqname"), h.get("format"))
              for h in vintf.findall("hal")}
    require(("android.hardware.nfc", "2", "INfc/default", "aidl")
            in actual, "current NXP NFC AIDL V2 VINTF changed")
    require(("vendor.nxp.nxpnfc_aidl", None, "INxpNfc/default", "aidl")
            in actual, "current NXP vendor AIDL V1 VINTF changed")
    require(len(actual) == 2, "more NXP VINTF HALs unexpectedly declared")
    require("startNxpNfcAidlService" in main
            and "AServiceManager_addService" in main,
            "NXP AIDL vendor service startup changed")
    require("17.07.00" in readme
            and "android-17.0.0_r1" in readme,
            "NXP current release changed")
    print("PASS: NXP Android17 17.07.00 AIDL V2 + frozen vendor AIDL V1 candidate")
    print("OPEN: targeted source comparison and device-specific AIDL/SE ABI validation")


def manifest(root):
    root = Path(root)
    entry = ET.parse(root / "default.xml").getroot()
    require(len(entry) == 1
            and entry[0].get("name") == "aosp17_pe_p2_kernel_configs.xml",
            "active default/source-only stage unexpectedly modified")
    base = ET.parse(root / "aosp17_pe_bootstrap.xml").getroot()
    owners = {p.get("path"): p.get("name") for p in base.findall("project")}
    for path, name in (
        ("hardware/nxp/nfc", "platform/hardware/nxp/nfc"),
        ("packages/modules/Nfc", "platform/packages/modules/Nfc"),
        ("system/secure_element", "platform/system/secure_element"),
    ):
        require(owners.get(path) == name,
                f"official AOSP17 NFC/SE owner replaced: {path}")
    require("vendor/nxp/opensource/pn5xx/halimpl" not in owners
            and "vendor_nxp_opensource_pn5xx_halimpl"
            not in owners.values(),
            "archived PN5xx HIDL source accidentally enabled")
    gate = (root / "tools/validate_aosp17_base_profiles.py").read_text()
    tests = (root / "tools/test_aosp17_manifest_entrypoint.py").read_text()
    require('if "vendor/nxp/opensource/pn5xx/halimpl" in projects:' in gate
            and '"vendor_nxp_opensource_pn5xx_halimpl"' in gate,
            "row 170 archived PN5xx path/name guard missing")
    for name in ("test_archived_pn5xx_hidl_hal_must_not_enter_android17",
                 "test_archived_pn5xx_hidl_cannot_replace_aosp17_nxp_hal"):
        require(f"def {name}(" in tests, f"row 170 negative test missing: {name}")
    subprocess.run(
        [sys.executable, str(root / "tools/validate_aosp17_base_profiles.py")],
        cwd=root, check=True)
    print("PASS: original 25-stage manifest, native NFC HAL/APEX and SE ownership")
    print("PASS: row 170 adversarial path/replacement tests present")


def main():
    require(len(sys.argv) == 5,
            "Usage: check_pn5xx_halimpl_boundary.py LEGACY_NXP AOSP17_NXP NEW_NXP MANIFEST")
    legacy, aosp, newer, mf = [Path(v).resolve() for v in sys.argv[1:]]
    require(all(d.is_dir() for d in (legacy, aosp, newer, mf)),
            "missing source checkout")
    historical_hal(legacy)
    official_aosp17(aosp)
    modern_nxp17(newer)
    manifest(mf)
    print("PASS: row 170 source-only legacy PN5xx versus Android17 AIDL boundary")
    print("NOT TESTED: Soong/NDK, VINTF + SELinux on device, CTS/VTS, physical NFC")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, ValueError, ET.ParseError,
            subprocess.CalledProcessError) as exc:
        print("FAIL:", exc, file=sys.stderr)
        sys.exit(1)
