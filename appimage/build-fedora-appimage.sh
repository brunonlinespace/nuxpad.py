#!/usr/bin/env bash
set -Eeuo pipefail

APP_NAME="Nuxpad"
APP_ID="nuxpad"
APP_VERSION="2.0.0-rc5.1"
ARCH="${ARCH:-x86_64}"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"
SOURCE_FILE="${ROOT}/source/nuxpad.py"
ASSET_DIR="${ROOT}/assets/icons"
TEMPLATE_APPDIR="${SCRIPT_DIR}/AppDir-template"
BUILD_REQUIREMENTS="${SCRIPT_DIR}/build-requirements.txt"

BUILD_ROOT="${SCRIPT_DIR}/build"
VENV="${BUILD_ROOT}/venv"
PYI_WORK="${BUILD_ROOT}/pyinstaller-work"
PYI_DIST="${BUILD_ROOT}/pyinstaller-dist"
FINAL_APPDIR="${BUILD_ROOT}/Nuxpad.AppDir"
TOOLS_DIR="${BUILD_ROOT}/tools"
DIST_DIR="${ROOT}/dist"

APPIMAGE="${DIST_DIR}/${APP_NAME}-${APP_VERSION}-${ARCH}.AppImage"
SHA_FILE="${APPIMAGE}.sha256"
BUILD_INFO="${DIST_DIR}/${APP_NAME}-${APP_VERSION}-${ARCH}.build-info.txt"
PYTHON_LOCK="${DIST_DIR}/${APP_NAME}-${APP_VERSION}-${ARCH}.build-python-lock.txt"

log() { printf '\n==> %s\n' "$*"; }
die() { printf 'Error: %s\n' "$*" >&2; exit 1; }
require_file() { [[ -f "$1" ]] || die "Missing file: $1"; }

cleanup() {
    rm -rf "${BUILD_ROOT}/source-stage"
}
trap cleanup EXIT

check_inputs() {
    require_file "$SOURCE_FILE"
    require_file "$BUILD_REQUIREMENTS"
    require_file "${ASSET_DIR}/nuxpad.png"
    require_file "${ASSET_DIR}/nuxpad-about.png"
    require_file "${TEMPLATE_APPDIR}/AppRun"
    require_file "${TEMPLATE_APPDIR}/nuxpad.desktop"

    [[ "$(uname -m)" == "$ARCH" ]] \
        || die "This kit currently targets ${ARCH}; host is $(uname -m)."

    grep -q "APP_VERSION = \"${APP_VERSION}\"" "$SOURCE_FILE" \
        || die "Canonical source is not version ${APP_VERSION}"

    mapfile -t python_files < <(
        find "$ROOT" -type f -name '*.py' \
            ! -path "${BUILD_ROOT}/*" -print
    )
    [[ "${#python_files[@]}" -eq 1 ]] \
        || die "Expected exactly one application .py file; found ${#python_files[@]}"
    [[ "${python_files[0]}" == "$SOURCE_FILE" ]] \
        || die "Unexpected Python source: ${python_files[0]}"

    if [[ -r /etc/os-release ]]; then
        # shellcheck disable=SC1091
        . /etc/os-release
        if [[ "${ID:-}" != "fedora" || ! "${VERSION_ID:-}" =~ ^(43|44)$ ]]; then
            if [[ "${NUXPAD_ALLOW_UNSUPPORTED_HOST:-0}" != "1" ]]; then
                die "Build on Fedora 43 or 44, or set NUXPAD_ALLOW_UNSUPPORTED_HOST=1."
            fi
            printf 'Warning: unsupported build host: %s\n' \
                "${PRETTY_NAME:-unknown}" >&2
        fi
    fi
}

install_dependencies() {
    if [[ "${NUXPAD_SKIP_DNF:-0}" == "1" ]]; then
        log "Skipping DNF dependency installation"
        return
    fi

    command -v dnf >/dev/null 2>&1 || die "This script targets Fedora."
    log "Installing Fedora build dependencies"
    sudo dnf install -y \
        python3 python3-pip python3-devel \
        gcc binutils patchelf file desktop-file-utils \
        fuse-libs curl zsync
}

