"""
NEXUS — NLE 통합 관제 플랫폼
영상 프로젝트 폴더 생성 · 최근 프로젝트 관리 · NLE 빈 자동 설정 · 버전 스냅샷 관리
"""

import sys
import re
import json
import uuid
import shutil
import subprocess
import platform
from datetime import datetime
from pathlib import Path

APP_NAME    = "NEXUS"
APP_TAGLINE = "NLE 통합 관제 플랫폼"
APP_VERSION = "1.1.0"
RECENT_LIMIT = 10  # 최근 프로젝트 표시 최대 개수

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QFrame, QStackedWidget, QLineEdit,
    QComboBox, QFileDialog, QScrollArea, QTreeWidget, QTreeWidgetItem,
    QMessageBox, QSizePolicy, QSpacerItem, QGridLayout, QCheckBox,
    QDialog, QTextEdit, QDialogButtonBox
)
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPalette, QIcon, QCursor

# ─────────────────────────────────────────────
# 색상 팔레트
# ─────────────────────────────────────────────
COLORS = {
    # 기반 배경 — 더 깊고 차분한 다크
    "bg":        "#09090b",
    "surface":   "#111114",
    "surface2":  "#18181c",
    "surface3":  "#1e1e24",
    "border":    "#27272f",
    "border2":   "#3a3a48",
    # 텍스트
    "text":      "#f0f0f8",
    "text2":     "#a8a8c0",
    "muted":     "#58586e",
    # NLE 브랜드 컬러
    "resolve":   "#f0b429",   # DaVinci — 황금
    "premiere":  "#9d9fff",   # Premiere — 보라
    "ae":        "#d080ff",   # AE — 마젠타
    # UI 액센트
    "accent":    "#4f8ef7",
    "accent2":   "#3b6fd4",
    "success":   "#34d17a",
    "warning":   "#f5a623",
    "danger":    "#ff4d4d",
}

# ─────────────────────────────────────────────
# 폴더 프리셋 (프로젝트 타입별)
# ─────────────────────────────────────────────
FOLDER_PRESETS = {
    "광고": [
        "01_FOOTAGE/RAW",
        "01_FOOTAGE/SELECTS",
        "02_AUDIO/MUSIC",
        "02_AUDIO/SFX",
        "02_AUDIO/VO",
        "03_GRAPHICS/AE_Projects",
        "03_GRAPHICS/Motion",
        "04_EDIT/Sequences",
        "04_EDIT/Exports",
        "05_DELIVERY/Master",
        "05_DELIVERY/Social",
        "06_DOCS/Brief",
        "06_DOCS/Scripts",
    ],
    "다큐": [
        "01_FOOTAGE/Camera_A",
        "01_FOOTAGE/Camera_B",
        "01_FOOTAGE/Archive",
        "01_FOOTAGE/SELECTS",
        "02_AUDIO/Interview",
        "02_AUDIO/Ambient",
        "02_AUDIO/Music",
        "03_GRAPHICS/Titles",
        "04_EDIT/Sequences",
        "04_EDIT/Exports",
        "05_DELIVERY/Master",
        "05_DELIVERY/Online",
        "06_DOCS/Research",
        "06_DOCS/Scripts",
    ],
    "MV": [
        "01_FOOTAGE/RAW",
        "01_FOOTAGE/SELECTS",
        "02_AUDIO/Reference",
        "02_AUDIO/Stems",
        "03_GRAPHICS/AE_Projects",
        "03_GRAPHICS/VFX",
        "04_EDIT/Sequences",
        "04_EDIT/Exports",
        "05_DELIVERY/Master",
        "05_DELIVERY/YouTube",
        "05_DELIVERY/Instagram",
        "06_DOCS/Concept",
        "06_DOCS/Lyrics",
    ],
    "단편": [
        "01_FOOTAGE/RAW",
        "01_FOOTAGE/SELECTS",
        "02_AUDIO/Production",
        "02_AUDIO/Music",
        "02_AUDIO/SFX",
        "02_AUDIO/Dialogue",
        "03_GRAPHICS/Titles",
        "04_EDIT/Sequences",
        "04_EDIT/Exports",
        "05_DELIVERY/DCP",
        "05_DELIVERY/Online",
        "06_DOCS/Script",
        "06_DOCS/Schedule",
    ],
    "이벤트": [
        "01_FOOTAGE/Main_Stage",
        "01_FOOTAGE/Behind",
        "01_FOOTAGE/SELECTS",
        "02_AUDIO/Sync",
        "02_AUDIO/Music",
        "03_GRAPHICS/Intro",
        "03_GRAPHICS/Lower_Thirds",
        "04_EDIT/Sequences",
        "04_EDIT/Exports",
        "05_DELIVERY/Highlight",
        "05_DELIVERY/Full",
        "06_DOCS/Runsheet",
    ],
    "유튜브": [
        "01_FOOTAGE/RAW",
        "01_FOOTAGE/SELECTS",
        "02_AUDIO/BGM",
        "02_AUDIO/SFX",
        "02_AUDIO/VO",
        "03_GRAPHICS/Thumbnail",
        "03_GRAPHICS/Intro_Outro",
        "04_EDIT/Sequences",
        "04_EDIT/Exports",
        "05_DELIVERY/YouTube",
        "05_DELIVERY/Shorts",
        "06_DOCS/Script",
    ],
}

# ─────────────────────────────────────────────
# Resolve 기술 스펙 매핑 테이블
# ─────────────────────────────────────────────
_RESOLVE_RESOLUTION_MAP: dict[str, tuple[str, str]] = {
    "4K UHD (3840×2160)":   ("3840", "2160"),
    "2K DCI (2048×1080)":   ("2048", "1080"),
    "FHD (1920×1080)":      ("1920", "1080"),
    "HD (1280×720)":        ("1280", "720"),
    "Vertical (1080×1920)": ("1080", "1920"),
}

# (colorScienceMode, colorSpaceTimeline)
_RESOLVE_COLORSPACE_MAP: dict[str, tuple[str, str]] = {
    "DaVinci Wide Gamut":  ("davinciYRGBColorManagedv2", "DaVinci WG/Intermediate"),
    "Rec. 709":            ("davinciYRGB",               "Rec.709 Gamma 2.4"),
    "Rec. 2020":           ("davinciYRGB",               "Rec.2020"),
    "S-Gamut3.Cine":       ("davinciYRGB",               "S-Gamut3.Cine/S-Log3"),
    "ARRI Wide Gamut 4":   ("davinciYRGB",               "ARRI LogC4/LogC4"),
    "P3-D65":              ("davinciYRGB",               "P3-D65/ST.2084"),
}

_RESOLVE_SAMPLERATE_MAP: dict[str, str] = {
    "48 kHz":   "48000",
    "44.1 kHz": "44100",
    "96 kHz":   "96000",
}


