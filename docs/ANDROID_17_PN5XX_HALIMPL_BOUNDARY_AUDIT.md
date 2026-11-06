# PE-Reborn Android 17 — row 170: legacy PN5xx HAL implementation boundary

**Audited:** 2026-11-07. **Target:** independent AOSP17 PixelExperience-Reborn. **Future device:** POCO F5 Pro / Redmi K60 (`mondrian`, SM8475).
**Status:** pinned source and ownership audit; **not** Android17 Soong/ELF linking, device VINTF/SELinux or hardware verification.

## Decision

**Do not activate** historical `vendor/nxp/opensource/pn5xx/halimpl` (or its old HIDL services, example configuration and eSE provisioning libraries). **Keep the official Android17 `platform/hardware/nxp/nfc` source as the single NXP NFC HAL owner**, and official NFC Mainline `platform/packages/modules/Nfc` / Secure Element `platform/system/secure_element` as their respective owners.

This is not ignoring new technology: the official AOSP17 NXP source already declares modern `android.hardware.nfc-service.nxp` and the frozen `vendor.nxp.nxpnfc_aidl` vendor AIDL. NXP's Android17 17.07.00 branch adds a candidate `android.hardware.nfc2-service.nxp` using **NFC AIDL V2** and a separate **vendor NXP AIDL V1** extension. These candidate changes must be assessed as exact source/ABI/security deltas against the *selected* official AOSP17 HAL, not by introducing an unrelated second HAL tree. See row 169's CI for proof official AOSP17 already contains the four-method NXP vendor AIDL contract.

## Immutable source evidence

| Source | Revision | Observations |
| --- | --- | --- |
| Historical PE `vendor_nxp_opensource_pn5xx_halimpl` `seventeen` | commit `36cf9d4af781d5aaa673227e5c06cf3e34ffa647`, Git tree `56d5e2b919750d354443a1052977e5f70fe2b0ad`, last commit 2021-11-21 | CAF `LA.UM.10.3.r1-00300-sdm845.0` ancestry, *not* Android17 or necessarily relevant to SM8475. Root `Android.bp` builds `nfc_nci.nqx.default.hw`, `se_nq_extn_client`, `jcos_nq_client`, `ls_nq_client`. NFC HAL links **HIDL NFC @1.0/@1.1/@1.2**, `vendor.nxp.hardware.nfc@1.0/@1.1/@2.0`, `vendor.nxp.nxpnfclegacy@1.0`, `android.hardware.secure_element@1.0` and `hal_libnfc`. |
| Historic separate `hal_libnfc` | same commit | `halimpl/src/halLibnfc/src/Android.bp` builds another legacy NFA/NCI implementation, imports `libchrome`, `libpower`, old HIDL dependencies and reference-tree source. Not an NFC Mainline JNI/stack replacement. |
| Historic VINTF fragments | same commit | `extns/intf/nxpnfc/2.0/manifest.xml` declares HIDL `android.hardware.nfc` 1.2 plus `vendor.nxp.nxpnfc` 2.0; `extns/intf/nxpnfclegacy/1.0/manifest.xml` declares `INfc/default` HIDL 1.2 plus `INxpNfcLegacy/default` HIDL 1.0. **Do not combine them** with Android17 AIDL INfc/default and vendor AIDL INxpNfc/default. These old fragments are source examples, not proof of runtime device services. |
| Historic example PN81T conf | same commit | `halimpl/libnfc-nxp-PN81T_example.conf` is a generic board/controller example; includes `NXP_NFC_CHIP=0x08`, example `NXP_NFC_DEV_NODE="/dev/pn553"`, `NXP_FW_NAME="libpn557_fw.so"` and eSE/clock/RF/standby values. **Do not interpret an example as the identified mondrian NFCC or flash its firmware.** |
| Official AOSP17 NFC HAL owner | `hardware/nxp/nfc` tag `android-17.0.0_r1`, commit `68931d93d3b2ccfc71553cb03088fe5d6fb5dd30`, tree `8386a3c67e07f5fe492c92d1888c256bbc37d48b` | `snxxx/Android.bp` includes official `android.hardware.nfc-service.nxp` Soong module and `intf/nxpnfc/aidl` provides modern vendor AIDL contract. **Active AOSP17 baseline**. |
| NXP current 17.07.00 | `NXPNFCProject/nfcandroid_nfc_hidlimpl`, branch `br_ar_17_aosp_mainline`, commit `debec247cea5570d259db3138124201e3769a728`, tree `31be748946aaf58dcf86034804db69c53a4ac3a7` | `snxxx/Android.bp` contains modern `android.hardware.nfc2-service.nxp`, `android.hardware.nfc-V2-ndk`, `vendor.nxp.nxpnfc_aidl-V1-ndk`; `snxxx/aidl/2.0/nfc2-service-nxp.xml` declares `android.hardware.nfc` AIDL v2 `INfc/default` and `vendor.nxp.nxpnfc_aidl` `INxpNfc/default`. Candidate for a **targeted, validated** AOSP17 HAL update, not a new fork checkout. |

