# -*- coding: utf-8 -*-
"""
Скрипт сборки и упаковки дистрибутивов Wordy / Lerne.

Создает две версии одним запуском:
  1. Standard (EXE отдельно) -- данные в %APPDATA%\\Lerne
  2. Portable (EXE + файл 'portable') -- данные рядом с EXE

Использование:
  python build_dist.py [--version 1.0]
"""

import argparse
import io
import os
import shutil
import subprocess
import sys
import zipfile

# Принудительно включаем UTF-8 для stdout/stderr на Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ─────────────────────────────────────────────────────────────
# Конфигурация
# ─────────────────────────────────────────────────────────────
APP_NAME = "Wordy"
EXE_NAME = "Wordy.exe"
SPEC_FILE = "wordy.spec"
DIST_DIR = "dist"
BUILD_DIR = "build"


def get_version(default: str) -> str:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--version", default=default)
    args, _ = parser.parse_known_args()
    return args.version


def run_pyinstaller():
    print("\n" + "=" * 60)
    print("  [BUILD] Building EXE with PyInstaller...")
    print("=" * 60)
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--noconfirm", SPEC_FILE],
        check=True,
    )


def find_exe() -> str:
    """Ищет собранный EXE файл в папке dist."""
    for candidate in [
        os.path.join(DIST_DIR, EXE_NAME),
        os.path.join(DIST_DIR, APP_NAME, EXE_NAME),
        os.path.join(DIST_DIR, EXE_NAME.replace(".exe", ""), EXE_NAME),
    ]:
        if os.path.exists(candidate):
            return candidate
    # Fallback: рекурсивный поиск
    for root, _, files in os.walk(DIST_DIR):
        for f in files:
            if f == EXE_NAME:
                return os.path.join(root, f)
    raise FileNotFoundError(f"Не найден '{EXE_NAME}' в папке '{DIST_DIR}'")


def create_zip(folder: str, zip_path: str):
    """Упаковывает содержимое папки в ZIP."""
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(folder):
            for file in files:
                abs_path = os.path.join(root, file)
                arcname = os.path.relpath(abs_path, start=folder)
                zf.write(abs_path, arcname)
    print(f"  [OK] Создан: {zip_path}")


def build_packages(version: str, exe_path: str):
    print("\n" + "=" * 60)
    print("  [PACK] Packaging distributions...")
    print("=" * 60)

    # Папки для каждой версии
    standard_dir = os.path.join(DIST_DIR, "release", f"{APP_NAME}_v{version}_Standard")
    portable_dir = os.path.join(DIST_DIR, "release", f"{APP_NAME}_v{version}_Portable")

    for d in [standard_dir, portable_dir]:
        if os.path.exists(d):
            shutil.rmtree(d)
        os.makedirs(d)

    # -- Standard: только EXE -----------------------------------------
    shutil.copy2(exe_path, os.path.join(standard_dir, EXE_NAME))
    print(f"  [Standard] Скопирован {EXE_NAME}")

    # -- Portable: EXE + маркер portable ------------------------------
    shutil.copy2(exe_path, os.path.join(portable_dir, EXE_NAME))
    marker_path = os.path.join(portable_dir, "portable")
    with open(marker_path, "w", encoding="utf-8") as f:
        f.write(
            "# Portable Mode\n"
            "# Этот файл сигнализирует приложению хранить все данные\n"
            "# (настройки, аудио, логи) в этой же папке, а не в %APPDATA%.\n"
            "# Идеально для использования на флешке или без установки.\n"
        )
    print(f"  [Portable] Скопирован {EXE_NAME} + создан маркер 'portable'")

    # -- ZIP архивы ----------------------------------------------------
    release_dir = os.path.join(DIST_DIR, "release")
    standard_zip = os.path.join(release_dir, f"{APP_NAME}_v{version}_Standard.zip")
    portable_zip = os.path.join(release_dir, f"{APP_NAME}_v{version}_Portable.zip")

    create_zip(standard_dir, standard_zip)
    create_zip(portable_dir, portable_zip)

    return standard_zip, portable_zip


def main():
    version = get_version("1.0")

    print(f"\n[*] Lerne Build Tool -- Version {version}")
    print(f"    Spec: {SPEC_FILE}")
    print(f"    Output: {DIST_DIR}/release/")

    # Шаг 1: Сборка EXE
    run_pyinstaller()

    # Шаг 2: Найти собранный EXE
    exe_path = find_exe()
    print(f"\n  [OK] Найден EXE: {exe_path}")

    # Шаг 3: Упаковка двух дистрибутивов
    std_zip, port_zip = build_packages(version, exe_path)

    # Итог
    print("\n" + "=" * 60)
    print("  [OK] Готово! Файлы для загрузки на GitHub Releases:")
    print(f"       {std_zip}")
    print(f"       {port_zip}")
    print("=" * 60)
    print(
        "\n  Как выложить на GitHub:\n"
        "  1. Откройте репозиторий на github.com\n"
        "  2. Перейдите в Releases -> 'Create a new release'\n"
        "  3. Укажите тег версии (например, v1.0)\n"
        "  4. Прикрепите оба ZIP файла через 'Attach binaries'\n"
        "  5. Опишите список изменений и нажмите 'Publish release'\n"
    )


if __name__ == "__main__":
    main()