# ─────────────────────────────────────────────
# ProjectManager
# ─────────────────────────────────────────────
class ProjectManager:
    """프로젝트 데이터 관리 (저장/불러오기/CRUD)"""

    DATA_DIR: Path = (
        Path.home() / "Library" / "Application Support" / "VideoProjectSetup"
        if platform.system() == "Darwin"
        else Path.home() / "AppData" / "Roaming" / "VideoProjectSetup"
        if platform.system() == "Windows"
        else Path.home() / ".config" / "VideoProjectSetup"
    )

    def __init__(self):
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._file = self.DATA_DIR / "projects.json"
        self._settings_file = self.DATA_DIR / "settings.json"
        self.projects: list[dict] = []
        self.settings: dict = {}
        self.load()

    def load(self):
        if self._file.exists():
            try:
                self.projects = json.loads(self._file.read_text(encoding="utf-8"))
            except Exception:
                self.projects = []
        if self._settings_file.exists():
            try:
                self.settings = json.loads(self._settings_file.read_text(encoding="utf-8"))
            except Exception:
                self.settings = {}

    def save(self):
        self._file.write_text(
            json.dumps(self.projects, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def save_settings(self):
        self._settings_file.write_text(
            json.dumps(self.settings, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def add(self, project: dict) -> dict:
        project["id"] = str(uuid.uuid4())
        project["created_at"] = datetime.now().isoformat()
        project["last_opened"] = project["created_at"]
        self.projects.insert(0, project)
        self.save()
        return project

    def delete(self, project_id: str):
        self.projects = [p for p in self.projects if p.get("id") != project_id]
        self.save()

    def update_last_opened(self, project_id: str):
        for p in self.projects:
            if p.get("id") == project_id:
                p["last_opened"] = datetime.now().isoformat()
                break
        self.save()

    def create_folders(self, project: dict) -> bool:
        """프리셋(또는 커스텀) 폴더 생성 + project.json 저장"""
        try:
            base = Path(project["location"]) / project["name"]
            folders = (
                project.get("folders")
                or FOLDER_PRESETS.get(project.get("type", "유튜브"), FOLDER_PRESETS["유튜브"])
            )
            for folder in folders:
                (base / folder).mkdir(parents=True, exist_ok=True)
            # 메타데이터 저장
            meta = {k: v for k, v in project.items() if k != "id"}
            (base / "project.json").write_text(
                json.dumps(meta, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            return True
        except Exception as e:
            print(f"[ERROR] create_folders: {e}")
            return False

    def get_default_location(self) -> str:
        return self.settings.get("default_location", str(Path.home() / "Movies"))

    def set_default_location(self, path: str):
        self.settings["default_location"] = path
        self.save_settings()

    def get_custom_preset(self, project_type: str) -> list[str] | None:
        """커스텀 폴더 프리셋 반환. 설정 없으면 None."""
        return self.settings.get("custom_presets", {}).get(project_type)

    def set_custom_preset(self, project_type: str, folders: list[str] | None):
        """커스텀 폴더 프리셋 저장. folders=None이면 기본값으로 복원."""
        if "custom_presets" not in self.settings:
            self.settings["custom_presets"] = {}
        if folders is None:
            self.settings["custom_presets"].pop(project_type, None)
        else:
            self.settings["custom_presets"][project_type] = folders
        self.save_settings()

    def get_nle_override(self, app_key: str) -> str:
        """사용자가 수동으로 지정한 NLE 경로 반환"""
        return self.settings.get(f"nle_{app_key}", "")

    def set_nle_override(self, app_key: str, path: str):
        self.settings[f"nle_{app_key}"] = path
        self.save_settings()

    def validate_project(self, project: dict) -> tuple[bool, str]:
        """프로젝트 생성 전 유효성 검사. (bool, 오류메시지) 반환"""
        name = project.get("name", "").strip()
        location = project.get("location", "").strip()

        if not name:
            return False, "프로젝트 이름을 입력해주세요."

        # Windows 금지 문자 체크
        forbidden = set(r'\/:*?"<>|')
        bad_chars = [c for c in name if c in forbidden]
        if bad_chars:
            return False, f"프로젝트 이름에 사용할 수 없는 문자가 포함되어 있습니다: {'  '.join(bad_chars)}"

        if not location:
            return False, "저장 위치를 선택해주세요."
        if not Path(location).exists():
            return False, f"저장 위치가 존재하지 않습니다:\n{location}"

        return True, ""


# ─────────────────────────────────────────────
# NLE 앱 감지
# ─────────────────────────────────────────────
def find_app(app_name: str, override_path: str = "") -> str | None:
    """설치된 NLE 앱 경로 반환 (없으면 None). 수동 지정 경로 우선."""
    if override_path and Path(override_path).exists():
        return override_path

    os_name = platform.system()
    # 가장 최신 버전부터 탐색 (2026→2022)
    years = list(range(2026, 2021, -1))

    paths: dict[str, dict[str, list[str]]] = {
        "Resolve": {
            "Darwin": [
                "/Applications/DaVinci Resolve/DaVinci Resolve.app",
            ],
            "Windows": [
                r"C:\Program Files\Blackmagic Design\DaVinci Resolve\Resolve.exe",
            ],
        },
        "Premiere": {
            "Darwin": [
                f"/Applications/Adobe Premiere Pro {y}/Adobe Premiere Pro {y}.app"
                for y in years
            ],
            "Windows": [
                rf"C:\Program Files\Adobe\Adobe Premiere Pro {y}\Adobe Premiere Pro.exe"
                for y in years
            ],
        },
        "AE": {
            "Darwin": [
                f"/Applications/Adobe After Effects {y}/Adobe After Effects {y}.app"
                for y in years
            ],
            "Windows": [
                rf"C:\Program Files\Adobe\Adobe After Effects {y}\AfterFX.exe"
                for y in years
            ],
        },
    }

    for path_str in paths.get(app_name, {}).get(os_name, []):
        if Path(path_str).exists():
            return path_str
    return None


def launch_app(app_name: str, app_path: str | None = None, manager: "ProjectManager | None" = None) -> bool:
    """NLE 앱 실행"""
    override = manager.get_nle_override(app_name) if manager else ""
    path = app_path or find_app(app_name, override)
    if not path:
        return False
    try:
        if platform.system() == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen([path])
        return True
    except Exception as e:
        print(f"[ERROR] launch_app: {e}")
        return False


def open_folder(folder_path: str):
    """파일 탐색기로 폴더 열기"""
    try:
        if platform.system() == "Darwin":
            subprocess.Popen(["open", folder_path])
        elif platform.system() == "Windows":
            subprocess.Popen(["explorer", folder_path])
        else:
            subprocess.Popen(["xdg-open", folder_path])
    except Exception as e:
        print(f"[ERROR] open_folder: {e}")


# ─────────────────────────────────────────────
# NLE 프로젝트 / 빈 자동 생성
# ─────────────────────────────────────────────

def _jsx_bins_premiere(folders: list[str], project_name: str, prproj_path: str) -> str:
    """Premiere Pro ExtendScript: 새 프로젝트 생성 + 빈 트리 구성"""
    safe_path = prproj_path.replace("\\", "/")
    lines = [
        "// VPS Auto-generated — Adobe Premiere Pro Setup",
        f'// Project: {project_name}',
        "",
        f'app.newProject("{safe_path}");',
        "var root = app.project.rootItem;",
        "",
    ]
    var_map: dict[str, str] = {}
    counter = [0]

    for path in folders:
        parts = path.split("/")
        cumulative = ""
        parent_var = "root"
        for part in parts:
            cumulative = f"{cumulative}/{part}" if cumulative else part
            if cumulative not in var_map:
                counter[0] += 1
                vname = f"b{counter[0]}"
                var_map[cumulative] = vname
                safe = part.replace('"', '\\"')
                lines.append(f'var {vname} = {parent_var}.createBin("{safe}");')
            parent_var = var_map[cumulative]

    lines += [
        "",
        "app.project.save();",
        f'$.writeln("VPS: {project_name} 생성 완료");',
    ]
    return "\n".join(lines)


def _jsx_bins_ae(folders: list[str], project_name: str, aep_path: str) -> str:
    """After Effects ExtendScript: 새 프로젝트 생성 + 폴더 트리 구성"""
    safe_path = aep_path.replace("\\", "/")
    lines = [
        "// VPS Auto-generated — Adobe After Effects Setup",
        f'// Project: {project_name}',
        "",
        "app.newProject();",
        "",
        "function mkFolder(name) { return app.project.items.addFolder(name); }",
        "",
    ]
    var_map: dict[str, str] = {}
    counter = [0]

    for path in folders:
        parts = path.split("/")
        cumulative = ""
        for i, part in enumerate(parts):
            cumulative = f"{cumulative}/{part}" if cumulative else part
            if cumulative not in var_map:
                counter[0] += 1
                vname = f"f{counter[0]}"
                var_map[cumulative] = vname
                safe = part.replace('"', '\\"')
                lines.append(f'var {vname} = mkFolder("{safe}");')
                if i > 0:
                    parent_key = "/".join(parts[:i])
                    parent_var = var_map.get(parent_key, "")
                    if parent_var:
                        lines.append(f"{vname}.parentFolder = {parent_var};")

    lines += [
        "",
        f'var saveFile = new File("{safe_path}");',
        "app.project.save(saveFile);",
        f'alert("VPS: {project_name}.aep 생성 완료!");',
    ]
    return "\n".join(lines)


def create_premiere_project(project: dict, base_path: Path) -> tuple[bool, str]:
    """
    Premiere Pro 프로젝트 자동 생성.
    JSX 스크립트를 생성하고 실행 중인 Premiere에 osascript로 전달 (macOS).
    """
    name = project["name"]
    prproj_path = base_path / f"{name}.prproj"
    jsx_path = base_path / f"_setup_premiere.jsx"

    folders = project.get("folders") or FOLDER_PRESETS.get(project.get("type", "유튜브"), [])
    jsx_path.write_text(
        _jsx_bins_premiere(folders, name, str(prproj_path)),
        encoding="utf-8"
    )

    if platform.system() == "Darwin":
        premiere_path = find_app("Premiere")
        if premiere_path:
            app_stem = Path(premiere_path).stem
            osa = f'tell application "{app_stem}" to do script "{str(jsx_path)}"'
            result = subprocess.run(
                ["osascript", "-e", osa],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                return True, f"Premiere 빈 구성 완료 → {prproj_path.name}"

    # Windows 또는 osascript 실패 → 수동 안내
    return True, (
        f"JSX 스크립트 생성됨: {jsx_path.name}\n"
        "Premiere 실행 후 File > Scripts > Browse 로 직접 실행하세요."
    )


def create_ae_project(project: dict, base_path: Path) -> tuple[bool, str]:
    """
    After Effects 프로젝트 자동 생성.
    JSX 생성 후 afterfx 바이너리를 -r flag로 실행.
    """
    name = project["name"]
    aep_path = base_path / f"{name}.aep"
    jsx_path = base_path / f"_setup_ae.jsx"

    folders = project.get("folders") or FOLDER_PRESETS.get(project.get("type", "유튜브"), [])
    jsx_path.write_text(
        _jsx_bins_ae(folders, name, str(aep_path)),
        encoding="utf-8"
    )

    ae_app = find_app("AE")
    ae_bin: str | None = None
    if ae_app:
        if platform.system() == "Darwin":
            candidates = list(Path(ae_app).glob("Contents/MacOS/After Effects*"))
            if candidates:
                ae_bin = str(candidates[0])
        else:
            ae_bin = ae_app  # Windows: .exe 직접

    if ae_bin and Path(ae_bin).exists():
        subprocess.Popen([ae_bin, "-r", str(jsx_path)])
        return True, f"AE 실행 중 — 스크립트로 {name}.aep 자동 생성됩니다"

    return True, (
        f"JSX 스크립트 생성됨: {jsx_path.name}\n"
        "AE 실행 후 File > Scripts > Run Script File 로 직접 실행하세요."
    )


def setup_resolve_bins(project: dict, base_path: Path | None = None) -> tuple[bool, str]:
    """
    DaVinci Resolve Python Scripting API로 프로젝트 + 빈 트리 생성.
    base_path 지정 시 .drp 아카이브를 해당 폴더에 내보냄 (Resolve 미실행 시 import 가능).
    Resolve가 실행 중이어야 합니다.
    """
    if platform.system() == "Darwin":
        modules_path = (
            "/Library/Application Support/Blackmagic Design"
            "/DaVinci Resolve/Developer/Scripting/Modules"
        )
    elif platform.system() == "Windows":
        modules_path = (
            r"C:\ProgramData\Blackmagic Design\DaVinci Resolve"
            r"\Support\Developer\Scripting\Modules"
        )
    else:
        return False, "지원하지 않는 OS입니다"

    if not Path(modules_path).exists():
        return False, f"Resolve Scripting Modules 없음:\n{modules_path}"

    if modules_path not in sys.path:
        sys.path.insert(0, modules_path)

    try:
        import DaVinciResolveScript as dvr_script  # type: ignore
    except ImportError as e:
        return False, f"DaVinciResolveScript 임포트 실패: {e}"

    try:
        resolve = dvr_script.scriptapp("Resolve")
    except Exception as e:
        return False, f"Resolve 연결 오류: {e}"

    if not resolve:
        return False, "Resolve가 실행 중이지 않거나 응답이 없습니다\n(Resolve를 먼저 실행해주세요)"

    pm = resolve.GetProjectManager()
    if not pm:
        return False, "ProjectManager를 가져올 수 없습니다"

    name = project["name"]
    new_proj = pm.CreateProject(name)
    if not new_proj:
        return False, f"프로젝트 '{name}' 생성 실패\n(이름 중복 또는 권한 문제)"

    media_pool = new_proj.GetMediaPool()
    root_folder = media_pool.GetRootFolder()
    folders = project.get("folders") or FOLDER_PRESETS.get(project.get("type", "유튜브"), [])
    _resolve_bin_tree(media_pool, root_folder, folders)

    # 기술 스펙 전체 적용 (해상도 / FPS / 색상 공간 / 샘플 레이트)
    _apply_resolve_settings(new_proj, project.get("spec", {}))

    # .drp 아카이브 내보내기 (로컬 import용)
    drp_exported = False
    if base_path:
        drp_path = base_path / f"{name}.drp"
        try:
            drp_exported = pm.ExportProject(name, str(drp_path), False)
        except Exception:
            pass

    msg = f"Resolve 프로젝트 '{name}' + 빈 구조 생성 완료"
    if drp_exported:
        msg += f"\n📦 {name}.drp 저장됨 (나중에 File > Import Project로 불러올 수 있습니다)"
    return True, msg


def _apply_resolve_settings(proj_obj, spec: dict):
    """Resolve 프로젝트에 기술 스펙(해상도/FPS/색상공간/샘플레이트) 적용"""
    # 해상도
    res_str = spec.get("resolution", "")
    if res_str in _RESOLVE_RESOLUTION_MAP:
        w, h = _RESOLVE_RESOLUTION_MAP[res_str]
        try:
            proj_obj.SetSetting("timelineResolutionWidth", w)
            proj_obj.SetSetting("timelineResolutionHeight", h)
        except Exception:
            pass

    # FPS (23.976, 29.97 등 소수점 포함 문자열 그대로 전달)
    fps_str = spec.get("fps", "")
    if fps_str:
        try:
            proj_obj.SetSetting("timelineFrameRate", fps_str)
        except Exception:
            pass

    # 색상 공간
    cs_str = spec.get("colorspace", "")
    if cs_str in _RESOLVE_COLORSPACE_MAP:
        science_mode, timeline_cs = _RESOLVE_COLORSPACE_MAP[cs_str]
        try:
            proj_obj.SetSetting("colorScienceMode", science_mode)
            proj_obj.SetSetting("colorSpaceTimeline", timeline_cs)
        except Exception:
            pass

    # 오디오 샘플 레이트
    sr_str = spec.get("samplerate", "")
    if sr_str in _RESOLVE_SAMPLERATE_MAP:
        try:
            proj_obj.SetSetting("timelineAudioSampleRate", _RESOLVE_SAMPLERATE_MAP[sr_str])
        except Exception:
            pass


def _resolve_bin_tree(media_pool, parent_folder, folder_paths: list[str]):
    """폴더 경로 리스트로 Resolve 빈 트리 생성"""
    created: dict[str, object] = {}
    for path in folder_paths:
        parts = path.split("/")
        cur = parent_folder
        cumulative = ""
        for part in parts:
            cumulative = f"{cumulative}/{part}" if cumulative else part
            if cumulative not in created:
                new_bin = media_pool.AddSubFolder(cur, part)
                created[cumulative] = new_bin
            cur = created[cumulative]


# ─────────────────────────────────────────────
# 버전 스냅샷 관리
# ─────────────────────────────────────────────

def get_project_versions(folder: Path, name: str) -> list[dict]:
    """
    프로젝트 폴더에서 버전 파일 탐색.
    패턴: ProjectName_V001.drp, ProjectName_V002.drp ...
    최신 버전 순으로 정렬해서 반환.
    """
    pattern = re.compile(rf'^{re.escape(name)}_V(\d+)\.drp$', re.IGNORECASE)
    versions = []
    for drp in folder.glob("*.drp"):
        m = pattern.match(drp.name)
        if m:
            stat = drp.stat()
            versions.append({
                "version":  int(m.group(1)),
                "path":     drp,
                "size_mb":  stat.st_size / (1024 * 1024),
                "modified": datetime.fromtimestamp(stat.st_mtime),
                "label":    f"V{int(m.group(1)):03d}",
            })
    return sorted(versions, key=lambda v: v["version"], reverse=True)


def create_smart_snapshot(project: dict) -> tuple[bool, str]:
    """
    스마트 스냅샷: 실행 중인 Resolve에서 현재 프로젝트 상태를 API로 내보낸 후 버전 파일로 저장.
    Resolve가 실행 중이지 않거나 해당 프로젝트가 열려있지 않으면 기존 .drp 파일 복사로 폴백.
    """
    folder = Path(project.get("location", "")) / project.get("name", "")
    name   = project.get("name", "")
    drp    = folder / f"{name}.drp"

    existing = get_project_versions(folder, name)
    next_v   = (max(v["version"] for v in existing) + 1) if existing else 1
    target   = folder / f"{name}_V{next_v:03d}.drp"

    # 1단계: Resolve API로 현재 상태 직접 내보내기 시도
    export_note = ""
    exported = False
    try:
        if platform.system() == "Darwin":
            mpath = ("/Library/Application Support/Blackmagic Design"
                     "/DaVinci Resolve/Developer/Scripting/Modules")
        elif platform.system() == "Windows":
            mpath = (r"C:\ProgramData\Blackmagic Design\DaVinci Resolve"
                     r"\Support\Developer\Scripting\Modules")
        else:
            mpath = ""
        if mpath and Path(mpath).exists():
            if mpath not in sys.path:
                sys.path.insert(0, mpath)
            import DaVinciResolveScript as dvr_script  # type: ignore
            resolve = dvr_script.scriptapp("Resolve")
            if resolve:
                pm = resolve.GetProjectManager()
                if pm:
                    cur = pm.GetCurrentProject()
                    if cur and cur.GetName() == name:
                        # 현재 열린 프로젝트와 이름이 일치 → API로 직접 내보내기
                        ok = pm.ExportProject(name, str(target), False)
                        if ok:
                            exported = True
                            export_note = "  [Resolve 현재 작업 상태]"
                    elif cur:
                        export_note = f"\n⚠ Resolve에 '{cur.GetName()}' 프로젝트가 열려 있어 파일 복사로 대체했습니다."
    except Exception:
        pass

    # 2단계: Resolve 내보내기 실패 → 기존 .drp 파일 복사 폴백
    if not exported:
        if not drp.exists():
            return False, (
                f"{name}.drp 파일을 찾을 수 없습니다.\n"
                "Resolve에서 해당 프로젝트를 열고 스냅샷을 생성해주세요."
            )
        shutil.copy2(drp, target)

    size_mb = target.stat().st_size / (1024 * 1024)
    return True, f"스냅샷 저장됨: {target.name}  ({size_mb:.1f} MB){export_note}"


# 하위 호환 별칭 (restore_version 내부에서 호출)
def create_version_snapshot(project: dict) -> tuple[bool, str]:
    return create_smart_snapshot(project)


def restore_version(version_path: Path, project: dict) -> tuple[bool, str]:
    """
    선택한 버전의 .drp를 현재 ProjectName.drp로 복원 (덮어쓰기).
    복원 전 현재 상태를 자동 백업.
    """
    folder = Path(project.get("location", "")) / project.get("name", "")
    name   = project.get("name", "")
    drp    = folder / f"{name}.drp"

    # 복원 전 현재 상태 백업
    if drp.exists():
        backup_ok, backup_msg = create_version_snapshot(project)
        if not backup_ok:
            return False, f"복원 전 백업 실패: {backup_msg}"

    shutil.copy2(version_path, drp)
    return True, (
        f"{version_path.name} → {name}.drp 복원 완료\n"
        "Resolve에서 File > Import Project로 복원된 파일을 불러오세요."
    )


def detect_project_nles(project: dict) -> set[str]:
    """프로젝트 폴더의 파일 존재 여부로 NLE 사용 여부 탐지"""
    folder = Path(project.get("location", "")) / project.get("name", "")
    name   = project.get("name", "")
    nles: set[str] = set()
    if not folder.exists():
        return nles
    if (folder / f"{name}.drp").exists() or any(folder.glob(f"{name}_V*.drp")):
        nles.add("Resolve")
    if any(folder.glob(f"{name}*.prproj")):
        nles.add("Premiere")
    if any(folder.glob(f"{name}*.aep")):
        nles.add("AE")
    return nles


def _resolve_import_drp(drp_path: str) -> tuple[bool, str]:
    """실행 중인 Resolve에 .drp 파일을 API로 import"""
    if platform.system() == "Darwin":
        modules_path = (
            "/Library/Application Support/Blackmagic Design"
            "/DaVinci Resolve/Developer/Scripting/Modules"
        )
    elif platform.system() == "Windows":
        modules_path = (
            r"C:\ProgramData\Blackmagic Design\DaVinci Resolve"
            r"\Support\Developer\Scripting\Modules"
        )
    else:
        return False, "지원하지 않는 OS"

    if not Path(modules_path).exists():
        return False, "Resolve Scripting Modules 없음"
    if modules_path not in sys.path:
        sys.path.insert(0, modules_path)
    try:
        import DaVinciResolveScript as dvr_script  # type: ignore
        resolve = dvr_script.scriptapp("Resolve")
    except Exception:
        resolve = None

    if not resolve:
        return False, "Resolve가 실행 중이지 않습니다"

    pm = resolve.GetProjectManager()
    if not pm:
        return False, "ProjectManager를 가져올 수 없습니다"

    ok = pm.ImportProject(drp_path)
    if ok:
        name = Path(drp_path).stem
        pm.LoadProject(name)
        return True, f"'{name}' 프로젝트가 Resolve에 import 되었습니다"
    return False, f"Import 실패: {drp_path}"


class ResolveSetupWorker(QThread):
    """
    Resolve가 꺼져있을 때:
      1. Resolve 자동 실행
      2. API 연결될 때까지 최대 90초 대기
      3. 연결 성공 → 프로젝트 + 빈 생성 + .drp 내보내기
    """
    status_changed = pyqtSignal(str)   # 진행 상태 텍스트
    finished = pyqtSignal(bool, str)   # (성공여부, 메시지)

    _RETRY_INTERVAL = 3   # 재시도 간격 (초)
    _MAX_RETRIES    = 30  # 최대 재시도 횟수 (90초)

    def __init__(self, project: dict, base_path: Path):
        super().__init__()
        self.project   = project
        self.base_path = base_path

    def run(self):
        import time

        self.status_changed.emit("DaVinci Resolve 실행 중...")
        launch_app("Resolve")

        for attempt in range(self._MAX_RETRIES):
            time.sleep(self._RETRY_INTERVAL)
            elapsed = (attempt + 1) * self._RETRY_INTERVAL
            self.status_changed.emit(
                f"Resolve 연결 대기 중... {elapsed}초"
            )
            ok, msg = setup_resolve_bins(self.project, self.base_path)
            if ok:
                self.finished.emit(True, msg)
                return
            # "실행 중이지 않" / "응답이 없" 이외의 오류는 재시도 불필요
            if "실행 중이지 않" not in msg and "응답이 없" not in msg:
                self.finished.emit(False, msg)
                return

        self.finished.emit(
            False,
            "Resolve 시작 대기 시간 초과 (90초)\n"
            "Resolve를 직접 실행 후 '최근 프로젝트' 탭에서 [Resolve 연결] 버튼을 눌러주세요."
        )


# ─────────────────────────────────────────────
# 공통 스타일 유틸
# ─────────────────────────────────────────────
def make_button(text: str, color: str = COLORS["accent"], small: bool = False) -> QPushButton:
    btn = QPushButton(text)
    h = 32 if small else 40
    pad = "6px 14px" if small else "8px 20px"
    btn.setStyleSheet(f"""
        QPushButton {{
            background: {color};
            color: #ffffff;
            border: none;
            border-radius: 6px;
            font-size: {'12px' if small else '13px'};
            font-weight: 600;
            padding: {pad};
            min-height: {h}px;
        }}
        QPushButton:hover {{
            background: {color}cc;
        }}
        QPushButton:pressed {{
            background: {color}99;
        }}
        QPushButton:disabled {{
            background: {COLORS['surface2']};
            color: {COLORS['muted']};
        }}
    """)
    btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    return btn


def make_ghost_button(text: str, color: str = COLORS["text"], small: bool = False) -> QPushButton:
    btn = QPushButton(text)
    h = 32 if small else 38
    btn.setStyleSheet(f"""
        QPushButton {{
            background: transparent;
            color: {color};
            border: 1px solid {COLORS['border']};
            border-radius: 6px;
            font-size: {'12px' if small else '13px'};
            font-weight: 500;
            padding: {'5px 12px' if small else '7px 16px'};
            min-height: {h}px;
        }}
        QPushButton:hover {{
            background: {COLORS['surface2']};
            border-color: {color}66;
        }}
        QPushButton:pressed {{
            background: {COLORS['surface']};
        }}
    """)
    btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    return btn


def labeled_input(label_text: str, placeholder: str = "") -> tuple[QLabel, QLineEdit]:
    lbl = QLabel(label_text)
    lbl.setStyleSheet(f"color: {COLORS['muted']}; font-size: 12px; font-weight: 500; margin-bottom: 4px;")
    inp = QLineEdit()
    inp.setPlaceholderText(placeholder)
    inp.setStyleSheet(f"""
        QLineEdit {{
            background: {COLORS['surface2']};
            border: 1px solid {COLORS['border']};
            border-radius: 6px;
            color: {COLORS['text']};
            font-size: 13px;
            padding: 8px 12px;
            min-height: 36px;
        }}
        QLineEdit:focus {{
            border-color: {COLORS['accent']};
        }}
    """)
    return lbl, inp


def make_combo(items: list[str]) -> QComboBox:
    cb = QComboBox()
    cb.addItems(items)
    cb.setStyleSheet(f"""
        QComboBox {{
            background: {COLORS['surface2']};
            border: 1px solid {COLORS['border']};
            border-radius: 6px;
            color: {COLORS['text']};
            font-size: 13px;
            padding: 6px 12px;
            min-height: 36px;
        }}
        QComboBox:focus {{
            border-color: {COLORS['accent']};
        }}
        QComboBox QAbstractItemView {{
            background: {COLORS['surface']};
            border: 1px solid {COLORS['border']};
            color: {COLORS['text']};
            selection-background-color: {COLORS['accent']};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 24px;
        }}
    """)
    return cb


def section_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(f"""
        color: {COLORS['muted']};
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 1px;
        text-transform: uppercase;
        padding: 12px 0 6px 0;
    """)
    return lbl


def divider() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet(f"background: {COLORS['border']}; max-height: 1px; border: none;")
    return line


# ─────────────────────────────────────────────
# FolderTreeEditDialog (커스텀 폴더 트리 편집)
# ─────────────────────────────────────────────
class FolderTreeEditDialog(QDialog):
    def __init__(self, project_type: str, folders: list[str], parent=None):
        super().__init__(parent)
        self._project_type = project_type
        self._reset = False
        self.setWindowTitle(f"폴더 트리 편집 — {project_type}")
        self.setMinimumSize(500, 420)
        self.setStyleSheet(f"""
            QDialog {{
                background: {COLORS['surface']};
            }}
            QLabel {{
                background: transparent;
            }}
        """)
        self._setup_ui(folders)

    def _setup_ui(self, folders: list[str]):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel(f"폴더 트리 편집  ·  {self._project_type}")
        title.setStyleSheet(
            f"color: {COLORS['text']}; font-size: 16px; font-weight: 700;"
        )
        layout.addWidget(title)

        hint = QLabel(
            "한 줄에 하나씩 폴더 경로를 입력하세요.\n"
            "'/' 로 하위 폴더를 표현합니다.  예)  01_FOOTAGE/RAW"
        )
        hint.setStyleSheet(f"color: {COLORS['muted']}; font-size: 12px;")
        layout.addWidget(hint)

        self.editor = QTextEdit()
        self.editor.setPlainText("\n".join(folders))
        self.editor.setStyleSheet(f"""
            QTextEdit {{
                background: {COLORS['surface2']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                color: {COLORS['text']};
                font-size: 13px;
                font-family: monospace;
                padding: 10px;
            }}
            QTextEdit:focus {{
                border-color: {COLORS['accent']};
            }}
        """)
        layout.addWidget(self.editor)

        btn_row = QHBoxLayout()

        reset_btn = make_ghost_button("기본값 복원", color=COLORS["warning"], small=True)
        reset_btn.clicked.connect(self._on_reset)
        btn_row.addWidget(reset_btn)
        btn_row.addStretch()

        cancel_btn = make_ghost_button("취소", small=True)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = make_button("저장", COLORS["accent"], small=True)
        save_btn.clicked.connect(self.accept)
        btn_row.addWidget(save_btn)

        layout.addLayout(btn_row)

    def _on_reset(self):
        self._reset = True
        self.accept()

    def get_folders(self) -> list[str] | None:
        """None 반환 = 기본값으로 복원, list 반환 = 커스텀 폴더 목록"""
        if self._reset:
            return None
        lines = self.editor.toPlainText().strip().splitlines()
        return [ln.strip() for ln in lines if ln.strip()]


# ─────────────────────────────────────────────
# NewProjectPage
# ─────────────────────────────────────────────
class NewProjectPage(QWidget):
    project_created = pyqtSignal(dict)

    PROJECT_TYPES = ["광고", "다큐", "MV", "단편", "이벤트", "유튜브"]

    def __init__(self, manager: ProjectManager):
        super().__init__()
        self.manager = manager
        self._selected_type = "유튜브"
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet(f"background: {COLORS['bg']};")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # 스크롤 영역
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        inner = QWidget()
        inner.setStyleSheet(f"background: {COLORS['bg']};")
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(40, 32, 40, 40)
        layout.setSpacing(4)

        # 페이지 타이틀
        title = QLabel("새 프로젝트")
        title.setStyleSheet(f"color: {COLORS['text']}; font-size: 22px; font-weight: 700; margin-bottom: 4px;")
        layout.addWidget(title)
        sub = QLabel("프로젝트 설정 후 폴더 구조를 자동으로 생성합니다")
        sub.setStyleSheet(f"color: {COLORS['muted']}; font-size: 13px; margin-bottom: 16px;")
        layout.addWidget(sub)
        layout.addWidget(divider())

        # ── 프로젝트 정보 ──
        layout.addWidget(section_label("프로젝트 정보"))
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(12)

        lbl_name, self.inp_name = labeled_input("프로젝트 이름 *", "Project_Name_YYMMDD")
        grid.addWidget(lbl_name, 0, 0)
        grid.addWidget(self.inp_name, 1, 0)

        lbl_client, self.inp_client = labeled_input("클라이언트", "클라이언트 / 브랜드명")
        grid.addWidget(lbl_client, 0, 1)
        grid.addWidget(self.inp_client, 1, 1)

        layout.addLayout(grid)

        # 저장 위치
        lbl_loc = QLabel("저장 위치 *")
        lbl_loc.setStyleSheet(f"color: {COLORS['muted']}; font-size: 12px; font-weight: 500; margin-top: 8px; margin-bottom: 4px;")
        layout.addWidget(lbl_loc)

        loc_row = QHBoxLayout()
        self.inp_location = QLineEdit()
        self.inp_location.setText(self.manager.get_default_location())
        self.inp_location.setStyleSheet(f"""
            QLineEdit {{
                background: {COLORS['surface2']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                color: {COLORS['text']};
                font-size: 13px;
                padding: 8px 12px;
                min-height: 36px;
            }}
            QLineEdit:focus {{ border-color: {COLORS['accent']}; }}
        """)
        browse_btn = make_ghost_button("찾아보기", small=True)
        browse_btn.clicked.connect(self._browse_location)
        loc_row.addWidget(self.inp_location)
        loc_row.addWidget(browse_btn)
        layout.addLayout(loc_row)

        # ── 프로젝트 타입 ──
        layout.addWidget(section_label("프로젝트 타입"))
        type_row = QHBoxLayout()
        type_row.setSpacing(8)
        self._type_buttons: dict[str, QPushButton] = {}
        for pt in self.PROJECT_TYPES:
            btn = QPushButton(pt)
            btn.setCheckable(True)
            btn.setChecked(pt == self._selected_type)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            self._style_type_btn(btn, btn.isChecked())
            btn.toggled.connect(lambda checked, b=btn, t=pt: self._on_type_toggled(b, t, checked))
            self._type_buttons[pt] = btn
            type_row.addWidget(btn)
        type_row.addStretch()
        layout.addLayout(type_row)

        # ── 기술 스펙 + Bin 미리보기 (가로 분할) ──
        layout.addWidget(section_label("기술 스펙"))
        spec_preview_row = QHBoxLayout()
        spec_preview_row.setSpacing(24)

        # 기술 스펙 (좌)
        spec_widget = QWidget()
        spec_layout = QVBoxLayout(spec_widget)
        spec_layout.setContentsMargins(0, 0, 0, 0)
        spec_layout.setSpacing(10)

        spec_grid = QGridLayout()
        spec_grid.setHorizontalSpacing(16)
        spec_grid.setVerticalSpacing(10)

        lbl_res = QLabel("해상도")
        lbl_res.setStyleSheet(f"color: {COLORS['muted']}; font-size: 12px;")
        self.cb_resolution = make_combo(["4K UHD (3840×2160)", "2K DCI (2048×1080)", "FHD (1920×1080)", "HD (1280×720)", "Vertical (1080×1920)"])
        spec_grid.addWidget(lbl_res, 0, 0)
        spec_grid.addWidget(self.cb_resolution, 1, 0)

        lbl_fps = QLabel("FPS")
        lbl_fps.setStyleSheet(f"color: {COLORS['muted']}; font-size: 12px;")
        self.cb_fps = make_combo(["23.976", "24", "25", "29.97", "30", "50", "59.94", "60"])
        spec_grid.addWidget(lbl_fps, 0, 1)
        spec_grid.addWidget(self.cb_fps, 1, 1)

        lbl_cs = QLabel("색상 공간")
        lbl_cs.setStyleSheet(f"color: {COLORS['muted']}; font-size: 12px;")
        self.cb_colorspace = make_combo(["DaVinci Wide Gamut", "Rec. 709", "Rec. 2020", "S-Gamut3.Cine", "ARRI Wide Gamut 4", "P3-D65"])
        spec_grid.addWidget(lbl_cs, 2, 0)
        spec_grid.addWidget(self.cb_colorspace, 3, 0)

        lbl_sr = QLabel("샘플 레이트")
        lbl_sr.setStyleSheet(f"color: {COLORS['muted']}; font-size: 12px;")
        self.cb_samplerate = make_combo(["48 kHz", "44.1 kHz", "96 kHz"])
        spec_grid.addWidget(lbl_sr, 2, 1)
        spec_grid.addWidget(self.cb_samplerate, 3, 1)

        spec_layout.addLayout(spec_grid)
        spec_layout.addStretch()
        spec_preview_row.addWidget(spec_widget)

        # Bin 트리 미리보기 (우)
        tree_widget = QWidget()
        tree_layout = QVBoxLayout(tree_widget)
        tree_layout.setContentsMargins(0, 0, 0, 0)
        tree_layout.setSpacing(6)
        tree_hdr = QHBoxLayout()
        tree_lbl = QLabel("폴더 구조 미리보기")
        tree_lbl.setStyleSheet(f"color: {COLORS['muted']}; font-size: 12px; font-weight: 500;")
        tree_hdr.addWidget(tree_lbl)
        tree_hdr.addStretch()
        edit_tree_btn = make_ghost_button("편집", small=True)
        edit_tree_btn.clicked.connect(self._edit_folder_tree)
        tree_hdr.addWidget(edit_tree_btn)
        tree_layout.addLayout(tree_hdr)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setStyleSheet(f"""
            QTreeWidget {{
                background: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                color: {COLORS['text']};
                font-size: 12px;
                padding: 6px;
            }}
            QTreeWidget::item {{ padding: 2px 4px; }}
            QTreeWidget::item:hover {{ background: {COLORS['surface2']}; border-radius: 4px; }}
            QTreeWidget::branch:has-children:closed {{ border-image: none; }}
            QTreeWidget::branch:has-children:open {{ border-image: none; }}
        """)
        self.tree.setMinimumHeight(200)
        self.tree.setMaximumWidth(300)
        self._refresh_tree()
        tree_layout.addWidget(self.tree)
        spec_preview_row.addWidget(tree_widget)

        layout.addLayout(spec_preview_row)

        # ── NLE 프로젝트 자동 생성 ──
        layout.addWidget(section_label("NLE 프로젝트 자동 생성"))
        self._detected_apps = self._detect_apps()

        nle_row = QHBoxLayout()
        nle_row.setSpacing(8)
        self._nle_checks: dict[str, QCheckBox] = {}

        nle_defs = [
            ("Resolve",  "DaVinci Resolve", COLORS["resolve"]),
            ("Premiere", "Premiere Pro",    COLORS["premiere"]),
            ("AE",       "After Effects",   COLORS["ae"]),
        ]
        for key, display, color in nle_defs:
            detected = bool(self._detected_apps.get(key))
            cb = QCheckBox(display)
            cb.setEnabled(detected)
            cb.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            if detected:
                cb.setStyleSheet(f"""
                    QCheckBox {{
                        color: {color};
                        font-size: 13px;
                        font-weight: 600;
                        spacing: 6px;
                        padding: 7px 14px;
                        background: {color}18;
                        border: 1px solid {color}44;
                        border-radius: 6px;
                    }}
                    QCheckBox::indicator {{
                        width: 15px; height: 15px;
                        border-radius: 3px;
                        border: 1.5px solid {color};
                        background: transparent;
                    }}
                    QCheckBox::indicator:checked {{
                        background: {color};
                        border-color: {color};
                    }}
                """)
            else:
                cb.setStyleSheet(f"""
                    QCheckBox {{
                        color: {COLORS['muted']};
                        font-size: 13px;
                        spacing: 6px;
                        padding: 7px 14px;
                        background: {COLORS['surface2']};
                        border: 1px solid {COLORS['border']};
                        border-radius: 6px;
                    }}
                    QCheckBox::indicator {{
                        width: 15px; height: 15px;
                        border-radius: 3px;
                        border: 1.5px solid {COLORS['border']};
                        background: transparent;
                    }}
                """)
            self._nle_checks[key] = cb
            nle_row.addWidget(cb)
        nle_row.addStretch()
        layout.addLayout(nle_row)

        resolve_note = QLabel(
            "Resolve: 실행 중인 Resolve에 API 연결 후 빈 자동 생성  ·  "
            "Premiere/AE: 프로젝트 파일 생성 후 빈 구성"
        )
        resolve_note.setStyleSheet(f"color: {COLORS['muted']}; font-size: 11px; margin-top: 2px;")
        layout.addWidget(resolve_note)

        # ── 실행 옵션 ──
        layout.addWidget(section_label("생성 후 실행"))
        app_items = ["실행 안 함"] + [
            {"Resolve": "DaVinci Resolve", "Premiere": "Adobe Premiere", "AE": "After Effects"}[k]
            for k, v in self._detected_apps.items() if v
        ]
        self.cb_launch = make_combo(app_items)
        layout.addWidget(self.cb_launch)

        # ── 생성 버튼 ──
        layout.addSpacing(20)
        self.btn_create = make_button("  프로젝트 생성", COLORS["success"])
        self.btn_create.setMinimumHeight(48)
        self.btn_create.setStyleSheet(self.btn_create.styleSheet() + "font-size: 15px;")
        self.btn_create.clicked.connect(self._create_project)
        layout.addWidget(self.btn_create)

        layout.addStretch()
        scroll.setWidget(inner)
        outer.addWidget(scroll)

    def _style_type_btn(self, btn: QPushButton, active: bool):
        if active:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {COLORS['accent']};
                    color: #ffffff;
                    border: 1px solid {COLORS['accent']};
                    border-radius: 6px;
                    font-size: 13px;
                    font-weight: 600;
                    padding: 7px 16px;
                    min-width: 70px;
                }}
            """)
        else:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {COLORS['surface2']};
                    color: {COLORS['muted']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 6px;
                    font-size: 13px;
                    font-weight: 500;
                    padding: 7px 16px;
                    min-width: 70px;
                }}
                QPushButton:hover {{
                    background: {COLORS['border']};
                    color: {COLORS['text']};
                }}
            """)

    def _on_type_toggled(self, btn: QPushButton, type_name: str, checked: bool):
        if checked:
            # 다른 버튼 해제
            for t, b in self._type_buttons.items():
                if t != type_name and b.isChecked():
                    b.blockSignals(True)
                    b.setChecked(False)
                    b.blockSignals(False)
                    self._style_type_btn(b, False)
            self._selected_type = type_name
            self._style_type_btn(btn, True)
            self._refresh_tree()
        else:
            # 아무것도 선택 안된 상태 방지
            if self._selected_type == type_name:
                btn.blockSignals(True)
                btn.setChecked(True)
                btn.blockSignals(False)
            self._style_type_btn(btn, True)

    def _refresh_tree(self):
        self.tree.clear()
        project_name = self.inp_name.text() or "PROJECT_NAME"
        custom = self.manager.get_custom_preset(self._selected_type)
        is_custom = custom is not None
        folders = custom if is_custom else FOLDER_PRESETS.get(self._selected_type, [])
        root_label = f"📁 {project_name}" + ("  *" if is_custom else "")
        root = QTreeWidgetItem(self.tree, [root_label])
        root.setForeground(0, QColor(COLORS["accent"] if is_custom else COLORS["text"]))
        # 트리 빌드
        nodes: dict[str, QTreeWidgetItem] = {}
        for path in folders:
            parts = path.split("/")
            parent = root
            cumulative = ""
            for part in parts:
                cumulative = f"{cumulative}/{part}" if cumulative else part
                if cumulative not in nodes:
                    item = QTreeWidgetItem(parent, [f"📂 {part}"])
                    item.setForeground(0, QColor(COLORS["muted"]))
                    nodes[cumulative] = item
                parent = nodes[cumulative]
        meta_item = QTreeWidgetItem(root, ["📄 project.json"])
        meta_item.setForeground(0, QColor(COLORS["muted"]))
        self.tree.expandAll()

    def _browse_location(self):
        path = QFileDialog.getExistingDirectory(
            self, "저장 위치 선택", self.inp_location.text()
        )
        if path:
            self.inp_location.setText(path)

    def _edit_folder_tree(self):
        custom = self.manager.get_custom_preset(self._selected_type)
        current = custom if custom is not None else FOLDER_PRESETS.get(self._selected_type, [])
        dlg = FolderTreeEditDialog(self._selected_type, current, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            result = dlg.get_folders()
            self.manager.set_custom_preset(self._selected_type, result)
            self._refresh_tree()

    def _detect_apps(self) -> dict[str, str | None]:
        """내부 키(Resolve/Premiere/AE) → 설치 경로 or None"""
        return {
            "Resolve":  find_app("Resolve",  self.manager.get_nle_override("Resolve")),
            "Premiere": find_app("Premiere", self.manager.get_nle_override("Premiere")),
            "AE":       find_app("AE",       self.manager.get_nle_override("AE")),
        }

    def _create_project(self):
        name = self.inp_name.text().strip()
        location = self.inp_location.text().strip()

        project_draft = {
            "name": name,
            "client": self.inp_client.text().strip(),
            "location": location,
            "type": self._selected_type,
        }
        ok, msg = self.manager.validate_project(project_draft)
        if not ok:
            QMessageBox.warning(self, "입력 오류", msg)
            return

        project_path = Path(location) / name
        if project_path.exists():
            reply = QMessageBox.question(
                self, "폴더 존재",
                f"'{project_path}' 폴더가 이미 존재합니다.\n계속 진행하시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        custom = self.manager.get_custom_preset(self._selected_type)
        folders = custom if custom is not None else FOLDER_PRESETS.get(self._selected_type, [])

        project = {
            "name": name,
            "client": self.inp_client.text().strip(),
            "location": location,
            "type": self._selected_type,
            "folders": folders,
            "spec": {
                "resolution": self.cb_resolution.currentText(),
                "fps": self.cb_fps.currentText(),
                "colorspace": self.cb_colorspace.currentText(),
                "samplerate": self.cb_samplerate.currentText(),
            },
        }

        # 폴더 생성
        self.btn_create.setEnabled(False)
        self.btn_create.setText("생성 중...")
        ok = self.manager.create_folders(project)
        if not ok:
            QMessageBox.critical(self, "오류", "폴더 생성에 실패했습니다.\n저장 위치 권한을 확인해주세요.")
            self.btn_create.setEnabled(True)
            self.btn_create.setText("  프로젝트 생성")
            return

        # 프로젝트 저장
        saved = self.manager.add(project)
        project["id"] = saved["id"]
        base_path = Path(location) / name

        # ── NLE 프로젝트 / 빈 자동 생성 ──
        nle_results: list[str] = []

        if self._nle_checks.get("Resolve", QCheckBox()).isChecked():
            self.btn_create.setText("Resolve 연결 중...")
            QApplication.processEvents()
            ok, msg = setup_resolve_bins(project, base_path)

            if not ok and ("실행 중이지 않" in msg or "응답이 없" in msg):
                # Resolve가 꺼져있음 → Worker로 자동 실행 + 대기
                self._launch_resolve_worker(project, base_path)
                nle_results.append(
                    "⏳ Resolve: 앱을 실행하고 백그라운드에서 연결 중...\n"
                    "   완료되면 알림이 표시됩니다."
                )
            else:
                nle_results.append(f"{'✓' if ok else '✗'} Resolve: {msg}")

        if self._nle_checks.get("Premiere", QCheckBox()).isChecked():
            self.btn_create.setText("Premiere 프로젝트 생성 중...")
            QApplication.processEvents()
            ok, msg = create_premiere_project(project, base_path)
            nle_results.append(f"{'✓' if ok else '✗'} Premiere: {msg}")

        if self._nle_checks.get("AE", QCheckBox()).isChecked():
            self.btn_create.setText("After Effects 프로젝트 생성 중...")
            QApplication.processEvents()
            ok, msg = create_ae_project(project, base_path)
            nle_results.append(f"{'✓' if ok else '✗'} AE: {msg}")

        # NLE 실행
        launch_choice = self.cb_launch.currentText()
        if launch_choice != "실행 안 함":
            launch_key_map = {
                "DaVinci Resolve": "Resolve",
                "Adobe Premiere":  "Premiere",
                "After Effects":   "AE",
            }
            app_key = launch_key_map.get(launch_choice)
            if app_key:
                launched = launch_app(app_key, manager=self.manager)
                if not launched:
                    QMessageBox.warning(self, "실행 오류", f"{launch_choice}을 실행할 수 없습니다.")

        self.btn_create.setEnabled(True)
        self.btn_create.setText("  프로젝트 생성")

        # 결과 팝업
        if nle_results:
            QMessageBox.information(
                self, "NLE 프로젝트 생성 결과",
                "\n\n".join(nle_results)
            )

        # 초기화
        self.inp_name.clear()
        self.inp_client.clear()
        self._refresh_tree()

        self.project_created.emit(saved)

    # ── Resolve Worker 관리 ──

    def _launch_resolve_worker(self, project: dict, base_path: Path):
        """Resolve 자동 실행 + 백그라운드 연결 워커 시작"""
        worker = ResolveSetupWorker(project, base_path)
        worker.status_changed.connect(self._on_resolve_status)
        worker.finished.connect(self._on_resolve_worker_done)
        # GC 방지
        self._resolve_worker = worker
        worker.start()

    def _on_resolve_status(self, msg: str):
        """워커 상태 메시지 → 버튼 텍스트로 표시"""
        self.btn_create.setText(msg)
        self.btn_create.setEnabled(False)

    def _on_resolve_worker_done(self, ok: bool, msg: str):
        """워커 완료 → 알림 팝업 + 버튼 복원"""
        self.btn_create.setEnabled(True)
        self.btn_create.setText("  프로젝트 생성")
        self._resolve_worker = None
        title = "Resolve 프로젝트 생성 완료" if ok else "Resolve 연결 실패"
        QMessageBox.information(self, title, msg)


# ─────────────────────────────────────────────
# ProjectCard (최근 프로젝트 카드)
# ─────────────────────────────────────────────
class ProjectCard(QFrame):
    deleted  = pyqtSignal(str)
    opened   = pyqtSignal(str)
    refresh_requested = pyqtSignal()   # 버전 복원 후 카드 목록 갱신

    NLE_COLORS = {
        "Resolve":  COLORS["resolve"],
        "Premiere": COLORS["premiere"],
        "AE":       COLORS["ae"],
    }
    NLE_LABELS = {
        "Resolve":  "Resolve",
        "Premiere": "Premiere",
        "AE":       "After Effects",
    }

    def __init__(self, project: dict, manager: ProjectManager):
        super().__init__()
        self.project = project
        self.manager = manager
        self._ver_expanded = False
        self._setup_ui()

    # ── 메인 UI ──────────────────────────────────
    def _setup_ui(self):
        from PyQt6.QtWidgets import QGraphicsDropShadowEffect
        pid         = self.project.get("id", "")
        name        = self.project.get("name", "Unknown")
        client      = self.project.get("client", "")
        ptype       = self.project.get("type", "")
        spec        = self.project.get("spec", {})
        resolution  = spec.get("resolution", self.project.get("resolution", ""))
        fps         = spec.get("fps", self.project.get("fps", ""))
        created_at  = self.project.get("created_at", "")
        location    = self.project.get("location", "")
        folder_path = str(Path(location) / name) if location else ""
        exists      = Path(folder_path).exists() if folder_path else False

        # 감지된 NLE 종류
        nles = detect_project_nles(self.project) if exists else set()

        # NLE 메인 컬러 (Resolve > Premiere > AE > accent)
        stripe_color = (
            COLORS["resolve"]  if "Resolve"  in nles else
            COLORS["premiere"] if "Premiere" in nles else
            COLORS["ae"]       if "AE"       in nles else
            COLORS["border2"]
        )

        # 카드 컨테이너 — 왼쪽 컬러 스트라이프
        self.setStyleSheet(f"""
            ProjectCard, QFrame#card {{
                background: {COLORS['surface2']};
                border: 1px solid {COLORS['border']};
                border-left: 4px solid {stripe_color if exists else COLORS['border']};
                border-radius: 12px;
            }}
        """)

        # 드롭 섀도우
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 80 if exists else 40))
        self.setGraphicsEffect(shadow)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── 본문 ──
        body = QWidget()
        body.setStyleSheet("background: transparent;")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(20, 16, 20, 14)
        body_layout.setSpacing(6)

        # 상단: 이름 + 배지들
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        name_text = name if exists else f"{name}  (폴더 없음)"
        name_lbl = QLabel(name_text)
        name_lbl.setStyleSheet(
            f"color: {COLORS['text'] if exists else COLORS['muted']};"
            f"font-size: 15px; font-weight: 700; background: transparent;"
        )
        top_row.addWidget(name_lbl)
        top_row.addStretch()

        # NLE 배지
        for nle_key in ["Resolve", "Premiere", "AE"]:
            if nle_key in nles:
                c = self.NLE_COLORS[nle_key]
                badge = QLabel(self.NLE_LABELS[nle_key])
                badge.setStyleSheet(f"""
                    background: {c}22;
                    color: {c};
                    border: 1px solid {c}55;
                    border-radius: 4px;
                    font-size: 10px;
                    font-weight: 700;
                    padding: 2px 7px;
                """)
                top_row.addWidget(badge)

        # 프로젝트 타입 배지
        if ptype:
            type_lbl = QLabel(ptype)
            type_lbl.setStyleSheet(f"""
                background: {COLORS['surface3']};
                color: {COLORS['text2']};
                border: 1px solid {COLORS['border2']};
                border-radius: 4px;
                font-size: 10px;
                font-weight: 600;
                padding: 2px 7px;
            """)
            top_row.addWidget(type_lbl)
        body_layout.addLayout(top_row)

        # 메타 정보
        meta_parts = []
        if client:
            meta_parts.append(client)
        if resolution:
            # 짧게 표시: "4K UHD" 부분만
            short_res = resolution.split("(")[0].strip() if "(" in resolution else resolution
            meta_parts.append(short_res)
        if fps:
            meta_parts.append(f"{fps} fps")
        if created_at:
            try:
                dt = datetime.fromisoformat(created_at)
                meta_parts.append(dt.strftime("%Y.%m.%d"))
            except Exception:
                pass

        if meta_parts:
            meta_lbl = QLabel("  ·  ".join(meta_parts))
            meta_lbl.setStyleSheet(
                f"color: {COLORS['text2']}; font-size: 12px; background: transparent;"
            )
            body_layout.addWidget(meta_lbl)

        # 경로
        if folder_path:
            path_lbl = QLabel(folder_path)
            path_lbl.setStyleSheet(
                f"color: {COLORS['muted']}; font-size: 11px; background: transparent;"
            )
            path_lbl.setWordWrap(True)
            body_layout.addWidget(path_lbl)

        # 폴더 없음 경고
        if not exists:
            warn = QLabel("⚠  폴더를 찾을 수 없습니다")
            warn.setStyleSheet(f"""
                color: {COLORS['danger']};
                background: {COLORS['danger']}12;
                border: 1px solid {COLORS['danger']}30;
                border-radius: 6px;
                font-size: 12px;
                padding: 5px 10px;
            """)
            body_layout.addWidget(warn)

        # ── 버전 히스토리 (Resolve .drp 존재 시) ──
        folder = Path(folder_path) if folder_path else None
        versions = get_project_versions(folder, name) if (folder and folder.exists()) else []
        drp_file = (folder / f"{name}.drp") if folder else None
        drp_exists = bool(drp_file and drp_file.exists())

        if drp_exists or versions:
            body_layout.addSpacing(4)
            self._ver_frame = self._build_version_section(
                name, folder, drp_exists, versions, pid
            )
            body_layout.addWidget(self._ver_frame)

        # ── 액션 버튼 행 ──
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        btn_row.setContentsMargins(0, 4, 0, 0)

        if exists:
            open_btn = make_ghost_button("폴더 열기", small=True)
            open_btn.clicked.connect(lambda: open_folder(folder_path))
            btn_row.addWidget(open_btn)

            # Resolve
            resolve_path = find_app("Resolve", self.manager.get_nle_override("Resolve"))
            if resolve_path:
                if drp_exists:
                    rb = make_ghost_button("▶ Resolve", color=COLORS["resolve"], small=True)
                    rb.clicked.connect(lambda: self._import_resolve_drp(str(drp_file)))
                else:
                    rb = make_ghost_button("⚡ Resolve 연결", color=COLORS["resolve"], small=True)
                    rb.clicked.connect(lambda: self._connect_resolve(name, folder_path))
                btn_row.addWidget(rb)

            # Premiere / AE
            for disp, app_key in [("▶ Premiere", "Premiere"), ("▶ AE", "AE")]:
                if find_app(app_key, self.manager.get_nle_override(app_key)):
                    ab = make_ghost_button(disp, color=self.NLE_COLORS[app_key], small=True)
                    ab.clicked.connect(lambda _, ak=app_key: self._launch_and_update(ak))
                    btn_row.addWidget(ab)

        btn_row.addStretch()
        del_btn = make_ghost_button("삭제", color=COLORS["danger"], small=True)
        del_btn.clicked.connect(lambda: self._confirm_delete(pid, name))
        btn_row.addWidget(del_btn)

        body_layout.addLayout(btn_row)
        outer.addWidget(body)

    # ── 버전 섹션 ─────────────────────────────────
    def _build_version_section(
        self, name: str, folder: Path, drp_exists: bool,
        versions: list[dict], pid: str
    ) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['surface3']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
        """)
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(12, 8, 12, 8)
        fl.setSpacing(4)

        # 헤더 행
        hdr = QHBoxLayout()
        ver_count = len(versions)
        hdr_lbl = QLabel(
            f"버전 히스토리  ·  {ver_count}개 스냅샷"
            if ver_count else "버전 히스토리  ·  스냅샷 없음"
        )
        hdr_lbl.setStyleSheet(
            f"color: {COLORS['text2']}; font-size: 11px; font-weight: 600; background: transparent;"
        )
        hdr.addWidget(hdr_lbl)
        hdr.addStretch()

        if drp_exists:
            snap_btn = QPushButton("스냅샷 생성")
            snap_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            snap_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {COLORS['resolve']}22;
                    color: {COLORS['resolve']};
                    border: 1px solid {COLORS['resolve']}44;
                    border-radius: 5px;
                    font-size: 11px;
                    font-weight: 600;
                    padding: 3px 10px;
                }}
                QPushButton:hover {{ background: {COLORS['resolve']}40; }}
            """)
            snap_btn.clicked.connect(
                lambda: self._create_snapshot(name, folder)
            )
            hdr.addWidget(snap_btn)

        fl.addLayout(hdr)

        # 버전 목록 (최대 5개)
        self._ver_list_widget = QWidget()
        self._ver_list_widget.setStyleSheet("background: transparent;")
        vl = QVBoxLayout(self._ver_list_widget)
        vl.setContentsMargins(0, 4, 0, 0)
        vl.setSpacing(3)

        self._render_version_list(vl, versions, name, folder)
        fl.addWidget(self._ver_list_widget)
        return frame

    def _render_version_list(
        self, layout: QVBoxLayout, versions: list[dict], name: str, folder: Path
    ):
        # 기존 위젯 제거
        while layout.count():
            w = layout.takeAt(0).widget()
            if w:
                w.deleteLater()

        show_versions = versions[:5]  # 최대 5개
        for v in show_versions:
            row = QHBoxLayout()
            row.setSpacing(6)
            ver_lbl = QLabel(v["label"])
            ver_lbl.setStyleSheet(
                f"color: {COLORS['resolve']}; font-size: 11px; font-weight: 700;"
                f"min-width: 38px; background: transparent;"
            )
            date_lbl = QLabel(v["modified"].strftime("%m/%d %H:%M"))
            date_lbl.setStyleSheet(
                f"color: {COLORS['muted']}; font-size: 11px; background: transparent;"
            )
            size_lbl = QLabel(f"{v['size_mb']:.1f} MB")
            size_lbl.setStyleSheet(
                f"color: {COLORS['muted']}; font-size: 11px; background: transparent;"
            )
            row.addWidget(ver_lbl)
            row.addWidget(date_lbl)
            row.addWidget(size_lbl)
            row.addStretch()

            restore_btn = QPushButton("복원")
            restore_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            restore_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {COLORS['accent']};
                    border: 1px solid {COLORS['accent']}44;
                    border-radius: 4px;
                    font-size: 10px;
                    font-weight: 600;
                    padding: 2px 8px;
                }}
                QPushButton:hover {{ background: {COLORS['accent']}22; }}
            """)
            vp = v["path"]
            restore_btn.clicked.connect(
                lambda _, p=vp: self._restore_version(p, name, folder)
            )
            row.addWidget(restore_btn)

            row_widget = QWidget()
            row_widget.setStyleSheet("background: transparent;")
            row_widget.setLayout(row)
            layout.addWidget(row_widget)

        if len(versions) > 5:
            more = QLabel(f"+ {len(versions) - 5}개 더...")
            more.setStyleSheet(
                f"color: {COLORS['muted']}; font-size: 11px; background: transparent;"
            )
            layout.addWidget(more)

    # ── 액션 핸들러 ────────────────────────────────
    def _create_snapshot(self, name: str, folder: Path):
        project_local = {**self.project, "name": name,
                         "location": str(folder.parent)}
        ok, msg = create_smart_snapshot(project_local)
        if ok:
            QMessageBox.information(self, "스냅샷 생성", msg)
            self.refresh_requested.emit()
        else:
            QMessageBox.warning(self, "스냅샷 실패", msg)

    def _restore_version(self, version_path: Path, name: str, folder: Path):
        v_label = version_path.stem.split("_")[-1]  # V003 등
        reply = QMessageBox.question(
            self, "버전 복원",
            f"{v_label} 버전으로 복원하시겠습니까?\n\n"
            "현재 상태가 자동으로 새 스냅샷으로 백업됩니다.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        project_local = {**self.project, "name": name,
                         "location": str(folder.parent)}
        ok, msg = restore_version(version_path, project_local)
        if ok:
            QMessageBox.information(self, "복원 완료", msg)
            self.refresh_requested.emit()
        else:
            QMessageBox.warning(self, "복원 실패", msg)

    def _import_resolve_drp(self, drp_path: str):
        ok, msg = _resolve_import_drp(drp_path)
        if ok:
            QMessageBox.information(self, "Import 완료", msg)
        else:
            reply = QMessageBox.question(
                self, "Resolve 실행 필요",
                f"{msg}\n\n파일 탐색기에서 .drp 위치를 열까요?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                open_folder(str(Path(drp_path).parent))

    def _connect_resolve(self, proj_name: str, folder_path: str):
        project_local = {**self.project, "name": proj_name}
        ok, msg = setup_resolve_bins(project_local, Path(folder_path))
        if ok:
            QMessageBox.information(self, "Resolve 연결 완료", msg)
            self.refresh_requested.emit()
        else:
            QMessageBox.warning(self, "Resolve 연결 실패", msg)

    def _launch_and_update(self, app_key: str):
        self.manager.update_last_opened(self.project.get("id", ""))
        self.opened.emit(self.project.get("id", ""))
        launch_app(app_key, manager=self.manager)

    def _confirm_delete(self, pid: str, name: str):
        reply = QMessageBox.question(
            self, "프로젝트 삭제",
            f"'{name}' 프로젝트를 목록에서 삭제하시겠습니까?\n(실제 폴더는 삭제되지 않습니다)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.deleted.emit(pid)


# ─────────────────────────────────────────────
# RecentProjectsPage
# ─────────────────────────────────────────────
class RecentProjectsPage(QWidget):
    _FILTERS = ["전체", "Resolve", "Premiere", "AE"]

    def __init__(self, manager: ProjectManager):
        super().__init__()
        self.manager = manager
        self._active_filter = "전체"
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet(f"background: {COLORS['bg']};")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── 헤더 ──
        header = QWidget()
        header.setStyleSheet(f"background: {COLORS['bg']};")
        hl = QVBoxLayout(header)
        hl.setContentsMargins(40, 28, 40, 0)
        hl.setSpacing(6)

        title_row = QHBoxLayout()
        title = QLabel("최근 프로젝트")
        title.setStyleSheet(
            f"color: {COLORS['text']}; font-size: 22px; font-weight: 700;"
        )
        title_row.addWidget(title)
        title_row.addStretch()
        self._count_lbl = QLabel("")
        self._count_lbl.setStyleSheet(
            f"color: {COLORS['muted']}; font-size: 12px;"
        )
        title_row.addWidget(self._count_lbl)
        hl.addLayout(title_row)

        # ── NLE 필터 탭 ──
        filter_row = QHBoxLayout()
        filter_row.setSpacing(6)
        filter_row.setContentsMargins(0, 10, 0, 12)
        self._filter_btns: dict[str, QPushButton] = {}

        filter_colors = {
            "전체":    COLORS["accent"],
            "Resolve": COLORS["resolve"],
            "Premiere":COLORS["premiere"],
            "AE":      COLORS["ae"],
        }
        for label in self._FILTERS:
            c = filter_colors[label]
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setChecked(label == self._active_filter)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setFixedHeight(30)
            self._filter_btns[label] = btn
            self._style_filter_btn(btn, label == self._active_filter, c)
            btn.clicked.connect(lambda _, l=label: self._set_filter(l))
            filter_row.addWidget(btn)
        filter_row.addStretch()
        hl.addLayout(filter_row)

        layout.addWidget(header)
        layout.addWidget(divider())

        # ── 스크롤 카드 영역 ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._cards_widget = QWidget()
        self._cards_widget.setStyleSheet(f"background: {COLORS['bg']};")
        self._cards_layout = QVBoxLayout(self._cards_widget)
        self._cards_layout.setContentsMargins(40, 20, 40, 40)
        self._cards_layout.setSpacing(14)
        self._cards_layout.addStretch()

        scroll.setWidget(self._cards_widget)
        layout.addWidget(scroll)
        self.refresh()

    def _style_filter_btn(self, btn: QPushButton, active: bool, color: str):
        if active:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {color};
                    color: #ffffff;
                    border: none;
                    border-radius: 6px;
                    font-size: 12px;
                    font-weight: 700;
                    padding: 0 16px;
                }}
            """)
        else:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {COLORS['surface2']};
                    color: {COLORS['text2']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 6px;
                    font-size: 12px;
                    font-weight: 500;
                    padding: 0 16px;
                }}
                QPushButton:hover {{
                    background: {COLORS['surface3']};
                    color: {color};
                    border-color: {color}66;
                }}
            """)

    def _set_filter(self, label: str):
        self._active_filter = label
        filter_colors = {
            "전체":    COLORS["accent"],
            "Resolve": COLORS["resolve"],
            "Premiere":COLORS["premiere"],
            "AE":      COLORS["ae"],
        }
        for lbl, btn in self._filter_btns.items():
            self._style_filter_btn(btn, lbl == label, filter_colors[lbl])
        self.refresh()

    def refresh(self):
        # 기존 카드 제거 (stretch 제외)
        while self._cards_layout.count() > 1:
            item = self._cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 필터 적용
        all_projects = self.manager.projects
        if self._active_filter == "전체":
            filtered = all_projects
        else:
            filtered = [
                p for p in all_projects
                if self._active_filter in detect_project_nles(p)
            ]

        # 최대 RECENT_LIMIT개만 표시
        projects = filtered[:RECENT_LIMIT]
        hidden  = max(0, len(filtered) - RECENT_LIMIT)

        # 카운트 레이블 업데이트
        total_txt = f"총 {len(all_projects)}개"
        if self._active_filter != "전체":
            total_txt += f"  ·  {self._active_filter} {len(filtered)}개"
        if hidden:
            total_txt += f"  ·  최근 {RECENT_LIMIT}개 표시"
        self._count_lbl.setText(total_txt)

        if not projects:
            msg = (
                "이 NLE로 생성된 프로젝트가 없습니다."
                if self._active_filter != "전체"
                else "아직 생성된 프로젝트가 없습니다.\n새 프로젝트 탭에서 첫 프로젝트를 만들어보세요!"
            )
            empty_lbl = QLabel(msg)
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_lbl.setStyleSheet(
                f"color: {COLORS['muted']}; font-size: 14px; padding: 60px;"
            )
            self._cards_layout.insertWidget(0, empty_lbl)
            return

        for i, project in enumerate(projects):
            card = ProjectCard(project, self.manager)
            card.deleted.connect(self._on_delete)
            card.opened.connect(self._on_opened)
            card.refresh_requested.connect(self.refresh)
            self._cards_layout.insertWidget(i, card)

    def _on_delete(self, project_id: str):
        self.manager.delete(project_id)
        self.refresh()

    def _on_opened(self, project_id: str):
        self.manager.update_last_opened(project_id)


# ─────────────────────────────────────────────
# SettingsPage
# ─────────────────────────────────────────────
class SettingsPage(QWidget):
    def __init__(self, manager: ProjectManager):
        super().__init__()
        self.manager = manager
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet(f"background: {COLORS['bg']};")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        inner = QWidget()
        inner.setStyleSheet(f"background: {COLORS['bg']};")
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(40, 32, 40, 40)
        layout.setSpacing(4)

        title = QLabel("설정")
        title.setStyleSheet(f"color: {COLORS['text']}; font-size: 22px; font-weight: 700; margin-bottom: 4px;")
        layout.addWidget(title)
        layout.addWidget(divider())

        # ── NLE 앱 감지 / 수동 경로 지정 ──
        layout.addWidget(section_label("NLE 앱 감지"))
        apps = {
            "DaVinci Resolve": ("Resolve", COLORS["resolve"]),
            "Adobe Premiere Pro": ("Premiere", COLORS["premiere"]),
            "Adobe After Effects": ("AE", COLORS["ae"]),
        }
        self._nle_inputs: dict[str, QLineEdit] = {}
        for display, (key, color) in apps.items():
            # 상태 행
            status_row = QHBoxLayout()
            lbl = QLabel(display)
            lbl.setStyleSheet(f"color: {COLORS['text']}; font-size: 13px; font-weight: 600; min-width: 200px;")
            status_row.addWidget(lbl)

            override = self.manager.get_nle_override(key)
            detected = find_app(key, override)
            if detected:
                status = QLabel("✓  감지됨")
                status.setStyleSheet(f"color: {COLORS['success']}; font-size: 12px; font-weight: 600;")
                status_row.addWidget(status)
                path_lbl = QLabel(detected)
                path_lbl.setStyleSheet(f"color: {COLORS['muted']}; font-size: 11px;")
                status_row.addWidget(path_lbl)
            else:
                status = QLabel("✗  미감지  —  아래에 경로를 직접 입력하세요")
                status.setStyleSheet(f"color: {COLORS['muted']}; font-size: 12px;")
                status_row.addWidget(status)
            status_row.addStretch()
            layout.addLayout(status_row)

            # 수동 경로 입력 행
            override_row = QHBoxLayout()
            nle_inp = QLineEdit()
            nle_inp.setPlaceholderText("수동 경로 지정 (선택 사항)")
            nle_inp.setText(override)
            nle_inp.setStyleSheet(f"""
                QLineEdit {{
                    background: {COLORS['surface2']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 6px;
                    color: {COLORS['text']};
                    font-size: 12px;
                    padding: 6px 10px;
                    min-height: 32px;
                }}
                QLineEdit:focus {{ border-color: {COLORS['accent']}; }}
            """)
            self._nle_inputs[key] = nle_inp

            nle_browse = make_ghost_button("찾아보기", small=True)
            nle_browse.clicked.connect(lambda _, k=key: self._browse_nle(k))
            nle_save = make_button("적용", small=True)
            nle_save.clicked.connect(lambda _, k=key: self._save_nle(k))

            override_row.addWidget(nle_inp)
            override_row.addWidget(nle_browse)
            override_row.addWidget(nle_save)
            layout.addLayout(override_row)
            layout.addSpacing(10)

        layout.addWidget(divider())

        # ── 기본 저장 경로 ──
        layout.addWidget(section_label("기본 저장 경로"))
        path_row = QHBoxLayout()
        self.inp_default_loc = QLineEdit()
        self.inp_default_loc.setText(self.manager.get_default_location())
        self.inp_default_loc.setStyleSheet(f"""
            QLineEdit {{
                background: {COLORS['surface2']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                color: {COLORS['text']};
                font-size: 13px;
                padding: 8px 12px;
                min-height: 36px;
            }}
            QLineEdit:focus {{ border-color: {COLORS['accent']}; }}
        """)
        browse_btn = make_ghost_button("찾아보기", small=True)
        browse_btn.clicked.connect(self._browse_default)
        save_btn = make_button("저장", small=True)
        save_btn.clicked.connect(self._save_default)
        path_row.addWidget(self.inp_default_loc)
        path_row.addWidget(browse_btn)
        path_row.addWidget(save_btn)
        layout.addLayout(path_row)

        layout.addWidget(divider())

        # ── 데이터 파일 위치 ──
        layout.addWidget(section_label("데이터 파일 위치"))
        data_row = QHBoxLayout()
        data_path_lbl = QLabel(str(self.manager.DATA_DIR))
        data_path_lbl.setStyleSheet(f"color: {COLORS['muted']}; font-size: 12px;")
        data_row.addWidget(data_path_lbl)
        data_row.addStretch()
        open_data_btn = make_ghost_button("폴더 열기", small=True)
        open_data_btn.clicked.connect(lambda: open_folder(str(self.manager.DATA_DIR)))
        data_row.addWidget(open_data_btn)
        layout.addLayout(data_row)

        layout.addStretch()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(inner)
        outer.addWidget(scroll)

    def _browse_default(self):
        path = QFileDialog.getExistingDirectory(
            self, "기본 저장 위치 선택", self.inp_default_loc.text()
        )
        if path:
            self.inp_default_loc.setText(path)

    def _save_default(self):
        path = self.inp_default_loc.text().strip()
        if path and Path(path).exists():
            self.manager.set_default_location(path)
            QMessageBox.information(self, "저장 완료", "기본 저장 경로가 저장되었습니다.")
        else:
            QMessageBox.warning(self, "경로 오류", "유효한 경로를 입력해주세요.")

    def _browse_nle(self, app_key: str):
        if platform.system() == "Darwin":
            path = QFileDialog.getExistingDirectory(self, f"앱 선택 (.app)", "/Applications")
        else:
            path, _ = QFileDialog.getOpenFileName(self, "실행 파일 선택", "C:/Program Files", "실행 파일 (*.exe)")
        if path and app_key in self._nle_inputs:
            self._nle_inputs[app_key].setText(path)

    def _save_nle(self, app_key: str):
        inp = self._nle_inputs.get(app_key)
        if not inp:
            return
        path = inp.text().strip()
        if path and not Path(path).exists():
            QMessageBox.warning(self, "경로 오류", f"해당 경로가 존재하지 않습니다:\n{path}")
            return
        self.manager.set_nle_override(app_key, path)
        QMessageBox.information(self, "저장 완료", f"경로가 저장되었습니다.\n앱을 재시작하면 감지 상태가 업데이트됩니다.")


# ─────────────────────────────────────────────
# Sidebar Nav Button
# ─────────────────────────────────────────────
class NavButton(QPushButton):
    def __init__(self, text: str, icon_char: str = ""):
        super().__init__()
        self._text = text
        self._icon = icon_char
        self.setCheckable(True)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setText(f"  {icon_char}  {text}" if icon_char else f"  {text}")
        self.setFixedHeight(42)
        self._apply_style(False)

    def _apply_style(self, active: bool):
        if active:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: {COLORS['accent']}22;
                    color: {COLORS['accent']};
                    border: none;
                    border-left: 3px solid {COLORS['accent']};
                    border-radius: 0px;
                    font-size: 13px;
                    font-weight: 600;
                    text-align: left;
                    padding-left: 14px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {COLORS['muted']};
                    border: none;
                    border-left: 3px solid transparent;
                    border-radius: 0px;
                    font-size: 13px;
                    font-weight: 500;
                    text-align: left;
                    padding-left: 14px;
                }}
                QPushButton:hover {{
                    background: {COLORS['surface2']};
                    color: {COLORS['text']};
                }}
            """)

    def setActive(self, active: bool):
        self._apply_style(active)


# ─────────────────────────────────────────────
# MainWindow
# ─────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.manager = ProjectManager()
        self.setWindowTitle(f"{APP_NAME}  —  {APP_TAGLINE}")
        self.resize(1120, 720)
        self.setMinimumSize(800, 560)
        self._setup_ui()
        self._apply_global_style()

    def _apply_global_style(self):
        self.setStyleSheet(f"""
            QMainWindow {{
                background: {COLORS['bg']};
            }}
            QScrollBar:vertical {{
                background: {COLORS['surface']};
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {COLORS['border']};
                border-radius: 4px;
                min-height: 24px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {COLORS['muted']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            QMessageBox {{
                background: {COLORS['surface']};
                color: {COLORS['text']};
            }}
        """)

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── 사이드바 ──
        sidebar = QFrame()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['surface']};
                border-right: 1px solid {COLORS['border']};
            }}
        """)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # 로고
        logo_widget = QWidget()
        logo_widget.setFixedHeight(64)
        logo_widget.setStyleSheet(f"background: {COLORS['surface']};")
        logo_layout = QHBoxLayout(logo_widget)
        logo_layout.setContentsMargins(20, 0, 20, 0)
        logo_icon = QLabel("⬡")
        logo_icon.setStyleSheet(f"font-size: 18px; color: {COLORS['accent']};")
        logo_txt = QLabel(APP_NAME)
        logo_txt.setStyleSheet(
            f"color: {COLORS['text']}; font-size: 15px; font-weight: 800; letter-spacing: 3px;"
        )
        logo_layout.addWidget(logo_icon)
        logo_layout.addWidget(logo_txt)
        logo_layout.addStretch()
        sidebar_layout.addWidget(logo_widget)
        sidebar_layout.addWidget(divider())
        sidebar_layout.addSpacing(8)

        # 네비게이션 버튼
        self._nav_buttons: list[NavButton] = []
        nav_items = [
            ("새 프로젝트", "＋"),
            ("최근 프로젝트", "⏱"),
            ("설정", "⚙"),
        ]
        for i, (label, icon) in enumerate(nav_items):
            btn = NavButton(label, icon)
            btn.clicked.connect(lambda _, idx=i: self._navigate(idx))
            self._nav_buttons.append(btn)
            sidebar_layout.addWidget(btn)

        sidebar_layout.addStretch()
        sidebar_layout.addWidget(divider())

        # 버전 + 태그라인
        ver_lbl = QLabel(f"v{APP_VERSION}  ·  {APP_TAGLINE}")
        ver_lbl.setWordWrap(True)
        ver_lbl.setStyleSheet(
            f"color: {COLORS['muted']}; font-size: 10px; padding: 10px 20px; line-height: 1.4;"
        )
        sidebar_layout.addWidget(ver_lbl)

        root.addWidget(sidebar)

        # ── 메인 영역 ──
        self._stack = QStackedWidget()
        self._stack.setStyleSheet(f"background: {COLORS['bg']};")

        self._new_page = NewProjectPage(self.manager)
        self._recent_page = RecentProjectsPage(self.manager)
        self._settings_page = SettingsPage(self.manager)

        self._stack.addWidget(self._new_page)
        self._stack.addWidget(self._recent_page)
        self._stack.addWidget(self._settings_page)

        # 프로젝트 생성 시 최근 탭으로 이동
        self._new_page.project_created.connect(self._on_project_created)

        root.addWidget(self._stack)

        # 초기 선택
        self._navigate(0)

    def _navigate(self, index: int):
        for i, btn in enumerate(self._nav_buttons):
            btn.setActive(i == index)
        self._stack.setCurrentIndex(index)
        if index == 1:
            self._recent_page.refresh()

    def _on_project_created(self, project: dict):
        self._navigate(1)


# ─────────────────────────────────────────────
# 엔트리포인트
# ─────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(APP_NAME)

    # 전역 폰트
    font = QFont("system-ui", 13)
    app.setFont(font)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