prepare_environment() {
    log "Preparing isolated build environment"
    rm -rf "$BUILD_ROOT"
    mkdir -p "$BUILD_ROOT" "$TOOLS_DIR" "$DIST_DIR"

    python3 -m venv "$VENV"
    "$VENV/bin/python" -m pip install --upgrade pip wheel setuptools
    "$VENV/bin/python" -m pip install -r "$BUILD_REQUIREMENTS"
    "$VENV/bin/python" -m py_compile "$SOURCE_FILE"
    "$VENV/bin/python" -m pip freeze --all > "$PYTHON_LOCK"
}

stage_source() {
    local stage="${BUILD_ROOT}/source-stage"
    mkdir -p "${stage}/icons"
    cp -f "$SOURCE_FILE" "${stage}/nuxpad.py"
    cp -a "${ASSET_DIR}/." "${stage}/icons/"
}

freeze_application() {
    log "Freezing the canonical source with PyInstaller"
    stage_source

    # PyInstaller has dedicated PyQt6 hooks. Avoid --collect-all PyQt6, which
    # collects every PyQt6 submodule, data file, and binary and greatly inflates
    # a small text editor.
    "$VENV/bin/pyinstaller" \
        --noconfirm \
        --clean \
        --onedir \
        --optimize 1 \
        --name "$APP_ID" \
        --distpath "$PYI_DIST" \
        --workpath "$PYI_WORK" \
        --specpath "$BUILD_ROOT" \
        --add-data "${BUILD_ROOT}/source-stage/icons:icons" \
        "${BUILD_ROOT}/source-stage/nuxpad.py"
}

assemble_appdir() {
    log "Assembling AppDir"
    rm -rf "$FINAL_APPDIR"
    cp -a "$TEMPLATE_APPDIR" "$FINAL_APPDIR"

    mkdir -p "$FINAL_APPDIR/usr/lib/nuxpad" "$FINAL_APPDIR/usr/bin"
    cp -a "${PYI_DIST}/${APP_ID}/." "$FINAL_APPDIR/usr/lib/nuxpad/"
    ln -s ../lib/nuxpad/nuxpad "$FINAL_APPDIR/usr/bin/nuxpad"

    chmod 0755 "$FINAL_APPDIR/AppRun"
    chmod 0755 "$FINAL_APPDIR/usr/lib/nuxpad/nuxpad"

    mkdir -p "$FINAL_APPDIR/usr/share/doc/nuxpad"
    for doc in README.md CHANGELOG.md RELEASE_NOTES.md FEATURE_FREEZE.md; do
        [[ -f "${ROOT}/docs/${doc}" ]] \
            && cp -f "${ROOT}/docs/${doc}" \
                "$FINAL_APPDIR/usr/share/doc/nuxpad/"
    done
    cp -f "${ROOT}/LICENSE" "$FINAL_APPDIR/usr/share/doc/nuxpad/LICENSE"

    desktop-file-validate "$FINAL_APPDIR/nuxpad.desktop"
    desktop-file-validate \
        "$FINAL_APPDIR/usr/share/applications/nuxpad.desktop"
}