Source links:
- https://github.com/PixelExperience-Reborn/vendor_nxp_opensource_pn5xx_halimpl/tree/seventeen
- https://android.googlesource.com/platform/hardware/nxp/nfc/+/refs/tags/android-17.0.0_r1
- https://github.com/NXPNFCProject/nfcandroid_nfc_hidlimpl/tree/br_ar_17_aosp_mainline

## Function/technology selection — Android17 and mondrian

| Capability | Preferred approach | Conditions |
| --- | --- | --- |
| NFC controller I/O, recovery, firmware and power | Official AOSP17 NXP native NFC HAL, compare with newest NXP 17.07.00 as needed | Exact NFCC and firmware version, trusted NDK/AIDL source, stable service, verified device/vendor configuration. Do not reintroduce `nfc_nci.nqx.default.hw` HIDL. |
| Newer `android.hardware.nfc` AIDL V2 | Review current NXP native implementation against official source; **do not replace without compatibility proof** | Single `INfc/default`, compatible Mainline NFC APEX, NDK ABI, VINTF, SELinux, HAL init & service registration. |
| Vendor-specific NXP controls | Keep already-owned `vendor.nxp.nxpnfc_aidl` where needed | Inspect service-side permissions/SELinux and exact consumer before enabling eSE reset/transit configuration. |
| JCOP/Loader Service/eSE firmware update | No speculative use of old `jcos_nq_client` or `ls_nq_client` | Authenticated applet/vendor firmware/licence, production provisioning rules, rollback/recovery and SE access-control verification. |
| PN81T/PN80T/PN557 `.conf` examples | **Reject as product defaults** | Must positively identify hardware and authorized manufacturer configuration; wrong settings can break NFC/HCE or SE/financial credentials. |
| RF/test support, NFC low-power | Prefer current official/vendor validation and measured change | Validate suspend/resume/reboot, chip firmware, NFC discovery and power draw on actual mondrian. |
| LineageOS/device tree examples | Optional last-resort read-only hardware evidence | Do not import ROM architecture, vendor product inheritance or random proprietary blobs. Reimplement minimum independently verified changes if actually required. |

## Security and completion gates

1. Identify exact `mondrian` NFC controller, firmware, eSE wiring, regulatory/RF calibration/SKU and production vendor binaries, **without guessing** from another ROM's configurations.
2. Inspect source-level NXP 17.07.00 delta vs official AOSP17 `hardware/nxp/nfc` for relevant fixes. A vendor release number is not a reason to overwrite AOSP17 security/compatibility support. Preserve licence and provenance.
3. Ensure **one** active `android.hardware.nfc.INfc/default` service and single native stack / required vendor AIDL. No duplicate APEX `com.android.nfcservices`, conflicting `com.android.nfc`, or old HIDL VINTF fragments.
4. Soong bootstrap/NDK build and frozen AIDL hashes; VINTF/FCM, SELinux enforcing/neverallow, ABI compatibility of vendor NXP libraries and correct init/permissions.
5. Mainline NFC Java/JNI/Apex signing, CTS/VTS/HCE and SE/OMAPI, NFC hardware tag tests, sleep/resume, eSE/UICC/payment if legally supported, long-term recovery and power/latency baselines.
6. Old JCOP/loader or firmware update must **not** be run by default or be represented as tested; Android17 does not by itself guarantee eSE hardware or certification.

## Confirmed continuous integration — completed

[GitHub Actions #42311566845](https://github.com/PixelExperience-Reborn/vendor_nxp_opensource_pn5xx_halimpl/actions/runs/42311566845) completed **SUCCESS** on `audit/a17-pn5xx-halimpl-modern-boundary-20261107`.

Verified by the immutable-source checker: exact original 2021 PN5xx tree, archived HIDL interfaces/VINTF, separate JCOP/loader modules and PN81T example; official AOSP17 NXP HAL and vendor AIDL; current NXP 17.07.00 AIDL V2 and NXP V1 service source. Manifest validation passed all 25 approved staged profiles and **29 of 29 adversarial/positive regressions**. The Android17 experimental NFC security candidate remains isolated; `default.xml` unchanged.

**Not verified by this run:** Soong/NDK/Java/APEX compilation, service running on hardware, shipped Xiaomi vendor NFC HAL, eSE/APDU, CTS/VTS, proper NFC eSE/UICC routing, NFC payment certification, firmware selection, or an independent PE-Reborn `mondrian` product.

## Work recorded in row 170

- Historical/official/current NXP source comparison, pinned host source checks and GitHub Actions CI.
- Manifest working branch guards against importing old `vendor/nxp/opensource/pn5xx/halimpl` by path/repo name and tests deliberate attempts to replace official HAL.
- No VINTF, sepolicy, product, device tree, kernel, proprietary blob, firmware or `default.xml` source change.

**Not completed:** actual AOSP17 Soong/ELF build or mondrian hardware integration; source-only CI is not device bring-up evidence.
