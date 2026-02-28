#!/usr/bin/env bash
# macOS .app 빌드 스크립트
# 사용: chmod +x build_mac.sh && ./build_mac.sh

set -e

APP_NAME="NEXUS"
BUNDLE_ID="com.nexus.nleplatform"

echo "의존성 설치 중..."
pip install -r requirements.txt

# pathlib 백포트가 설치돼 있으면 제거 (PyInstaller 충돌)
pip show pathlib 2>/dev/null && pip uninstall pathlib -y || true

echo "PyInstaller 빌드 중..."
pyinstaller \
  --onedir \
  --windowed \
  --name "$APP_NAME" \
  --osx-bundle-identifier "$BUNDLE_ID" \
  --icon assets/icon.icns \
  --clean \
  main.py

echo ""
echo "빌드 완료: dist/$APP_NAME.app  ($(du -sh dist/$APP_NAME.app | cut -f1))"
echo ""
echo "Gatekeeper 경고가 뜨는 경우:"
echo "  1) 시스템 설정 > 개인 정보 보호 및 보안 > '확인 없이 열기' 허용"
echo "  2) 또는 터미널에서: xattr -cr dist/$APP_NAME.app"