validate_bundle() {
    log "Validating Qt bundle"

    find "$FINAL_APPDIR/usr/lib/nuxpad" -name 'libqxcb.so' -print -quit \
        | grep -q . || die "Qt XCB platform plugin was not bundled"

    find "$FINAL_APPDIR/usr/lib/nuxpad" \
        \( -name 'libqwayland*.so' -o -name '*wayland*.so' \) \
        -print -quit | grep -q . \
        || printf 'Warning: Qt Wayland plugin was not detected; test XWayland carefully.\n' >&2

    find "$FINAL_APPDIR/usr/lib/nuxpad" \
        \( -name '*Qt6PrintSupport*' -o -name '*QtPrintSupport*' \) \
        -print -quit | grep -q . \
        || die "Qt Print Support was not bundled"

    if find "$FINAL_APPDIR/usr/lib/nuxpad" -iname '*WebEngine*' -print -quit \
        | grep -q .; then
        printf 'Warning: Qt WebEngine was bundled unexpectedly; inspect bundle size.\n' >&2
    fi

    log "Running off-screen smoke test"
    local smoke_log status
    smoke_log="$(mktemp --tmpdir nuxpad-smoke.XXXXXX.log)"
    set +e
    timeout 8s env QT_QPA_PLATFORM=offscreen \
        "$FINAL_APPDIR/AppRun" >"$smoke_log" 2>&1
    status=$?
    set -e

    if [[ "$status" -ne 0 && "$status" -ne 124 ]]; then
        cat "$smoke_log" >&2
        rm -f "$smoke_log"
        die "Smoke test failed"
    fi
    rm -f "$smoke_log"
}

get_appimagetool() {
    local tool="${TOOLS_DIR}/appimagetool-${ARCH}.AppImage"
    if [[ ! -x "$tool" ]]; then
        log "Downloading current appimagetool" >&2
        curl --proto '=https' --tlsv1.2 -fL \
          "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-${ARCH}.AppImage" \
          -o "$tool"
        chmod +x "$tool"
    fi

    if [[ -n "${APPIMAGETOOL_SHA256:-}" ]]; then
        printf '%s  %s\n' "$APPIMAGETOOL_SHA256" "$tool" \
            | sha256sum --check --status \
            || die "appimagetool SHA-256 verification failed"
    else
        printf 'Warning: APPIMAGETOOL_SHA256 was not supplied; its resolved hash will be recorded.\n' >&2
    fi

    printf '%s\n' "$tool"
}

build_appimage() {
    local tool
    tool="$(get_appimagetool)"

    log "Building ${APPIMAGE##*/}"
    rm -f "$APPIMAGE" "$SHA_FILE"
    ARCH="$ARCH" "$tool" --appimage-extract-and-run \
        "$FINAL_APPDIR" "$APPIMAGE"
    chmod +x "$APPIMAGE"
    (cd "$DIST_DIR" && sha256sum "${APPIMAGE##*/}" > "${SHA_FILE##*/}")
}

write_build_info() {
    local tool="${TOOLS_DIR}/appimagetool-${ARCH}.AppImage"
    {
        echo "Nuxpad build"
        echo "Version: ${APP_VERSION}"
        echo "Architecture: ${ARCH}"
        echo "Built: $(date --iso-8601=seconds)"
        echo "Host: $(grep '^PRETTY_NAME=' /etc/os-release | cut -d= -f2-)"
        echo "System Python: $(python3 --version 2>&1)"
        echo "Build Python: $("$VENV/bin/python" --version 2>&1)"
        echo "PyInstaller: $("$VENV/bin/pyinstaller" --version)"
        "$VENV/bin/python" - <<'PY'
from PyQt6.QtCore import PYQT_VERSION_STR, QT_VERSION_STR
print(f"PyQt6: {PYQT_VERSION_STR}")
print(f"Qt: {QT_VERSION_STR}")
PY
        echo "Canonical source SHA-256: $(sha256sum "$SOURCE_FILE" | awk '{print $1}')"
        echo "appimagetool SHA-256: $(sha256sum "$tool" | awk '{print $1}')"
        echo "Output: ${APPIMAGE##*/}"
    } > "$BUILD_INFO"
}

main() {
    check_inputs
    install_dependencies
    prepare_environment
    freeze_application
    assemble_appdir
    validate_bundle
    build_appimage
    write_build_info

    log "Build complete"
    printf '%s\n%s\n%s\n%s\n' \
        "$APPIMAGE" "$SHA_FILE" "$BUILD_INFO" "$PYTHON_LOCK"
}

main "$@"
