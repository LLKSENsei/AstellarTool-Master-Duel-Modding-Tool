"""
================================================================================
MD AstellarTool (MD 阿斯特婭工具箱)
================================================================================
An open-source GUI tool for Yu-Gi-Oh! Master Duel asset analysis, modification, 
over-frame rendering, and virtual mod management.

Author: LonelyMaJo (https://www.pixiv.net/users/126514098)
License: MIT License

[ 免費與防詐騙聲明 / Free Tool & Refund Disclaimer ]
1. 本程式為完全免費且開源之工具，僅供技術交流與個人研究使用。
2. 本程式嚴禁任何形式的商業轉售、打包販售或變相收費。
3. 若您是付費才取得本程式，您已被詐騙！請立即向賣家或平台申請退款並檢舉該商家。
   (This tool is 100% FREE and Open Source. If you paid for this software, 
    you have been scammed! Please request a refund immediately.)
================================================================================
"""

__author__ = "LonelyMaJo"
__license__ = "MIT"
__version__ = "1.5.0"
__url__ = "https://www.pixiv.net/users/126514098"

import os
import sys
import csv
import json
import shutil
import traceback
import struct
import zlib
import re
import difflib
import multiprocessing
import concurrent.futures
import textwrap
import threading
# ==================== 音效庫虛擬化 (Mock 補丁) ====================
#為了打包成exe，這是必要的步驟，不要將其移除
from types import ModuleType
class MockModule(ModuleType):
    def __getattr__(self, name): return lambda *args, **kwargs: None
sys.modules["fmod_toolkit"] = MockModule("fmod_toolkit")
sys.modules["pyfmodex"] = MockModule("pyfmodex")
# =========================================================================

import UnityPy
from PIL import Image

# 確保 QApplication 在最一開始建立
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QFormLayout, QGroupBox, QPushButton, QLabel, QLineEdit, QCheckBox, QComboBox, 
    QFileDialog, QMessageBox, QScrollArea, QStackedWidget, QListWidget, QMenu,
    QAbstractItemView, QPlainTextEdit, QProgressBar, QGraphicsOpacityEffect, QSlider, QSizePolicy,
    QRadioButton, QButtonGroup, QListWidgetItem
)
from PySide6.QtCore import Qt, QObject, Signal, QRunnable, QThreadPool, QTimer, QRect, QPoint, QSize, QEvent
from PySide6.QtGui import QFont, QPixmap, QImage, QPainter, QColor, QFontDatabase, QPolygon, QPen, QIcon, QKeySequence, QShortcut

try:
    import msgpack
except ImportError:
    import sys
    from PySide6.QtWidgets import QApplication, QMessageBox
    _temp_app = QApplication(sys.argv)
    QMessageBox.critical(None, "缺少依賴模組", "找不到 msgpack 模組！\n\n請開啟終端機(CMD)輸入:\npip install msgpack\n\n安裝完成後再重新啟動程式。")
    sys.exit(1)

# =========================================================================
# ==================== 第一區：設定總管與資料綁定 (ConfigManager) ===========
# =========================================================================
CONFIG_FILE = "md_tool_config.json"
UI_LANG_DICT = {}
def _(text): return UI_LANG_DICT.get(text, text)

def _init_worker(lang_dict):
    """分配給所有子執行緒，讓它們啟動時裝備上主程序的字典"""
    global UI_LANG_DICT
    UI_LANG_DICT.update(lang_dict)

# 多語系橫向擴展標頭對照表與靈擺關鍵字矩陣
LEGACY_LANG_HEADERS = {
    "zh-tw": ("繁中卡片名稱(Name)", "繁中卡片效果(Desc)"),
    "zh-cn": ("简中卡片名称(Name)", "简中卡片效果(Desc)"),
    "en-us": ("English Card Name(Name)", "English Card Effect(Desc)"),
    "ja-jp": ("日本語カード名(Name)", "日本語カード効果(Desc)")
}
PENDULUM_KEYWORDS = ["靈擺效果", "鐘擺效果", "钟摆效果", "灵摆效果", "Pendulum Effect", "Ｐ効果", "ペンデュラム効果"]

PROP_HEADERS = ["Type", "SubType"] # 🛡️ 改為英文標準標頭

RE_CARD_ID_EXTRACTOR = re.compile(r'^([a-zA-Z]*)(\d+)(.*)$')

DEFAULT_README = (
    "Made by LonelyMaJo\n"
    "Find more MasterDuel mods on my pixiv\n"
    "https://www.pixiv.net/users/126514098 \n\n"
    "[ How to Install ]\n"
    "1. Open the \"0000\" folder from this mod.\n"
    "2. Copy everything inside it.\n"
    "3. Paste and overwrite them into your game directory:\n"
    "...\\Yu-Gi-Oh! Master Duel\\LocalData\\[Your-8-Digit-ID]\\0000\\\n\n"
    "[ How to Uninstall ]\n"
    "Replace the modded files with the backup files using the same path."
)

def _check_admin():
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

DEFAULT_TABS = [
    {"id": "t0_guide", "name": "0. 新手指南與操作旅程"}, {"id": "t1_scan", "name": "1. 爆搜與補齊"},
    {"id": "t2_find", "name": "2. 找出檔案"}, {"id": "t3_extract", "name": "3. 提取資料"},
    {"id": "t4_replace", "name": "4. 更改卡圖"}, {"id": "t5_package", "name": "5. 封裝模組"},
    {"id": "t6_chain", "name": "6. 智慧串連執行"}, {"id": "t8_pendulum", "name": "7. 靈擺與超框卡圖後處理"},
    {"id": "t9_quick_mod", "name": "8. 快捷單卡改圖"},{"id": "t13_overframe", "name": "9. 超框卡片註冊器"},
    {"id": "t12_gallery", "name": "10. 圖形化瀏覽器"}, {"id": "t10_updater", "name": "11. 模組串流修復器"},
    {"id": "t11_virtual", "name": "12. 虛擬模組管理器"}, {"id": "t7_settings", "name": "13. 設定與外觀"}
]

class ConfigSignals(QObject):
    sync_root = Signal(str)
    sync_src = Signal(str)
    sync_csv = Signal(str)
    sync_t3_src = Signal(str)
    sync_t2_txt = Signal(str)
    sync_folder = Signal(str)
    bg_changed = Signal()
    request_filter_view = Signal(list)
    sync_filter_result = Signal(list)
    request_overframe_return = Signal()
    toggle_overframe_return = Signal(bool)
    sync_extraction_list = Signal(str)
    request_overframe_register = Signal(str)
    set_return_to_tab4 = Signal(bool)
    request_overframe_shortcut = Signal(str, str, str)  # 傳遞: card_id, img_path, root_dir
    return_to_quick_mod = Signal(str)                   # 傳遞: processed_img_path
    quick_mod_to_overframe_reg = Signal(str) 
    append_extraction_list = Signal(str)      # 廣播給「找出檔案」追加清單
    set_quick_mod_id = Signal(str)            # 廣播給「快捷單卡」填入ID
    request_pendulum_reload = Signal()
    set_t8_mode = Signal(str)   

class ConfigManager:
    """真・模組化核心：唯一真相來源。各分頁只負責更新與讀取這裡的資料。"""
    def __init__(self):
        self.data = self._get_default()
        self.signals = ConfigSignals()
        import threading
        self._save_lock = threading.RLock() # 🛡️ 使用 RLock (可重入鎖)，徹底解決重複 Lock 導致的死結
        
        # 定義跨分頁同步群組
        self.group_root = ["t1_out_dir", "t2_out_dir", "t4_root_dir", "t5_root_dir", "t8_root_dir", "t9_out_dir", "t10_out_dir", "t13_out_dir"]
        self.group_src = ["t2_src_dir", "t9_src_dir", "t10_clean_src_dir", "t13_src_dir"]
        self.group_csv = ["t2_csv_dir", "t4_csv_dir", "t5_csv_dir", "t8_csv_dir", "t9_csv_dir", "t13_csv_dir"]
        self.load()

    def _get_default(self):
        return {
            "max_threads":  "Auto", "enable_visual_only_filter": True, "search_lang": "zh-tw", # 獨立搜尋語系
            "use_disk_cache": False,
            "ui_theme_color": "#2CC985", "ui_bg_color": "#1C1C1C", "ui_text_color": "#EBEBEC", "ui_widget_bg_color": "#2B2B2B", "ui_border_color": "#444444",
            "ui_language": "zh-tw", "sync_paths": True, "auto_switch_tab": False,
            "font_family": "", "bg_image": "", "bg_opacity": 1.0, "bg_brightness": 0.5, "bg_anchor": "center",
            "tab_order": [t["id"] for t in DEFAULT_TABS], "tab_names": {t["id"]: t["name"] for t in DEFAULT_TABS},
            "t1_target_dir": "", "t1_out_dir": "", "t1_txt_name": "Extracted_Names.txt", "t1_csv_name": "Extracted_Mapping.csv",
            "t1_incomplete_csv": "", "t1_size_filter": True, "t1_min_size": "50", "t1_max_size": "2400", "t1_only_numbers": True,
            "t1_gen_txt": True, "t1_gen_csv": True, "t1_ext_name": True, "t1_ext_desc": True, "t1_parse_meta": True,
            "t1_lang": "zh-tw", "t1_use_cache": False, "t1_xor_key": "61", "t1_deep_scan": False,
            "t2_csv_dir": "", "t2_txt_dir": "", "t2_src_dir": "", "t2_out_dir": "", "t2_folder_name": "",
            "t3_img_folder": "", "t3_exp_csv": False, "t3_exp_img": True, "t3_exp_txt": True, "t3_exp_backup": True,
            "t4_csv_dir": "", "t4_root_dir": "", "t4_backup_name": "", "t4_mod_name": "",
            "t5_csv_dir": "", "t5_root_dir": "", "t5_mod_folder_name": "ModFolder", "t5_pack_zip": False, "t5_readme_text": "",
            "t5_include_mod_folder": True, "t5_include_readme": True,
            "t8_csv_dir": "", "t8_root_dir": "", "t8_mod_dir": "", "t8_padding_pct": "25", "t8_enable_backup": True, "t8_backup_folder": "修改前原檔",
            "t8_op_periframe": 1.0, "t8_op_namebox": 1.0, "t8_op_artframe": 1.0, "t8_op_effframe": 1.0, "t8_op_effbox": 1.0, "t8_op_background": 1.0,
            "t8_cutin_src": "", "t8_cutin_id": "",
            "t8_adv_ch_x": 0, "t8_adv_ch_y": 0, "t8_adv_ch_s": 100, "t8_adv_ch_rot": 0,
            "t8_adv_bg_x": 0, "t8_adv_bg_y": 0, "t8_adv_bg_s": 100, "t8_adv_bg_rot": 0, "t8_adv_bg_color": "#FF000000",
            "t8_adv_z_order": ["CH_LAYER", "PeriFrame", "NameBox", "EffFrame", "ArtFrame", "EffBox", "BackGround", "BG_LAYER"],
            "t8_foil_palette": "PALETTE_OPAL", "t8_foil_base_light": 60, "t8_foil_sharpness": 20, "t8_foil_blend_mode": "BLEND_SOFT",
            "t8_foil_intensity": 200, "t8_foil_saturation": 130, "t8_foil_frequency": 5.0, "t8_foil_angle": 60, "t8_foil_bake_enable": False,
            "t8_foil_prev_PeriFrame": True, "t8_foil_prev_NameBox": False, "t8_foil_prev_ArtFrame": True, "t8_foil_prev_EffFrame": True, "t8_foil_prev_EffBox": False, "t8_foil_prev_BackGround": False,
            "t8_foil_bake_PeriFrame": False, "t8_foil_bake_NameBox": False, "t8_foil_bake_ArtFrame": False, "t8_foil_bake_EffFrame": False, "t8_foil_bake_EffBox": False, "t8_foil_bake_BackGround": False,
            "t8_adv_mask_PeriFrame": True, "t8_adv_mask_NameBox": False, "t8_adv_mask_ArtFrame": True, "t8_adv_mask_EffFrame": True, "t8_adv_mask_EffBox": False, "t8_adv_mask_BackGround": False,
            "t8_adv_foil_sim": False,
            "c_hd_res": "HD 1280x720", "c_fill_mode": "Crop",
            "c_start_time": 0.0, "c_duration": 3.0, "c_fps": 30, "c_speed": 1.0,
            "c_rot": 0, "c_offset_x": 0, "c_offset_y": 0,
            "c_chroma_en": True, "c_despill_en": False, "c_chroma_color": "#00FF00", "c_chroma_tol": 15, "c_chroma_feather": 0, "c_chroma_despill": 50,
            "c_bright": 0, "c_contrast": 0, "c_vignette": 0,
            "c_pt1_t": 0.0, "c_pt1_s": 70, "c_pt2_t": 0.3, "c_pt2_s": 105,
            "c_pt3_t": 1.0, "c_pt3_s": 98, "c_pt4_t": 2.0, "c_pt4_s": 100,
            "t9_csv_dir": "", "t9_src_dir": "", "t9_out_dir": "", "t9_img_path": "", "t9_overwrite_game": False,
            "t10_old_mod_dir": "", "t10_clean_src_dir": "", "t10_out_dir": "", "t10_overwrite": False,
            "t11_mod_root_dir": "", "t11_game_0000_dir": "", "t11_scan_depth": "3", "t11_active_mods": [],
            "s_folder_raw": "原檔", "s_folder_img": "原卡圖", "s_folder_backup": "文件備份", "s_folder_mod": "卡圖改", "s_folder_out": "改完的文件", "s_csv_mapping": "2DTexture_Mapping.csv",
            "c_t2": True, "c_t3": True, "c_t8": False, "c_t4": True, "c_t5": True
        }

    def load(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f: self.data.update(json.load(f))
            except Exception: pass
        
        # [修復] 自動修復舊設定檔，補齊遺失的新分頁 (如 T11)
        default_ids = [t["id"] for t in DEFAULT_TABS]
        saved_ids = self.data.get("tab_order", [])
        missing_ids = [tid for tid in default_ids if tid not in saved_ids]
        for tid in missing_ids:
            if "t7_settings" in saved_ids: saved_ids.insert(saved_ids.index("t7_settings"), tid)
            else: saved_ids.append(tid)
        self.data["tab_order"] = saved_ids
        
        self.data.pop("t2_extraction_list", None)

        # === 智慧外部語系動態載入 ===
        ui_lang = str(self.data.get("ui_language", "zh-tw")).strip().lower()
        
        # 1. 內建基本英文相容
        if ui_lang == "en-us":
            UI_LANG_DICT.update({
                "MD 阿斯特婭工具箱": "MD AstellarToolBox",
                "解碼圖片發生錯誤 (Error decoding image)": "Error decoding image",
                "子行程讀取檔案失敗 (Child process failed loading)": "Child process failed loading",
                "衝突覆蓋": "Conflict override", "由": "by", "覆寫": "overwritten", "正在掃描模組": "Scanning mod"
            }) 

        # 2. 自動嘗試讀取外部 Languages 目錄下的自訂語系檔
        lang_dir = os.path.join(os.getcwd(), "MD_Tool_Essential", "Languages")
        lang_file = os.path.join(lang_dir, f"{ui_lang}.json")
        if os.path.exists(lang_file):
            try:
                with open(lang_file, "r", encoding="utf-8") as lf:
                    custom_dict = json.load(lf)
                    if isinstance(custom_dict, dict):
                        UI_LANG_DICT.update(custom_dict)
            except Exception:
                # 🛡️ 異常防護：當 JSON 損壞時不中斷啟動，直接安全降級使用預設繁體中文
                pass

    def _atomic_write_json(self, data_dict):
        """🛡️ DRY 核心：原子化寫入，加入重試機制與安全退回防線，防範防毒軟體干擾"""
        import time
        with self._save_lock:
            tmp_file = f"{CONFIG_FILE}.tmp"
            try:
                with open(tmp_file, "w", encoding="utf-8") as f:
                    json.dump(data_dict, f, ensure_ascii=False, indent=4)
                
                success = False
                for dummy_retry in range(3):
                    try:
                        os.replace(tmp_file, CONFIG_FILE)
                        success = True
                        break
                    except Exception:
                        time.sleep(0.1)
                        
                # 安全退回防線：如果 os.replace 真的徹底失敗，改用直接開檔覆寫
                if not success:
                    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                        json.dump(data_dict, f, ensure_ascii=False, indent=4)
                    try: os.remove(tmp_file)
                    except Exception: pass
            except Exception: pass

    def save(self):
        save_data = self.data.copy()
        save_data.pop("t2_extraction_list", None)
        self._atomic_write_json(save_data)

    def save_single_key(self, key, value):
        """🛡️ 防汙染儲存：只更新 JSON 檔案中的單一數值，絕對不寫入 UI 上的其他草稿"""
        self.data[key] = value
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                disk_data = json.load(f)
        except Exception:
            disk_data = self.data.copy()
            
        disk_data[key] = value
        self._atomic_write_json(disk_data)

    def save_t11_only(self, active_mods):
        """只抽換 T11 的狀態並存檔，絕不污染其他分頁的草稿"""
        self.data["t11_active_mods"] = active_mods
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f: 
                disk_data = json.load(f)
        except Exception: 
            disk_data = self.data.copy()
            
        disk_data["t11_active_mods"] = active_mods
        self._atomic_write_json(disk_data)

    def get(self, key, default=None): return self.data.get(key, default)
    
    def set(self, key, value):
        if self.data.get(key) == value: return
        self.data[key] = value
        
        # 智慧路徑與連動同步
        if self.data.get("sync_paths"):
            # 【智慧修正】當修改全域「原檔」名稱時，同步更新分頁 2 的資料夾後綴，並發送解耦訊號更新 UI
            if key == "s_folder_raw":
                self.data["t2_folder_name"] = value
                self.signals.sync_folder.emit(value)
            elif key == "t2_folder_name":
                self.signals.sync_folder.emit(value)
                
            if key in self.group_root:
                for k in self.group_root: self.data[k] = value
                self.signals.sync_root.emit(value)
            elif key in self.group_src:
                for k in self.group_src: self.data[k] = value
                self.signals.sync_src.emit(value)
            elif key in self.group_csv:
                for k in self.group_csv: self.data[k] = value
                self.signals.sync_csv.emit(value)
            
            # [修復] 跨分頁路徑自動連動：當 T2 輸出改變或原檔設定改變時，動態組合路徑推送給 T3
            if key in ["t1_out_dir", "t2_out_dir", "t1_txt_name", "t2_folder_name", "s_folder_raw"]:
                root_d = clean_path(self.data.get("t2_out_dir") or self.data.get("t1_out_dir", ""))
                txt_name = self.data.get("t1_txt_name", "Extracted_Names.txt").strip()
                if root_d and txt_name:
                    new_txt_path = os.path.join(root_d, txt_name)
                    self.data["t2_txt_dir"] = new_txt_path
                    self.signals.sync_t2_txt.emit(new_txt_path)
                folder = self.data.get("t2_folder_name", "").strip() or "原檔"
                if root_d:
                    t3_path = os.path.join(root_d, folder)
                    self.data["t3_src_var"] = t3_path
                    self.signals.sync_t3_src.emit(t3_path)
                
            
# =========================================================================
# ==================== 特製元件：遊戲王 Link 箭頭九宮格 =====================
# =========================================================================
class LinkAnchorPicker(QWidget):
    anchorChanged = Signal(str)
    def __init__(self, current_anchor):
        super().__init__()
        self.setFixedSize(90, 90)
        self.anchor = current_anchor
        self.map = [
            ("nw", 0, 0), ("n", 30, 0), ("ne", 60, 0),
            ("w", 0, 30), ("center", 30, 30), ("e", 60, 30),
            ("sw", 0, 60), ("s", 30, 60), ("se", 60, 60)
        ]

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#1A1A1A"))
        
        for name, bx, by in self.map:
            color = QColor("#D83C3C") if self.anchor == name else QColor("#555555")
            painter.setBrush(color)
            painter.setPen(Qt.NoPen)
            
            if name == "center":
                painter.drawRect(bx+8, by+8, 14, 14)
            else:
                pts = {
                    "nw": [QPoint(bx+6,by+6), QPoint(bx+24,by+6), QPoint(bx+6,by+24)],
                    "n": [QPoint(bx+15,by+6), QPoint(bx+24,by+24), QPoint(bx+6,by+24)],
                    "ne": [QPoint(bx+24,by+6), QPoint(bx+6,by+6), QPoint(bx+24,by+24)],
                    "w": [QPoint(bx+6,by+15), QPoint(bx+24,by+6), QPoint(bx+24,by+24)],
                    "e": [QPoint(bx+24,by+15), QPoint(bx+6,by+6), QPoint(bx+6,by+24)],
                    "sw": [QPoint(bx+6,by+24), QPoint(bx+6,by+6), QPoint(bx+24,by+24)],
                    "s": [QPoint(bx+15,by+24), QPoint(bx+24,by+6), QPoint(bx+6,by+6)],
                    "se": [QPoint(bx+24,by+24), QPoint(bx+6,by+24), QPoint(bx+24,by+6)]
                }
                painter.drawPolygon(QPolygon(pts[name]))

    def mousePressEvent(self, event):
        col, row = int(event.position().x() // 30), int(event.position().y() // 30)
        if 0 <= col <= 2 and 0 <= row <= 2:
            self.anchor = self.map[row * 3 + col][0]
            self.anchorChanged.emit(self.anchor)
            self.update()

# =========================================================================
# ==================== Qt 執行緒通訊網 ======================================
# =========================================================================
class WorkerSignals(QObject):
    progress = Signal(int)
    finished = Signal(bool, object, object)

class TaskWorker(QRunnable):
    def __init__(self, engine_func, args):
        super().__init__()
        self.engine_func = engine_func
        self.args = args
        self.signals = WorkerSignals()

    def run(self):
        def progress_cb(count): self.signals.progress.emit(count)
        def finish_cb(success, count_or_err, extra=None): self.signals.finished.emit(success, count_or_err, extra)
        try:
            self.engine_func(*self.args, progress_cb, finish_cb)
        except Exception as e:
            finish_cb(False, _("系統底層崩潰：{error}").format(error=str(e)), traceback.format_exc())

# =========================================================================
# ==================== 第三區：核心邏輯大腦 (純粹運算，無 UI 依賴) ==============
# =========================================================================
def clean_path(path_str): return str(path_str).strip(' "\'')

class MDEngine:
    TEMP_DIR = os.path.join(os.getcwd(), "MD_Tool_Temp")
    _csv_cache = {}

    @staticmethod
    def safe_copy_file(src_path, dst_path):
        """🛡️ 原子化複製：複製到暫存檔後再瞬間替換，防範中途斷電或當機導致 0KB 損壞"""
        tmp_path = f"{dst_path}.tmp"
        shutil.copy2(src_path, tmp_path)
        os.replace(tmp_path, dst_path)
        
    @staticmethod
    def safe_write_bytes(dst_path, byte_data):
        """🛡️ 原子化二進位寫入：防範 Unity Bundle 寫入失敗導致遊戲崩潰"""
        tmp_path = f"{dst_path}.tmp"
        with open(tmp_path, "wb") as f:
            f.write(byte_data)
        os.replace(tmp_path, dst_path)

    CSV_HEADER_FOLDER    = "Folder Name"
    CSV_HEADER_CONTAINER = "Container"
    CSV_HEADER_TYPE      = "Type"
    CSV_HEADER_SUBTYPE   = "SubType"
    CSV_HEADER_FILE_ID   = "File ID"
    CSV_HEADER_ITEM_ID   = "ITEM ID"
    RE_CUTIN_PATH = re.compile(r'monstercutin/.*?(p\d+)', re.IGNORECASE)
    RE_CUTIN_FILE = re.compile(r'^(p\d+)(.*)$', re.IGNORECASE)

    @staticmethod
    def normalize_string(text):
        """✨ 雙向同化核心：消除全半形與大小寫差異 (NFKC + lower)"""
        import unicodedata
        if not text: return ""
        return unicodedata.normalize('NFKC', str(text)).strip().lower()

    @staticmethod
    def find_longest_prefix(filename, valid_ids):
        """✨ 字典引導的最長前綴匹配：精準剝離使用者自訂後綴 (具備邊界防護，徹底斷絕誤殺)"""
        name_no_ext = os.path.splitext(filename)[0]
        dummy_is_cut, clean_base, dummy_tag = MDEngine.parse_cutin_tag_and_base(name_no_ext)
        
        sorted_ids = sorted(valid_ids, key=len, reverse=True)
        
        def is_valid_match(test_str, prefix):
            """🛡️ 邊界防護：比對成功後，剩餘字串的第一個字元必須是合法分隔符或結尾"""
            test_lower = test_str.lower()
            prefix_lower = prefix.lower()
            if test_lower.startswith(prefix_lower):
                if len(test_lower) == len(prefix_lower): 
                    return True
                # 確保下一個字元是明確的分隔符
                return test_lower[len(prefix_lower)] in ('_', '-', '.', ' ')
            return False

        # 1. 先用拔除標籤的 clean_base 測
        for vid in sorted_ids:
            if is_valid_match(clean_base, vid): return vid
            
        # 2. 如果沒中，用原始無副檔名測 (常規卡片或場地多貼圖)
        for vid in sorted_ids:
            if is_valid_match(name_no_ext, vid): return vid
                
        # 3. 如果還是沒中，退回傳統切底線法 (向下相容防呆)
        return name_no_ext.split('_')[0]

    @staticmethod
    def parse_cutin_tag_and_base(filename_or_id):
        """DRY輔助函式：解析檔名中的 -hd / -sd，並執行 p+數字 的安全防護鎖校驗"""
        name_without_ext = os.path.splitext(filename_or_id)[0]
        
        # ✨ 修正：移除結尾錨點 $，避免被雙副檔名干擾，精準全域替換 -(hd|sd)
        clean_name = re.sub(r'-(hd|sd)', "", name_without_ext, flags=re.IGNORECASE)
        
        # 安全防護鎖：限定為 p + 數字 開頭的動畫資產
        if re.match(r'^p\d+', clean_name, re.IGNORECASE):
            req_res_tag = ""
            name_lower = name_without_ext.lower()
            if "-hd" in name_lower:
                req_res_tag = "highend_hd"
            elif "-sd" in name_lower:
                req_res_tag = "/sd/"
            
            if req_res_tag:
                return True, clean_name, req_res_tag
        return False, name_without_ext, ""

    @staticmethod
    def is_cutin_asset(container_path, obj_type_name, clean_name):
        """智慧識別：判定是否為 Spine 召喚動畫 (Cut-In) 的相關資源"""
        c_lower = str(container_path).lower()
        safe_name = str(clean_name).strip()
        name_lower = safe_name.lower()
        
        if 'monstercutin' not in c_lower:
            return False, ""
            
        match = MDEngine.RE_CUTIN_PATH.search(c_lower)
        item_id = match.group(1).lower() if match else ""
        
        if not item_id:
            match_f = MDEngine.RE_CUTIN_FILE.match(name_lower)
            if match_f:
                item_id = match_f.group(1).lower()

        if not item_id:
            return False, ""
            
        # ✨ 動態解析度標籤改為 -hd 與 -sd
        res_tag = "-hd" if "highend_hd" in c_lower else ("-sd" if "/sd/" in c_lower else "")

        if obj_type_name == "Texture2D":
            # 🛡️ 核心修復：優先保留貼圖本身的真實名稱，防止子部件被強制降級為資料夾 ID
            # 舉例：若貼圖名為 p152423，它將保留 p152423 而不會被資料夾的 p15242 覆蓋
            actual_id = item_id
            match_name = MDEngine.RE_CUTIN_FILE.match(name_lower)
            if match_name:
                actual_id = match_name.group(1).lower()
                
            return True, f"{actual_id}{res_tag}"
            
        elif obj_type_name == "TextAsset":
            if 'atlas' in name_lower or 'js' in name_lower or name_lower.endswith('.json') or name_lower.endswith('.txt'):
                if "." in safe_name:
                    parts = safe_name.split(".", 1) # p18826.atlas.txt -> p18826, atlas.txt
                    new_id = f"{parts[0]}{res_tag}.{parts[1]}"
                else:
                    new_id = f"{safe_name}{res_tag}"
                return True, new_id
                
        return False, ""

    @staticmethod
    def is_subpath(child_path, parent_path):
        """🛡️ 物理路徑結界判定：精準化解磁碟機根目錄帶來的邊界 Bug"""
        if not child_path or not parent_path: return False
        try:
            # 使用 rstrip 剝除結尾可能的斜線，完美對齊 Windows 根目錄 (如 D:\) 與一般資料夾的格式
            c_real = os.path.normcase(os.path.realpath(str(child_path))).rstrip(os.sep)
            p_real = os.path.normcase(os.path.realpath(str(parent_path))).rstrip(os.sep)
            if c_real == p_real: return True
            if c_real.startswith(p_real + os.sep): return True
            return False
        except Exception:
            return False

    @staticmethod
    def get_child_exclude_paths(scan_root, candidate_paths):
        """🛡️ 智慧結界篩選器：只在排除目標『確實位在掃描根目錄內部 (Strict Child)』時才納入排除名單，防範父目錄反向誤殺"""
        safe_excludes = []
        if not scan_root: return safe_excludes
        try:
            root_real = os.path.normcase(os.path.realpath(str(scan_root))).rstrip(os.sep)
            for path in candidate_paths:
                if not path: continue
                p_real = os.path.normcase(os.path.realpath(str(path))).rstrip(os.sep)
                # 只有當路徑位於 scan_root 內部，且不等於 scan_root 本身時，才視為需要避開的內部資料夾
                if p_real != root_real and p_real.startswith(root_real + os.sep):
                    safe_excludes.append(path)
        except Exception: pass
        return safe_excludes

    @staticmethod
    def prune_walk_dirs(current_root, dirs, exclude_paths):
        """🛡️ 動態剪枝器：將即將踏入的子目錄中，屬於結界的目標直接剔除，阻斷 os.walk 遞迴"""
        if not dirs or not exclude_paths: return
        for i in range(len(dirs) - 1, -1, -1):
            child_full = os.path.join(current_root, dirs[i])
            if any(MDEngine.is_subpath(child_full, ex) for ex in exclude_paths if ex):
                dirs.pop(i)

    @staticmethod
    def get_csv_indices(header):
        """集中式 CSV 索引解析器 (徹底消滅硬編碼與迴圈)"""
        h_lower = [str(c).strip().lower() for c in header]
        return {
            "folder": h_lower.index(MDEngine.CSV_HEADER_FOLDER.lower()) if MDEngine.CSV_HEADER_FOLDER.lower() in h_lower else -1,
            "container": h_lower.index(MDEngine.CSV_HEADER_CONTAINER.lower()) if MDEngine.CSV_HEADER_CONTAINER.lower() in h_lower else -1,
            "type": h_lower.index(MDEngine.CSV_HEADER_TYPE.lower()) if MDEngine.CSV_HEADER_TYPE.lower() in h_lower else -1,
            "subtype": h_lower.index(MDEngine.CSV_HEADER_SUBTYPE.lower()) if MDEngine.CSV_HEADER_SUBTYPE.lower() in h_lower else -1,
            "hash": h_lower.index(MDEngine.CSV_HEADER_FILE_ID.lower()) if MDEngine.CSV_HEADER_FILE_ID.lower() in h_lower else -1,
            "id": h_lower.index(MDEngine.CSV_HEADER_ITEM_ID.lower()) if MDEngine.CSV_HEADER_ITEM_ID.lower() in h_lower else -1
        }

    @staticmethod
    def task_generate_translation_template(source_file, out_dir):
        """AST 語法樹解析器與備用 JSON 樣板生成器 (支援繁中自動安全對等映射)"""
        import ast
        try:
            # 方案 A：若存在 Python 原始碼，優先使用 AST 語法樹精準萃取程式碼中所有的 _("...")
            if source_file and os.path.exists(source_file) and source_file.endswith('.py'):
                with open(source_file, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read())
                
                strings = set()
                for node in ast.walk(tree):
                    # 1. 抓取標準的 _("...")
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == '_':
                        if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                            strings.add(node.args[0].value)
                    
                    # 2. ✨ 智慧抓取：自動擷取所有 placeholder="..." 裡面的浮水印字串
                    elif isinstance(node, ast.keyword) and node.arg == 'placeholder':
                        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                            strings.add(node.value.value)
                            
                    # 3. ✨ 智慧抓取：自動擷取 DEFAULT_TABS 字典裡的 "name": "..." (側邊欄)
                    elif isinstance(node, ast.Dict):
                        for k, v in zip(node.keys, node.values):
                            if isinstance(k, ast.Constant) and k.value == "name":
                                if isinstance(v, ast.Constant) and isinstance(v.value, str):
                                    strings.add(v.value)
                
                os.makedirs(out_dir, exist_ok=True)
                
                # A1. 產生空白翻譯樣板 raw.json
                raw_path = os.path.join(out_dir, "raw.json")
                raw_dict = {s: "" for s in sorted(strings)}
                with open(raw_path, "w", encoding="utf-8") as f:
                    json.dump(raw_dict, f, ensure_ascii=False, indent=4)
                
                # A2. ✨ 自動建立/補齊對等映射的 zh-tw.json (安全合併不覆蓋已調整項目)
                zhtw_path = os.path.join(out_dir, "zh-tw.json")
                zhtw_dict = {}
                if os.path.exists(zhtw_path):
                    try:
                        with open(zhtw_path, "r", encoding="utf-8-sig") as lf:
                            existing_data = json.load(lf)
                            if isinstance(existing_data, dict):
                                zhtw_dict = existing_data
                    except Exception:
                        pass
                
                # 僅對不存在或目前為空的 Key 進行對等映射自動填充 (Key = Value 形式)
                for s in strings:
                    if s not in zhtw_dict or not zhtw_dict[s]:
                        zhtw_dict[s] = s
                        
                # 重新排序字典
                zhtw_dict = {k: zhtw_dict[k] for k in sorted(zhtw_dict.keys())}
                with open(zhtw_path, "w", encoding="utf-8") as f:
                    json.dump(zhtw_dict, f, ensure_ascii=False, indent=4)
                
                success_msg = _("已成功匯出翻譯樣板！\n\n"
                                "1. 空白樣板：raw.json (用於翻譯其他語系)\n"
                                "2. 對等映射繁體中文：zh-tw.json (已安全補齊新項目並保留舊內容)\n\n"
                                "儲存路徑：{path}").format(path=out_dir)
                return True, success_msg

            # 方案 B (備用機制)：打包為 EXE 後找不到原始碼時，自動讀取現有的 zh-tw.json 提取字串 Key
            fallback_json = os.path.join(os.getcwd(), "MD_Tool_Essential", "Languages", "zh-tw.json")
            if os.path.exists(fallback_json):
                with open(fallback_json, "r", encoding="utf-8-sig") as f:
                    raw_dict = json.load(f)
                
                if isinstance(raw_dict, dict):
                    os.makedirs(out_dir, exist_ok=True)
                    out_path = os.path.join(out_dir, "raw.json")
                    out_dict = {k: "" for k in sorted(raw_dict.keys())}
                    
                    with open(out_path, "w", encoding="utf-8") as f:
                        json.dump(out_dict, f, ensure_ascii=False, indent=4)
                    
                    success_msg = _("在目前的封裝環境下找不到 Python 原始碼，已從現有的 zh-tw.json 還原出空白樣板：raw.json\n\n"
                                    "儲存路徑：{path}").format(path=out_dir)
                    return True, success_msg

            return False, _("找不到 Python 原始碼 (.py)，也找不到備用的 zh-tw.json 檔案！")
        except Exception as e:
            return False, str(e)
        
    @staticmethod
    def find_lang_column_index(header, search_lang="zh-tw", col_type="Name", strict=False):
        """
        集中管理的語言欄位索引解析器 (標準化標頭版)
        標準標頭格式： "{lang}(Name)" / "{lang}(Desc)"
        """
        target_suffix = f"({col_type})"
        std_head = f"{search_lang}{target_suffix}"
        
        # 1. 優先尋找精準的標準標頭 (e.g., "zh-tw(Name)")
        for i, col in enumerate(header):
            if col.lower() == std_head.lower():
                return i
                
        # 2. 尋找舊版冗長標頭 (向下相容)
        legacy_headers = LEGACY_LANG_HEADERS.get(search_lang)
        if legacy_headers:
            n_head, d_head = legacy_headers
            legacy_target = n_head if col_type == "Name" else d_head
            if legacy_target in header:
                return header.index(legacy_target)

        # 🛡️ 嚴格模式 (寫入/擴充)：找不到精準的專屬匹配，必須回傳 -1 觸發新增欄位，嚴禁亂抓！
        if strict:
            return -1

        # --- 以下為讀取/搜尋專用的降級相容防線 (strict=False) ---
        blacklist = ["folder", "file", "hash", "檔名", "目錄"]
        
        # 降級 A：尋找任何包含指定語言代碼與 (Name) 的欄位
        for i, col in enumerate(header):
            col_lower = col.lower()
            if search_lang in col_lower and target_suffix.lower() in col_lower:
                return i

        # 降級 B：尋找任意帶有 (Name)/(Desc) 的欄位 (排除黑名單)
        for i, col in enumerate(header):
            col_lower = col.lower()
            if target_suffix.lower() in col_lower and not any(x in col_lower for x in blacklist):
                return i

        # 降級 C：相容極舊版，完全沒有括號標籤的自訂標頭
        fallback_keywords = ["名稱", "名", "name"] if col_type == "Name" else ["效果", "desc"]
        for i, col in enumerate(header):
            col_lower = col.lower()
            if any(kw in col_lower for kw in fallback_keywords) and "(" not in col_lower and not any(x in col_lower for x in blacklist):
                return i

        return -1

    @staticmethod
    def is_valuable_texture(name):
        """內建智慧過濾器：過濾無用的 Shader 貼圖，保留有意義的視覺資源
        現在為了測試先全部改TRUE"""
        if not name: return True
        val = str(name).strip()
        if val.isdigit(): return True  # 純數字 (官方卡圖) 絕對保留
        val_lower = val.lower()
        
        # 黑名單：精準阻擊 3D 渲染貼圖
        black_list = ['_normal', '_nrm', '_metallic', '_metalness', '_roughness', '_gloss', '_specular', '_spec', '_occlusion', '_ao', '_height', 'lightmap', '_lm', '_shadow', '_stencil', '_emission', '_em']
        if any(b in val_lower for b in black_list): return False
        
        # 白名單：寬鬆保留主體貼圖與所有外觀/UI資源
        white_list = ['tex', 'color', 'bg', 'diffuse', 'albedo', 'basecolor', 'near', 'far', 'profileicon', 'sleeve', 'protector', 'coin', 'mate', 'ui', 'card', 'icon', 'mat', 'frame', 'deck']
        if any(w in val_lower for w in white_list): return True
        
        return True # 非主流雜訊一律給過，十分關鍵
    
    @staticmethod
    def check_memory_limit(limit_pct=85.0):
        """作業系統級記憶體雷達：帶有 30 秒超時機制的防死鎖設計"""
        import ctypes
        import time
        try:
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            max_retries = 30 # 最大休眠容忍時間：30 秒
            retry_count = 0
            while retry_count < max_retries:
                stat = MEMORYSTATUSEX()
                stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
                ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
                # dwMemoryLoad 即為當前系統實體記憶體使用率 (0~100)
                if stat.dwMemoryLoad < limit_pct:
                    break
                time.sleep(1.0)
                retry_count += 1
        except Exception:
            pass # 如果非 Windows 系統或取得失敗，則直接放行不卡死

    @staticmethod
    def resolve_path(base_path, input_path):
        """將相對路徑與絕對路徑智慧解析為絕對路徑"""
        clean_input = clean_path(input_path)
        return clean_input if os.path.isabs(clean_input) else os.path.join(base_path, clean_input)

    @staticmethod
    def parse_workers(cfg_val):
        """算力調度器：智慧 Auto 與完全尊重使用者手動設定"""
        total = os.cpu_count() or 2
        if str(cfg_val).lower() == "auto" or not str(cfg_val).strip().isdigit():
            return max(1, total - 1) if total <= 4 else (total - 2 if total <= 8 else max(4, total - 4))
        # 🌸 移除強制上限限制，將硬體主導權完全交還給使用者
        return max(1, int(cfg_val))

    @staticmethod
    def get_optimal_workers(cfg_val="Auto"): return MDEngine.parse_workers(cfg_val)
    
    @staticmethod
    def get_heavy_task_workers(cfg_val="Auto"): return MDEngine.parse_workers(cfg_val)

    @staticmethod
    def get_csv_data(csv_path):
        if not os.path.exists(csv_path): return {}, []
        mtime = os.path.getmtime(csv_path)
        if csv_path in MDEngine._csv_cache:
            cached_mtime, cached_map, cached_db = MDEngine._csv_cache[csv_path]
            if cached_mtime == mtime: return cached_map, cached_db
        
        mapping, db_dict = {}, {}
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            header = next(reader, [])
            
            indices = MDEngine.get_csv_indices(header)
            f_idx, c_idx, h_idx, id_idx = indices["folder"], indices["container"], indices["hash"], indices["id"]
            t_idx, st_idx = indices["type"], indices["subtype"] # 👈 提取 Type 與 SubType 欄位索引
            
            if h_idx == -1 or id_idx == -1:
                raise Exception(_("偵測到不相容的舊版 CSV 格式！請至分頁 1 重新掃描並生成對照表。"))
                
            for row in reader:
                if len(row) > max(h_idx, id_idx) and h_idx != -1 and id_idx != -1:
                    c_id, h_name = row[id_idx].strip(), row[h_idx].strip()
                    folder = row[f_idx].strip() if f_idx != -1 and len(row) > f_idx else "0000"
                    container = row[c_idx].strip() if c_idx != -1 and len(row) > c_idx else "Common"
                    
                    # 👈 解析卡片真實的 Type 與 SubType
                    c_type = row[t_idx].strip() if t_idx != -1 and len(row) > t_idx else "None"
                    c_subtype = row[st_idx].strip() if st_idx != -1 and len(row) > st_idx else "None"
                    
                    if c_id and h_name:
                        mapping.setdefault(c_id, []).append({'folder': folder or "0000", 'container': container, 'hash': h_name})
                        if c_id not in db_dict: 
                            db_dict[c_id] = {
                                'id': c_id, 
                                'hash': h_name, 
                                'header': header, 
                                'full_row': row,
                                'properties': {'Type': c_type, 'SubType': c_subtype} # 👈 補齊 properties！
                            }
        db = list(db_dict.values())
        MDEngine._csv_cache[csv_path] = (mtime, mapping, db)
        return mapping, db

    @staticmethod
    def get_actual_bundle_path(src_dir, hash_name):
        p1 = os.path.join(src_dir, hash_name[:2].lower(), hash_name)
        return p1 if os.path.exists(p1) else os.path.join(src_dir, hash_name)

    @staticmethod
    def get_actual_source_path(base_src_dir, hash_name, folder="0000"):
        if folder == "StreamingAssets":
            try:
                sa_dir = MDEngine.get_sa_dir_safe(base_src_dir)
                if os.path.exists(sa_dir): return MDEngine.get_actual_bundle_path(sa_dir, hash_name)
            except Exception: pass
        return MDEngine.get_actual_bundle_path(base_src_dir, hash_name)

    @staticmethod
    def is_unity_bundle(filepath):
        try:
            with open(filepath, 'rb') as f: return f.read(7) in (b'UnityFS', b'UnityWe', b'UnityRa')
        except Exception: return False

    @staticmethod
    def is_visual_asset(name):
        """智慧辨識：判定是否為指定的視覺資產"""
        if not name: return False
        n = str(name).lower()
        if 'basecolor' in n and 'mat_' in n: return True
        if 'coin01tex' in n or 'cointossicon' in n: return True
        if 'deckcase' in n: return True
        if 'profileframe' in n: return True
        if 'profileicon' in n: return True
        if 'protectoricon' in n: return True
        if 'wallpaper' in n:
            # 🛡️ 大廳背景擴充黑名單，剔除無用的 UI 裝飾與商店縮圖
            black_list = ['wallpapericon', 'wallpaperthumb', 'gui_wallpaperbg', 'productthumbbgwallpaperprofile', 'sactx-0-2048x1024-bc7', 'wallpapersale', 'wallpapertopicsthumb']
            if not any(b in n for b in black_list): return True
        return False

    @staticmethod
    def get_base_item_name(name):
        """智慧主幹辨識：將雜亂的變體代號還原為純粹的物品主幹"""
        if name.startswith("Mat_"):
            parts = name.split('_')
            if len(parts) >= 2: return f"{parts[0]}_{parts[1]}"
        if name.startswith("ProtectorIcon"):
            m = re.match(r'(ProtectorIcon\d+)', name)
            if m: return m.group(1)
        return re.sub(r'_(l|m|s|1|2|near|far|128|256|512)$', '', name, flags=re.IGNORECASE)

    @staticmethod
    def extract_id_from_line(line_text):
        """
        🛡️ 集中化 ID 萃取器：統一從文字行中剝離資產 ID
        新增支援連字號 (-) 與點號 (.)，完美相容 Spine 動畫與文字資產 (如 p18478-hd)
        """
        import re
        safe_line = str(line_text).strip()
        match = re.match(r'^([a-zA-Z0-9_\-\.]+)', safe_line)
        return match.group(1) if match else None

    @staticmethod
    def task_gallery_cache(items_to_fetch, src_dir, cache_dir, progress_cb, finish_cb):
        """背景快取生成器：100% 對齊掃描端優先權，不卡頓、低記憶體消耗地提取縮圖"""
        os.makedirs(cache_dir, exist_ok=True)
        
        # 🛡️ O(N) 磁碟 I/O 轉換為 O(1) 記憶體查表，提升機械硬碟上的校驗速度
        try:
            existing_files = set(os.listdir(cache_dir))
        except Exception:
            existing_files = set()

        count = 0; success = 0
        for hash_name, item_ids in items_to_fetch.items():
            count += 1
            if progress_cb: progress_cb(count)
            # 使用記憶體查表取代硬碟 I/O 查詢
            if all(f"{iid}.png" in existing_files for iid in item_ids):
                success += len(item_ids); continue
            
            src_file = MDEngine.get_actual_source_path(src_dir, hash_name, "0000")
            if not os.path.exists(src_file): src_file = MDEngine.get_actual_source_path(src_dir, hash_name, "StreamingAssets")
            if not os.path.exists(src_file): continue

            env = None            
            try:
                env = UnityPy.load(src_file)
                path_to_container = {obj.path_id: str(c_path) for c_path, obj in env.container.items()}
                base_container_path = str(next(iter(env.container.keys()), ""))
                
                # ✨ DRY 優化：大小寫同化字典在迴圈外建構一次即可，大幅提升效能
                item_ids_lower = {vid.lower(): vid for vid in item_ids}

                for obj in env.objects:
                    if obj.type.name == "Texture2D":
                        try:
                            clean_name = ""
                            try:
                                if hasattr(obj, "peek_name"):
                                    peeked = obj.peek_name()
                                    if peeked: clean_name = str(peeked)
                                if not clean_name:
                                    data = obj.read()
                                    if hasattr(data, "name") and data.name:
                                        clean_name = str(data.name)
                            except Exception: pass

                            clean_name = clean_name.replace('.bmp', '').replace('.png', '').strip()
                            c_path = str(path_to_container.get(obj.path_id, base_container_path))

                            if not clean_name:
                                if c_path:
                                    clean_name = c_path.split('/')[-1].replace('.prefab', '').replace('.mat', '').replace('.bmp', '').replace('.png', '')
                                else:
                                    clean_name = str(hash_name).replace('.bundle', '')

                            clean_name = str(clean_name).strip()

                            clean_name_lower = clean_name.lower() if clean_name else ""
                            base_id_lower = re.sub(r'_(l|m|s|128|256|512)$', '', clean_name_lower, flags=re.IGNORECASE) if clean_name_lower else ""
                            
                            target_id = None
                            if clean_name_lower in item_ids_lower: 
                                target_id = item_ids_lower[clean_name_lower]
                            elif base_id_lower in item_ids_lower: 
                                target_id = item_ids_lower[base_id_lower]
                            elif c_path:
                                # 🛡️ 雙重降級保護：若內部物件名稱為通用名(如 "BaseColor")，自動嘗試從 Container 路徑 (c_path) 萃取 ID 進行匹配
                                c_name = c_path.split('/')[-1].replace('.prefab', '').replace('.mat', '').replace('.bmp', '').replace('.png', '').strip().lower()
                                c_base = re.sub(r'_(l|m|s|128|256|512)$', '', c_name, flags=re.IGNORECASE)
                                if c_name in item_ids_lower:
                                    target_id = item_ids_lower[c_name]
                                elif c_base in item_ids_lower:
                                    target_id = item_ids_lower[c_base]

                            if target_id:
                                img_filename = f"{target_id}.png"
                                img_path = os.path.join(cache_dir, img_filename)
                                # 同樣使用查表，確認記憶體中是否不存在該圖
                                if img_filename not in existing_files:
                                    data = obj.read()
                                    img = data.image
                                    w, h = img.size
                                    short_side = min(w, h)
                                    
                                    if short_side < 127: continue
                                    
                                    ratio = 128.0 / short_side
                                    new_w, new_h = int(round(w * ratio)), int(round(h * ratio))
                                    
                                    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                                    img.save(img_path)
                                    existing_files.add(img_filename) # 儲存新圖後，立刻向記憶體註冊，供後續查表
                                success += 1
                        except Exception: pass
            except Exception: pass
            finally:
                # 🛡️ 修正記憶體釋放位置：確保整個 Bundle 內的所有物件都遍歷完成後，才於最外層釋放資源
                if env: del env
        finish_cb(True, success, cache_dir)

    @staticmethod
    def search_cards(query, database, search_lang="zh-tw", limit=200, visual_only=False):
        if not query or not database: return []
        import unicodedata
        
        query_norm = unicodedata.normalize('NFKC', query).strip().lower()
        if not query_norm: return []

        results = []
        for card in database:
            cid = card['id']
            if visual_only and not MDEngine.is_visual_asset(cid): continue
            header, row = card.get('header', []), card.get('full_row', [])
            
            # 使用集中解析器獲取當前指定語系的名稱與效果索引
            n_idx = MDEngine.find_lang_column_index(header, search_lang, "Name")
            d_idx = MDEngine.find_lang_column_index(header, search_lang, "Desc")
            
            raw_name = row[n_idx] if n_idx != -1 and len(row) > n_idx else ""
            raw_desc = row[d_idx] if d_idx != -1 and len(row) > d_idx else ""
            
            cid = card['id']
            chash = card['hash']
            
            s_cid = unicodedata.normalize('NFKC', cid).lower()
            s_chash = unicodedata.normalize('NFKC', chash).lower()
            s_name = unicodedata.normalize('NFKC', raw_name).lower()
            s_desc = unicodedata.normalize('NFKC', raw_desc).lower()
            
            score = 0.0
            
            # 權重分級
            if query_norm == s_cid or query_norm == s_chash: 
                score = 2.0  
            elif query_norm == s_name: 
                score = 1.8  
            elif query_norm in s_cid or query_norm in s_chash: 
                score = 1.5  
            elif query_norm in s_name: 
                score = 1.0  
            elif query_norm in s_desc: 
                score = 0.8  
            elif len(query_norm) >= 2:
                ratio = difflib.SequenceMatcher(None, query_norm, s_name).ratio()
                if ratio > 0.5: score = ratio
            
            if score > 0:
                cat = 1 if '(' in raw_name and ')' in raw_name else 0
                if not raw_name: cat = 2
                results.append((cat, score, {'id': cid, 'name': raw_name, 'hash': chash}))
        
        results.sort(key=lambda x: (x[0], -x[1]))
        
        final_list = []
        for r in results[:limit]:
            item = r[2]
            if item['name']:
                final_list.append(f"{item['id']} ({item['name']}) [{item['hash']}]")
            else:
                final_list.append(f"{item['id']} [{item['hash']}]")
                
        return final_list

    @staticmethod
    def _fuzzy_match(query, text, threshold=0.75):
        if not query or not text: return 0.0
        if len(query) >= len(text):
            return difflib.SequenceMatcher(None, query, text).ratio()
        max_ratio = 0.0
        win_size = len(query)
        for i in range(len(text) - win_size + 1):
            ratio = difflib.SequenceMatcher(None, query, text[i:i+win_size]).ratio()
            if ratio > max_ratio: max_ratio = ratio
        return max_ratio

    @staticmethod
    def search_cards_advanced(params, database, search_lang="zh-tw", current_page=1):
        if not database: return [], 0, 0, 1, []
        
        import unicodedata
        query = params.get("query", "")
        visual_only = params.get("visual_only", False)
        inc_str = params.get("inc_words", "")
        exc_str = params.get("exc_words", "")
        f_name = params.get("fuzzy_name", False)
        f_desc = params.get("fuzzy_desc", False)
        limit_per_page = params.get("limit_per_page", 200)
        filters = params.get("filters", {})
        
        # --- 軌道 1：標準精確同化 ---
        norm_q = unicodedata.normalize('NFKC', query).strip().lower()
        norm_q = re.sub(r'[「」“”《》『』]', '"', norm_q)
        norm_q = norm_q.replace('－', '-').replace('／', '/').replace('～', '~').replace('・', '.')
        
        # --- 分詞器 (Tokenizer) ---
        includes = set([w.strip().lower() for w in inc_str.split() if w.strip()])
        excludes = set([w.strip().lower() for w in exc_str.split() if w.strip()])
        phrases = set()
        
        for m in re.finditer(r'"([^"]+)"', norm_q): phrases.add(m.group(1))
        norm_q = re.sub(r'"([^"]+)"', '', norm_q)
        
        for m in re.finditer(r'(?:^|\s)-([^\s]+)', norm_q): excludes.add(m.group(1))
        norm_q = re.sub(r'(?:^|\s)-([^\s]+)', '', norm_q)
        
        for m in re.finditer(r'(?:^|\s)\+([^\s]+)', norm_q): includes.add(m.group(1))
        norm_q = re.sub(r'(?:^|\s)\+([^\s]+)', '', norm_q)
        
        normal_terms = [w for w in norm_q.split() if w and w != '-']
        
        all_terms = normal_terms + list(phrases)
        full_query_stripped = re.sub(r'[\W_]+', '', "".join(all_terms)) # 軌道 2：完全脫水
        
        results = []
        
        # 矩陣判定開關提取
        chk_m_en = filters.get("怪獸", {}).get("enabled", False)
        chk_s_en = filters.get("魔法", {}).get("enabled", False)
        chk_t_en = filters.get("陷阱", {}).get("enabled", False)
        all_unrestricted = not (chk_m_en or chk_s_en or chk_t_en)
        
        for card in database:
            cid = str(card['id'])
            chash = str(card['hash'])
            header, row = card.get('header', []), card.get('full_row', [])
            
            n_idx = MDEngine.find_lang_column_index(header, search_lang, "Name")
            d_idx = MDEngine.find_lang_column_index(header, search_lang, "Desc")
            
            raw_name = row[n_idx] if n_idx != -1 and len(row) > n_idx else ""
            raw_desc = row[d_idx] if d_idx != -1 and len(row) > d_idx else ""
            
            props = card.get("properties", {})
            c_type = props.get("Type", "None")
            c_subtype = props.get("SubType", "None")
            
            # --- 1. 直通判定 (Pass-Through) ---
            is_passthrough = False
            if query:
                q_clean = query.strip().lower()
                if q_clean == cid.lower() or q_clean == chash.lower(): is_passthrough = True
                # ✨ 修正：涵蓋檢查 cid, chash 與卡名
                elif MDEngine.is_visual_asset(q_clean) and (q_clean in cid.lower() or q_clean in chash.lower() or q_clean in raw_name.lower()): is_passthrough = True
            
            # --- 2. 視覺配件篩選 ---
            if visual_only and not MDEngine.is_visual_asset(cid): continue
            
            # --- 3. 矩陣式 Type/SubType 篩選 ---
            if not is_passthrough and not all_unrestricted:
                type_match = False
                if c_type == "怪獸" and chk_m_en:
                    m_subs = filters["怪獸"]["subs"]
                    pen_en = filters["怪獸"]["pendulum"]
                    is_pen_card = "靈擺" in c_subtype
                    
                    if not m_subs and not pen_en: type_match = True
                    elif not m_subs and pen_en and is_pen_card: type_match = True
                    elif m_subs:
                        base_match = any(sub in c_subtype for sub in m_subs)
                        if pen_en: type_match = base_match and is_pen_card
                        else: type_match = base_match
                
                elif c_type == "魔法" and chk_s_en:
                    s_subs = filters["魔法"]["subs"]
                    if not s_subs: type_match = True
                    elif any(sub in c_subtype for sub in s_subs): type_match = True
                
                elif c_type == "陷阱" and chk_t_en:
                    t_subs = filters["陷阱"]["subs"]
                    if not t_subs: type_match = True
                    elif any(sub in c_subtype for sub in t_subs): type_match = True
                    
                if not type_match: continue
                
            # 同化準備
            s_name = unicodedata.normalize('NFKC', raw_name).lower()
            s_desc = unicodedata.normalize('NFKC', raw_desc).lower()
            s_name = re.sub(r'[「」“”《》『』]', '"', s_name)
            s_name = s_name.replace('－', '-').replace('／', '/').replace('～', '~').replace('・', '.')
            s_name_stripped = re.sub(r'[\W_]+', '', s_name) # 脫水卡名
            
            # --- 4. 排除詞過濾 ---
            if not is_passthrough and excludes:
                if any(exc in s_name for exc in excludes) or any(exc in s_desc for exc in excludes): continue
                
            # --- 5. 必含詞過濾 ---
            if not is_passthrough and includes:
                if not all((inc in s_name or inc in s_desc) for inc in includes): continue
                
            score = 0.0
            
            # --- 6. 階梯評分 ---
            if is_passthrough: score = 2.0
            elif query:
                joined_query = " ".join(all_terms)
                if joined_query == s_name: score = 1.8
                elif full_query_stripped and full_query_stripped == s_name_stripped: score = 1.6
                elif joined_query in s_name: score = 1.4
                elif all_terms and all(t in s_name for t in all_terms): score = 1.2
                elif phrases and any(f'"{p}"' in s_desc for p in phrases): score = 1.1
                elif joined_query in s_desc: score = 1.0
                elif all_terms and all(t in s_desc for t in all_terms): score = 0.8
                
                # --- 7. 滑動視窗模糊比對 ---
                if score == 0.0 and joined_query:
                    if f_name and normal_terms:
                        # ✨ 修正：針對各別分詞單獨進行滑動比對，防稀釋
                        if any(MDEngine._fuzzy_match(t, s_name) >= 0.75 for t in normal_terms): score = 0.6
                    if score == 0.0 and f_desc and normal_terms:
                        if any(MDEngine._fuzzy_match(t, s_desc) >= 0.75 for t in normal_terms): score = 0.4
                        
            # 無搜尋條件，純過濾器時給予基本分
            if not query and not is_passthrough: score = 0.1
            
            if score > 0:
                cat = 1 if '(' in raw_name and ')' in raw_name else 0
                if not raw_name: cat = 2
                results.append((cat, score, {'id': cid, 'name': raw_name, 'hash': chash}))
                
        # --- 8. 排序與分頁切片 ---
        results.sort(key=lambda x: (x[0], -x[1]))
        
        all_formatted = []
        for dummy_cat, dummy_score, item in results:
            if item['name']: all_formatted.append(f"{item['id']} ({item['name']}) [{item['hash']}]")
            else: all_formatted.append(f"{item['id']} [{item['hash']}]")
            
        return all_formatted # ✨ 修正：直接回傳全量清單，切片交由 Widget 處理

    @staticmethod
    def decrypt_file_bytes(raw_bytes, key=61):
        decrypted = bytearray(raw_bytes)
        for i in range(len(decrypted)): decrypted[i] ^= ((i + key + 0x23D) * key ^ (i % 7)) & 0xFF
        return decrypted

    @staticmethod
    def try_decompress(decrypted_bytes):
        try: return zlib.decompress(decrypted_bytes)
        except Exception: pass
        try: return zlib.decompress(decrypted_bytes[2:], -zlib.MAX_WBITS)
        except Exception: return None

    @staticmethod
    def validate_gate_file(filepath):
        """🛡️ 智慧指紋驗證：驗證該 Bundle 是否確實包含 of_card_asset 註冊表"""
        if not filepath or not os.path.exists(filepath): return False
        if not MDEngine.is_unity_bundle(filepath): return False
        
        env = None        # 👈 新增宣告
        file_data = None  # 👈 新增宣告
        try:
            with open(filepath, "rb") as f:
                file_data = f.read()
            env = UnityPy.load(file_data)
            for obj in env.objects:
                if obj.type.name == "TextAsset":
                    data = obj.read()
                    name = getattr(data, "m_Name", getattr(data, "name", ""))
                    if str(name) == "of_card_asset":
                        return True
        except Exception: 
            pass
        finally:          # 👈 新增強制釋放區塊
            if env: del env
            if file_data: del file_data
        return False

    @staticmethod
    def get_raw_bytes_safe(obj):
        try:
            data = obj.read()
            if hasattr(data, "script") and data.script: return data.script
        except Exception: pass
        try:
            raw = obj.get_raw_data()
            if len(raw) < 8: return None
            name_len = struct.unpack('<I', raw[0:4])[0]
            if name_len > 256: return None
            script_len_offset = 4 + name_len
            if script_len_offset % 4 != 0: script_len_offset += 4 - (script_len_offset % 4)
            if len(raw) < script_len_offset + 4: return None
            return raw[script_len_offset+4 : script_len_offset+4+struct.unpack('<I', raw[script_len_offset : script_len_offset+4])[0]]
        except Exception: return None

    @staticmethod
    def auto_crack_key(raw_bytes, default_key=61):
        if MDEngine.try_decompress(MDEngine.decrypt_file_bytes(raw_bytes, default_key)) is not None: return default_key
        for k in range(1024):
            if k != default_key and MDEngine.try_decompress(MDEngine.decrypt_file_bytes(raw_bytes, k)) is not None: return k
        return None
    
    @staticmethod
    def parse_card_properties(prop_bytes, i, desc=""):
        """
        🛡️ 混血雙軌精準屬性解析器：結合靈擺文本防線與 6-bit 物理遮罩
        （已根據深度研究白皮書，收斂所有特殊召喚與協調變異位元）
        """
        props = {k: "None" for k in PROP_HEADERS}
        try:
            offset = i * 8
            if offset + 8 > len(prop_bytes): return props
            
            raw_chunk = prop_bytes[offset : offset + 8]
            b2, b3, b6 = raw_chunk[2], raw_chunk[3], raw_chunk[6]
            val_1 = (b3 << 8) | b2 
            
            # 1. 魔法與陷阱物理防線 (100% 精準)
            if val_1 == 0x020D:
                props["Type"] = "魔法"
                st_map = {0x00: "通常", 0x04: "反制", 0x08: "場地", 0x0C: "裝備", 0x10: "永續", 0x14: "速攻", 0x18: "儀式"}
                props["SubType"] = st_map.get(b6, "通常")
                return props
                
            elif val_1 == 0x024E:
                props["Type"] = "陷阱"
                st_map = {0x00: "通常", 0x04: "反制", 0x08: "場地", 0x0C: "裝備", 0x10: "永續"}
                props["SubType"] = st_map.get(b6, "通常")
                return props
                
            # 2. 怪獸防線
            props["Type"] = "怪獸"
            
            # 取得剔除干擾蓋章後的純淨 6-bit ID
            b_clean = b2 & 0x3F 
            
            # DRY：集中定義靈擺的物理特徵碼對應表
            pendulum_byte_map = {
                0x19: "通常=靈擺",
                0x1A: "效果=靈擺", 0x21: "效果=靈擺",
                0x22: "超量=靈擺",
                0x24: "同步=靈擺",
                0x29: "融合=靈擺",
                0x34: "儀式=靈擺"
            }
            
            # 第一防線：效果文是否包含靈擺關鍵字 (主指標 - 語義判定)
            is_text_pendulum = any(kw in desc for kw in PENDULUM_KEYWORDS)
            
            # 第二防線：二進位 6-bit 物理遮罩是否命中靈擺特徵 (副指標 - 物理判定)
            is_byte_pendulum = b_clean in pendulum_byte_map
            
            # ✨ 雙軌放行 (邏輯 OR)：只要「有寫靈擺文字」或「物理二進位是靈擺」，任一符合就直接給過
            if is_text_pendulum or is_byte_pendulum:
                # 若物理特徵碼有明確對應(如超量、同步)則精準賦予，否則預設給 "效果=靈擺"
                props["SubType"] = pendulum_byte_map.get(b_clean, "效果=靈擺")
            else:
                # 兩道防線皆未命中，進入純粹的常規怪獸判定
                if b_clean in {0x00, 0x0F}: props["SubType"] = "通常"
                elif b_clean in {0x01, 0x06, 0x08, 0x09, 0x10, 0x18, 0x1B}: props["SubType"] = "效果"
                elif b_clean in {0x02, 0x03}: props["SubType"] = "融合"
                elif b_clean in {0x11, 0x12, 0x13}: props["SubType"] = "同步"
                elif b_clean in {0x16, 0x17}: props["SubType"] = "超量"
                elif b_clean == 0x05: props["SubType"] = "儀式"
                elif b_clean in {0x2A, 0x2B}: props["SubType"] = "連結"
                elif b_clean in {0x0A, 0x0D, 0x31}: props["SubType"] = "衍生物"
                else: props["SubType"] = "效果"
                
        except Exception:
            props["Type"] = "例外"
            props["SubType"] = "例外"
            props["Raw_Data"] = "Exception Parsing"
            
        return props

    @staticmethod
    def apply_premultiplied_alpha(img):
        """✨ 核心新增：Premultiplied Alpha (PMA) 影像轉換器"""
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        try:
            import numpy as np
            # 優先使用 Numpy 進行極速向量化運算
            data = np.array(img, dtype=np.float32)
            alpha = data[..., 3] / 255.0
            data[..., 0] = data[..., 0] * alpha
            data[..., 1] = data[..., 1] * alpha
            data[..., 2] = data[..., 2] * alpha
            return Image.fromarray(data.astype(np.uint8), 'RGBA')
        except ImportError:
            # 降級備用防線：若無 numpy 則使用 PIL 內建混合運算
            from PIL import ImageChops
            r, g, b, a = img.split()
            r = ImageChops.multiply(r, a)
            g = ImageChops.multiply(g, a)
            b = ImageChops.multiply(b, a)
            return Image.merge("RGBA", (r, g, b, a))

    @staticmethod
    def build_spine_atlas_text(png_filename, atlas_size, packed_regions):
        """生成符合 libGDX / Spine 標準格式的 .atlas.txt 文本"""
        atlas_w, atlas_h = atlas_size
        lines = [
            f"\n{png_filename}",
            f"size: {atlas_w},{atlas_h}",
            "format: RGBA8888",
            "filter: Linear,Linear",
            "repeat: none"
        ]
        for region in packed_regions:
            lines.extend([
                f"{region['name']}",
                "  rotate: false",
                f"  xy: {region['x']}, {region['y']}",  # 🛡️ 修正：直接使用左上角原點座標，解除二次反轉
                f"  size: {region['w']}, {region['h']}",
                f"  orig: {region['orig_w']}, {region['orig_h']}",
                f"  offset: {region['offset_x']}, {region['offset_y']}",
                "  index: -1"
            ])
        return "\n".join(lines)

    @staticmethod
    def _generate_spine_cutin_sync(src_path, cutin_id, hd_size, options, mod_dir):
        """Returns error_msg if failed, else None"""
        sd_size = (854, 480) # 🛡️ 完美的 16:9 SD 解析度
        
        # 🛡️ 動態指派專屬快取目錄，防範多程序同時寫入衝突
        hd_options = options.copy()
        hd_options["cache_sub_dir"] = f"frames_cache_{cutin_id}_hd"
        hd_frames, dummy_is_single_hd = MDEngine.extract_and_process_frames(src_path, hd_size, hd_options)
        hd_atlas_img, hd_packed = MDEngine.pack_textures(hd_frames, max_size=8192)
        if hd_atlas_img is None: return hd_packed if isinstance(hd_packed, str) else _("HD 圖集面積超出顯示卡極限 (8192x8192)")
        
        sd_options = options.copy()
        sd_options["cache_sub_dir"] = f"frames_cache_{cutin_id}_sd"
        sd_frames, dummy_is_single_sd = MDEngine.extract_and_process_frames(src_path, sd_size, sd_options)
        sd_atlas_img, sd_packed = MDEngine.pack_textures(sd_frames, max_size=8192)
        if sd_atlas_img is None: return sd_packed if isinstance(sd_packed, str) else _("SD 圖集面積超出顯示卡極限 (8192x8192)")

        # 提取平移數值，準備交給 Spine 骨骼
        off_x = options.get("offset_x", 0)
        off_y = options.get("offset_y", 0)

        # 🛡️ 在匯出硬碟前，實施 PMA 預乘 Alpha 渲染轉換，徹底消滅邊緣雜訊
        hd_atlas_img = MDEngine.apply_premultiplied_alpha(hd_atlas_img)

        # 寫入 HD 檔案
        hd_atlas_img.save(os.path.join(mod_dir, f"{cutin_id}-hd.png"))
        with open(os.path.join(mod_dir, f"{cutin_id}-hd.atlas.txt"), "w", encoding="utf-8") as f:
            f.write(MDEngine.build_spine_atlas_text(f"{cutin_id.upper()}.png", hd_atlas_img.size, hd_packed))
        with open(os.path.join(mod_dir, f"{cutin_id}js-hd.json"), "w", encoding="utf-8") as f:
            f.write(MDEngine.build_spine_42_json_text(cutin_id, hd_packed, options["fps"], options["speed"], options["popup_curve"], dummy_is_single_hd, off_x, off_y, hd_size[0], hd_size[1]))
            
        # 🛡️ SD 檔同步實施 PMA 預乘 Alpha 渲染轉換
        sd_atlas_img = MDEngine.apply_premultiplied_alpha(sd_atlas_img)

        # 寫入 SD 檔案
        sd_atlas_img.save(os.path.join(mod_dir, f"{cutin_id}-sd.png"))
        with open(os.path.join(mod_dir, f"{cutin_id}-sd.atlas.txt"), "w", encoding="utf-8") as f:
            f.write(MDEngine.build_spine_atlas_text(f"{cutin_id.upper()}.png", sd_atlas_img.size, sd_packed))
        with open(os.path.join(mod_dir, f"{cutin_id}js-sd.json"), "w", encoding="utf-8") as f:
            f.write(MDEngine.build_spine_42_json_text(cutin_id, sd_packed, options["fps"], options["speed"], options["popup_curve"], dummy_is_single_sd, off_x, off_y, hd_size[0], hd_size[1]))
            
        return None

    @staticmethod
    def _worker_cutin_single(task_info):
        target, src_dir, mod_dir, bk_dir, enable_backup, hd_size, options = task_info
        try:
            cid_match = re.match(r'^(p\d+)', target, re.IGNORECASE)
            cutin_id = cid_match.group(1).lower() if cid_match else os.path.splitext(target)[0]
            
            source_to_read = None
            if enable_backup:
                bk_possible_path = MDEngine.resolve_cutin_material_path(bk_dir, cutin_id)
                if os.path.exists(bk_possible_path):
                    source_to_read = bk_possible_path
                    
            if not source_to_read:
                src_path = MDEngine.resolve_cutin_material_path(src_dir, target)
                if not os.path.exists(src_path):
                    return target, False, _("找不到對應素材")
                if enable_backup:
                    target_basename = os.path.basename(src_path)
                    bk_target_path = os.path.join(bk_dir, target_basename)
                    try:
                        shutil.move(src_path, bk_target_path)
                        source_to_read = bk_target_path
                    except Exception:
                        source_to_read = src_path
                else:
                    source_to_read = src_path
                    
            if not source_to_read or not os.path.exists(source_to_read):
                return target, False, _("無法定位有效素材，請檢查原檔或備份檔")
                
            err = MDEngine._generate_spine_cutin_sync(source_to_read, cutin_id, hd_size, options, mod_dir)
            
            # 🛡️ 任務完成，清理專屬暫存並強制 GC
            try:
                hd_cache = os.path.join(MDEngine.TEMP_DIR, f"frames_cache_{cutin_id}_hd")
                sd_cache = os.path.join(MDEngine.TEMP_DIR, f"frames_cache_{cutin_id}_sd")
                if os.path.exists(hd_cache): shutil.rmtree(hd_cache, ignore_errors=True)
                if os.path.exists(sd_cache): shutil.rmtree(sd_cache, ignore_errors=True)
            except Exception: pass
            
            import gc
            gc.collect()
            
            if err: return target, False, err
            return target, True, None
        except Exception as e:
            # 🛡️ 盲點 B 修正：動畫生成包含 OpenCV 與 Spine 等複雜底層，加入 traceback 確保除錯線索不遺失
            import traceback
            return target, False, f"{str(e)}\n{traceback.format_exc()}"

    @staticmethod
    def task_post_process_cutin_batch(src_dir, root_dir, mod_folder, bk_folder, enable_backup, targets, hd_size, options, progress_cb, finish_cb):
        try:
            mod_dir = MDEngine.resolve_path(root_dir, mod_folder)
            bk_dir = MDEngine.resolve_path(mod_dir, bk_folder)
            os.makedirs(mod_dir, exist_ok=True)
            if enable_backup: os.makedirs(bk_dir, exist_ok=True)
            
            tasks = [(target, src_dir, mod_dir, bk_dir, enable_backup, hd_size, options.copy()) for target in targets]
            
            success = 0
            errors = []
            count = 0
            
            # 🛡️ 智慧節流閥：尊重使用者設定，但強制將算力鎖死在上限 3，徹底消滅 16 核心 OOM 的危機
            user_threads = options.get("max_threads", "Auto")
            safe_workers = max(1, min(MDEngine.get_heavy_task_workers(user_threads), 3))
            
            with concurrent.futures.ProcessPoolExecutor(max_workers=safe_workers, initializer=_init_worker, initargs=(UI_LANG_DICT,)) as executor:
                futures = [executor.submit(MDEngine._worker_cutin_single, t) for t in tasks]
                for future in concurrent.futures.as_completed(futures):
                    count += 1
                    if progress_cb: progress_cb(count)
                    try:
                        tgt, is_ok, err_msg = future.result()
                        if is_ok: success += 1
                        else: errors.append(f"{tgt}: {err_msg}")
                    except Exception as e:
                        errors.append(_("系統例外錯誤：{error}").format(error=str(e)))
            
            MDEngine.clean_temp_dir()
            finish_cb(True, success, errors)
        except Exception as e:
            finish_cb(False, str(e), traceback.format_exc())

    @staticmethod
    def build_spine_42_json_text(cutin_id, packed_regions, fps, speed_mult, popup_curve, is_single_image, offset_x=0, offset_y=0, canvas_w=1920, canvas_h=1080):
        """構建符合 Master Duel 原廠 Spine 4.2.43 規格的 JSON 數據 (鎖定 4800x2700 標準世界尺寸)"""
        WORLD_W = 4800.0
        WORLD_H = 2700.0
        
        # 🛡️ 動態世界坐標換算：將像素平移轉換為世界比例平移 (完美同步 SD 與 HD)
        world_off_x = (offset_x / float(canvas_w)) * WORLD_W
        # Spine Y 軸朝上，PIL Y 軸朝下，因此 Y 必須反轉
        world_off_y = -(offset_y / float(canvas_h)) * WORLD_H
        
        sorted_curve = sorted(popup_curve, key=lambda item: item['time'])
        
        # 🛡️ 時間軸防重疊：確保每個 Spine 關鍵幀時間戳絕對單調遞增，防止 Unity 崩潰
        for dummy_idx in range(1, len(sorted_curve)):
            if sorted_curve[dummy_idx]['time'] <= sorted_curve[dummy_idx-1]['time']:
                sorted_curve[dummy_idx]['time'] = sorted_curve[dummy_idx-1]['time'] + 0.0001
                
        attachments_dict = {}
        attachment_timeline = []
        frame_duration = 1.0 / (fps * speed_mult) if (fps * speed_mult) > 0 else 0.0333
        
        for dummy_idx, region in enumerate(packed_regions):
            frame_name = region['name']
            attachments_dict[frame_name] = {"width": WORLD_W, "height": WORLD_H}
            
            if is_single_image:
                if dummy_idx == 0:
                    attachment_timeline.append({"time": 0.0, "name": frame_name})
            else:
                time_stamp = round(dummy_idx * frame_duration, 4) if dummy_idx > 0 else 0.0
                attachment_timeline.append({"time": time_stamp, "name": frame_name})

        spine_data = {
            "skeleton": {
                "hash": "MD_AstellarTool_Generated", 
                "spine": "4.2.43",
                # 🛡️ Y 軸視口下沉修正：從 -1350 下壓至 -1470，完美躲避頂部 UI 裁切邊界
                "x": -WORLD_W / 2.0, "y": -1470.0,
                "width": WORLD_W, "height": WORLD_H,
                "images": "/images/", "audio": ""
            },
            # 🛡️ 無損平移：直接透過骨骼位移，絕對不會導致圖片被畫布切斷
            "bones": [ { "name": "root", "x": world_off_x, "y": world_off_y } ],
            "slots": [ { "name": cutin_id, "bone": "root", "attachment": packed_regions[0]['name'] if packed_regions else "" } ],
            "skins": [ { "name": "default", "attachments": { cutin_id: attachments_dict } } ],
            "animations": { 
                "animation": { 
                    "bones": { "root": { "scale": sorted_curve } },
                    "slots": { cutin_id: { "attachment": attachment_timeline } } 
                } 
            }
        }
        return json.dumps(spine_data, indent=2, ensure_ascii=False)

    @staticmethod
    def clear_psd_cache():
        """清除常駐於 RAM 的 PSD 解析快取，防止 OOM"""
        MDEngine._psd_cache.clear()
        
    @staticmethod
    def clean_temp_dir():
        """定期清道夫：支援動態清理多程序產生的專屬快取資料夾"""
        try:
            if not os.path.exists(MDEngine.TEMP_DIR): return
            for item in os.listdir(MDEngine.TEMP_DIR):
                # 🛡️ 支援動態後綴的快取資料夾清理
                if item.startswith("frames_cache") or item.startswith("psd_cache"):
                    cache_path = os.path.join(MDEngine.TEMP_DIR, item)
                    shutil.rmtree(cache_path, ignore_errors=True)
        except Exception: pass

    @staticmethod
    def pack_textures(images_dict, max_size=8192):
        """Alpha 透明邊緣裁切與 Shelf Packing 圖集打包演算法 (支援 RAM / Disk-Cache 雙軌)"""
        metadata = []
        padding_val = 2 # 🛡️ 新增防溢色間距，防止 Spine 動態縮放時出現黑邊

        for name, img_or_path in images_dict.items():
            is_path = isinstance(img_or_path, str)
            img = Image.open(img_or_path) if is_path else img_or_path
            
            bbox = img.getbbox()
            if bbox:
                crop_w = bbox[2] - bbox[0]
                crop_h = bbox[3] - bbox[1]
                offset_x = bbox[0]
                # 🛡️ 修正 offset_y，嚴格對齊 Spine 左下角原點的裁切位移
                offset_y = img.height - bbox[3]
            else:
                crop_w, crop_h, offset_x, offset_y = 1, 1, 0, 0
                
            # 🛡️ 新增：防範單張超大圖片導致排版崩潰 (回傳 None, None 維持與原生型態絕對一致)
            if crop_w > max_size or crop_h > max_size:
                if is_path: img.close()
                return None, None
                
            metadata.append({
                "name": name, "source": img_or_path, "bbox": bbox,
                "w": crop_w, "h": crop_h, "orig_w": img.width, "orig_h": img.height,
                "offset_x": offset_x, "offset_y": offset_y, "is_path": is_path
            })
            if is_path: img.close() # 🛡️ 只在硬碟模式下立即關閉物件

        metadata.sort(key=lambda item: item['h'], reverse=True)
        packed_regions = []
        current_x, current_y, max_h_in_row, atlas_w = 0, 0, 0, 0
        
        for item in metadata:
            # 🛡️ 越界與換行檢查：若當前行放不下，則進行換行，並累加當前最高度與防溢色間距
            if current_x + item['w'] > max_size:
                current_x = 0
                current_y += max_h_in_row + padding_val
                max_h_in_row = 0
                
            # 🛡️ 極限邊界檢查：若 Y 軸加上當前圖片高度後超出顯卡極限，立即提早攔截 (Early Exit)
            if current_y + item['h'] > max_size:
                return None, _("圖集排版後面積超出顯示卡極限 ({max_size}x{max_size})，請降低輸入數量或縮小素材！").format(max_size=max_size)
            
            item['x'] = current_x
            item['y'] = current_y
            packed_regions.append(item)
            
            atlas_w = max(atlas_w, current_x + item['w'])
            max_h_in_row = max(max_h_in_row, item['h'])
            
            # 推進 X 座標時加入間距
            current_x += item['w'] + padding_val
            
        raw_atlas_h = current_y + max_h_in_row
        
        # 向上湊齊至 2 的指數倍 (Power-of-Two, POT)，大幅提升 GPU 紋理壓縮與 Unity 載入效能
        def to_pot(val):
            return 1 if val <= 0 else 1 << (val - 1).bit_length()
            
        pot_w = min(max_size, to_pot(atlas_w))
        pot_h = min(max_size, to_pot(raw_atlas_h))
        
        # 🛡️ 修正：完全移除 spine_y 二次反轉的邏輯，保持最原始的左上角原點座標
        
        atlas_img = Image.new("RGBA", (pot_w, pot_h), (0, 0, 0, 0))
        
        for item in packed_regions:
            img = Image.open(item['source']) if item['is_path'] else item['source']
            crop_img = img.crop(item['bbox']) if item['bbox'] else Image.new("RGBA", (1, 1), (0,0,0,0))
            atlas_img.paste(crop_img, (item['x'], item['y']))
            
            if item['is_path']: img.close() # 🛡️ 僅關閉硬碟打開的資源

            del item['source']
            del item['bbox']
            del item['is_path']
            
        packed_regions.sort(key=lambda item: item['name'])
        return atlas_img, packed_regions

    @staticmethod
    def get_interpolated_scale(popup_curve, time_sec):
        """POP UP 曲線時間軸精準補間器：根據當前秒數，動態計算 Spine 曲線縮放率"""
        sorted_curve = sorted(popup_curve, key=lambda item: item['time'])
        if not sorted_curve: return 1.0
        if time_sec <= sorted_curve[0]['time']: return sorted_curve[0]['x']
        if time_sec >= sorted_curve[-1]['time']: return sorted_curve[-1]['x']
        
        for dummy_idx in range(len(sorted_curve) - 1):
            p1, p2 = sorted_curve[dummy_idx], sorted_curve[dummy_idx+1]
            if p1['time'] <= time_sec <= p2['time']:
                ratio = (time_sec - p1['time']) / (p2['time'] - p1['time']) if p2['time'] != p1['time'] else 0
                return p1['x'] + (p2['x'] - p1['x']) * ratio
        return 1.0

    @staticmethod
    def resolve_cutin_material_path(src_dir, target):
        """🛡️ 模糊路徑解析器：自動將純編號 p18532 補全為 p18532.mp4 或 p18532_龍.psd (並排除已生成的產物)"""
        exact_path = os.path.join(src_dir, target)
        target_lower = target.lower()
        
        # 若傳入的路徑確實存在，且不是已產出的後綴檔案，直接回傳
        if os.path.exists(exact_path) and not any(suffix in target_lower for suffix in ['-hd', '-sd', 'js-']): 
            return exact_path
        
        try:
            for item in os.listdir(src_dir):
                item_lower = item.lower()
                # 🛡️ 自動過濾掉已經生成出來的產物與描述檔，防止循環讀取
                if any(suffix in item_lower for suffix in ['-hd', '-sd', 'js-', '.atlas', '.json']):
                    continue
                    
                stem = os.path.splitext(item)[0].lower()
                if stem == target_lower or stem.startswith(f"{target_lower}_"):
                    return os.path.join(src_dir, item)
        except Exception: pass
        return exact_path

    @staticmethod
    def resolve_overframe_material_path(mod_dir, bk_dir, target_id):
        """✨ 智慧雙軌路徑解析器：統一處理超框/單圖素材與備份區尋找"""
        if not target_id: return "", "", False
        target_id = re.sub(r'-(ch|bg)$', '', os.path.splitext(target_id)[0], flags=re.IGNORECASE)
        
        search_dirs = []
        if bk_dir and os.path.exists(bk_dir): search_dirs.append(bk_dir)
        if mod_dir and os.path.exists(mod_dir): search_dirs.append(mod_dir)
        
        ch_path, bg_path, norm_path = "", "", ""
        
        for d in search_dirs:
            if not os.path.exists(d): continue
            for ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp"]:
                cand_ch = os.path.join(d, f"{target_id}-ch{ext}")
                cand_bg = os.path.join(d, f"{target_id}-bg{ext}")
                cand_norm = os.path.join(d, f"{target_id}{ext}")
                
                if not ch_path and os.path.exists(cand_ch): ch_path = cand_ch
                if not bg_path and os.path.exists(cand_bg): bg_path = cand_bg
                if not norm_path and os.path.exists(cand_norm): norm_path = cand_norm
        
        if ch_path:
            return ch_path, bg_path, True
        return norm_path, "", False

    @staticmethod
    def extract_and_process_frames(src_path, canvas_size, options, single_frame_only=False, preview_time_sec=0.0):
        """通用素材解析與完整影像處理流水線 (支援原生 FPS 精準時間軸抽幀與 PSD 白名單)"""
        if not os.path.exists(src_path): raise Exception(_("找不到素材來源路徑：{path}").format(path=src_path))
            
        def get_sequence(name):
            if not name: return None
            name_clean = str(name).strip()
            # ✨ DRY：優先剔除前綴的 p18533_ 或 p18533，徹底解開正規表示式的束縛
            name_no_prefix = re.sub(r'^p\d+_?', '', name_clean, flags=re.IGNORECASE)
            
            # ✨ 智慧萃取：精準抓取字串中剩餘的「第一組數字」作為序列號
            # 完美支援 "1_龍特效", "01_火焰", "Layer 1", "圖層 1" 等命名
            match = re.search(r'\d+', name_no_prefix)
            if match:
                return int(match.group(0))
            return None
            
        def natural_sort_key(s):
            import re
            return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s[1] if isinstance(s, tuple) else s)]

        ext = os.path.splitext(src_path)[1].lower() if not os.path.isdir(src_path) else ''
        
        out_fps = options.get("fps", 30) * options.get("speed", 1.0)
        if out_fps <= 0: out_fps = 30.0
        
        def frame_generator():
            if os.path.isdir(src_path):
                files = []
                for f in os.listdir(src_path):
                    if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                        seq = get_sequence(f)
                        files.append((seq, f))
                
                valid_seqs = [x for x in files if x[0] is not None]
                if valid_seqs: files.sort(key=lambda x: (x[0] if x[0] is not None else 999999, x[1]))
                else: files.sort(key=natural_sort_key)
                    
                if single_frame_only:
                    seq_target_idx = int(preview_time_sec * out_fps)
                    target = min(seq_target_idx, len(files) - 1) if files else 0
                    if files:
                        with Image.open(os.path.join(src_path, files[target][1])) as img: yield 0, img.convert("RGBA")
                else:
                    for dummy_idx, (seq, f) in enumerate(files):
                        with Image.open(os.path.join(src_path, f)) as img: yield dummy_idx, img.convert("RGBA")
                    
            elif ext == '.psd':
                try: from psd_tools import PSDImage
                except ImportError: raise Exception(_("缺少 psd-tools 模組！請在終端機輸入 pip install psd-tools"))
                
                psd_mtime = os.path.getmtime(src_path)
                psd_cache_base = os.path.join(MDEngine.TEMP_DIR, "psd_cache")
                psd_cache_dir = os.path.join(psd_cache_base, f"{os.path.basename(src_path)}_{psd_mtime}")
                layers_data = []
                
                # 🛡️ 智慧防線：偵測並破解「空資料夾陷阱」
                psd_needs_parse = True
                if os.path.exists(psd_cache_dir):
                    cached_files = os.listdir(psd_cache_dir)
                    if not cached_files:
                        # 發現上次崩潰殘留的空資料夾，強制刪除並解除封印
                        shutil.rmtree(psd_cache_dir, ignore_errors=True)
                    else:
                        psd_needs_parse = False
                        for f in cached_files:
                            seq = get_sequence(f)
                            if seq is not None: layers_data.append((seq, os.path.join(psd_cache_dir, f)))
                            
                if psd_needs_parse:
                    if os.path.exists(psd_cache_base) and not os.path.exists(psd_cache_dir):
                        shutil.rmtree(psd_cache_base, ignore_errors=True)
                    os.makedirs(psd_cache_dir, exist_ok=True)
                    
                    psd = PSDImage.open(src_path)
                    psd_size = getattr(psd, 'size', (1920, 1080))
                    
                    # 🛡️ 向下相容的遞迴顯示判定 (免疫舊版 psd-tools 的 API 變動)
                    def is_visible_safe(node):
                        try:
                            if getattr(node, 'visible', getattr(node, 'is_visible', lambda: True)()) == False: return False
                            p = node.parent
                            while p and getattr(p, 'parent', None) is not None:
                                if getattr(p, 'visible', getattr(p, 'is_visible', lambda: True)()) == False: return False
                                p = p.parent
                            return True
                        except: return True
                        
                    for psd_layer in psd.descendants():
                        try:
                            # 安全判定是否為群組
                            is_group = psd_layer.is_group() if callable(getattr(psd_layer, 'is_group', None)) else getattr(psd_layer, 'is_group', False)
                            
                            if not is_group and is_visible_safe(psd_layer):
                                layer_name = str(getattr(psd_layer, 'name', ''))
                                seq = get_sequence(layer_name)
                                
                                if seq is not None:
                                    layer_img = None
                                    
                                    # 🛡️ 第一防線：常規局部提取 (最快，但智慧型圖層會崩潰)
                                    try: 
                                        slice_img = psd_layer.composite()
                                        if slice_img:
                                            slice_img = slice_img.convert("RGBA")
                                            # 安全取得偏移座標
                                            offset = getattr(psd_layer, 'offset', (0, 0))
                                            if not isinstance(offset, tuple) or len(offset) < 2: offset = (0, 0)
                                            else: offset = (int(offset[0]), int(offset[1]))
                                            
                                            # ✨ DRY：貼回全透明畫布，保留精準位置
                                            full_canvas = Image.new("RGBA", psd_size, (0, 0, 0, 0))
                                            full_canvas.paste(slice_img, offset, slice_img)
                                            layer_img = full_canvas
                                    except Exception: 
                                        pass
                                    
                                    # 🛡️ 第二防線：燈光隔離渲染法 (智慧型圖層與特殊效果圖層的 100% 終極解法)
                                    if layer_img is None:
                                        try:
                                            # 1. 備份並暫時關閉所有圖層的燈光 (可見度)
                                            vis_backup = {}
                                            for node in psd.descendants():
                                                vis_backup[node] = getattr(node, 'visible', True)
                                                node.visible = False
                                            
                                            # 2. 點亮當前圖層與其所有父群組，打通視覺通道
                                            curr = psd_layer
                                            while curr:
                                                curr.visible = True
                                                curr = curr.parent
                                                
                                            # 3. 呼叫官方全局渲染 (回傳的直接就是精準尺寸的全畫布，自帶效果與變形)
                                            fallback_img = psd.composite()
                                            if fallback_img:
                                                layer_img = fallback_img.convert("RGBA")
                                        except Exception:
                                            pass
                                        finally:
                                            # 4. 無論成功與否，絕對還原所有圖層燈光狀態，不干擾後續影格
                                            for node, v in vis_backup.items():
                                                node.visible = v
                                        
                                    if layer_img:
                                        layer_path = os.path.join(psd_cache_dir, f"layer_{seq:04d}.png")
                                        layer_img.save(layer_path)
                                        layers_data.append((seq, layer_path))
                        except Exception:
                            pass
                            
                    # 🛡️ 致命防呆：如果整個 PSD 跑完一張圖都沒存下來，立刻刪除空資料夾，防止未來再次陷入空快取陷阱
                    if not layers_data:
                        shutil.rmtree(psd_cache_dir, ignore_errors=True)
                        
                layers_data.sort(key=lambda x: x[0])
                
                if single_frame_only:
                    seq_target_idx = int(preview_time_sec * out_fps)
                    target = min(seq_target_idx, len(layers_data) - 1) if layers_data else 0
                    if layers_data:
                        with Image.open(layers_data[target][1]) as img: yield 0, img.convert("RGBA")
                else:
                    for dummy_idx, (seq, layer_path) in enumerate(layers_data):
                        with Image.open(layer_path) as img: yield dummy_idx, img.convert("RGBA")
                    
            elif ext in ['.mp4', '.avi', '.mov']:
                try: import cv2
                except ImportError: raise Exception(_("缺少 opencv-python 模組！無法讀取影片。請輸入 pip install opencv-python"))
                cap = cv2.VideoCapture(src_path)
                try:
                    fps_vid = cap.get(cv2.CAP_PROP_FPS) or 30.0
                    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    start_frame = int(options.get("start_time", 0.0) * fps_vid)
                    
                    base_fps = options.get("fps", 30)
                    speed_mult = options.get("speed", 1.0)
                    
                    if single_frame_only:
                        target_frame = start_frame + int(preview_time_sec * speed_mult * fps_vid)
                        target_frame = min(target_frame, max(0, total_frames - 1))
                        cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
                        ret, frame = cap.read()
                        if ret: yield 0, Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA))
                    else:
                        max_out_frames = int(options.get("duration", 3.0) * out_fps)
                        count = 0
                        current_vid_frame = start_frame
                        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
                        
                        while cap.isOpened() and count < max_out_frames:
                            target_vid_frame = start_frame + int(count * (fps_vid / base_fps))
                            if target_vid_frame >= total_frames: break
                            
                            if current_vid_frame != target_vid_frame:
                                cap.set(cv2.CAP_PROP_POS_FRAMES, target_vid_frame)
                                current_vid_frame = target_vid_frame
                                
                            ret, frame = cap.read()
                            if not ret: break
                            current_vid_frame += 1
                            
                            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
                            yield count, Image.fromarray(frame)
                            count += 1
                finally:
                    cap.release() # 🛡️ 無論迴圈是否提早 yield break，必定釋放影片鎖定
                
            elif ext == '.gif':
                with Image.open(src_path) as gif:
                    if single_frame_only:
                        seq_target_idx = int(preview_time_sec * out_fps)
                        target = min(seq_target_idx, gif.n_frames - 1)
                        gif.seek(target)
                        yield 0, gif.convert("RGBA")
                    else:
                        for dummy_frame in range(gif.n_frames):
                            gif.seek(dummy_frame)
                            yield dummy_frame, gif.convert("RGBA")
                        
            elif ext in ['.png', '.jpg', '.jpeg', '.bmp']:
                with Image.open(src_path) as img: yield 0, img.convert("RGBA")
        
        processed_frames = {}
        canvas_w, canvas_h = canvas_size
        bg_hex = options.get("chroma_color", "#00FF00")
        tr, tg, tb = int(bg_hex[1:3], 16), int(bg_hex[3:5], 16), int(bg_hex[5:7], 16)
        tol = options.get("chroma_tol", 15) * 2.55
        despill_str = options.get("chroma_despill", 50) / 100.0
        
        from PIL import ImageEnhance, ImageFilter, ImageDraw, ImageChops
        try: import numpy as np; has_np = True
        except ImportError: has_np = False
        
        is_single = True; count_frames = 0
        use_disk_cache = options.get("use_disk_cache", False) and not single_frame_only
        cache_sub_dir = options.get("cache_sub_dir", "frames_cache")
        frames_cache_dir = os.path.join(MDEngine.TEMP_DIR, cache_sub_dir)
        
        if use_disk_cache:
            if os.path.exists(frames_cache_dir): shutil.rmtree(frames_cache_dir, ignore_errors=True)
            os.makedirs(frames_cache_dir, exist_ok=True)
        
        for dummy_i, frame in frame_generator():
            count_frames += 1
            if count_frames > 1: is_single = False

            # --- 🛡️ 階段 1：邊緣淨化與色彩去背 (必須在 Resize 前執行，斬斷殘留雜訊與色彩復闢) ---
            if has_np and (options.get("enable_chroma", False) or options.get("enable_despill", False)):
                data = np.array(frame)
                r, g, b = data[:,:,0].astype(float), data[:,:,1].astype(float), data[:,:,2].astype(float)
                original_alpha = data[:,:,3]
                
                if options.get("enable_despill", False) and despill_str > 0:
                    valid_mask = (original_alpha > 0)
                    if tg > tr and tg > tb:
                        is_dom = (g > r) & (g > b) & valid_mask
                        target = np.minimum(g, np.maximum(r, b))
                        g = np.where(is_dom, g - (g - target) * despill_str, g)
                    elif tb > tr and tb > tg:
                        is_dom = (b > r) & (b > g) & valid_mask
                        target = np.minimum(b, np.maximum(r, g))
                        b = np.where(is_dom, b - (b - target) * despill_str, b)
                    elif tr > tg and tr > tb:
                        is_dom = (r > g) & (r > b) & valid_mask
                        target = np.minimum(r, np.maximum(g, b))
                        r = np.where(is_dom, r - (r - target) * despill_str, r)
                    
                    data[:,:,0], data[:,:,1], data[:,:,2] = r.astype(np.uint8), g.astype(np.uint8), b.astype(np.uint8)
                    frame = Image.fromarray(data, "RGBA")
                    
                if options.get("enable_chroma", False):
                    dist = np.sqrt((r - tr)**2 + (g - tg)**2 + (b - tb)**2)
                    chroma_mask = (dist > tol).astype(np.uint8) * 255
                    mask_img = Image.fromarray(chroma_mask, mode="L")
                    
                    if options.get("chroma_feather", 0) > 0: 
                        mask_img = mask_img.filter(ImageFilter.GaussianBlur(radius=options.get("chroma_feather", 0) / 5.0))
                        
                    final_mask_np = np.minimum(original_alpha, np.array(mask_img))
                    final_alpha = Image.fromarray(final_mask_np, mode="L")
                    frame.putalpha(final_alpha)

            # 🛡️ 強制斬斷 Alpha=0 背後的隱藏 RGB (防雜訊與黑邊)
            r_ch, g_ch, b_ch, a_ch = frame.split()
            wipe_mask = a_ch.point(lambda p: 255 if p > 0 else 0)
            frame = Image.merge("RGBA", (
                ImageChops.multiply(r_ch, wipe_mask),
                ImageChops.multiply(g_ch, wipe_mask),
                ImageChops.multiply(b_ch, wipe_mask),
                a_ch
            ))

            # --- 🛡️ 階段 2：色彩調校 ---
            if options.get("bright", 0) != 0:
                frame = ImageEnhance.Brightness(frame).enhance(1.0 + options.get("bright", 0) / 100.0)
            if options.get("contrast", 0) != 0:
                frame = ImageEnhance.Contrast(frame).enhance(1.0 + options.get("contrast", 0) / 100.0)

            # --- 🛡️ 階段 3：幾何重採樣 (Resize/Crop/Rotate) ---
            fill_mode = options.get("fill_mode", "Crop")
            if "Crop" in fill_mode:
                ratio = max(canvas_w / frame.width, canvas_h / frame.height)
                new_w, new_h = int(frame.width * ratio), int(frame.height * ratio)
                frame = frame.resize((new_w, new_h), Image.Resampling.LANCZOS)
                left, top = (new_w - canvas_w) // 2, (new_h - canvas_h) // 2
                frame = frame.crop((left, top, left + canvas_w, top + canvas_h))
            elif "Stretch" in fill_mode:
                frame = frame.resize((canvas_w, canvas_h), Image.Resampling.LANCZOS)
            else:
                ratio = min(canvas_w / frame.width, canvas_h / frame.height)
                new_w, new_h = int(frame.width * ratio), int(frame.height * ratio)
                frame = frame.resize((new_w, new_h), Image.Resampling.LANCZOS)
                new_img = Image.new("RGBA", (canvas_w, canvas_h), (0,0,0,0))
                new_img.paste(frame, ((canvas_w - new_w) // 2, (canvas_h - new_h) // 2))
                frame = new_img
                
            if options.get("rot", 0) != 0: 
                frame = frame.rotate(-options.get("rot", 0), resample=Image.Resampling.BICUBIC, expand=False)
                
            # 🛡️ 註：已徹底移除硬切的像素平移代碼 (改交由 Spine JSON 骨骼做無損位移)

            # --- 🛡️ 階段 4：Vignette 暗角 ---
            if options.get("vignette", 0) > 0:
                vig_mask = Image.new("L", (canvas_w, canvas_h), int(255 - options.get("vignette", 0)*2.55))
                draw = ImageDraw.Draw(vig_mask)
                draw.ellipse((0, 0, canvas_w, canvas_h), fill=255)
                vig_mask = vig_mask.filter(ImageFilter.GaussianBlur(radius=min(canvas_w, canvas_h)//4))
                frame_a = frame.split()[3]
                final_a = ImageChops.multiply(frame_a, vig_mask)
                frame.putalpha(final_a)
                
            if use_disk_cache:
                cache_path = os.path.join(frames_cache_dir, f"frame_{dummy_i+1:03d}.png")
                frame.save(cache_path, format="PNG")
                processed_frames[f"Frame_{dummy_i+1:03d}"] = cache_path
                frame.close()
            else:
                processed_frames[f"Frame_{dummy_i+1:03d}"] = frame
                
            if single_frame_only: break
                
        return processed_frames, is_single

    @staticmethod
    def task_generate_cutin_single_frame_preview(src_path, hd_size, options, preview_time_sec, progress_cb, finish_cb):
        """UI 即時預覽專用：純記憶體光速抽幀並真實反映 POP UP 動態縮放與平移補償"""
        try:
            options["use_disk_cache"] = False # 🛡️ 強制關閉硬碟快取
            frames_dict, dummy_single = MDEngine.extract_and_process_frames(src_path, hd_size, options, single_frame_only=True, preview_time_sec=preview_time_sec)
            if not frames_dict: return finish_cb(False, _("無法解析素材，或路徑無效。"), None)
            
            frame = list(frames_dict.values())[0]
            popup_curve = options.get("popup_curve", [])
            base_scale = MDEngine.get_interpolated_scale(popup_curve, preview_time_sec)
            
            w, h = frame.size
            new_w, new_h = max(1, int(w * base_scale)), max(1, int(h * base_scale))
            scaled_frame = frame.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            final_img = Image.new("RGBA", (w, h), (0,0,0,0))
            
            # 🛡️ 動態視覺平移：由於真實像素平移已移除，預覽時在此手動補償以確保所見即所得
            off_x = options.get("offset_x", 0)
            off_y = options.get("offset_y", 0)
            paste_x = ((w - new_w) // 2) + off_x
            paste_y = ((h - new_h) // 2) + off_y
            
            final_img.paste(scaled_frame, (paste_x, paste_y))
            
            data = final_img.tobytes("raw", "RGBA")
            qimg = QImage(data, final_img.width, final_img.height, final_img.width * 4, QImage.Format_RGBA8888).copy()
            
            # 🛡️ 徹底銷毀中介物件，防止記憶體洩漏
            frame.close()
            scaled_frame.close()
            final_img.close()
            
            finish_cb(True, qimg, None)
        except Exception as e:
            finish_cb(False, str(e), traceback.format_exc())

    @staticmethod
    def task_generate_cutin_preview(src_path, hd_size, options, progress_cb, finish_cb):
        """生成 GIF 預覽專用：純記憶體運算並自動釋放，支援單圖與影片序列之動態平移補償"""
        try:
            preview_path = os.path.join(MDEngine.TEMP_DIR, "cutin_preview.gif")
            os.makedirs(MDEngine.TEMP_DIR, exist_ok=True)
            if os.path.exists(preview_path):
                try: os.rename(preview_path, preview_path)
                except OSError: return finish_cb(False, _("⚠️ 檔案鎖定：請先關閉目前正在播放的預覽視窗，再重新生成！"), None)
                    
            options["use_disk_cache"] = False
            frames_dict, is_single = MDEngine.extract_and_process_frames(src_path, hd_size, options)
            if not frames_dict: return finish_cb(False, _("無法解析素材，或路徑/白名單無效。"), None)
                
            frames_list = list(frames_dict.values())
            canvas_w, canvas_h = hd_size
            
            popup_curve = options.get("popup_curve", [])
            base_fps = options.get("fps", 30)
            speed_mult = options.get("speed", 1.0)
            effective_fps = base_fps * speed_mult
            if effective_fps <= 0: effective_fps = 30.0
            frame_interval_sec = 1.0 / effective_fps
            duration_ms = int(frame_interval_sec * 1000)
            
            off_x = options.get("offset_x", 0)
            off_y = options.get("offset_y", 0)
            
            gif_frames = []
            
            if is_single and len(frames_list) == 1:
                base_frame = frames_list[0]
                duration_sec = options.get("duration", 3.0)
                total_preview_frames = max(1, int(duration_sec * effective_fps))
                
                for i in range(total_preview_frames):
                    curr_t = i * frame_interval_sec
                    scale = MDEngine.get_interpolated_scale(popup_curve, curr_t)
                    
                    new_w, new_h = max(1, int(canvas_w * scale)), max(1, int(canvas_h * scale))
                    scaled_img = base_frame.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    
                    canvas_img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
                    paste_x = ((canvas_w - new_w) // 2) + off_x
                    paste_y = ((canvas_h - new_h) // 2) + off_y
                    canvas_img.paste(scaled_img, (paste_x, paste_y), scaled_img)
                    gif_frames.append(canvas_img)
                base_frame.close()
            else:
                for idx, frame in enumerate(frames_list):
                    curr_t = idx * frame_interval_sec
                    scale = MDEngine.get_interpolated_scale(popup_curve, curr_t)
                    
                    new_w, new_h = max(1, int(canvas_w * scale)), max(1, int(canvas_h * scale))
                    scaled_img = frame.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    
                    canvas_img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
                    paste_x = ((canvas_w - new_w) // 2) + off_x
                    paste_y = ((canvas_h - new_h) // 2) + off_y
                    canvas_img.paste(scaled_img, (paste_x, paste_y), scaled_img)
                    gif_frames.append(canvas_img)
            
            sim_boxes = []
            for img in gif_frames:
                bbox = img.getbbox()
                if bbox:
                    sim_boxes.append((bbox[2] - bbox[0], bbox[3] - bbox[1]))
                else:
                    sim_boxes.append((1, 1))
            
            # 🛡️ 與 pack_textures 完全同步：依據高度降冪排序，計算 Padding
            sim_boxes.sort(key=lambda box: box[1], reverse=True)
            
            sim_x, sim_y, max_h_in_row = 0, 0, 0
            is_over_limit = False
            padding_val = 2 # 🛡️ 加入防溢色間距

            for crop_w, crop_h in sim_boxes:
                if sim_x + crop_w > 8192:
                    sim_x = 0
                    sim_y += max_h_in_row + padding_val
                    max_h_in_row = 0
                
                if sim_y + crop_h > 8192:
                    is_over_limit = True
                    break
                    
                sim_x += crop_w + padding_val
                max_h_in_row = max(max_h_in_row, crop_h)
                
            warn_msg = _("⚠️ 警告：預估圖集排列後已超出顯示卡上限 (8192x8192)！正式輸出時將會被攔截。") if is_over_limit else ""
            
            final_gif_frames = []
            key_color = (26, 0, 51)
            
            for img in gif_frames:
                alpha = img.getchannel('A')
                mask = Image.eval(alpha, lambda a: 255 if a <= 128 else 0)
                
                bg = Image.new("RGB", img.size, key_color)
                bg.paste(img, (0, 0), img)
                
                img_p = bg.quantize(colors=255)
                img_p.paste(255, mask)
                final_gif_frames.append(img_p)
                img.close()
                
            final_gif_frames[0].save(preview_path, save_all=True, append_images=final_gif_frames[1:], duration=duration_ms, loop=0, disposal=2, transparency=255)
            for img in final_gif_frames: img.close()
            
            final_msg = _("GIF 預覽生成完畢！\n檔案儲存於：\n{path}").format(path=preview_path)
            if warn_msg:
                final_msg = warn_msg + "\n\n" + final_msg
                
            finish_cb(True, preview_path, final_msg)
        except Exception as e:
            finish_cb(False, str(e), traceback.format_exc())

    @staticmethod
    def get_frame_template_name(card_type, sub_type_str):
        """
        🔀 相框路由映射器：將文字標籤翻譯為檔名 (完全不處理圖片)
        """
        if card_type == "魔法": return "Spell"
        if card_type == "陷阱": return "Trap"
        if card_type == "例外" or sub_type_str == "例外": return "Effect" # 依要求：例外強制套用 Effect
        
        tags = sub_type_str.split("=") if "=" in sub_type_str else [sub_type_str]
        is_pendulum = "靈擺" in tags
        
        if is_pendulum:
            if "通常" in tags: return "PendulumNormal"
            if "融合" in tags: return "PendulumFusion"
            if "同步" in tags: return "PendulumSynchro"
            if "超量" in tags: return "PendulumXyz"
            if "儀式" in tags: return "PendulumRitual"
            return "PendulumEffect"
        else:
            if "連結" in tags: return "Link"
            if "衍生物" in tags: return "Token"
            if "融合" in tags: return "Fusion"
            if "同步" in tags: return "Synchro"
            if "超量" in tags: return "Xyz"
            if "儀式" in tags: return "Ritual"
            if "通常" in tags: return "Normal"
            return "Effect"

    @staticmethod
    def generate_exception_report(aligned_db, out_dir):
        """
        🚨 例外收集器：過濾並產出開發者與使用者的獨立除錯名單
        """
        exceptions = []
        for c_id, info in aligned_db.items():
            props = info.get("properties", {})
            if props.get("Type") == "例外":
                exceptions.append({"id": c_id, "name": info.get("name", ""), "Raw_Data": props.get("Raw_Data", "")})
        
        if exceptions:
            try:
                # 產出給開發者的完整 JSON 證據檔
                with open(os.path.join(out_dir, "Unknown_Cards_Report.json"), "w", encoding="utf-8") as f:
                    json.dump(exceptions, f, indent=4, ensure_ascii=False)
                # 產出給使用者的純 ID 清單，方便貼回 UI 操作
                with open(os.path.join(out_dir, "Exception_IDs_List.txt"), "w", encoding="utf-8") as f:
                    f.write("\n".join(ex["id"] for ex in exceptions))
            except Exception: pass

    @staticmethod
    def build_db_from_assets(assets, target_dir, parse_meta=True):
        db, item_dict_str, desc_dict_str = {}, {}, {}
        name_bytes, desc_bytes, indx_bytes, prop_bytes = [assets.get(f, b'') for f in ('card_name.bytes', 'card_desc.bytes', 'card_indx.bytes', 'card_prop.bytes')]
        
        if indx_bytes and name_bytes and desc_bytes and prop_bytes:
            num_cards = len(indx_bytes) // 8
            name_offsets = [struct.unpack('<I', indx_bytes[i*8 : i*8+4])[0] for i in range(num_cards)] + [len(name_bytes)]
            desc_offsets = [struct.unpack('<I', indx_bytes[i*8+4 : i*8+8])[0] for i in range(num_cards)] + [len(desc_bytes)]
            for i in range(1, min(num_cards, len(prop_bytes) // 8)):
                cid = struct.unpack('<H', prop_bytes[i*8 : i*8+2])[0]
                # 🛡️ 提取 desc 傳入解析器，賦予其語意判讀能力
                desc_text = desc_bytes[desc_offsets[i]:desc_offsets[i+1]].split(b'\x00')[0].decode('utf-8', errors='ignore').strip()
                db[str(cid)] = {
                    "name": name_bytes[name_offsets[i]:name_offsets[i+1]].split(b'\x00')[0].decode('utf-8', errors='ignore').strip(),
                    "desc": desc_text,
                    "properties": MDEngine.parse_card_properties(prop_bytes, i, desc_text)
                }
                
        for k_file, target_dict in [('ids_item.bytes', item_dict_str), ('ids_itemdesc.bytes', desc_dict_str)]:
            if k_file in assets:
                try:
                    for k, v in msgpack.unpackb(assets[k_file], strict_map_key=False).items():
                        if isinstance(k, int): target_dict[format(k & 0xFFFFFFFF, '08x')] = target_dict[struct.pack('<I', k & 0xFFFFFFFF).hex()] = str(v)
                        else: target_dict[str(k)] = str(v)
                except Exception: pass

        if parse_meta:
            try:
                parts = os.path.normpath(target_dir).split(os.sep)
                localdata_idx = next((i for i, p in enumerate(parts) if p.lower() == "localdata"), -1)
                if localdata_idx != -1:
                    meta_path = os.path.join(os.sep.join(parts[:localdata_idx]), "masterduel_Data", "il2cpp_data", "Metadata", "global-metadata.dat")
                    if os.path.exists(meta_path):
                        with open(meta_path, 'rb') as f: meta_data = f.read()
                        for item_id in set(m.group(1).decode('ascii') for m in re.compile(b'ID([0-9]{6,7})').finditer(meta_data)):
                            crc_id, crc_item, crc_desc = [zlib.crc32(x.encode('utf-8')) & 0xFFFFFFFF for x in (f"ID{item_id}", f"IDS_ITEM.ID{item_id}", f"IDS_ITEMDESC.ID{item_id}")]
                            hashes = [format(crc_id, '08x'), struct.pack('<I', crc_id).hex(), format(crc_item, '08x'), struct.pack('<I', crc_item).hex()]
                            desc_hashes = [format(crc_desc, '08x'), struct.pack('<I', crc_desc).hex()]
                            n = next((item_dict_str[h] for h in hashes if h in item_dict_str), "")
                            d = next((desc_dict_str[h] for h in desc_hashes if h in desc_dict_str), "")
                            if not n: n = next((item_dict_str[h] for h in desc_hashes if h in item_dict_str), "")
                            if n or d: db[item_id] = {"name": n, "desc": d, "properties": {k: "None" for k in PROP_HEADERS}}
            except Exception: pass

        for k, v in item_dict_str.items():
            if k not in db: db[k] = {"name": v, "desc": desc_dict_str.get(k, ""), "properties": {k: "None" for k in PROP_HEADERS}}
        return db

    @staticmethod
    def get_aligned_database(target_dir, opts, progress_cb=None):
        """並行化字典加載器：僅將原本的單執行緒搜尋改為多程序並行，並提供平滑即時進度回報"""
        lang = opts.get('lang', 'zh-tw')
        use_cache = opts.get('use_cache', False) # 🌸 完全保留你原本的暫存開關設定，不作改動
        xor_key = opts.get('xor_key', 61)
        parse_meta = opts.get('parse_meta', True)
        size_filter = opts.get('size_filter', False)
        min_b = opts.get('min_b', 0)
        max_b = opts.get('max_b', 0)

        core = ["card_name.bytes", "card_desc.bytes", "card_indx.bytes", "card_prop.bytes"]
        opt_files = ["ids_item.bytes", "ids_itemdesc.bytes"]
        target_files = set(core + opt_files)
        found_text_assets = {}

        # 1. 讀取暫存
        if use_cache and os.path.exists(MDEngine.TEMP_DIR):
            cache_ready = True
            for f in core:
                if not (os.path.exists(os.path.join(MDEngine.TEMP_DIR, f"{f}.decrypted")) or 
                        os.path.exists(os.path.join(MDEngine.TEMP_DIR, f"{f.replace('.bytes', '')}.decrypted"))):
                    cache_ready = False
                    break
            
            if cache_ready:
                for f in target_files:
                    p1 = os.path.join(MDEngine.TEMP_DIR, f"{f}.decrypted")
                    p2 = os.path.join(MDEngine.TEMP_DIR, f"{f.replace('.bytes', '')}.decrypted")
                    tp = p1 if os.path.exists(p1) else (p2 if os.path.exists(p2) else None)
                    if tp:
                        with open(tp, "rb") as bf: found_text_assets[f] = bf.read()
                return MDEngine.build_db_from_assets(found_text_assets, target_dir, parse_meta)

        if not os.path.isdir(target_dir): raise Exception(_("目標資料夾不存在！"))

        # 2. 收集搜尋路徑 (🛡️ 修正：移除此處 os.walk 的 progress_cb，避免 0.08 秒內瞬間暴衝造成後續假死)
        raw_files = []
        for root, dummy_dirs, files in os.walk(target_dir):
            for file in files:
                raw_files.append((os.path.join(root, file), file))

        # 3. 將搜尋改為多程序並行 (🛡️ 修正：在此耗時 30 多秒的階段，加入即時進度回報)
        found_paths = {}
        workers_num = MDEngine.get_heavy_task_workers(opts.get('max_workers', 'Auto'))
        total_files = len(raw_files)
        if total_files > 0:
            batch_size = max(50, total_files // (workers_num * 4))
            batches = [raw_files[i:i + batch_size] for i in range(0, total_files, batch_size)]
            
            completed_batches = 0
            stop_event = opts.get('stop_event') # 🛡️ 取得中斷標記
            with concurrent.futures.ProcessPoolExecutor(max_workers=workers_num, initializer=_init_worker, initargs=(UI_LANG_DICT,)) as executor:
                futures = [executor.submit(MDEngine._worker_find_db_files, b, target_files, lang, size_filter, min_b, max_b, stop_event) for b in batches]
                for future in concurrent.futures.as_completed(futures):
                    if stop_event and stop_event.is_set():
                        for f in futures: f.cancel()
                        break # 🛡️ 接收中斷訊號
                    completed_batches += 1
                    # 🛡️ 在解密與尋找的 30 秒期間，平滑回報等比例的檔案處理數量，不再讓介面死卡！
                    if progress_cb: progress_cb(completed_batches * batch_size)
                    try:
                        res = future.result()
                        if res:
                            found_paths.update(res)
                            # 🌸 只要找齊目標檔案就提早退出，不多佔用 CPU 資源
                            if len(found_paths) >= len(target_files):
                                for f in futures: f.cancel()
                                break
                    except Exception: pass

        # 4. 解密並寫入暫存
        os.makedirs(MDEngine.TEMP_DIR, exist_ok=True)
        for key_name, filepath in found_paths.items():
            env = None
            try:
                env = UnityPy.load(filepath)
                # ✨ 修正還原：必須掃描 env.objects 才能抓到真正的 TextAsset 實體
                # (因為 MD 字典檔的 container 內有時候只是空殼參考)
                for obj in env.objects:
                    if obj.type.name == "TextAsset":
                        raw_bytes = MDEngine.get_raw_bytes_safe(obj)
                        if not raw_bytes: continue
                        
                        ydlz_idx = raw_bytes.find(b'YDLZ')
                        dec_bytes = zlib.decompressobj().decompress(raw_bytes[ydlz_idx+8:]) if ydlz_idx != -1 else None
                        
                        if not dec_bytes:
                            cracked_key = MDEngine.auto_crack_key(raw_bytes, xor_key)
                            if cracked_key is not None: 
                                opts['xor_key'] = cracked_key
                                dec_bytes = MDEngine.try_decompress(MDEngine.decrypt_file_bytes(raw_bytes, cracked_key))
                                
                        # 🛡️ 修正 break 邏輯：只有在「成功解密並寫入檔案後」才允許中斷迴圈
                        if dec_bytes:
                            found_text_assets[key_name] = dec_bytes
                            with open(os.path.join(MDEngine.TEMP_DIR, f"{key_name}.decrypted"), "wb") as bf: 
                                bf.write(dec_bytes)
                            break 
            except Exception: pass
            finally:
                if env: del env # 安全釋放記憶體，避免原本的記憶體洩漏問題
            
        return MDEngine.build_db_from_assets(found_text_assets, target_dir, parse_meta)

    @staticmethod
    def get_info_from_db(aligned_db, hash_name, clean_name):
        info = aligned_db.get(clean_name)
        if info and (info.get("name") or info.get("desc") or info.get("properties")): 
            return info.get("name", ""), info.get("desc", ""), info.get("properties", {k: "None" for k in PROP_HEADERS})
        
        if not any(c.isdigit() for c in clean_name):
            info = aligned_db.get(hash_name) or aligned_db.get(hash_name.lower())
            return (info["name"], info["desc"], info.get("properties", {k: "None" for k in PROP_HEADERS})) if info else ("", "", {k: "None" for k in PROP_HEADERS})

        match = RE_CARD_ID_EXTRACTOR.match(clean_name)
        if match:
            tag = "_".join(t.strip('_') for t in [match.group(1), match.group(3)] if t).strip('_')
            info = aligned_db.get(match.group(2))
            if info and (info.get("name") or info.get("desc") or info.get("properties")): 
                return (f"{info['name']} ({tag})" if info.get("name") and tag else info.get("name", "")), info.get("desc", ""), info.get("properties", {k: "None" for k in PROP_HEADERS})
        
        info = aligned_db.get(hash_name) or aligned_db.get(hash_name.lower())
        return (info["name"], info["desc"], info.get("properties", {k: "None" for k in PROP_HEADERS})) if info else ("", "", {k: "None" for k in PROP_HEADERS})
    
    @staticmethod
    def get_pendulum_list(csv_path, img_dir):
        lines = []
        if not os.path.exists(csv_path) or not os.path.isdir(img_dir): return lines
        try:
            dummy_map, db = MDEngine.get_csv_data(csv_path)
            card_dict = {d['id']: d for d in db}
            for img_name in os.listdir(img_dir):
                if not img_name.lower().endswith(('.png', '.jpg')): continue
                card_id = os.path.splitext(img_name)[0].split('_')[0]
                if card_id.isdigit() and card_id in card_dict:
                    
                    # ✨ 雙重防線 1：檢查 CSV 屬性欄位是否包含「靈擺」(物理遮罩)
                    p_idx = MDEngine.get_csv_indices(card_dict[card_id]['header'])["subtype"]
                    is_pen_prop = False
                    if p_idx != -1 and len(card_dict[card_id]['full_row']) > p_idx:
                        is_pen_prop = "靈擺" in card_dict[card_id]['full_row'][p_idx]
                        
                    # ✨ 雙重防線 2：全文檢索 (保留原廠文字判定)
                    full_text = " ".join(card_dict[card_id].get('full_row', []))
                    
                    if is_pen_prop or any(kw in full_text for kw in PENDULUM_KEYWORDS):
                        # ✨ O(1) 內部標記尋找引擎 (並具備防呆退回機制)
                        header = card_dict[card_id]['header']
                        n_idx = next((i for i, c in enumerate(header) if "(Name)" in c and not any(x in c.lower() for x in ["folder", "file", "hash", "檔名", "目錄"])), -1)
                        if n_idx == -1: n_idx = next((i for i, c in enumerate(header) if ("名稱" in c or "名" in c or "name" in c.lower()) and not any(x in c.lower() for x in ["folder", "file", "hash", "檔名", "目錄"])), -1)
                        
                        name = card_dict[card_id]['full_row'][n_idx] if n_idx != -1 and len(card_dict[card_id]['full_row']) > n_idx else ""
                        lines.append(f"{img_name}  # ID: {card_id} ({name})")
        except Exception: pass
        return lines
    
    @staticmethod
    def _worker_find_db_files(file_batch, target_files, lang, size_filter, min_b, max_b, stop_event=None):
        """並行字典尋找工作站：完全遵循你原本設定的過濾條件進行並行搜尋"""
        import UnityPy
        import os
        found = {}
        for filepath, filename in file_batch:
            if stop_event and stop_event.is_set(): break # 🛡️ 新增煞車檢查
            env = None
            try:
                if size_filter:
                    f_size = os.path.getsize(filepath)
                    if not (min_b <= f_size <= max_b): continue
                
                if not MDEngine.is_unity_bundle(filepath): continue
                
                env = UnityPy.load(filepath)
                for container_path, obj in env.container.items():
                    path_lower = str(container_path).lower()
                    if f"/{lang}/" in path_lower or f"_{lang}" in path_lower or "ids_item" in path_lower:
                        filename_lower = path_lower.split('/')[-1]
                        if filename_lower in target_files:
                            found[filename_lower] = filepath
            except Exception: pass
            finally:    # 👈 新增 finally 區塊
                if env: del env
        return found

    @staticmethod
    def _worker_scan_batch(task_batch, opts):
        """批次處理工作站：接手多個檔案的生路徑，並行完成硬碟 I/O 與解析"""
        extracted = set()
        mapping = []
        processed_count = 0
        
        for file_path, file_name, folder_type in task_batch:
            processed_count += 1
            env = None
            try:
                # 🛡️ 將硬碟 I/O 檢查移至子程序，讓多核心併發讀取，切除主程序排隊瓶頸
                if opts.get('size_filter'):
                    f_size = os.path.getsize(file_path)
                    if not (opts['min_b'] <= f_size <= opts['max_b']): continue
                
                if not MDEngine.is_unity_bundle(file_path): continue

                env = UnityPy.load(file_path)
                
                if not opts.get('deep_scan'):
                    for container_path, obj in env.container.items():
                        if obj.type.name in ("Texture2D", "TextAsset"):
                            clean_name = str(container_path).split('/')[-1].replace('.bmp', '').replace('.png', '')
                            is_cutin, cutin_id = MDEngine.is_cutin_asset(container_path, obj.type.name, clean_name)
                            
                            if is_cutin:
                                container_type = "TCG/OCG CutIn"
                                extracted.add(cutin_id)
                                if opts['gen_csv']: mapping.append([folder_type, container_type, file_name, cutin_id])
                            elif obj.type.name == "Texture2D":
                                if opts['only_num'] and not clean_name.isdigit(): continue
                                if opts.get('visual_only') and not MDEngine.is_visual_asset(clean_name): continue
                                container_type = "TCG/OCG" if "/tcg/" in str(container_path).lower() or "/ocg/" in str(container_path).lower() else "Common"
                                extracted.add(clean_name)
                                if opts['gen_csv']: mapping.append([folder_type, container_type, file_name, clean_name])
                else:
                    path_to_container = {obj.path_id: str(c_path) for c_path, obj in env.container.items()}
                    base_container_path = str(next(iter(env.container.keys()), ""))

                    for obj in env.objects:
                        if obj.type.name in ("Texture2D", "TextAsset"):
                            try:
                                clean_name = ""
                                try:
                                    if hasattr(obj, "peek_name"):
                                        peeked = obj.peek_name()
                                        if peeked: clean_name = str(peeked)
                                    if not clean_name:
                                        data = obj.read()
                                        if hasattr(data, "name") and data.name:
                                            clean_name = str(data.name)
                                except Exception:
                                    pass

                                clean_name = clean_name.replace('.bmp', '').replace('.png', '').strip()
                                c_path = str(path_to_container.get(obj.path_id, base_container_path))

                                if not clean_name:
                                    if c_path:
                                        clean_name = c_path.split('/')[-1].replace('.prefab', '').replace('.mat', '').replace('.bmp', '').replace('.png', '')
                                    else:
                                        clean_name = str(file_name).replace('.bundle', '')

                                clean_name = str(clean_name).strip()
                                if not clean_name: continue

                                is_cutin, cutin_id = MDEngine.is_cutin_asset(c_path, obj.type.name, clean_name)
                                
                                if is_cutin:
                                    container_type = "TCG/OCG CutIn"
                                    extracted.add(cutin_id)
                                    if opts['gen_csv']: mapping.append([folder_type, container_type, file_name, cutin_id])
                                elif obj.type.name == "Texture2D":
                                    if opts['only_num'] and not clean_name.isdigit(): continue
                                    if not MDEngine.is_valuable_texture(clean_name): continue
                                    
                                    container_type = "TCG/OCG" if "/tcg/" in c_path.lower() or "/ocg/" in c_path.lower() else "Common"
                                    extracted.add(clean_name)
                                    if opts['gen_csv']: mapping.append([folder_type, container_type, file_name, clean_name])
                            except Exception: pass
            except Exception: pass
            finally:
                if env: del env
            
        return extracted, mapping, processed_count

    @staticmethod
    def _worker_extract_single(task_info):
        file_path, file_name, out_img_dir, backup_dir, exp_csv, exp_img, exp_txt, exp_backup, visual_only = task_info
        success_count, csv_rows = 0, []
        if exp_backup:
            try: shutil.copy2(file_path, os.path.join(backup_dir, file_name))
            except Exception: pass
        if file_name.lower().endswith(('.png', '.jpg', '.csv', '.txt', '.json')): return success_count, csv_rows, 1
        env = None
        try:
            env = UnityPy.load(file_path)
            # 🛡️ 實作與掃描端一致的深度搜尋與路徑解析
            path_to_container = {obj.path_id: str(c_path) for c_path, obj in env.container.items()}
            base_container_path = str(next(iter(env.container.keys()), ""))

            for obj in env.objects:
                if obj.type.name == "Texture2D":
                    try:
                        clean_name = ""
                        data = None
                        base_id = ""
                        try:
                            if hasattr(obj, "peek_name"):
                                peeked = obj.peek_name()
                                if peeked: clean_name = str(peeked)
                            if not clean_name:
                                data = obj.read()
                                if hasattr(data, "name") and data.name:
                                    clean_name = str(data.name)
                        except Exception: pass

                        clean_name = clean_name.replace('.bmp', '').replace('.png', '').strip()
                        c_path = str(path_to_container.get(obj.path_id, base_container_path))

                        if not clean_name:
                            if c_path:
                                clean_name = c_path.split('/')[-1].replace('.prefab', '').replace('.mat', '').replace('.bmp', '').replace('.png', '')
                            else:
                                clean_name = str(file_name).replace('.bundle', '')

                        clean_name = str(clean_name).strip()
                        if not clean_name: continue
                        if visual_only and not MDEngine.is_visual_asset(clean_name): continue
                        
                        # 🛡️ 導入智慧過濾機制
                        if not MDEngine.is_valuable_texture(clean_name): continue
                        
                        # ✨ 呼叫精準識別器，若是動畫圖片則直接給予帶標籤的 ID，免除被 _ 截斷的悲劇
                        is_cutin_img, cutin_img_id = MDEngine.is_cutin_asset(c_path, "Texture2D", clean_name)
                        if is_cutin_img:
                            base_id = cutin_img_id
                        else:
                            base_id = re.sub(r'_(l|m|s|128|256|512)$', "", clean_name, flags=re.IGNORECASE)
                        
                        if exp_img:
                            if data is None: data = obj.read()
                            out_path = os.path.join(out_img_dir, f"{base_id}.png")
                            save_it = True
                            if os.path.exists(out_path):
                                try:
                                    with Image.open(out_path) as ext_img:
                                        # 如果舊圖比較大，就不覆蓋 (保護高畫質貼圖)
                                        if (data.image.width * data.image.height) <= (ext_img.width * ext_img.height):
                                            save_it = False
                                except Exception: pass
                            if save_it: data.image.save(out_path)
                            
                        # 回傳時增加 c_path (容器路徑)，以供主程序組裝時判斷使用
                        if exp_csv: csv_rows.append([file_name, base_id, c_path])
                        success_count += 1
                    except Exception as e:
                        try:
                            # 🛡️ 修正：拔除危險的 locals() 判斷，直接依靠上方事前宣告的安全變數
                            if exp_img and base_id:
                                with open(os.path.join(out_img_dir, f"ERROR_{base_id}.txt"), "w", encoding="utf-8") as ef:
                                    ef.write(f"{_('解碼圖片發生錯誤 (Error decoding image)')} {base_id}:\n{str(e)}")
                        except Exception: pass
                elif obj.type.name == "TextAsset" and exp_txt:
                    try:
                        data = obj.read()
                        raw_script = MDEngine.get_raw_bytes_safe(obj) or getattr(data, "m_Script", None)
                        
                        # 🛡️ 強制安全轉型，取得物件真正的內部名稱
                        safe_name = str(getattr(data, "m_Name", getattr(data, "name", ""))).strip()
                        
                        c_path = str(path_to_container.get(obj.path_id, base_container_path))
                        
                        # 呼叫已經重構好的核心引擎，cutin_id 會直接給出如 p18826_hd.atlas 這樣完美的 ID
                        is_cutin, cutin_id = MDEngine.is_cutin_asset(c_path, "TextAsset", safe_name)
                        
                        if is_cutin and raw_script:
                            # 賦予對應的實體副檔名
                            ext = ".txt" if "atlas" in safe_name.lower() else ".json"
                            
                            # 智慧防呆：如果引擎給的 ID 已經自帶正確副檔名就不重複加
                            final_name = cutin_id if cutin_id.lower().endswith(ext) else f"{cutin_id}{ext}"
                            out_text_path = os.path.join(out_img_dir, final_name)
                            
                            # 🛡️ 實體檔案防覆蓋防線：只有在檔案不存在時才寫入（完美保留高畫質優先的設計）
                            if not os.path.exists(out_text_path):
                                if isinstance(raw_script, str):
                                    with open(out_text_path, "w", encoding="utf-8") as tf: tf.write(raw_script)
                                elif isinstance(raw_script, (bytes, bytearray)):
                                    with open(out_text_path, "wb") as tf: tf.write(raw_script)
                                    
                            success_count += 1
                            
                            # ✨ 補齊缺失：將精確命名的 TextAsset 無縫匯出至 CSV 對照表
                            if exp_csv:
                                csv_rows.append([file_name, cutin_id, c_path])
                    except Exception:
                        pass
        except Exception: pass
        finally:
            if env: del env
        return success_count, csv_rows, 1
    
    @staticmethod
    def filter_valid_mods(mod_root, mod_list):
        valid, ghosts = [], []
        for mod in mod_list:
            if os.path.isdir(os.path.join(mod_root, mod)): valid.append(mod)
            else: ghosts.append(mod)
        return valid, ghosts

    @staticmethod
    def _worker_replace_bundle(task_info):
        hash_name, img_dict, mod_img_dir, backup_dir, out_dir = task_info
        src_bundle = os.path.join(backup_dir, hash_name)
        tgt_bundle = os.path.join(out_dir, hash_name)
        if not os.path.exists(src_bundle): return 0
        
        target_images = {}
        target_texts = {}
        parsed_texts_meta = {} 
        
        for img, mapped_id in img_dict.items():
            ext = os.path.splitext(img)[1].lower()
            if ext in ('.txt', '.json', '.bytes', '.atlas'):
                target_texts[img] = img
                parsed_texts_meta[img] = MDEngine.parse_cutin_tag_and_base(img)
            else:
                is_cut, base_name, req_res = MDEngine.parse_cutin_tag_and_base(mapped_id)
                if is_cut:
                    tag = "-hd" if req_res == "highend_hd" else "-sd"
                    target_images[f"{base_name}{tag}"] = img
                else:
                    target_images[mapped_id] = img

        # ✨ 呼叫既有的同化核心：建立全半形與大小寫歸一化的 O(1) 速查字典
        target_images_norm = {MDEngine.normalize_string(k): (k, v) for k, v in target_images.items()}
                
        success = 0
        env = None
        try:
            env = UnityPy.load(src_bundle)
            modded = False
            
            # ✨ 預先建立容器路徑對照表，為後續的 env.objects 遍歷作好準備
            path_to_container = {obj.path_id: str(c_path) for c_path, obj in env.container.items()}
            base_container_path = str(next(iter(env.container.keys()), ""))
            
            # ✨ 改用 env.objects 進行深度遍歷，補齊降級備用掃描機制，並支援多貼圖共用容器
            for obj in env.objects:
                c_path = str(path_to_container.get(obj.path_id, base_container_path))
                
                # ✨ 專屬容器副檔名清理：剝離 .prefab, .mat，完美應對場地與大廳背景
                target_name = c_path.split('/')[-1].replace('.prefab', '').replace('.mat', '').replace('.bmp', '').replace('.png', '').strip()
                base_id = re.sub(r'_(l|m|s|128|256|512)$', "", target_name, flags=re.IGNORECASE)
                
                # 【軌道一：Texture2D 圖片處理】
                if obj.type.name == "Texture2D":
                    is_cutin_img, cutin_img_id = MDEngine.is_cutin_asset(c_path, "Texture2D", target_name)
                    lookup_id = cutin_img_id if is_cutin_img else base_id

                    # ✨ 呼叫既有的 normalize_string 進行雙向同化比對
                    matched_item = None
                    norm_lookup = MDEngine.normalize_string(lookup_id)
                    
                    if norm_lookup in target_images_norm:
                        matched_item = target_images_norm[norm_lookup]
                    else:
                        # 🛡️ 降級備用掃描：若 Container 比對失敗，嘗試讀取 Texture2D 內部真實 m_Name 並同化比對
                        try:
                            clean_name = ""
                            if hasattr(obj, "peek_name"):
                                peeked = obj.peek_name()
                                if peeked: clean_name = str(peeked)
                            if not clean_name:
                                data = obj.read()
                                if hasattr(data, "name") and data.name:
                                    clean_name = str(data.name)
                            clean_name = clean_name.replace('.bmp', '').replace('.png', '').strip()
                            clean_base = re.sub(r'_(l|m|s|128|256|512)$', "", clean_name, flags=re.IGNORECASE)
                            
                            norm_clean = MDEngine.normalize_string(clean_name)
                            norm_base = MDEngine.normalize_string(clean_base)
                            
                            if norm_clean in target_images_norm:
                                matched_item = target_images_norm[norm_clean]
                            elif norm_base in target_images_norm:
                                matched_item = target_images_norm[norm_base]
                        except Exception: pass

                    if matched_item:
                        orig_key, target_img_file = matched_item
                        img_path = os.path.join(mod_img_dir, target_img_file)
                        if os.path.exists(img_path):
                            data = obj.read()
                            with Image.open(img_path) as mod_img:
                                mod_img = mod_img.convert("RGBA")
                                options = {"target_size": (data.image.width, data.image.height)}
                                mod_img = MDEngine.process_texture_image(mod_img, orig_key, {}, "MODE_FIT_VISUAL" if MDEngine.is_visual_asset(orig_key) else "NONE", options)
                                        
                                data.image = mod_img
                                # ✨ 核心修正：單點防護隔離，僅針對 P 編號 Cut-In 動畫，強制修正色彩空間防雜訊
                                if is_cutin_img and hasattr(data, "m_ColorSpace"):
                                    data.m_ColorSpace = 0
                                data.save()
                                modded = True
                        
                # 【軌道二：TextAsset 文字資料處理】
                elif obj.type.name == "TextAsset" and target_texts:
                    data = None
                    for txt_file in target_texts.keys():
                        is_cut, clean_m_name, req_res_tag = parsed_texts_meta[txt_file]
                        
                        if data is None: data = obj.read()
                        obj_name = str(getattr(data, "m_Name", getattr(data, "name", "")))
                        
                        # ✨ 雙向同化比對，徹底消滅大小寫與全半形差異
                        norm_obj = MDEngine.normalize_string(obj_name)
                        norm_clean = MDEngine.normalize_string(clean_m_name)
                        
                        if norm_obj == norm_clean and (not req_res_tag or req_res_tag in c_path.lower()):
                            txt_path = os.path.join(mod_img_dir, txt_file)
                            if os.path.exists(txt_path):
                                new_content = MDEngine.read_text_file_clean(txt_path)
                                if new_content:
                                    if isinstance(data.m_Script, bytes) and isinstance(new_content, str):
                                        data.m_Script = new_content.encode("utf-8")
                                    elif isinstance(data.m_Script, str) and isinstance(new_content, bytes):
                                        data.m_Script = new_content.decode("utf-8", errors="ignore")
                                    else:
                                        data.m_Script = new_content
                                    data.save()
                                    modded = True
            if modded:
                with open(tgt_bundle, "wb") as f: f.write(env.file.save())
                success = 1
        except Exception: pass
        finally:
            if env: del env
        return success

    @staticmethod
    def _worker_stream_update_single(task_info):
        import gc
        gc.collect()
        MDEngine.check_memory_limit(85.0)
        
        root_dir, file_name, clean_src_dir, out_base, overwrite, old_mod_dir = task_info
        clean_file = MDEngine.get_actual_bundle_path(clean_src_dir, file_name)
        if not os.path.exists(clean_file): clean_file = MDEngine.get_actual_source_path(clean_src_dir, file_name, "StreamingAssets")
        
        # 🛡️ 補齊翻譯包裹：使用 format 將變數抽離
        if not os.path.exists(clean_file): 
            return (0, _("[{file_name}] 找不到對應的遊戲乾淨原檔。").format(file_name=file_name))
        
        old_env = None
        env_clean = None
        try:
            old_env = UnityPy.load(os.path.join(root_dir, file_name))
            old_obj_map = {}
            for path, obj in old_env.container.items():
                if obj.type.name == "Texture2D": 
                    name_key = path.split('/')[-1].replace('.bmp', '').replace('.png', '')
                    old_obj_map[name_key] = obj
            
            if not old_obj_map:
                del old_env
                return (0, _("[{file_name}] 舊模組中未發現 Texture2D 貼圖資源。").format(file_name=file_name))
                
            env_clean = UnityPy.load(clean_file)
            injected = False
            
            for path, obj in env_clean.container.items():
                name_key = path.split('/')[-1].replace('.bmp', '').replace('.png', '')
                if obj.type.name == "Texture2D" and name_key in old_obj_map:
                    old_data = old_obj_map[name_key].read()
                    new_data = obj.read()
                    
                    # 🛡️ 修正：Texture2D 實體沒有 get_raw_data 方法，真實的純圖片資料存在 image_data 中
                    raw_bytes = getattr(old_data, 'image_data', b'')
                    
                    if not raw_bytes:
                        continue
                        
                    if hasattr(old_data, 'm_TextureFormat') and hasattr(new_data, 'm_TextureFormat'):
                        if old_data.m_TextureFormat != new_data.m_TextureFormat:
                            continue

                    if hasattr(new_data, "m_StreamData") and new_data.m_StreamData:
                        new_data.m_StreamData.path = ""
                        new_data.m_StreamData.offset = 0
                        new_data.m_StreamData.size = 0

                    new_data.image_data = raw_bytes
                    new_data.m_Width = old_data.m_Width
                    new_data.m_Height = old_data.m_Height
                    new_data.m_TextureFormat = old_data.m_TextureFormat
                    
                    if hasattr(old_data, 'm_MipCount') and hasattr(new_data, 'm_MipCount'):
                        new_data.m_MipCount = old_data.m_MipCount
                        
                    if hasattr(new_data, 'm_CompleteImageSize'):
                        new_data.m_CompleteImageSize = len(raw_bytes)
                    
                    # ✨ 核心修正：串流修復時，同樣利用正則確保動畫貼圖維持正確的 Gamma 空間
                    if re.match(r'^p\d+', name_key, re.IGNORECASE) and hasattr(new_data, "m_ColorSpace"):
                        new_data.m_ColorSpace = 0
                        
                    new_data.save()
                    injected = True
                    
            if injected:
                out_hash_dir = root_dir if overwrite else os.path.normpath(os.path.join(out_base, os.path.relpath(root_dir, old_mod_dir)))
                if not overwrite: os.makedirs(out_hash_dir, exist_ok=True)
                with open(os.path.join(out_hash_dir, file_name), "wb") as f: f.write(env_clean.file.save())
                
            # 🛡️ 補齊翻譯包裹
            return (1, None) if injected else (0, _("[{file_name}] 未能成功注入任何貼圖 (可能格式不相容)。").format(file_name=file_name))
        except Exception as e: 
            return (0, _("[{file_name}] 核心處理例外崩潰: {error}").format(file_name=file_name, error=str(e)))
        finally:
            if old_env: del old_env
            if env_clean: del env_clean

    @staticmethod
    def task_scan(target_dir, out_dir, txt_name, csv_name, opts, progress_cb, finish_cb):
        import time # 載入高精度計時器
        try:
            os.makedirs(out_dir, exist_ok=True)
            aligned_db, error_logs = {}, []
            
            # 🌸 診斷點一：測量文字字典載入時間
            print("\n========== [TELEMETRY START] ==========")
            t_db_start = time.perf_counter()
            if opts['gen_name'] or opts['gen_desc']:
                try: 
                    print(_("[INFO] 開始獲取文字字典（get_aligned_database）..."))
                    aligned_db = MDEngine.get_aligned_database(target_dir, opts, progress_cb)
                except Exception as e: 
                    error_logs.append(_("獲取文本字典失敗: {error}\n").format(error=e))
            t_db_end = time.perf_counter()
            db_duration = t_db_end - t_db_start
            print(_("[METRIC] 字典載入耗時: {duration:.4f} 秒 (找到 {count} 筆資料)").format(duration=db_duration, count=len(aligned_db)))

            target_dirs = [target_dir]
            parts = os.path.normpath(target_dir).split(os.sep)
            localdata_idx = next((i for i, p in enumerate(parts) if p.lower() == "localdata"), -1)
            if localdata_idx != -1:
                sa_dir = os.path.join(os.sep.join(parts[:localdata_idx]), "masterduel_Data", "StreamingAssets", "AssetBundle")
                if os.path.exists(sa_dir): target_dirs.append(sa_dir)

            # 🌸 診斷點二：測量檔案路徑搜尋時間 (os.walk)
            t_walk_start = time.perf_counter()
            raw_files = []
            
            if progress_cb: progress_cb(0) # 🛡️ 立即推動狀態列，脫離「準備啟動」
            
            stop_event = opts.get('stop_event') # 🛡️ 提取中斷標記
            
            for d in target_dirs:
                if stop_event and stop_event.is_set(): break # 🛡️ 第一層煞車
                folder_type = "StreamingAssets" if "StreamingAssets" in d else "0000"
                exclude_paths = MDEngine.get_child_exclude_paths(d, [MDEngine.TEMP_DIR])
                for root, dummy_dirs, files in os.walk(d):
                    if stop_event and stop_event.is_set(): break # 🛡️ 核心迴圈煞車
                    MDEngine.prune_walk_dirs(root, dummy_dirs, exclude_paths) # 🛡️ 動態剪枝
                    for f in files:
                        raw_files.append((os.path.join(root, f), f, folder_type))
                        # 🛡️ 第二階段檢索發射訊號
                        if progress_cb and len(raw_files) % 500 == 0: 
                            progress_cb(len(raw_files))
            t_walk_end = time.perf_counter()
            walk_duration = t_walk_end - t_walk_start
            print(_("[METRIC] os.walk 搜尋 {count} 個檔案路徑耗時: {duration:.4f} 秒").format(count=len(raw_files), duration=walk_duration))

            extracted_names, mapping_data, count = set(), [], 0
            total_files = len(raw_files)
            
            # 🌸 診斷點三：測量多程序併發掃描時間
            t_mp_start = time.perf_counter()
            if total_files > 0:
                workers_num = MDEngine.get_heavy_task_workers(opts.get('max_workers', 'Auto'))
                batch_size = max(50, min(500, total_files // max(1, (workers_num * 4))))
                batches = [raw_files[i:i + batch_size] for i in range(0, total_files, batch_size)]
                
                print(_("[INFO] 啟動多程序（{workers} 核心），分裝成 {batch_count} 個批次（每批約 {batch_size} 個）...").format(workers=workers_num, batch_count=len(batches), batch_size=batch_size))
                with concurrent.futures.ProcessPoolExecutor(max_workers=workers_num, initializer=_init_worker, initargs=(UI_LANG_DICT,)) as executor:
                    # 🛡️ 防護：傳遞 opts 的深度副本，防止多核狂奔時污染 XOR 密鑰記憶體
                    opts_copy = opts.copy()
                    futures = [executor.submit(MDEngine._worker_scan_batch, b, opts_copy) for b in batches]
                    for future in concurrent.futures.as_completed(futures):
                        try:
                            ext, map_d, processed = future.result()
                            if ext: extracted_names.update(ext)
                            if map_d: mapping_data.extend(map_d)
                            count += processed
                            if progress_cb: progress_cb(count)
                        except Exception as e:
                            error_logs.append(_("批次處理發生異常: {error}\n").format(error=e))
            t_mp_end = time.perf_counter()
            mp_duration = t_mp_end - t_mp_start
            print(_("[METRIC] 多程序掃描 3D/2D 貼圖耗時: {duration:.4f} 秒").format(duration=mp_duration))
            print("========== [TELEMETRY END] ==========\n")

            # 🛡️ 資料保護結界：只有在「未被中斷」的情況下，才允許覆寫實體檔案
            is_aborted = opts.get('stop_event') and opts.get('stop_event').is_set()
            
            if not is_aborted:
                if opts['gen_txt'] and extracted_names:
                    with open(os.path.join(out_dir, txt_name), 'w', encoding='utf-8') as f: f.write("\n".join(sorted(extracted_names)) + "\n")
                        
                if opts['gen_csv'] and mapping_data:
                    # ✨ 如果是未知語系，自動套用標準 i18n 標記
                    n_head, d_head = f"{opts['lang']}(Name)", f"{opts['lang']}(Desc)"
                    # 🛡️ 核心：標頭組合與動態排序錨點
                    headers = [MDEngine.CSV_HEADER_FOLDER, MDEngine.CSV_HEADER_CONTAINER] + PROP_HEADERS + [MDEngine.CSV_HEADER_FILE_ID, MDEngine.CSV_HEADER_ITEM_ID]
                    if opts['gen_name']: headers.append(n_head)
                    if opts['gen_desc']: headers.append(d_head)
                    
                    id_idx = headers.index(MDEngine.CSV_HEADER_ITEM_ID)
                    
                    def sort_key(row):
                        val = str(row[id_idx]).strip() if len(row) > id_idx else ""
                        if val.isdigit(): return (0, int(val), "")
                        return (1, 0, val.lower())
                    
                    full_rows = []
                    for r in mapping_data:
                        name, desc, props = MDEngine.get_info_from_db(aligned_db, r[2], r[3])
                        out_row = [r[0], r[1]] + [props.get(p, "None") for p in PROP_HEADERS] + [r[2], r[3]]
                        if opts['gen_name']: out_row.append(name)
                        if opts['gen_desc']: out_row.append(desc)
                        full_rows.append(out_row)
                        
                    full_rows.sort(key=sort_key)
                    
                    with open(os.path.join(out_dir, csv_name), 'w', newline='', encoding='utf-8-sig') as f:
                        writer = csv.writer(f)
                        writer.writerow(headers)
                        writer.writerows(full_rows)
                        
                MDEngine.generate_exception_report(aligned_db, out_dir)

            err_path = os.path.join(out_dir, "t1_scan_error.txt")
            if error_logs:
                # 就算中斷了，錯誤日誌依然保留寫入，方便除錯
                with open(err_path, "w", encoding="utf-8") as f: f.writelines(error_logs)
            
            # 🛡️ 修正數據回報指標：若被中斷，寫入的 CSV 數量為 0
            final_count = len(full_rows) if (opts['gen_csv'] and mapping_data and not is_aborted) else len(extracted_names)
            
            finish_cb(True, final_count, {"err_path": err_path if error_logs else None, "new_key": opts.get('xor_key')})
        except PermissionError: finish_cb(False, _("權限不足！請確認 CSV 檔案是否正被 Excel 等軟體開啟中，請關閉後再試。"), traceback.format_exc())
        except Exception as e: finish_cb(False, str(e), traceback.format_exc())

    @staticmethod
    def _scan_bundles_parallel(target_dir, opts, progress_cb):
        """✨ 模組化共用引擎：高速多程序硬碟掃描，專門為擴充與掃描提供映射資料"""
        target_dirs = [target_dir]
        parts = os.path.normpath(target_dir).split(os.sep)
        localdata_idx = next((i for i, p in enumerate(parts) if p.lower() == "localdata"), -1)
        if localdata_idx != -1:
            sa_dir = os.path.join(os.sep.join(parts[:localdata_idx]), "masterduel_Data", "StreamingAssets", "AssetBundle")
            if os.path.exists(sa_dir): target_dirs.append(sa_dir)

        raw_files = []
        stop_event = opts.get('stop_event') # 🛡️ 提取中斷標記
        
        for d in target_dirs:
            if stop_event and stop_event.is_set(): break # 🛡️ 第一層煞車
            folder_type = "StreamingAssets" if "StreamingAssets" in d else "0000"
            # 🛡️ 貫徹 DRY 原則，與 task_scan 採用完全一致的安全結界過濾器
            exclude_paths = MDEngine.get_child_exclude_paths(d, [MDEngine.TEMP_DIR])
            for root, dummy_dirs, files in os.walk(d):
                if stop_event and stop_event.is_set(): break # 🛡️ 核心迴圈煞車
                MDEngine.prune_walk_dirs(root, dummy_dirs, exclude_paths) # 🛡️ 動態剪枝
                for f in files:
                    raw_files.append((os.path.join(root, f), f, folder_type))

        mapping_data = []
        total_files = len(raw_files)
        if total_files > 0:
            workers_num = MDEngine.get_heavy_task_workers(opts.get('max_workers', 'Auto'))
            batch_size = max(50, min(500, total_files // max(1, (workers_num * 4))))
            batches = [raw_files[i:i + batch_size] for i in range(0, total_files, batch_size)]

            count = 0
            with concurrent.futures.ProcessPoolExecutor(max_workers=workers_num, initializer=_init_worker, initargs=(UI_LANG_DICT,)) as executor:
                # 🛡️ 防護：變數隔離
                opts_copy = opts.copy()
                futures = [executor.submit(MDEngine._worker_scan_batch, b, opts_copy) for b in batches]
                for future in concurrent.futures.as_completed(futures):
                    if stop_event and stop_event.is_set():
                        for f in futures: f.cancel()
                        break # 🛡️ 併發掃描煞車
                    try:
                        ext, map_d, processed = future.result()
                        if map_d: mapping_data.extend(map_d)
                        count += processed
                        if progress_cb and count % 200 == 0: progress_cb(count)
                    except Exception: pass
        return mapping_data

    @staticmethod
    def task_enrich(csv_path, target_dir, opts, progress_cb, finish_cb):
        try:
            lang = opts.get('lang', 'zh-tw')
            aligned_db = MDEngine.get_aligned_database(target_dir, opts, progress_cb)
            updated_rows = []
            n_head, d_head = f"{lang}(Name)", f"{lang}(Desc)"
            
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                header = next(reader, [])
                
                # 🛡️ 動態標頭防護：尋找並安插 7 大屬性
                indices = MDEngine.get_csv_indices(header)
                if indices["hash"] == -1 or indices["id"] == -1:
                    raise Exception(_("偵測到不相容的舊版 CSV 格式！請至分頁 1 重新掃描並生成對照表。"))
                f_idx, c_idx, h_idx, id_idx = indices["folder"], indices["container"], indices["hash"], indices["id"]
                p_start_idx = indices["type"]
                
                # ✨ 使用嚴格模式尋找名稱欄位索引
                n_idx = MDEngine.find_lang_column_index(header, lang, "Name", strict=True)
                if n_idx != -1: 
                    # 若找到專屬本語系的欄位，統一覆寫升級為標準化標頭
                    header[n_idx] = n_head  
                else:
                    # 💡 找不到專屬語系，向最右側擴充新欄位
                    n_idx = len(header); header.append(n_head)
                        
                # ✨ 使用嚴格模式尋找效果欄位索引
                d_idx = MDEngine.find_lang_column_index(header, lang, "Desc", strict=True)
                if d_idx != -1:
                    header[d_idx] = d_head
                else:
                    d_idx = len(header); header.append(d_head)
                
                existing_hashes = set() 
                
                updated_rows.append(header)
                for row in reader:
                    if not row: continue
                    
                    # 💡 DRY 核心：用最簡單的邏輯確保資料列長度絕對對齊標頭 (取代複雜的 max 計算)
                    while len(row) < len(header): row.append("")
                    
                    h_name = row[h_idx].strip() if h_idx != -1 and len(row) > h_idx else ""
                    c_id = row[id_idx].strip() if id_idx != -1 and len(row) > id_idx else ""
                    
                    # 僅註冊已存在的 Hash
                    if h_name: existing_hashes.add(h_name)
                    
                    name, desc, props = MDEngine.get_info_from_db(aligned_db, h_name, c_id) 
                    
                    if name: row[n_idx] = name
                    if desc: row[d_idx] = desc
                    if props and p_start_idx != -1:
                        for i, p_name in enumerate(PROP_HEADERS):
                            row[p_start_idx + i] = props.get(p_name, "None")
                    updated_rows.append(row)
                    
            # 第二階段：補齊新 Bundle 擴增 (維持原樣)
            mapping_data = MDEngine._scan_bundles_parallel(target_dir, opts, progress_cb)
            
            for folder, container, h_name, c_id in mapping_data:
                # ✨ 核心修正：只認 Hash！只要是遊戲新出的檔案，就無條件為它建立全新的一列
                if h_name not in existing_hashes:
                    new_row = [""] * len(header)
                    if f_idx != -1: new_row[f_idx] = folder
                    if c_idx != -1: new_row[c_idx] = container
                    if h_idx != -1: new_row[h_idx] = h_name
                    if id_idx != -1: new_row[id_idx] = c_id
                    
                    name, desc, props = MDEngine.get_info_from_db(aligned_db, h_name, c_id)
                    if n_idx != -1: new_row[n_idx] = name
                    if d_idx != -1: new_row[d_idx] = desc
                    if p_start_idx != -1:
                        for i, p_name in enumerate(PROP_HEADERS):
                            new_row[p_start_idx + i] = props.get(p_name, "None")
                            
                    updated_rows.append(new_row)
                    # 追加完畢後，註冊進記憶體，防止後續重複添加
                    existing_hashes.add(h_name)
                    
            def sort_key(row):
                val = str(row[id_idx]).strip() if id_idx != -1 and len(row) > id_idx else ""
                if val.isdigit(): return (0, int(val), "")
                return (1, 0, val.lower())
                
            data_sorted = sorted(updated_rows[1:], key=sort_key)
            
            # 🛡️ 資料保護結界：只有在「未被中斷」的情況下，才允許覆寫實體檔案
            is_aborted = opts.get('stop_event') and opts.get('stop_event').is_set()
            if not is_aborted:
                with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f: 
                    writer = csv.writer(f)
                    writer.writerow(updated_rows[0])
                    writer.writerows(data_sorted)
                
            finish_cb(True, len(data_sorted), None)
        except Exception as e: finish_cb(False, str(e), traceback.format_exc())

    @staticmethod
    def _worker_copy_single(src, dst):
        try:
            if os.path.exists(src):
                shutil.copy2(src, dst)
                return 1
        except Exception: pass
        return 0

    @staticmethod
    def task_find(csv_path, src_dir, out_dir, target_ids, visual_only, progress_cb, finish_cb):
        try:
            os.makedirs(out_dir, exist_ok=True)
            mapping_dict, dummy_db = MDEngine.get_csv_data(csv_path)
            
            # 1. 整理去重任務清單 (確保 I/O 不會踩踏)
            tasks = set()
            for card_id in target_ids:
                if visual_only and not MDEngine.is_visual_asset(card_id): continue
                if card_id in mapping_dict:
                    for item in mapping_dict[card_id]:
                        src = MDEngine.get_actual_source_path(src_dir, item['hash'], item['folder'])
                        dst = os.path.join(out_dir, item['hash'])
                        tasks.add((src, dst))
            
            # 2. 多執行緒派發 (使用 ThreadPool 極速調度 SSD 寫入佇列)
            success, count = 0, 0
            optimal_threads = max(4, MDEngine.get_optimal_workers() * 2)
            with concurrent.futures.ThreadPoolExecutor(max_workers=optimal_threads) as executor:
                futures = [executor.submit(MDEngine._worker_copy_single, s, d) for s, d in tasks]
                for future in concurrent.futures.as_completed(futures):
                    count += 1
                    if progress_cb and count % 10 == 0: progress_cb(count)
                    try: success += future.result()
                    except Exception: pass
                    
            finish_cb(True, success, None)
        except Exception as e: finish_cb(False, str(e), traceback.format_exc())

    @staticmethod
    def task_extract(hash_dir, img_folder, backup_folder, csv_name, exp_csv, exp_img, exp_txt, exp_backup, master_csv_path, visual_only, progress_cb, finish_cb):
        try:
            parent_dir = os.path.dirname(hash_dir)
            out_img_dir, backup_dir = os.path.join(parent_dir, img_folder or "原卡圖"), os.path.join(parent_dir, backup_folder or "文件備份")
            csv_path = os.path.join(parent_dir, csv_name or "2DTexture_Mapping.csv")
            if exp_img or exp_txt: os.makedirs(out_img_dir, exist_ok=True)
            if exp_backup: os.makedirs(backup_dir, exist_ok=True)
            
            # 🛡️ 提前將主對照表載入記憶體，建立 Hash -> 屬性 的 O(1) 速查表
            hash_to_meta = {}
            if exp_csv and os.path.exists(master_csv_path):
                mapping, _db = MDEngine.get_csv_data(master_csv_path)
                for items in mapping.values():
                    for item in items:
                        hash_to_meta[item['hash']] = (item['folder'], item['container'])
            
            # 🛡️ 展開迴圈並套用動態剪枝，防止把剛提取出來的備份又當作來源讀取
            tasks = []
            exclude_paths = [out_img_dir, backup_dir, MDEngine.TEMP_DIR]
            for root, dummy_dirs, files in os.walk(hash_dir):
                MDEngine.prune_walk_dirs(root, dummy_dirs, exclude_paths)
                for f in files:
                    tasks.append((os.path.join(root, f), f, out_img_dir, backup_dir, exp_csv, exp_img, exp_txt, exp_backup, visual_only))
                    
            success, count, all_csv_rows = 0, 0, []
            
            with concurrent.futures.ProcessPoolExecutor(max_workers=MDEngine.get_optimal_workers(), initializer=_init_worker, initargs=(UI_LANG_DICT,)) as executor:
                for succ, c_rows, processed in executor.map(MDEngine._worker_extract_single, tasks, chunksize=10):
                    success += succ
                    if c_rows: all_csv_rows.extend(c_rows)
                    count += processed
                    if progress_cb and count % 20 == 0: progress_cb(count)
                        
            # 🛡️ 以標準四欄格式重新組裝，完美對齊後續改圖與打包流程
            if exp_csv and all_csv_rows:
                unique_rows = []
                seen = set()
                id_to_row = {}
                master_header = [MDEngine.CSV_HEADER_FOLDER, MDEngine.CSV_HEADER_CONTAINER] + PROP_HEADERS + [MDEngine.CSV_HEADER_FILE_ID, MDEngine.CSV_HEADER_ITEM_ID]
                
                if os.path.exists(master_csv_path):
                    _m, db = MDEngine.get_csv_data(master_csv_path)
                    if db and 'header' in db[0]:
                        master_header = list(db[0]['header'])
                    id_to_row = {d['id']: d.get('full_row', []) for d in db}

                # 🛡️ 呼叫中央解析器進行動態索引重算 (徹底消滅硬編碼 Bug)
                indices = MDEngine.get_csv_indices(master_header)
                f_idx, c_idx, h_idx, id_idx = indices["folder"], indices["container"], indices["hash"], indices["id"]
                p_start = indices["type"]

                for file_name, base_id, c_path in all_csv_rows:
                    if (file_name, base_id) in seen: continue 
                    seen.add((file_name, base_id))
                    
                    meta = hash_to_meta.get(file_name)
                    if meta:
                        folder, container = meta
                    else:
                        folder = "StreamingAssets" if "StreamingAssets" in file_name or "StreamingAssets" in c_path else "0000"
                        container = "TCG/OCG" if "/tcg/" in c_path.lower() or "/ocg/" in c_path.lower() else "Common"
                    
                    # 🛡️ 若主對照表有資料，複製整列，並防呆對齊最新標頭長度
                    if base_id in id_to_row and id_to_row[base_id]:
                        row_data = list(id_to_row[base_id])
                        while len(row_data) < len(master_header): row_data.append("")
                        
                        # 🛡️ 精準透過動態索引寫入，絕對不破壞其他欄位！
                        if f_idx != -1: row_data[f_idx] = folder
                        if c_idx != -1: row_data[c_idx] = container
                        if h_idx != -1: row_data[h_idx] = file_name
                        if id_idx != -1: row_data[id_idx] = base_id
                        unique_rows.append(row_data)
                    else:
                        row_data = [""] * len(master_header)
                        if f_idx != -1: row_data[f_idx] = folder
                        if c_idx != -1: row_data[c_idx] = container
                        if h_idx != -1: row_data[h_idx] = file_name
                        if id_idx != -1: row_data[id_idx] = base_id
                        
                        # 如果是新加入的卡片，透過解析出的 p_start 精準填上空的屬性
                        if p_start != -1:
                            for i in range(len(PROP_HEADERS)): row_data[p_start + i] = "None"
                            
                        unique_rows.append(row_data)
                
                with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    writer.writerow(master_header)
                    writer.writerows(unique_rows)
                    
            finish_cb(True, success, None)
        except PermissionError: finish_cb(False, _("權限不足！請確認 CSV 檔案是否正被 Excel 等軟體開啟中，請關閉後再試。"), traceback.format_exc())
        except Exception as e: finish_cb(False, str(e), traceback.format_exc())

    @staticmethod
    def task_replace(csv_path, root_dir, backup_dir, mod_img_dir, out_folder, progress_cb, finish_cb):
        try:
            out_dir = os.path.join(root_dir, out_folder or "改完的文件")
            os.makedirs(out_dir, exist_ok=True)
            mapping_dict, dummy_db = MDEngine.get_csv_data(csv_path)
            target_bundles = {}
            valid_ids = list(mapping_dict.keys())
            
            for img_name in os.listdir(mod_img_dir):
                if not img_name.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.txt', '.json', '.bytes', '.atlas')): continue
                
                # ✨ 呼叫最長前綴匹配：精準剝離自訂後綴，完美相容場地多貼圖與多重底線
                base_id = MDEngine.find_longest_prefix(img_name, valid_ids)
                dummy_is_cut, clean_base, dummy_req_res = MDEngine.parse_cutin_tag_and_base(base_id)
                
                for test_id in [img_name, os.path.splitext(img_name)[0], base_id, clean_base]:
                    if test_id in mapping_dict:
                        for item in mapping_dict[test_id]: 
                            # 🛡️ 傳遞 img_name 與 mapped_id 的對應關係，取代單純的 list
                            target_bundles.setdefault(item['hash'], {})[img_name] = base_id
                        break
            tasks = [(h, imgs_dict, mod_img_dir, backup_dir, out_dir) for h, imgs_dict in target_bundles.items()]
            success, count = 0, 0
            with concurrent.futures.ProcessPoolExecutor(max_workers=MDEngine.get_optimal_workers(), initializer=_init_worker, initargs=(UI_LANG_DICT,)) as executor:
                futures = [executor.submit(MDEngine._worker_replace_bundle, t) for t in tasks]
                for future in concurrent.futures.as_completed(futures):
                    count += 1
                    if progress_cb and count % 5 == 0: progress_cb(count)
                    try: success += future.result()
                    except Exception: pass
            finish_cb(True, success, out_dir)
        except PermissionError: finish_cb(False, _("權限不足！請確認 CSV 檔案是否正被 Excel 等軟體開啟中，請關閉後再試。"), traceback.format_exc())
        except Exception as e: finish_cb(False, str(e), traceback.format_exc())

    @staticmethod
    def task_package(root_path, mod_name, readme_text, tex_src_folder, pack_zip, csv_path, backup_folder, out_folder, pendulum_backup_name, include_mod, include_readme, csv_filename, progress_cb, finish_cb):
        try:
            out_dir = os.path.join(root_path, mod_name)
            os.makedirs(out_dir, exist_ok=True)
            if include_readme and readme_text:
                with open(os.path.join(out_dir, "ReadMe.txt"), "w", encoding="utf-8") as f: f.write(readme_text)
            hash_to_folder = {}
            if os.path.exists(csv_path):
                mapping, _db = MDEngine.get_csv_data(csv_path)
                for items in mapping.values():
                    for item in items: hash_to_folder[item['hash']] = item['folder']
            def smart_package(src, dst_base, is_backup=False):
                if not os.path.exists(src): return
                # 🛡️ 物理結界：如果來源恰好是準備輸出的目錄，立刻跳過阻止無限迭代
                if MDEngine.is_subpath(src, dst_base) or MDEngine.is_subpath(src, out_dir): return
                for item in os.listdir(src):
                    s = os.path.join(src, item)
                    if os.path.isfile(s) and len(item) >= 2:
                        folder = hash_to_folder.get(item, "0000")
                        t_dir = os.path.join(dst_base, "backup" if is_backup else "", "masterduel_Data", "StreamingAssets", "AssetBundle") if folder == "StreamingAssets" else os.path.join(dst_base, "backup" if is_backup else "", "0000", item[:2].lower())
                        os.makedirs(t_dir, exist_ok=True)
                        shutil.copy2(s, os.path.join(t_dir, item))
                    elif os.path.isdir(s):
                        for sub_item in os.listdir(s):
                            sub_s = os.path.join(s, sub_item)
                            if os.path.isfile(sub_s) and len(sub_item) >= 2:
                                folder = hash_to_folder.get(sub_item, "0000")
                                t_dir = os.path.join(dst_base, "backup" if is_backup else "", "masterduel_Data", "StreamingAssets", "AssetBundle") if folder == "StreamingAssets" else os.path.join(dst_base, "backup" if is_backup else "", "0000", sub_item[:2].lower())
                                os.makedirs(t_dir, exist_ok=True)
                                shutil.copy2(sub_s, os.path.join(t_dir, sub_item))
            smart_package(os.path.join(root_path, backup_folder or "文件備份"), out_dir, True)
            if include_mod:
                smart_package(os.path.join(root_path, out_folder or "改完的文件"), out_dir, False)
            target_csv = os.path.join(root_path, csv_filename)
            if os.path.exists(target_csv):
                try: shutil.copy2(target_csv, os.path.join(out_dir, csv_filename))
                except Exception: pass
            tex_dst = os.path.join(out_dir, "texture")
            if os.path.exists(tex_src_folder):
                if os.path.exists(tex_dst): shutil.rmtree(tex_dst)
                
                # 動態找出備份資料夾 (精準匹配設定名稱，或包含備份特徵關鍵字)
                backup_dirs = []
                for f in os.listdir(tex_src_folder):
                    d_path = os.path.join(tex_src_folder, f)
                    if os.path.isdir(d_path):
                        name_lower = f.lower()
                        if name_lower == pendulum_backup_name.lower() or any(k in name_lower for k in ["原檔", "原本", "backup", "origin"]):
                            backup_dirs.append(f)
                
                # 第一階段：複製所有檔案並忽略備份資料夾，確保基底完整
                def safe_ignore(current_dir, dir_contents):
                    ignored = []
                    # 1. 物理結界防護：如果整個人已經在結界內部，全數忽略
                    if MDEngine.is_subpath(current_dir, tex_dst) or MDEngine.is_subpath(current_dir, out_dir):
                        return dir_contents
                        
                    # 2. 記憶體級過濾：將結界的實體路徑先在迴圈外算好，避免迴圈內頻繁呼叫硬碟 I/O
                    c_real = os.path.normcase(os.path.realpath(current_dir)).rstrip(os.sep)
                    t_real = os.path.normcase(os.path.realpath(tex_dst)).rstrip(os.sep)
                    o_real = os.path.normcase(os.path.realpath(out_dir)).rstrip(os.sep)
                    
                    for item in dir_contents:
                        # 備份資料夾字串比對
                        if item in backup_dirs:
                            ignored.append(item)
                            continue
                            
                        # 純字串拼接比對：完全不觸碰硬碟，效能極致釋放
                        item_real = os.path.join(c_real, os.path.normcase(item))
                        if item_real == t_real or item_real == o_real:
                            ignored.append(item)
                            
                    return ignored
                    
                shutil.copytree(tex_src_folder, tex_dst, ignore=safe_ignore)
                
                # 第二階段：強制將備份資料夾內的高清原始未填充卡圖覆蓋過去
                for b_dir in backup_dirs:
                    p_backup_dir = os.path.join(tex_src_folder, b_dir)
                    for img_name in os.listdir(p_backup_dir):
                        src_img = os.path.join(p_backup_dir, img_name)
                        if os.path.isfile(src_img):
                            try: shutil.copy2(src_img, os.path.join(tex_dst, img_name))
                            except Exception: pass
                            
            if pack_zip: shutil.make_archive(os.path.join(root_path, mod_name), 'zip', out_dir)
            finish_cb(True, 0, out_dir)
        except PermissionError: 
            finish_cb(False, _("權限不足！請確認 CSV 檔案或輸出資料夾是否正被 Excel 等軟體開啟，請關閉後再試。"), traceback.format_exc())
        except Exception as e: 
            finish_cb(False, str(e), traceback.format_exc())

    @staticmethod
    def read_text_file_clean(filepath):
        """文字檔安全讀取器 (DRY核心)：自動清除 UTF-8 BOM 標頭，並具備二進位退回防線"""
        try:
            with open(filepath, "r", encoding="utf-8-sig") as f:
                return f.read()
        except UnicodeDecodeError:
            with open(filepath, "rb") as f:
                return f.read()
        except Exception:
            return ""

    @staticmethod
    def process_texture_image(img, img_name, card_dict, mode, options):
        """
        統一影像處理策略引擎 (Strategy Pipeline)
        嚴格遵守 DRY 與解耦原則：將裁切、相框、填充、拉伸邏輯全數收攏於此。
        """
        w, h = img.size
        c_id_raw = os.path.splitext(img_name)[0].split('_')[0]
        c_id = re.sub(r'-ch$', '', c_id_raw, flags=re.IGNORECASE)
        card_type, sub_type = "怪獸", "通常"
        
        if c_id in card_dict:
            d = card_dict[c_id]
            header, row = d.get('header', []), d.get('full_row', [])
            indices = MDEngine.get_csv_indices(header)
            c_idx, s_idx = indices["type"], indices["subtype"]
            if c_idx != -1 and len(row) > c_idx: card_type = row[c_idx]
            if s_idx != -1 and len(row) > s_idx: sub_type = row[s_idx]

        # 策略 1: 傳統靈擺填充 (自動補透明底)
        if mode == "MODE_PENDULUM_PAD":
            pad_pct = options.get("pad_pct", 25)
            pad_h = int(h * (pad_pct / 100.0))
            new_img = Image.new("RGBA", (w, h + pad_h), (0, 0, 0, 0))
            new_img.paste(img, (0, 0))
            return new_img
            
        # 策略 2: 靈擺原卡圖處理 (橫向拉伸 1.25 倍並裁切頂部正方形)
        if mode == "MODE_PENDULUM_ORIGINAL_CROP":
            new_w = int(w * 1.25)
            img = img.resize((new_w, h), Image.Resampling.LANCZOS)
            img = img.crop((0, 0, new_w, min(new_w, h))) # 1:1 正方形裁切
            return img
            
        # 策略 3: 視覺配件自適應縮放 (保護高畫質，僅在大小不合時縮放)
        if mode == "MODE_FIT_VISUAL":
            target_w, target_h = options.get("target_size", (w, h))
            if (w, h) != (target_w, target_h):
                img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
            return img

        # 策略 4: 超框化處理 (11:16 裁切與相框疊加)
        if mode == "MODE_OVERFRAME":
            frame_name = MDEngine.get_frame_template_name(card_type, sub_type)
            frame_dir = os.path.join(os.getcwd(), "MD_Tool_Essential", "CardFrame")
            psd_path = os.path.join(frame_dir, f"{frame_name}.psd")
            png_path = os.path.join(frame_dir, f"{frame_name}.png")
            
            try: from psd_tools import PSDImage; HAS_PSD_TOOLS = True
            except ImportError: HAS_PSD_TOOLS = False
            
            opacities = options.get("opacities", {})
            frame_layers = {}
            raw_masks = {} # 儲存純淨布林幾何遮罩
            
            if HAS_PSD_TOOLS and os.path.exists(psd_path):
                if frame_name not in MDEngine._psd_cache:
                    psd = PSDImage.open(psd_path)
                    layer_dict = {}
                    for layer in psd.descendants():
                        if layer.is_group(): continue
                        name = layer.name.strip()
                        if name in ["PeriFrame", "NameBox", "ArtFrame", "EffFrame", "EffBox", "BackGround"]:
                            layer_img = layer.composite().convert("RGBA")
                            full_canvas = Image.new("RGBA", psd.size, (0, 0, 0, 0))
                            full_canvas.paste(layer_img, layer.offset)
                            layer_dict[name] = full_canvas
                    MDEngine._psd_cache[frame_name] = layer_dict
                
                import numpy as np # 提前引入供 mask 提取使用
                for l_name, l_img in MDEngine._psd_cache[frame_name].items():
                    resized = l_img.resize((704, 1024), Image.Resampling.LANCZOS)
                    # 提取純淨幾何遮罩
                    raw_masks[l_name] = (np.array(resized, dtype=np.uint8)[:, :, 3] > 0)
                    
                    op = opacities.get(l_name.lower(), 1.0)
                    if op > 0:
                        if op < 1.0:
                            r_ch, g_ch, b_ch, a_ch = resized.split()
                            a_ch = a_ch.point(lambda p: int(p * op))
                            resized = Image.merge("RGBA", (r_ch, g_ch, b_ch, a_ch))
                        frame_layers[l_name] = resized

            # 🛡️【階段 1：幾何純化 (Sanitization)】
            m_effbox = raw_masks.get("EffBox", np.zeros((1024, 704), dtype=bool))
            if "ArtFrame" in raw_masks:
                raw_masks["ArtFrame"] = raw_masks["ArtFrame"] & ~m_effbox
            if "EffFrame" in raw_masks:
                raw_masks["EffFrame"] = raw_masks["EffFrame"] & ~m_effbox

            masks = options.get("masks", {})
            if not masks:
                masks = {
                    "prev": {"PeriFrame": True, "ArtFrame": True, "EffFrame": True},
                    "bake": {"PeriFrame": False, "ArtFrame": False, "EffFrame": False},
                    "dirty": {"PeriFrame": True, "ArtFrame": True, "EffFrame": True}
                }
            prev_dict = masks.get("prev", {})
            bake_dict = masks.get("bake", {})
            dirty_dict = masks.get("dirty", {})
            
            is_preview = options.get("is_preview", False)
            foil_params = options.get("foil_params", {})
            sim_enable = foil_params.get("sim_enable", False)

            # --- 🚀 階段 2：底層貼圖真相 (Bake) ---
            # 嚴格只看「寫入貼圖 (Bake)」勾選，將 RGB 永久烙印進底層組件
            for l_name, layer_img in frame_layers.items():
                if bake_dict.get(l_name, False):
                    layer_mask = raw_masks.get(l_name, np.zeros((1024, 704), dtype=bool))
                    frame_layers[l_name] = MDEngine._simulate_foil(layer_img, layer_mask, foil_params, use_alpha_weight=True)

            # --- 🚀 階段 3：圖層 Z-Order 幾何合成 ---
            # 取出共用的排序邏輯，統一單圖與雙圖的 Z-Order 系統
            z_order = options.get("z_order", ["CH_LAYER", "PeriFrame", "NameBox", "EffFrame", "ArtFrame", "EffBox", "BackGround", "BG_LAYER"])
            
            if options.get("is_advanced", False):
                adv_bg_path = options.get("adv_bg_path", "")
                if adv_bg_path and os.path.exists(adv_bg_path):
                    with Image.open(adv_bg_path) as bg_raw:
                        layer_bg = MDEngine._apply_adv_transform(bg_raw.convert("RGBA"), options.get("bg_x", 0), options.get("bg_y", 0), options.get("bg_s", 100), options.get("bg_rot", 0))
                else:
                    hex_str = options.get("bg_color", "#FF000000").lstrip('#')
                    if len(hex_str) == 8:
                        a, r_c, g_c, b_c = int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16), int(hex_str[6:8], 16)
                    elif len(hex_str) == 6:
                        a, r_c, g_c, b_c = 255, int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16)
                    else:
                        a, r_c, g_c, b_c = 255, 0, 0, 0
                    layer_bg = Image.new("RGBA", (704, 1024), (r_c, g_c, b_c, a))

                layer_ch = MDEngine._apply_adv_transform(img, options.get("ch_x", 0), options.get("ch_y", 0), options.get("ch_s", 100), options.get("ch_rot", 0))
                base_art_layer = layer_ch
            else:
                # 傳統單圖自適應縮放
                if w < 704 or h < 1024:
                    ratio = max(704.0 / w, 1024.0 / h)
                    new_w, new_h = int(w * ratio), int(h * ratio)
                    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    w, h = img.size 
                    
                target_ratio = 11 / 16.0
                current_ratio = w / h
                if current_ratio > target_ratio:
                    new_w = int(h * target_ratio)
                    left = (w - new_w) // 2
                    img = img.crop((left, 0, left + new_w, h))
                elif current_ratio < target_ratio:
                    new_h = int(w / target_ratio)
                    img = img.crop((0, 0, w, new_h))

                base_art_layer = img.resize((704, 1024), Image.Resampling.LANCZOS)
                layer_bg = base_art_layer  # 將普通單圖指派給最底層 (BG_LAYER)
                layer_ch = Image.new("RGBA", (704, 1024), (0,0,0,0))  # 頂層角色層 (CH_LAYER) 保持全透明

            new_img = Image.new("RGBA", (704, 1024), (0,0,0,0))
            for l_name in reversed(z_order):
                if l_name == "BG_LAYER": new_img = Image.alpha_composite(new_img, layer_bg)
                elif l_name == "CH_LAYER": new_img = Image.alpha_composite(new_img, layer_ch)
                elif l_name in frame_layers:
                    resized_frame = frame_layers[l_name].resize(new_img.size, Image.Resampling.LANCZOS)
                    new_img = Image.alpha_composite(new_img, resized_frame)

            # --- 🚀 階段 4：透明通道判定 (Dirty Alpha & Character Punch) ---
            try:
                import numpy as np
                data = np.array(new_img, dtype=np.uint8)
                m_ch_art = np.array(base_art_layer, dtype=np.uint8)[:, :, 3] > 0
                
                empty_mask = np.zeros((1024, 704), dtype=bool)
                m_explicit_dirty = np.zeros((1024, 704), dtype=bool)
                m_3frames_clean = np.zeros((1024, 704), dtype=bool)

                for fname in ["PeriFrame", "NameBox", "ArtFrame", "EffFrame", "EffBox", "BackGround"]:
                    layer_mask = raw_masks.get(fname, empty_mask)
                    # 軌道 B：使用者手動勾選透明化，直接生效，完全不受烘焙勾選干擾
                    if dirty_dict.get(fname, False):
                        m_explicit_dirty |= layer_mask
                    # 純淨三大框 (供角色 -ch 超框交集挖空使用)
                    if fname in ["PeriFrame", "ArtFrame", "EffFrame"]:
                        m_3frames_clean |= layer_mask
                    
                # 軌道 A：只有使用 -ch 角色圖層時，才強制自動觸發「角色超框交集挖空」
                if options.get("is_advanced", False):
                    m_character_punch = m_ch_art & m_3frames_clean
                else:
                    m_character_punch = empty_mask
                
                # 最終 Alpha 歸零遮罩 = 角色超框挖空 ∪ 使用者手動整塊挖空
                m_final_zero = m_character_punch | m_explicit_dirty

                # --- 🚀 階段 5：分支輸出與頂層著色器模擬 ---
                if is_preview:
                    if sim_enable:
                        m_shine_preview = np.zeros((1024, 704), dtype=bool)
                        for fname in ["PeriFrame", "NameBox", "ArtFrame", "EffFrame", "EffBox", "BackGround"]:
                            if prev_dict.get(fname, False):
                                m_shine_preview |= raw_masks.get(fname, empty_mask)
                                
                        # 扣除 Alpha 為 0 的挖空區域，模擬遊戲真實 3D 著色器行為
                        m_shine_top = m_shine_preview & ~m_final_zero
                        
                        if np.any(m_shine_top):
                            prev_img = Image.fromarray(data, "RGBA")
                            prev_img = MDEngine._simulate_foil(prev_img, m_shine_top, foil_params, use_alpha_weight=False)
                            data = np.array(prev_img, dtype=np.uint8)
                            
                    # 預覽畫面強制將背景設為不透明，以防 Qt 渲染黑塊，但光斑已經完美避開了透明挖空區
                    data[:, :, 3] = 255
                    new_img = Image.fromarray(data, "RGBA")
                else:
                    # 實際輸出：精準寫入透明化遮罩
                    data[m_final_zero, 3] = 0
                    new_img = Image.fromarray(data, "RGBA")
                    
            except ImportError:
                pass
            
            return new_img
        return img

    @staticmethod
    def task_generate_preview(img_path, csv_path, mode, pad_pct, options_dict, progress_cb, finish_cb):
        try:
            dummy_map, db = MDEngine.get_csv_data(csv_path)
            card_dict = {d['id']: d for d in db}
            img_name = os.path.basename(img_path)
            with Image.open(img_path) as img:
                img = img.convert("RGBA")
                strategy_mode = "MODE_PENDULUM_PAD" if mode == "pendulum" else "MODE_OVERFRAME"
                
                options = {"pad_pct": pad_pct}
                if "opacities" in options_dict: options.update(options_dict)
                else: options["opacities"] = options_dict

                is_advanced = "-ch" in img_name.lower()
                options["is_advanced"] = is_advanced
                if is_advanced:
                    img_dir = os.path.dirname(img_path)
                    bg_base = re.sub(r'-ch$', '-bg', os.path.splitext(img_name)[0], flags=re.IGNORECASE)
                    bg_path = ""
                    search_dirs = [img_dir, os.path.dirname(img_dir), os.path.join(img_dir, "修改前原檔")]
                    for d in search_dirs:
                        if not os.path.exists(d): continue
                        for ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp"]:
                            cand = os.path.join(d, f"{bg_base}{ext}")
                            if os.path.exists(cand):
                                bg_path = cand; break
                        if bg_path: break
                    options["adv_bg_path"] = bg_path

                res_img = MDEngine.process_texture_image(img, img_name, card_dict, strategy_mode, options)
                
                # 轉化為 QImage 提供給 UI
                data = res_img.tobytes("raw", "RGBA")
                
                # 🛡️ 致命閃退修復 1：加上 res_img.width * 4 (bytesPerLine) 確保記憶體對齊
                qimg = QImage(data, res_img.width, res_img.height, res_img.width * 4, QImage.Format_RGBA8888).copy()
                finish_cb(True, qimg, None)
        except Exception as e:
            finish_cb(False, str(e), None)

    @staticmethod
    def _apply_adv_transform(img, dx, dy, scale_pct, rot_deg):
        w_orig, h_orig = img.size
        s_base = min(704.0 / w_orig, 1024.0 / h_orig)
        w_fit = max(1, int(round(w_orig * s_base * (scale_pct / 100.0))))
        h_fit = max(1, int(round(h_orig * s_base * (scale_pct / 100.0))))
        
        resized = img.resize((w_fit, h_fit), Image.Resampling.LANCZOS)
        if rot_deg != 0:
            resized = resized.rotate(-rot_deg, resample=Image.Resampling.BICUBIC, expand=True)
            
        w_rot, h_rot = resized.size
        x_paste = int(round((704 - w_rot) / 2.0)) + dx
        y_paste = int(round((1024 - h_rot) / 2.0)) + dy
        
        canvas = Image.new("RGBA", (704, 1024), (0, 0, 0, 0))
        canvas.paste(resized, (x_paste, y_paste), resized)
        return canvas

    @staticmethod
    def _simulate_foil(img, m_shine_mask, params, use_alpha_weight=False):
        try:
            import numpy as np
            import math
            data = np.array(img, dtype=np.float32)
            m_shine = np.asarray(m_shine_mask, dtype=bool)
            params = params or {}
            
            # 取得基礎參數與進階光學參數
            intensity = max(0.0, float(params.get("intensity", 100)) / 100.0)
            saturation = max(0.0, float(params.get("saturation", 120)) / 100.0)
            frequency = max(0.0001, float(params.get("frequency", 10.0)) / 5000.0)
            angle = float(params.get("angle", 45))
            rad = math.radians(angle % 360.0)
            
            palette_mode = params.get("palette", "PALETTE_OPAL")
            base_light = float(params.get("base_light", 40)) / 100.0
            sharpness = max(1.0, float(params.get("sharpness", 10)) / 10.0)
            blend_mode = params.get("blend_mode", "BLEND_SOFT")
            
            h, w = data.shape[:2]
            Y, X = np.ogrid[:h, :w]
            G = (X * math.cos(rad) + Y * math.sin(rad)) * frequency
            
            # 餘弦光譜調變 (IQ Cosine Palette) 基準化至 0.0~1.0 確保不泛白
            if palette_mode == "PALETTE_RAINBOW":
                pa, pb, pc, pd = (0.5, 0.5, 0.5), (0.5, 0.5, 0.5), (1.0, 1.0, 1.0), (0.0, 0.333, 0.667)
            elif palette_mode == "PALETTE_GOLD":
                pa, pb, pc, pd = (0.5, 0.5, 0.5), (0.5, 0.5, 0.2), (1.0, 1.0, 1.0), (0.0, 0.1, 0.2)
            elif palette_mode == "PALETTE_SILVER":
                pa, pb, pc, pd = (0.5, 0.5, 0.5), (0.2, 0.2, 0.3), (1.0, 1.0, 1.0), (0.5, 0.5, 0.5)
            else: # PALETTE_OPAL (柔和珍珠粉彩)
                pa, pb, pc, pd = (0.5, 0.5, 0.5), (0.4, 0.4, 0.4), (1.0, 1.0, 1.0), (0.0, 0.333, 0.667)

            def cos_color(t_val, a, b, c_val, d):
                return a + b * np.cos(2.0 * math.pi * (c_val * t_val + d))

            r_wave = cos_color(G, pa[0], pb[0], pc[0], pd[0])
            g_wave = cos_color(G, pa[1], pb[1], pc[1], pd[1])
            b_wave = cos_color(G, pa[2], pb[2], pc[2], pd[2])

            # 階段 1：色彩飽和度增益 (在純淨波形上作用)
            r_foil = np.clip((r_wave - 0.5) * saturation + 0.5, 0.0, 1.0)
            g_foil = np.clip((g_wave - 0.5) * saturation + 0.5, 0.0, 1.0)
            b_foil = np.clip((b_wave - 0.5) * saturation + 0.5, 0.0, 1.0)

            # 階段 2：高光銳利化 (聚焦光弧) - 採用亮度權重法，保護色相不偏移
            if sharpness > 1.0:
                lum = 0.299 * r_foil + 0.587 * g_foil + 0.114 * b_foil
                lum_shaped = np.power(lum, sharpness)
                ratio = np.where(lum > 0, lum_shaped / lum, 0)
                r_foil = np.clip(r_foil * ratio, 0.0, 1.0)
                g_foil = np.clip(g_foil * ratio, 0.0, 1.0)
                b_foil = np.clip(b_foil * ratio, 0.0, 1.0)

            # 階段 3：底色珠光調變 (線性混入粉白基底)
            r_foil = base_light + (1.0 - base_light) * r_foil
            g_foil = base_light + (1.0 - base_light) * g_foil
            b_foil = base_light + (1.0 - base_light) * b_foil

            # 卡面原色提取
            r = data[:, :, 0] / 255.0
            g = data[:, :, 1] / 255.0
            b = data[:, :, 2] / 255.0
            
            actual_intensity = intensity
            if use_alpha_weight:
                alpha_ratio = data[:, :, 3] / 255.0
                actual_intensity = intensity * alpha_ratio[m_shine]
            
            base_intensity = np.minimum(1.0, actual_intensity)
            overdrive = np.maximum(0.0, actual_intensity - 1.0)
            
            # 階段 4：雙軌混色系統 (柔光滲透 vs 鮮明覆蓋)
            if blend_mode == "BLEND_SOFT":
                # Pegtop 柔光公式 (保留底層凹凸紋理與深色輪廓)
                r_soft = (1.0 - 2.0 * r_foil[m_shine]) * (r[m_shine] ** 2) + 2.0 * r[m_shine] * r_foil[m_shine]
                g_soft = (1.0 - 2.0 * g_foil[m_shine]) * (g[m_shine] ** 2) + 2.0 * g[m_shine] * g_foil[m_shine]
                b_soft = (1.0 - 2.0 * b_foil[m_shine]) * (b[m_shine] ** 2) + 2.0 * b[m_shine] * b_foil[m_shine]

                res_r = r[m_shine] * (1.0 - base_intensity) + r_soft * base_intensity + (r_foil[m_shine] * overdrive)
                res_g = g[m_shine] * (1.0 - base_intensity) + g_soft * base_intensity + (g_foil[m_shine] * overdrive)
                res_b = b[m_shine] * (1.0 - base_intensity) + b_soft * base_intensity + (b_foil[m_shine] * overdrive)
            else:
                # 傳統濾色 (螢幕疊加) + 高光過驅 (強烈雷射感)
                res_r = 1.0 - (1.0 - r[m_shine]) * (1.0 - r_foil[m_shine] * base_intensity) + (r_foil[m_shine] * overdrive)
                res_g = 1.0 - (1.0 - g[m_shine]) * (1.0 - g_foil[m_shine] * base_intensity) + (g_foil[m_shine] * overdrive)
                res_b = 1.0 - (1.0 - b[m_shine]) * (1.0 - b_foil[m_shine] * base_intensity) + (b_foil[m_shine] * overdrive)
            
            # 原地布林遮罩覆寫與溢出防護 (Tone Mapping)
            data[m_shine, 0] = np.clip(res_r * 255.0, 0.0, 255.0)
            data[m_shine, 1] = np.clip(res_g * 255.0, 0.0, 255.0)
            data[m_shine, 2] = np.clip(res_b * 255.0, 0.0, 255.0)
            
            return Image.fromarray(data.astype(np.uint8), 'RGBA')
        except ImportError:
            return img

    _psd_cache = {}

    @staticmethod
    def _worker_post_process_single(task_info):
        target_id, mod_img_dir, backup_dir, enable_backup, strategy_mode, options, card_mini_dict = task_info
        
        # 呼叫集中解析器
        ch_path, bg_path, is_advanced = MDEngine.resolve_overframe_material_path(mod_img_dir, backup_dir, target_id)
        
        if not ch_path:
            return target_id, False, _("找不到指定的圖片素材")
            
        options["is_advanced"] = is_advanced
        options["adv_bg_path"] = bg_path
        
        dummy_name, ext = os.path.splitext(ch_path)
        base_name = re.sub(r'-(ch|bg)$', '', os.path.splitext(target_id)[0], flags=re.IGNORECASE)
        out_img_name = f"{base_name}{ext}"
        img_name = os.path.basename(ch_path)
        
        try:
            backup_img_path = os.path.join(backup_dir, img_name)
            source_to_read = ch_path
            
            # 若備份檔案不存在且啟用備份，則執行搬移/複製
            if enable_backup and os.path.dirname(ch_path) == mod_img_dir:
                shutil.copy2(ch_path, backup_img_path)
                if bg_path and os.path.dirname(bg_path) == mod_img_dir:
                    shutil.copy2(bg_path, os.path.join(backup_dir, os.path.basename(bg_path)))
            
            with Image.open(source_to_read) as raw_img:
                img_rgba = raw_img.convert("RGBA")
                new_img = MDEngine.process_texture_image(img_rgba, out_img_name, card_mini_dict, strategy_mode, options)
                
            out_img_path = os.path.join(mod_img_dir, out_img_name)
            temp_path = f"{out_img_path}_tmp.png"
            new_img.save(temp_path, format="PNG")
            os.replace(temp_path, out_img_path)
            
            # 清理原始的 -ch 與 -bg (非破壞性生命週期，已備份)
            if is_advanced and enable_backup:
                if os.path.dirname(ch_path) == mod_img_dir:
                    try: os.remove(ch_path)
                    except Exception: pass
                if bg_path and os.path.dirname(bg_path) == mod_img_dir:
                    try: os.remove(bg_path)
                    except Exception: pass
            
            if new_img is not img_rgba:
                img_rgba.close()
                
            new_img.close()
            import gc
            gc.collect()
            
            return out_img_name, True, None
        except Exception as e:
            import traceback
            return target_id, False, f"{str(e)}\n{traceback.format_exc()}"

    @staticmethod
    def task_post_process(mod_img_dir, backup_dir, enable_backup, pad_pct, targets, mode, csv_path, options_dict, progress_cb, finish_cb):
        try:
            if enable_backup: os.makedirs(backup_dir, exist_ok=True)
            dummy_map, db = MDEngine.get_csv_data(csv_path)
            card_dict = {d['id']: d for d in db}

            tasks = []
            for raw_target in targets:
                if re.search(r'-bg\.(png|jpg|jpeg|webp|bmp)$', raw_target, re.IGNORECASE): continue
                c_id_raw = os.path.splitext(raw_target)[0].split('_')[0]
                c_id = re.sub(r'-(ch|bg)$', '', c_id_raw, flags=re.IGNORECASE)
                card_mini_dict = {c_id: card_dict[c_id]} if c_id in card_dict else {}
                
                if mode == "pendulum": strategy_mode = "MODE_PENDULUM_PAD"
                elif mode == "pendulum_orig": strategy_mode = "MODE_PENDULUM_ORIGINAL_CROP"
                else: strategy_mode = "MODE_OVERFRAME"
                
                options = {"pad_pct": pad_pct}
                if "opacities" in options_dict: options.update(options_dict)
                else: options["opacities"] = options_dict
                
                # 直接將 target 傳給 Worker，由 Worker 調用 resolve_overframe_material_path 判定
                tasks.append((raw_target, mod_img_dir, backup_dir, enable_backup, strategy_mode, options, card_mini_dict))

            success, count = 0, 0
            errors = []
            with concurrent.futures.ProcessPoolExecutor(max_workers=MDEngine.get_optimal_workers(), initializer=_init_worker, initargs=(UI_LANG_DICT,)) as executor:
                futures = [executor.submit(MDEngine._worker_post_process_single, t) for t in tasks]
                for future in concurrent.futures.as_completed(futures):
                    count += 1
                    if progress_cb: progress_cb(count)
                    try: 
                        tgt_name, is_ok, err_msg = future.result()
                        if is_ok: success += 1
                        else: errors.append(f"{tgt_name}: {err_msg}")
                    except Exception as e: 
                        errors.append(_("處理失敗: {error}").format(error=str(e)))

            # 🛡️ 將收集到的錯誤字串往上拋
            err_report = "\n".join(errors) if errors else None
            finish_cb(True, success, err_report)
        except Exception as e: 
            finish_cb(False, str(e), traceback.format_exc())

    @staticmethod
    def task_quick_replace(target_id, csv_path, src_dir, out_root, img_path, overwrite, backup_folder, out_folder, progress_cb, finish_cb):
        try:
            mapping, _db = MDEngine.get_csv_data(csv_path)
            if target_id not in mapping: raise Exception(_("CSV 中找不到 ID: {id}").format(id=target_id))
            success, count = 0, 0
            for item in mapping[target_id]:
                hash_name, folder = item['hash'], item['folder']
                count += 1
                if progress_cb: progress_cb(count)
                src_file = MDEngine.get_actual_source_path(src_dir, hash_name, folder)
                if not os.path.exists(src_file): continue
                if folder == "StreamingAssets":
                    tgt_backup = os.path.join(out_root, backup_folder or "文件備份", "masterduel_Data", "StreamingAssets", "AssetBundle")
                    tgt_modded = os.path.join(out_root, out_folder or "改完的文件", "masterduel_Data", "StreamingAssets", "AssetBundle")
                else:
                    hash_prefix = hash_name[:2].lower()
                    tgt_backup = os.path.join(out_root, backup_folder or "文件備份", "0000", hash_prefix)
                    tgt_modded = os.path.join(out_root, out_folder or "改完的文件", "0000", hash_prefix)
                os.makedirs(tgt_backup, exist_ok=True)
                os.makedirs(tgt_modded, exist_ok=True)
                backup_file = os.path.join(tgt_backup, hash_name)
                modded_file = os.path.join(tgt_modded, hash_name)
                if not os.path.exists(backup_file): shutil.copy2(src_file, backup_file)
                
                env = None
                try:
                    env = UnityPy.load(src_file)
                    
                    # ✨ 呼叫 DRY 核心注入器
                    modded_flag = MDEngine._inject_texture_core(env, target_id, img_path)
                    
                    if modded_flag:
                        MDEngine.safe_write_bytes(modded_file, env.file.save()) # 🛡️ 套用原子化寫入
                        if overwrite: MDEngine.safe_copy_file(modded_file, src_file) # 🛡️ 套用原子化覆寫
                        success += 1
                except Exception: pass
                finally:
                    if env: del env
                    
            finish_cb(True, success, None)
        except PermissionError:
            finish_cb(False, _("權限不足！請確認資料來源、目標資料夾或圖片是否被系統保護，或嘗試使用系統管理員權限執行。"), traceback.format_exc())
        except Exception as e: 
            finish_cb(False, str(e), traceback.format_exc())

    @staticmethod
    def task_stream_update(old_mod_dir, clean_src_dir, out_root, overwrite, progress_cb, finish_cb):
        try:
            success, count = 0, 0
            out_base = old_mod_dir if overwrite else os.path.join(out_root, "FIXED_MOD")
            
            tasks = []
            exclude_paths = [out_base] if not overwrite else []
            # 🛡️ 防護：將所有 _dirs 替換為 dirs_list，絕對杜絕底線變數污染
            for root, dirs_list, files in os.walk(old_mod_dir):
                MDEngine.prune_walk_dirs(root, dirs_list, exclude_paths)
                for f in files:
                    if not f.lower().endswith(('.png', '.jpg', '.txt', '.csv', '.json', '.bytes')):
                        tasks.append((root, f, clean_src_dir, out_base, overwrite, old_mod_dir))
            
            errors = []
            with concurrent.futures.ProcessPoolExecutor(max_workers=MDEngine.get_heavy_task_workers(), initializer=_init_worker, initargs=(UI_LANG_DICT,)) as executor:
                for res, err in executor.map(MDEngine._worker_stream_update_single, tasks, chunksize=1):
                    count += 1
                    success += res
                    if err: errors.append(err)
                    if progress_cb and count % 5 == 0: progress_cb(count)
                    
            if errors:
                os.makedirs(out_base, exist_ok=True)
                with open(os.path.join(out_base, "stream_update_error.log"), "w", encoding="utf-8") as f:
                    f.write("\n".join(errors))
                    
            finish_cb(True, success, out_base)
        except Exception as e: 
            finish_cb(False, str(e), traceback.format_exc())

    @staticmethod
    def get_data_unity3d_safe(game_0000):
        """智慧反推 data.unity3d 的實體路徑"""
        norm = os.path.normpath(game_0000)
        parts = norm.split(os.sep)
        ld_idx = next((i for i, p in enumerate(parts) if p.lower() == "localdata"), -1)
        if ld_idx != -1: return os.path.join(os.sep.join(parts[:ld_idx]), "masterduel_Data", "data.unity3d")
        return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(norm))), "masterduel_Data", "data.unity3d")

    @staticmethod
    def get_sa_dir_safe(game_0000):
        """🛡️ 智慧反推 StreamingAssets/AssetBundle 的實體路徑"""
        norm = os.path.normpath(game_0000)
        parts = norm.split(os.sep)
        ld_idx = next((i for i, p in enumerate(parts) if p.lower() == "localdata"), -1)
        if ld_idx != -1:
            return os.path.join(os.sep.join(parts[:ld_idx]), "masterduel_Data", "StreamingAssets", "AssetBundle")
        # 降級備用：如果找不到 LocalData，直接往上推三層尋找
        return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(norm))), "masterduel_Data", "StreamingAssets", "AssetBundle")

    @staticmethod
    def _inject_texture_core(env, target_name, img_path):
        """DRY 核心注入器：共用的貼圖與文字替換邏輯，回傳是否成功修改"""
        modded_flag = False
        is_text_file = img_path.lower().endswith(('.txt', '.json', '.bytes'))
        
        txt_content = None
        clean_m_name = ""
        req_res_tag = ""
        
        if is_text_file:
            txt_content = MDEngine.read_text_file_clean(img_path)
            if not txt_content: return False
            file_name = os.path.basename(img_path)
            
            # ✨ 呼叫修復後的 DRY 輔助函式，它已經會自動處理剝離副檔名的動作了
            dummy_is_cut, clean_m_name, req_res_tag = MDEngine.parse_cutin_tag_and_base(file_name)

        # 優先搜尋 container (適用於常規 0000 檔案與部分大廳資源)
        for path, obj in env.container.items():
            if is_text_file and obj.type.name == "TextAsset":
                data = obj.read()
                obj_name = str(getattr(data, "m_Name", getattr(data, "name", "")))
                
                # ✨ 雙向同化比對
                norm_obj = MDEngine.normalize_string(obj_name)
                norm_clean = MDEngine.normalize_string(clean_m_name)
                norm_target = MDEngine.normalize_string(target_name)
                
                if (norm_obj == norm_clean or norm_obj == norm_target) and (not req_res_tag or req_res_tag in path.lower()):
                    if isinstance(data.m_Script, bytes) and isinstance(txt_content, str):
                        data.m_Script = txt_content.encode("utf-8")
                    elif isinstance(data.m_Script, str) and isinstance(txt_content, bytes):
                        data.m_Script = txt_content.decode("utf-8", errors="ignore")
                    else:
                        data.m_Script = txt_content
                    data.save()
                    modded_flag = True
            
            elif not is_text_file and obj.type.name == "Texture2D":
                name_key = path.split('/')[-1].replace('.bmp', '').replace('.png', '')
                base_id = re.sub(r'_(l|m|s|128|256|512)$', "", name_key, flags=re.IGNORECASE)
                
                is_cutin_img, cutin_img_id = MDEngine.is_cutin_asset(path, "Texture2D", name_key)
                lookup_id = cutin_img_id if is_cutin_img else base_id
                
                if lookup_id == target_name or name_key.lower() == target_name.lower():
                    try:
                        data = obj.read()
                        with Image.open(img_path) as mod_img:
                            options = {"target_size": (data.image.width, data.image.height)}
                            strategy = "MODE_FIT_VISUAL" if (MDEngine.is_visual_asset(lookup_id) or target_name == "ShopBGBase02") else "NONE"
                            mod_img = MDEngine.process_texture_image(mod_img, lookup_id, {}, strategy, options)
                            data.image = mod_img
                            # ✨ 核心修正：單點防護隔離，僅對 Cut-In 動畫修復色彩空間
                            if is_cutin_img and hasattr(data, "m_ColorSpace"):
                                data.m_ColorSpace = 0
                            data.save()
                            modded_flag = True
                    except Exception: pass

        # 若 container 找不到，備用掃描 objects (防呆，確保特殊根目錄資產也能命中)
        if not modded_flag:
            for obj in env.objects:
                if is_text_file and obj.type.name == "TextAsset":
                    try:
                        data = obj.read()
                        obj_name = str(getattr(data, "m_Name", getattr(data, "name", "")))
                        
                        # ✨ 雙向同化比對
                        norm_obj = MDEngine.normalize_string(obj_name)
                        norm_clean = MDEngine.normalize_string(clean_m_name)
                        norm_target = MDEngine.normalize_string(target_name)
                        
                        if norm_obj == norm_clean or norm_obj == norm_target:
                            if isinstance(data.m_Script, bytes) and isinstance(txt_content, str):
                                data.m_Script = txt_content.encode("utf-8")
                            elif isinstance(data.m_Script, str) and isinstance(txt_content, bytes):
                                data.m_Script = txt_content.decode("utf-8", errors="ignore")
                            else:
                                data.m_Script = txt_content
                            data.save()
                            modded_flag = True
                    except Exception: pass

                elif not is_text_file and obj.type.name == "Texture2D":
                    try:
                        data = obj.read()
                        obj_name = getattr(data, "m_Name", getattr(data, "name", ""))
                        if str(obj_name) == target_name:
                            with Image.open(img_path) as mod_img:
                                options = {"target_size": (data.image.width, data.image.height)}
                                mod_img = MDEngine.process_texture_image(mod_img, str(obj_name), {}, "MODE_FIT_VISUAL", options)
                                data.image = mod_img
                                # ✨ 核心修正：使用正則防護，確保備用掃描時僅對 P 編號動畫修復色彩空間
                                if re.match(r'^p\d+', str(obj_name), re.IGNORECASE) and hasattr(data, "m_ColorSpace"):
                                    data.m_ColorSpace = 0
                                data.save()
                                modded_flag = True
                    except Exception: pass

        return modded_flag

    @staticmethod
    def task_direct_replace(target_file_path, target_texture_name, out_root, img_path, overwrite, backup_folder, out_folder, progress_cb, finish_cb):
        """裸檔流向引擎：專門處理 data.unity3d 等不需要深層目錄結構的單一大檔"""
        try:
            if not os.path.exists(target_file_path):
                return finish_cb(False, _("找不到目標檔案：\n{path}").format(path=target_file_path), None)
            
            # 裸檔備份設定 (不建立 0000 等子目錄)
            tgt_backup = os.path.join(out_root, backup_folder or "文件備份")
            tgt_modded = os.path.join(out_root, out_folder or "改完的文件")
            os.makedirs(tgt_backup, exist_ok=True)
            os.makedirs(tgt_modded, exist_ok=True)
            
            file_name = os.path.basename(target_file_path)
            backup_file = os.path.join(tgt_backup, file_name)
            modded_file = os.path.join(tgt_modded, file_name)
            
            if not os.path.exists(backup_file): 
                shutil.copy2(target_file_path, backup_file)
            
            if progress_cb: progress_cb(50)
            
            env = None
            try:
                env = UnityPy.load(target_file_path)
                modded_flag = MDEngine._inject_texture_core(env, target_texture_name, img_path)
            
                if modded_flag:
                    MDEngine.safe_write_bytes(modded_file, env.file.save()) # 🛡️ 套用原子化寫入
                    import gc
                    gc.collect() 
                    if overwrite: 
                        MDEngine.safe_copy_file(modded_file, target_file_path) # 🛡️ 套用原子化覆寫
                    finish_cb(True, 1, None)
                else:
                    finish_cb(False, _("在檔案中找不到目標貼圖：{name}").format(name=target_texture_name), None)
            finally:
                if env: del env
        except PermissionError:
            finish_cb(False, _("權限不足！請確認檔案是否被遊戲佔用，請關閉遊戲後再試。"), traceback.format_exc())
        except Exception as e:
            finish_cb(False, str(e), traceback.format_exc())

    @staticmethod
    def t11_save_state(state_dict):
        try:
            with open("symlink_state.json", "w", encoding="utf-8") as f: json.dump(state_dict, f, ensure_ascii=False, indent=2)
        except Exception: pass
        
    @staticmethod
    def t11_load_state():
        if os.path.exists("symlink_state.json"):
            try:
                with open("symlink_state.json", "r", encoding="utf-8") as f: return json.load(f)
            except Exception: pass
        return {}

    @staticmethod
    def task_virtual_mount(mod_root, game_0000, active_mods, max_depth, ignore_list, log_cb, progress_cb, finish_cb):
        state_log = {}
        try:
            game_sa = MDEngine.get_sa_dir_safe(game_0000)
            link_map = {}
            def scan_files(src_folder, dest_root, base_mod_name):
                for root, dummy_dirs, files in os.walk(src_folder):
                    for f in files:
                        src_file = os.path.join(root, f)
                        rel = os.path.relpath(src_file, src_folder)
                        if dest_root.endswith("AssetBundle") and rel.lower().startswith("assetbundle"):
                            parts = os.path.normpath(rel).split(os.sep)
                            rel = os.path.join(*parts[1:]) if len(parts) > 1 else parts[0]
                        game_target = os.path.normpath(os.path.join(dest_root, rel))
                        if game_target in link_map and log_cb: log_cb(_("⚠️ 衝突覆蓋: {file} (由 {mod} 覆寫)").format(file=f, mod=base_mod_name))
                        link_map[game_target] = src_file

            def smart_scan(base_mod_dir, current_dir, current_depth):
                if current_depth > max_depth: return
                try: items = os.listdir(current_dir)
                except Exception: return
                for item in items:
                    path = os.path.join(current_dir, item)
                    if not os.path.isdir(path): continue
                    name_lower = item.lower()
                    if name_lower in ignore_list or any(x in name_lower for x in ["backup", "original", "vanilla", "原檔", "文件備份"]): 
                        continue
                    
                    if name_lower == "0000": scan_files(path, game_0000, base_mod_dir)
                    elif name_lower == "streamingassets" or name_lower == "assetbundle": scan_files(path, game_sa, base_mod_dir)
                    else: smart_scan(base_mod_dir, path, current_depth + 1)

            for mod_name in reversed(active_mods):
                if log_cb: log_cb(_("\n📂 正在掃描模組: {mod}").format(mod=mod_name))
                smart_scan(mod_name, os.path.join(mod_root, mod_name), 1)

            if not link_map: return finish_cb(False, _("未找到資源"), None)
            
            # 🛡️ 預檢階段 (Pre-flight Check)：先確認目標路徑是否皆具備寫入權限
            for target_path in link_map.keys():
                target_dir = os.path.dirname(target_path)
                try:
                    os.makedirs(target_dir, exist_ok=True)
                    if not os.access(target_dir, os.W_OK):
                        return finish_cb(False, _("權限不足：無法寫入目錄 {dir}，已取消掛載防護遊戲檔案。").format(dir=target_dir), None)
                except Exception as dummy_err:
                    return finish_cb(False, _("資料夾建立失敗 ({err})，已取消掛載防護遊戲檔案。").format(err=str(dummy_err)), None)
            
            MDEngine.task_virtual_unmount(True, None, None, None)
            
            success_count = 0
            # 🛡️ 實作 Transaction (交易) 回滾防護機制
            for target_path, src_path in link_map.items():
                backup_path = target_path + ".vanilla_backup"
                
                # 如果該路徑有實體檔案且還不是符號連結，先行備份
                if os.path.lexists(target_path) and not os.path.islink(target_path):
                    if not os.path.exists(backup_path):
                        try: 
                            os.rename(target_path, backup_path)
                        except Exception: 
                            continue # 備份失敗則跳過該檔案，不強制掛載
                
                try:
                    # 強制清理舊連結，然後建立新連結
                    if os.path.islink(target_path) or os.path.lexists(target_path): 
                        os.unlink(target_path)
                    os.symlink(src_path, target_path)
                    state_log[target_path] = backup_path
                    success_count += 1
                except Exception as e:
                    # 💥 捕捉到系統錯誤 (例如權限不足)，立刻啟動全局回滾，將已修改的目錄全數還原
                    if log_cb: log_cb(_("❌ 建立連結失敗 ({error})\n🔄 正在啟動安全回滾程序，還原遊戲目錄...").format(error=str(e)))
                    for rb_target, rb_backup in state_log.items():
                        try:
                            if os.path.lexists(rb_target): os.unlink(rb_target)
                            if os.path.exists(rb_backup): os.rename(rb_backup, rb_target)
                        except Exception: pass
                    state_log.clear() # 回滾完畢，清空 JSON 紀錄，當作一切都沒發生過
                    return finish_cb(False, _("權限不足或系統錯誤，已全數還原防護狀態。\n詳細原因: {error}").format(error=str(e)), None)
                    
            finish_cb(True, success_count, None)
        except Exception as e: finish_cb(False, str(e), traceback.format_exc())
        finally:
            if state_log: MDEngine.t11_save_state(state_log)

    @staticmethod
    def task_virtual_unmount(silent, log_cb, progress_cb, finish_cb):
        try:
            state = MDEngine.t11_load_state()
            if not state:
                if finish_cb: finish_cb(True, 0, "NO_RECORD")
                return
            success_count = 0
            for target_path, backup_path in state.items():
                resolved = False
                if os.path.lexists(target_path):
                    try:
                        if os.path.islink(target_path): os.unlink(target_path)
                        else: os.remove(target_path)
                        resolved = True
                    except Exception: pass
                else: resolved = True 

                if os.path.exists(backup_path):
                    try:
                        if os.path.lexists(target_path): os.remove(backup_path)
                        else: os.rename(backup_path, target_path)
                        resolved = True
                    except Exception: resolved = False
                if resolved: success_count += 1
            MDEngine.t11_save_state({})
            if finish_cb: finish_cb(True, success_count, None)
        except Exception as e:
            if finish_cb: finish_cb(False, str(e), traceback.format_exc())

    @staticmethod
    def get_id_to_name_map(csv_path, search_lang="zh-tw"):
        """智慧解析：從 CSV 速查表中榨取 ID 到名稱的 O(1) 字典"""
        try:
            dummy_map, db = MDEngine.get_csv_data(csv_path)
            name_map = {}
            for c in db:
                header, row = c.get('header', []), c.get('full_row', [])
                # 調用集中化解析器
                n_idx = MDEngine.find_lang_column_index(header, search_lang, "Name")
                if n_idx != -1 and len(row) > n_idx:
                    try: name_map[int(c['id'])] = row[n_idx]
                    except ValueError: pass
            return name_map
        except Exception: return {}

    @staticmethod
    def format_overframe_records(records_dict, name_map):
        import unicodedata
        
        def get_visual_width(text):
            # 🛡️ 智慧視覺寬度計算：將全形字元與模糊字元(如 γ,「」)視為雙倍寬度
            return sum(2 if unicodedata.east_asian_width(c) in ('W', 'F', 'A') else 1 for c in text)

        parsed_items = []
        max_left_width = 0

        # 第一階段：動態找出當下名單中「最寬」的左半邊
        for t, b in sorted(records_dict.items()):
            n_t = name_map.get(t, "")
            n_b = name_map.get(b, "")
            str_t = f"{t}" + (f" ({n_t})" if n_t else "")
            str_b = f"{b}" + (f" ({n_b})" if n_b else "")
            
            w = get_visual_width(str_t)
            if w > max_left_width:
                max_left_width = w
                
            parsed_items.append((str_t, str_b, w))

        # 預留 4 個半形空白的緩衝區
        target_width = max_left_width + 4

        # 第二階段：精準補齊空白
        lines = []
        for str_t, str_b, w in parsed_items:
            padding = " " * (target_width - w)
            lines.append(f"{str_t}{padding}->    {str_b}")
            
        return "\n".join(lines)

    @staticmethod
    def read_overframe_bytes(filepath):
        """從 Unity Bundle 二進位中光速提取紀錄，完全阻斷檔案鎖定"""
        records = {}
        env = None        # 👈 新增宣告
        file_data = None  # 👈 新增宣告
        try:
            with open(filepath, "rb") as f:
                file_data = f.read()
            env = UnityPy.load(file_data)
            for obj in env.objects:
                if obj.type.name == "TextAsset":
                    data = obj.read()
                    if hasattr(data, "m_Name") and str(data.m_Name) == "of_card_asset":
                        script_bytes = bytes(data.m_Script.encode("utf-8", "surrogateescape")) if isinstance(data.m_Script, str) else bytes(data.m_Script)
                        n = len(script_bytes) - (len(script_bytes) % 4)
                        for i in range(0, n, 4):
                            t, b = struct.unpack("<HH", script_bytes[i:i+4])
                            records[t] = b
                        break
        except Exception: 
            pass
        finally:          # 👈 新增強制釋放區塊
            if env: del env
            if file_data: del file_data
        return records
    
    @staticmethod
    def _worker_locate_gate(file_batch, stop_event=None):
        """背景工作站：加入 stop_event 支援多進程光速提早中斷"""
        import UnityPy
        import os
        for filepath, filename in file_batch:
            if stop_event and stop_event.is_set(): return None, None, 0 # 🛡️ 接到中斷訊號，立刻停止佔用 CPU
            
            file_data = None
            env = None
            try:
                if os.path.getsize(filepath) > 1024 * 1024: continue
                if not MDEngine.is_unity_bundle(filepath): continue
                
                with open(filepath, "rb") as f:
                    file_data = f.read()
                    
                env = UnityPy.load(file_data)
                for obj in env.objects:
                    if obj.type.name == "TextAsset":
                        data = obj.read()
                        name = getattr(data, "m_Name", getattr(data, "name", ""))
                        if str(name) == "of_card_asset": 
                            return filepath, filename, os.path.getmtime(filepath)
            except Exception: pass
            finally:
                if env: del env
                if file_data: del file_data
        return None, None, 0

    @staticmethod
    def _search_gate_bundle_core(src_dir, exclude_paths, strategy="FAST", progress_cb=None):
        """核心搜尋引擎：加入帶有上下文自動關閉的 Manager，徹底消滅殘留進程"""
        raw_files = []
        for root, dummy_dirs, files in os.walk(src_dir):
            MDEngine.prune_walk_dirs(root, dummy_dirs, exclude_paths)
            for f in files: 
                raw_files.append(os.path.join(root, f))
                
        total_files = len(raw_files)
        if progress_cb: progress_cb(1)
        
        workers_num = MDEngine.get_heavy_task_workers("Auto")
        batch_size = max(50, total_files // max(1, (workers_num * 4)))
        batches = [[(p, os.path.basename(p)) for p in raw_files[i:i + batch_size]] for i in range(0, total_files, batch_size)]
        
        best_path, best_hash, best_time = None, None, 0
        processed_count = 0
        
        # 🛡️ 使用 with 管理 Manager，任務結束後自動 shutdown 關閉進程，防止背景殘留
        with multiprocessing.Manager() as dummy_manager:
            stop_event = dummy_manager.Event()
            
            with concurrent.futures.ProcessPoolExecutor(max_workers=workers_num, initializer=_init_worker, initargs=(UI_LANG_DICT,)) as executor:
                future_to_batch = {executor.submit(MDEngine._worker_locate_gate, b, stop_event): len(b) for b in batches}
                
                for future in concurrent.futures.as_completed(future_to_batch):
                    processed_count += future_to_batch[future]
                    if progress_cb: progress_cb(processed_count)
                    
                    try:
                        fp, fh, ftime = future.result()
                        if fp:
                            if strategy == "FAST":
                                stop_event.set() # 廣播中斷訊號給其餘進程
                                return fp, fh
                            elif strategy == "LATEST":
                                if ftime > best_time:
                                    best_path, best_hash, best_time = fp, fh, ftime
                    except Exception: pass
                    
        return best_path, best_hash

    @staticmethod
    def task_auto_repair_gate(src_dir, out_root, out_folder, backup_folder, current_hash, progress_cb, finish_cb):
        """自動無縫修復器：三道防線尋找玩家心血，歷史快軌驗證避免盲目爆搜"""
        try:
            backup_dir = os.path.join(MDEngine.TEMP_DIR, "of_card_asset_backups")
            snap_path = os.path.join(backup_dir, "snapshot.bundle")
            history_file = os.path.join(backup_dir, "hash_history.json")
            out_dir = os.path.join(out_root, out_folder)

            user_records = {}
            pristine_records = {}
            found_old_data = False
            latest_history_hash = ""

            if os.path.exists(history_file):
                try:
                    with open(history_file, "r", encoding="utf-8") as f_hist:
                        hist_data = json.load(f_hist)
                        if isinstance(hist_data, list) and len(hist_data) > 0:
                            latest_history_hash = str(hist_data[0]).strip()
                except Exception:
                    pass

            user_file_t1 = os.path.join(out_dir, current_hash)
            pristine_file_t1 = os.path.join(backup_dir, f"{current_hash}.pristine")
            if os.path.exists(user_file_t1) and os.path.exists(pristine_file_t1):
                user_records = MDEngine.read_overframe_bytes(user_file_t1)
                pristine_records = MDEngine.read_overframe_bytes(pristine_file_t1)
                found_old_data = True

            if not found_old_data and latest_history_hash:
                user_file_t2 = os.path.join(out_dir, latest_history_hash)
                pristine_file_t2 = os.path.join(backup_dir, f"{latest_history_hash}.pristine")
                if os.path.exists(user_file_t2) and os.path.exists(pristine_file_t2):
                    user_records = MDEngine.read_overframe_bytes(user_file_t2)
                    pristine_records = MDEngine.read_overframe_bytes(pristine_file_t2)
                    found_old_data = True

            if not found_old_data and os.path.exists(snap_path):
                user_records = MDEngine.read_overframe_bytes(snap_path)
                if os.path.exists(pristine_file_t1):
                    pristine_records = MDEngine.read_overframe_bytes(pristine_file_t1)
                elif latest_history_hash:
                    fallback_pristine = os.path.join(backup_dir, f"{latest_history_hash}.pristine")
                    if os.path.exists(fallback_pristine):
                        pristine_records = MDEngine.read_overframe_bytes(fallback_pristine)

            # 步驟 1：萃取使用者歷史變更
            user_diff = MDEngine._calculate_user_diff(user_records, pristine_records)

            best_path = ""
            best_hash = ""

            # 步驟 2：歷史快軌驗證
            if latest_history_hash:
                candidate_path = MDEngine.get_actual_bundle_path(src_dir, latest_history_hash)
                if not os.path.exists(candidate_path):
                    candidate_path = MDEngine.get_actual_source_path(src_dir, latest_history_hash, "StreamingAssets")
                    
                if os.path.exists(candidate_path) and MDEngine.validate_gate_file(candidate_path):
                    best_path = candidate_path
                    best_hash = latest_history_hash

            # 若快軌失效，執行 FAST 爆搜
            if not best_path:
                found_path, found_hash = MDEngine._search_gate_bundle_core(src_dir, [out_root, MDEngine.TEMP_DIR], "FAST", progress_cb)
                if found_path:
                    best_path = found_path
                    best_hash = found_hash

            if not best_path:
                return finish_cb(False, _("在來源資料夾中找不到任何 of_card_asset 註冊表！"), None)

            # 🛡️ 步驟 3：於修復函式內完成 new_official + user_diff 的增量組合
            new_official_records = MDEngine.read_overframe_bytes(best_path)
            combined_records = dict(new_official_records)
            for t, b in user_diff.items():
                combined_records[t] = b

            # 步驟 4：呼叫核心，傳入找到的最新 Hash 與組合好的清單
            MDEngine.task_locate_and_write_overframe(src_dir, out_root, out_folder, backup_folder, combined_records, {}, best_hash, progress_cb, finish_cb)
        except Exception as e:
            finish_cb(False, str(e), traceback.format_exc())

    @staticmethod
    def _calculate_user_diff(user_records, pristine_records):
        """核心輔助：萃取淨差異 (修改檔 - 基底檔)"""
        return {t: b for t, b in user_records.items() if t not in pristine_records or pristine_records[t] != b}

    @staticmethod
    def task_locate_and_write_overframe(src_dir, out_root, out_folder, backup_folder, rec_curr, rec_new, target_hash, progress_cb, finish_cb):
        """核心寫入引擎：負責生成原裝備份與純淨輸出，嚴格控制資源與檔案鎖定"""
        try:
            backup_dir = os.path.join(MDEngine.TEMP_DIR, "of_card_asset_backups")
            os.makedirs(backup_dir, exist_ok=True)
            
            # 🛡️ 前置作業：淨化傳入的路徑，徹底剝離雙引號
            target_hash = clean_path(target_hash)
            
            # 🛡️ 純檔名萃取防護：防止絕對路徑穿透，保護輸出沙盒
            target_filename = os.path.basename(target_hash)
            
            # --- 步驟 1：萃取使用者變更 (因應歷史紀錄 json 的純差量儲存需求) ---
            user_diff = dict(rec_curr)
            old_pristine_file = os.path.join(backup_dir, f"{target_filename}.pristine")
            if os.path.exists(old_pristine_file):
                old_pristine_records = MDEngine.read_overframe_bytes(old_pristine_file)
                user_diff = MDEngine._calculate_user_diff(rec_curr, old_pristine_records)

            # --- 步驟 2：檢索遊戲原檔 ---
            # 🛡️ 順位 1：標準路徑
            gate_path = MDEngine.get_actual_bundle_path(src_dir, target_hash)
            if not os.path.exists(gate_path): 
                gate_path = MDEngine.get_actual_source_path(src_dir, target_hash, "StreamingAssets")
            is_valid = MDEngine.validate_gate_file(gate_path)
            
            # 🛡️ 順位 2：使用者絕對路徑
            if not is_valid and os.path.isabs(target_hash) and os.path.isfile(target_hash):
                if MDEngine.validate_gate_file(target_hash):
                    gate_path = target_hash
                    is_valid = True

            # 🛡️ 順位 3：爆搜 / 報錯
            if not is_valid:
                found_path, found_hash = MDEngine._search_gate_bundle_core(src_dir, [out_root, MDEngine.TEMP_DIR], "FAST", progress_cb)
                if not found_path:
                    return finish_cb(False, _("在來源資料夾中找不到 of_card_asset 註冊表！"), None)
                gate_path, target_hash = found_path, found_hash
                target_filename = os.path.basename(target_hash) # 重新提取檔名

            # --- 步驟 3：全新純淨原檔備份 ---
            new_pristine_file = os.path.join(backup_dir, f"{target_filename}.pristine")
            if os.path.exists(gate_path):
                if not os.path.exists(new_pristine_file):
                    shutil.copy2(gate_path, new_pristine_file)
                if backup_folder:
                    user_backup_dir = os.path.join(out_root, backup_folder)
                    os.makedirs(user_backup_dir, exist_ok=True)
                    user_backup_file = os.path.join(user_backup_dir, target_filename)
                    if not os.path.exists(user_backup_file):
                        shutil.copy2(gate_path, user_backup_file)

            # --- 步驟 4：提取最新官方基底 ---
            read_target = new_pristine_file if os.path.exists(new_pristine_file) else gate_path
            official_records = {}
            if os.path.exists(read_target):
                official_records = MDEngine.read_overframe_bytes(read_target)

            # --- 步驟 5：增量融合與衝突檢測 (🛡️ 還原為所見即所得直接寫入) ---
            merged_records = dict(rec_curr)
            for t, b in rec_new.items():
                merged_records[t] = b
                
            # 🛡️ 空白防呆保護：若清單完全為空，退回使用官方基底，防範壞檔
            if not merged_records:
                merged_records = dict(official_records)

            conflicts = []
            for t, b in rec_new.items():
                if t in rec_curr and rec_curr[t] != b:
                    conf_type = _("【官方保留佔位符衝突】") if (b == t and rec_curr[t] == 0) else _("【同項目指向不同目標】")
                    conf_msg = _("❌ 衝突類型：{ctype}\n   - 衝突項目 ID：[{t}]\n   - 現有/官方指向：[{curr}]\n   - 您的新註冊指向：[{new_b}]\n   👉 解決建議：若為官方佔位符(指向0)，請勿對其進行註冊；若為手動覆寫，請確認是否要刪除舊有指向。").format(ctype=conf_type, t=t, curr=rec_curr[t], new_b=b)
                    conflicts.append(conf_msg)

            if conflicts: 
                return finish_cb(False, _("🚨 偵測到註冊表合併衝突，為保護檔案結構，已中斷寫入：\n\n") + "\n\n".join(conflicts), None)

            # --- 步驟 6：安全寫入與歷史紀錄更新 ---
            with open(gate_path, "rb") as f_gate:
                file_data = f_gate.read()

            env = None
            success = False
            try:
                env = UnityPy.load(file_data)
                for obj in env.objects:
                    if obj.type.name == "TextAsset":
                        data = obj.read()
                        name = getattr(data, "m_Name", getattr(data, "name", ""))
                        if str(name) == "of_card_asset":
                            sorted_records = sorted(merged_records.items())
                            payload = b"".join(struct.pack("<HH", t, b) for t, b in sorted_records)
                            data.m_Script = payload.decode("utf-8", "surrogateescape") if isinstance(data.m_Script, str) else payload
                            data.save()
                            
                            out_dir = os.path.join(out_root, out_folder)
                            os.makedirs(out_dir, exist_ok=True)
                            final_path = os.path.join(out_dir, target_filename)
                            
                            try:
                                MDEngine.safe_write_bytes(final_path, env.file.save()) # 🛡️ 套用原子化寫入
                            except PermissionError:
                                return finish_cb(False, _("寫入失敗！檔案可能正被遊戲或其他程式佔用，請關閉後再試。"), None)
                                
                            success = True
                            try:
                                snap_path = os.path.join(backup_dir, "snapshot.bundle")
                                MDEngine.safe_copy_file(final_path, snap_path) # 🛡️ 原子化複製快照
                            except Exception: pass
                            break
            finally:
                if env: del env 
                del file_data
            
            if not success: return finish_cb(False, _("寫入失敗！檔案結構異常。"), None)
            
            try:
                history_file = os.path.join(backup_dir, "registered_history.json")
                hist = {}
                if os.path.exists(history_file):
                    with open(history_file, "r", encoding="utf-8") as f_hist:
                        old_hist = json.load(f_hist)
                        if isinstance(old_hist, dict):
                            hist = {str(k): int(v) for k, v in old_hist.items()}
                
                # 嚴格只記錄真正的非官方差異
                for k, v in user_diff.items():
                    hist[str(k)] = int(v)
                for k, v in rec_new.items():
                    hist[str(k)] = int(v)
                
                with open(history_file, "w", encoding="utf-8") as f_hist_out: 
                    json.dump(hist, f_hist_out, indent=4)
            except Exception: pass

            finish_cb(True, len(merged_records), target_filename)
        except Exception as e:
            finish_cb(False, str(e), traceback.format_exc())

    @staticmethod
    def task_manual_sync_overframe(src_dir, out_root, out_folder, backup_folder, curr_hash, progress_cb, finish_cb):
        """手動爆搜修正：提取舊差異 -> 全搜 LATEST 爆搜 -> 合併寫入"""
        try:
            backup_dir = os.path.join(MDEngine.TEMP_DIR, "of_card_asset_backups")
            pristine_path = os.path.join(backup_dir, f"{curr_hash}.pristine")
            snap_path = os.path.join(backup_dir, "snapshot.bundle")
            
            user_file = os.path.join(out_root, out_folder, curr_hash)
            if not os.path.exists(user_file) and os.path.exists(snap_path): user_file = snap_path
                
            user_records = {}
            if os.path.exists(user_file): user_records = MDEngine.read_overframe_bytes(user_file)
            pristine_records = {}
            if os.path.exists(pristine_path): pristine_records = MDEngine.read_overframe_bytes(pristine_path)
                
            # 步驟 1：萃取使用者歷史變更
            user_diff = MDEngine._calculate_user_diff(user_records, pristine_records)

            # 步驟 2：強制啟動 LATEST 爆搜
            best_path, best_hash = MDEngine._search_gate_bundle_core(src_dir, [out_root, MDEngine.TEMP_DIR], "LATEST", progress_cb)
            if not best_path: return finish_cb(False, _("在來源資料夾中找不到任何 of_card_asset 註冊表！"), None)

            # 🛡️ 步驟 3：於修復函式內完成 new_official + user_diff 的增量組合
            new_official_records = MDEngine.read_overframe_bytes(best_path)
            combined_records = dict(new_official_records)
            for t, b in user_diff.items():
                combined_records[t] = b

            # 步驟 4：呼叫核心，傳入找到的最新 Hash 與組合好的清單
            MDEngine.task_locate_and_write_overframe(src_dir, out_root, out_folder, backup_folder, combined_records, {}, best_hash, progress_cb, finish_cb)
        except Exception as e:
            finish_cb(False, str(e), traceback.format_exc())

    @staticmethod
    def parse_overframe_text(text):
        """多語系防護版：以 '#' 或 '=' 開頭的字串一律視為分隔線安全忽略"""
        records, conflicts = {}, []
        for line in text.splitlines():
            line = line.strip()
            # 🛡️ 只要是以 # 或 = 開頭，一律安全忽略，徹底免疫翻譯造成的字串變動
            if not line or line.startswith("#") or line.startswith("="): continue
            parts = re.split(r'->|>', line)
            try:
                t_match = re.search(r'\d+', parts[0])
                if not t_match: continue
                trigger = int(t_match.group(0))
                base = trigger
                if len(parts) >= 2:
                    b_match = re.search(r'\d+', parts[1])
                    if b_match: base = int(b_match.group(0))
                
                if trigger < 0 or trigger > 65535 or base < 0 or base > 65535:
                    conflicts.append(_("錯誤：ID 超出範圍 (0~65535) -> {line}").format(line=line))
                    continue
                if trigger in records and records[trigger] != base:
                    conflicts.append(_("❌ 內部衝突：卡片 ID [{trigger}] 同時被指派了兩個不同的目標：[{old}] 與 [{new}]。請刪除文字框中的其中一行。").format(trigger=trigger, old=records[trigger], new=base))
                records[trigger] = base
            except Exception: pass
        return records, conflicts

# =========================================================================
# ==================== 第四區：真・模組化 UI 分頁 ===========================
# =========================================================================
DARK_QSS = """
QMainWindow { background-color: #000001; }
QWidget { color: #EBEBEC; font-size: 14px; } 
QScrollArea { border: none; background: transparent; }
QScrollArea > QWidget > QWidget { background: transparent; }
QGroupBox { border: 1px solid #444; border-radius: 8px; margin-top: 15px; padding-top: 25px; font-weight: bold; }
QGroupBox::title { subcontrol-origin: margin; left: 15px; padding: 0 5px; color: #2CC985; }
QPushButton { background-color: #2B2B2B; border: 1px solid #444; border-radius: 6px; padding: 8px; font-weight: bold;}
QPushButton:hover { background-color: #3B8E8E; border: 1px solid #2CC985; }
QPushButton:pressed { background-color: #2A6A6A; }
QPushButton:disabled { background-color: #1A1A1A; color: #666; border: 1px solid #333; }
QLineEdit, QPlainTextEdit, QListWidget, QComboBox { background-color: #2B2B2B; border: 1px solid #444; border-radius: 6px; padding: 6px; }
QLineEdit:focus, QPlainTextEdit:focus, QListWidget:focus { border: 1px solid #2CC985; }
QListWidget::item { padding: 5px; }
QListWidget::item:selected { background-color: #3B8E8E; color: white; }
QProgressBar { border: 1px solid #444; border-radius: 6px; text-align: center; font-weight: bold; }
QProgressBar::chunk { background-color: #2CC985; border-radius: 4px; }
QScrollBar:vertical { background: #1C1C1C; width: 18px; margin: 0px; }
QScrollBar::handle:vertical { background: #555; min-height: 35px; border-radius: 9px; margin: 2px; }
QScrollBar::handle:vertical:hover { background: #2CC985; }
QCheckBox::indicator { width: 18px; height: 18px; border: 2px solid #444; border-radius: 4px; background-color: #2B2B2B; }
QCheckBox::indicator:checked { background-color: #2CC985; border: 2px solid #2CC985; }
"""

class LinearDragScrollFilter(QObject):
    """
    自訂線性拖曳捲動過濾器 (小數點累積器究極版)：
    1. 徹底消除釋放後的慣性 (即停即止)
    2. 解除強制最低 1 像素限制，允許極緩慢的微調捲動
    """
    def __init__(self, list_widget, speed_boost=1.0):
        super().__init__(list_widget)
        self.list_widget = list_widget
        self.speed_boost = speed_boost
        
        self.scroll_timer = QTimer(self)
        self.scroll_timer.setInterval(16) # 約 60 FPS
        self.scroll_timer.timeout.connect(self.do_scroll)
        
        self.mouse_y = 0
        self.is_dragging = False
        
        # 🛡️ 專門用來儲存不到 1 像素的「極微小速度」
        self.scroll_accumulator = 0.0 
        
        self.list_widget.viewport().installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj == self.list_widget.viewport():
            if event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.LeftButton:
                    self.is_dragging = True
                    self.mouse_y = int(event.position().y())
                    self.scroll_accumulator = 0.0 # 重新拖曳時歸零
                    
            elif event.type() == QEvent.Type.MouseMove:
                if self.is_dragging:
                    self.mouse_y = int(event.position().y())
                    viewport_h = self.list_widget.viewport().height()
                    if self.mouse_y < 0 or self.mouse_y > viewport_h:
                        if not self.scroll_timer.isActive():
                            self.scroll_timer.start()
                    else:
                        self.scroll_timer.stop()
                        self.scroll_accumulator = 0.0
                        
            elif event.type() == QEvent.Type.MouseButtonRelease:
                if event.button() == Qt.LeftButton:
                    self.is_dragging = False
                    self.scroll_timer.stop()
                    self.scroll_accumulator = 0.0
                    
        return False

    def do_scroll(self):
        viewport_h = self.list_widget.viewport().height()
        
        if self.list_widget.viewMode() == QListWidget.IconMode:
            h = self.list_widget.gridSize().height()
            if h <= 0: h = 205
        else:
            h = self.list_widget.sizeHintForRow(0)
            if h <= 0: h = 30
            
        # 🛡️ 精準測量滑鼠與清單邊界的距離 (d)
        if self.mouse_y < 0:
            d = abs(self.mouse_y)
            direction = -1
        elif self.mouse_y > viewport_h:
            d = self.mouse_y - viewport_h
            direction = 1
        else:
            self.scroll_timer.stop()
            self.scroll_accumulator = 0.0
            return
            
        # 🛡️ 移除 max(1)，允許出現 0.5, 0.1 這種小數點步長
        # 分母 800.0 是靈敏度係數，你可以依據喜好微調 (數字越大整體越不敏感)
        raw_step = (d * h / 800.0) * self.speed_boost
        
        # 🛡️ 把這次算出的小數點步長加進水桶裡
        self.scroll_accumulator += raw_step
        
        # 🛡️ 只有當水桶滿 1 像素時，才執行實際的畫面捲動
        actual_step = int(self.scroll_accumulator)
        if actual_step > 0:
            self.scroll_accumulator -= actual_step # 把用掉的整數像素扣除，保留剩下的小數點
            v_bar = self.list_widget.verticalScrollBar()
            v_bar.setValue(v_bar.value() + direction * actual_step)

class UIHelper:
    @staticmethod
    def move_list_items(list_widget, direction):
        """在 QListWidget 中上下移動選定項目 (direction: -1 向上, 1 向下)"""
        selected_rows = sorted([list_widget.row(item) for item in list_widget.selectedItems()], reverse=(direction == 1))
        if not selected_rows: return
        if direction == -1 and selected_rows[0] == 0: return
        if direction == 1 and selected_rows[0] == list_widget.count() - 1: return

        for row in selected_rows:
            item = list_widget.takeItem(row)
            list_widget.insertItem(row + direction, item)
            item.setSelected(True)

    @staticmethod
    def setup_quick_transfer(lst_from, lst_to):
        """綁定滑鼠右鍵與中鍵快速轉移"""
        old_mousePressEvent = lst_from.mousePressEvent
        def new_mousePressEvent(event):
            if event.button() in (Qt.RightButton, Qt.MiddleButton):
                item = lst_from.itemAt(event.pos())
                if item:
                    lst_to.addItem(lst_from.takeItem(lst_from.row(item)))
                    return
            old_mousePressEvent(event)
        lst_from.mousePressEvent = new_mousePressEvent

class BaseTab(QWidget):
    """基底模組：負責資料綁定與排版快速建立"""
    def __init__(self, main_app):
        super().__init__()
        self.app = main_app
        self.config = main_app.config_mgr
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignTop)

    def prevent_scroll_propagation(self, widget):
        """強制吸收滾輪事件，避免清單滾到底時帶動背景視窗亂跑"""
        old_wheel = widget.wheelEvent
        def blocked_wheel(event):
            old_wheel(event)
            event.accept() # 吸收動能，絕不向父元件(背景)傳遞
        widget.wheelEvent = blocked_wheel

    def get_safe_int(self, config_key, default_val=0):
        """真・防禦性轉換：確保任何空字串或格式錯誤輸入都不會引發崩潰"""
        try:
            return int(str(self.config.get(config_key, default_val)).strip())
        except ValueError:
            return default_val

    def make_path_row(self, form_layout, label_text, config_key, is_file=False, ftype="CSV", sync_type=None, placeholder=None):
        edit = QLineEdit()
        edit.setText(clean_path(self.config.get(config_key, "")))
        
        # 綁定浮水印提示字元，並且套用翻譯系統
        if placeholder:
            edit.setPlaceholderText(_(placeholder))
        else:
            edit.setPlaceholderText(_("請輸入對應路徑..."))
        
        def on_text_changed(text):
            cleaned = clean_path(text)
            if cleaned != text:
                edit.setText(cleaned) 
            self.config.set(config_key, cleaned)
            
        edit.textChanged.connect(on_text_changed)
        
        btn = QPushButton(_("瀏覽"))
        def browse():
            cur = clean_path(edit.text())
            # 🛡️ 路徑純粹化：若不存在，只給空字串，不隨意退回其他目錄節外生枝
            start_dir = cur if os.path.exists(cur) else ""
            if is_file:
                filt = "Images (*.png *.jpg *.jpeg *.bmp)" if ftype == "IMG" else f"{ftype} Files (*.{ftype.lower()});;All Files (*.*)"
                path, dummy_dirs = QFileDialog.getOpenFileName(self, _("選擇檔案"), start_dir, filt)
            else: 
                path = QFileDialog.getExistingDirectory(self, _("選擇資料夾"), start_dir)
            if path: edit.setText(path)
        btn.clicked.connect(browse)
        
        row = QHBoxLayout()
        row.addWidget(edit); row.addWidget(btn)
        form_layout.addRow(label_text, row)
        
        if sync_type == "root": self.config.signals.sync_root.connect(lambda p: edit.setText(p) if edit.text() != p else None)
        elif sync_type == "csv": self.config.signals.sync_csv.connect(lambda p: edit.setText(p) if edit.text() != p else None)
        elif sync_type == "src": self.config.signals.sync_src.connect(lambda p: edit.setText(p) if edit.text() != p else None)
        elif sync_type == "txt": self.config.signals.sync_t2_txt.connect(lambda p: edit.setText(p) if edit.text() != p else None)
        return edit

    def bind_check(self, config_key, text):
        cb = QCheckBox(text)
        cb.setChecked(self.config.get(config_key, True))
        cb.toggled.connect(lambda state: self.config.set(config_key, state))
        return cb

    def bind_text(self, config_key, text_widget):
        val = str(self.config.get(config_key, ""))
        if isinstance(text_widget, QPlainTextEdit):
            text_widget.setPlainText(val)
            text_widget.setUndoRedoEnabled(True)
            text_widget.textChanged.connect(lambda: self.config.set(config_key, text_widget.toPlainText()))
        else:
            text_widget.setText(val)
            text_widget.textChanged.connect(lambda t: self.config.set(config_key, t))

    def block_slider_wheel(self, slider):
        slider.wheelEvent = lambda event: event.ignore()

    def block_wheelEvent(self, widget):
        """強制吸收滾輪事件，保護下拉選單防誤觸"""
        widget.wheelEvent = lambda event: event.ignore()

    def bind_visual_filter(self, form_layout=None):
        cb = QCheckBox(_("⚠️ 僅處理場地/卡套/頭像等物件"))
        cb.setStyleSheet("color: #E0C030; font-weight: bold;")
        cb.setChecked(self.config.get("enable_visual_only_filter", False))
        cb.toggled.connect(lambda state: self.config.set("enable_visual_only_filter", state))
        if form_layout is not None: form_layout.addRow(cb)
        return cb

class SearchFilterSignals(QObject):
    search_requested = Signal(dict)
    page_display_updated = Signal(list) # ✨ 新增：0ms 切片更新訊號
    add_current_page_requested = Signal(list)
    add_all_results_requested = Signal(list)

class GoogleSearchFilterWidget(QWidget):
    def __init__(self, config_manager, enable_batch_add=True, parent=None):
        super().__init__(parent)
        self.config = config_manager
        self.signals = SearchFilterSignals()
        self.enable_batch_add = enable_batch_add
        
        # 記憶體分頁快取
        self.all_matches = []
        self.current_page = 1
        self.total_pages = 1
        
        self.init_ui()
        self.update_badge_and_state()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # --- 第一列：主搜尋列 ---
        h_top = QHBoxLayout()
        
        lbl_lang = QLabel(_("對照語系:"))
        lbl_lang.setMinimumWidth(70)

        self.cb_lang = QComboBox()
        self.cb_lang.setMinimumWidth(100)
        self.cb_lang.addItems(["zh-tw", "zh-cn", "en-us", "ja-jp"])
        self.cb_lang.setEditable(True)
        self.cb_lang.setCurrentText(self.config.get("search_lang", "zh-tw"))
        self.cb_lang.currentTextChanged.connect(self._on_lang_changed)
        
        # 阻擋滾輪，必須定義在內部或呼叫外部輔助
        self.cb_lang.wheelEvent = lambda event: event.ignore()

        self.edit_search = QLineEdit()
        self.edit_search.setMinimumWidth(180)
        self.edit_search.setPlaceholderText(_("🔍 輸入 ID/名稱/效果/Hash/語法 (+, -, \"\")..."))
        
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.trigger_search)
        self.edit_search.textChanged.connect(lambda dummy_text: self.search_timer.start(300))
        
        btn_clear = QPushButton(_("✕"))
        btn_clear.setFixedWidth(30)
        btn_clear.clicked.connect(self.edit_search.clear)
        
        self.btn_toggle_filter = QPushButton(_("⚙️ 篩選"))
        self.btn_toggle_filter.setCheckable(True)
        self.btn_toggle_filter.clicked.connect(self.toggle_filter_panel)
        
        h_top.addWidget(lbl_lang)
        h_top.addWidget(self.cb_lang)
        h_top.addWidget(self.edit_search, 1)
        h_top.addWidget(btn_clear)
        h_top.addWidget(self.btn_toggle_filter)
        main_layout.addLayout(h_top)
        
        # --- 第二列：收納式篩選面板 ---
        self.panel_filter = QWidget()
        v_panel = QVBoxLayout(self.panel_filter)
        v_panel.setContentsMargins(5, 5, 5, 5)
        
        # 怪獸區
        grp_monster = QGroupBox(_("怪獸 (Monster)"))
        grid_m = QGridLayout(grp_monster)
        self.chk_m_enable = QCheckBox(_("啟用怪獸")); self.chk_m_enable.setStyleSheet("color: #2CC985;")
        self.chk_m_eff = QCheckBox(_("效果")); self.chk_m_norm = QCheckBox(_("通常")); self.chk_m_fus = QCheckBox(_("融合")); self.chk_m_syn = QCheckBox(_("同步"))
        self.chk_m_xyz = QCheckBox(_("超量")); self.chk_m_link = QCheckBox(_("連結")); self.chk_m_rit = QCheckBox(_("儀式")); self.chk_m_pen = QCheckBox(_("靈擺")); self.chk_m_tok = QCheckBox(_("衍生物"))
        grid_m.addWidget(self.chk_m_enable, 0, 0); grid_m.addWidget(self.chk_m_eff, 0, 1); grid_m.addWidget(self.chk_m_norm, 0, 2); grid_m.addWidget(self.chk_m_fus, 0, 3); grid_m.addWidget(self.chk_m_syn, 0, 4)
        grid_m.addWidget(self.chk_m_xyz, 1, 1); grid_m.addWidget(self.chk_m_link, 1, 2); grid_m.addWidget(self.chk_m_rit, 1, 3); grid_m.addWidget(self.chk_m_pen, 1, 4); grid_m.addWidget(self.chk_m_tok, 1, 5)
        
        # 魔法區
        grp_spell = QGroupBox(_("魔法 (Spell)"))
        h_s = QHBoxLayout(grp_spell)
        self.chk_s_enable = QCheckBox(_("啟用魔法")); self.chk_s_enable.setStyleSheet("color: #4AA4FF;")
        self.chk_s_norm = QCheckBox(_("通常")); self.chk_s_qp = QCheckBox(_("速攻")); self.chk_s_cont = QCheckBox(_("永續")); self.chk_s_field = QCheckBox(_("場地")); self.chk_s_equip = QCheckBox(_("裝備")); self.chk_s_rit = QCheckBox(_("儀式"))
        for w in [self.chk_s_enable, self.chk_s_norm, self.chk_s_qp, self.chk_s_cont, self.chk_s_field, self.chk_s_equip, self.chk_s_rit]: h_s.addWidget(w)
        
        # 陷阱區
        grp_trap = QGroupBox(_("陷阱 (Trap)"))
        h_t = QHBoxLayout(grp_trap)
        self.chk_t_enable = QCheckBox(_("啟用陷阱")); self.chk_t_enable.setStyleSheet("color: #FF5A9B;")
        self.chk_t_norm = QCheckBox(_("通常")); self.chk_t_count = QCheckBox(_("反制")); self.chk_t_cont = QCheckBox(_("永續"))
        for w in [self.chk_t_enable, self.chk_t_norm, self.chk_t_count, self.chk_t_cont]: h_t.addWidget(w)
        
        # 輔助與進階區
        grp_adv = QGroupBox(_("🛠️ 輔助與進階設定"))
        v_adv = QVBoxLayout(grp_adv)
        
        h_adv1 = QHBoxLayout()
        self.chk_visual = QCheckBox(_("⚠️ 僅處理場地/卡套/頭像等物件")); self.chk_visual.setStyleSheet("color: #E0C030; font-weight: bold;")
        self.chk_visual.setChecked(self.config.get("enable_visual_only_filter", False))
        btn_reset = QPushButton(_("🔄 重設所有篩選條件")); btn_reset.clicked.connect(self.reset_filters)
        h_adv1.addWidget(self.chk_visual); h_adv1.addStretch(); h_adv1.addWidget(btn_reset)
        
        h_adv2 = QHBoxLayout()
        self.edit_inc = QLineEdit(); self.edit_inc.setPlaceholderText(_("必須包含 (+)..."))
        self.edit_exc = QLineEdit(); self.edit_exc.setPlaceholderText(_("不能包含 (-)..."))
        h_adv2.addWidget(QLabel(_("必須包含 (+):"))); h_adv2.addWidget(self.edit_inc)
        h_adv2.addWidget(QLabel(_("不能包含 (-):"))); h_adv2.addWidget(self.edit_exc)
        
        h_adv3 = QHBoxLayout()
        self.chk_fuzzy_name = QCheckBox(_("卡名模糊")); self.chk_fuzzy_desc = QCheckBox(_("效果文模糊"))
        self.cb_page_limit = QComboBox()
        limit_options = [
            ("50", 50),
            ("100", 100),
            ("200", 200),
            ("500", 500),
            ("1000", 1000),
            (_("全部 (All)"), 999999)
        ]
        for display_text, val in limit_options:
            self.cb_page_limit.addItem(display_text, val)

        self.cb_page_limit.setEditable(True)
        self.cb_page_limit.setCurrentText("200")
        self.cb_page_limit.wheelEvent = lambda event: event.ignore()
        h_adv3.addWidget(QLabel(_("容錯比對:"))); h_adv3.addWidget(self.chk_fuzzy_name); h_adv3.addWidget(self.chk_fuzzy_desc)
        h_adv3.addStretch(); h_adv3.addWidget(QLabel(_("單頁顯示上限:"))); h_adv3.addWidget(self.cb_page_limit)
        
        v_adv.addLayout(h_adv1); v_adv.addLayout(h_adv2); v_adv.addLayout(h_adv3)
        
        v_panel.addWidget(grp_monster); v_panel.addWidget(grp_spell); v_panel.addWidget(grp_trap); v_panel.addWidget(grp_adv)
        self.panel_filter.setVisible(False)
        main_layout.addWidget(self.panel_filter)
        
        # --- 第三列：分頁導覽列 ---
        self.nav_bar = QWidget()
        h_nav = QHBoxLayout(self.nav_bar)
        h_nav.setContentsMargins(0, 5, 0, 0)
        
        self.btn_prev = QPushButton(_("◀ 上一頁")); self.btn_prev.clicked.connect(self.prev_page)
        self.lbl_page_info = QLabel(_("第 1 / 1 頁 (共 0 筆)")); self.lbl_page_info.setAlignment(Qt.AlignCenter)
        self.btn_next = QPushButton(_("下一頁 ▶")); self.btn_next.clicked.connect(self.next_page)
        
        h_nav.addWidget(self.btn_prev); h_nav.addWidget(self.lbl_page_info, 1); h_nav.addWidget(self.btn_next)
        
        if self.enable_batch_add:
            self.btn_add_page = QPushButton(_("＋ 加入本頁全部")); self.btn_add_page.clicked.connect(self.add_current_page)
            self.btn_add_all = QPushButton(_("＋ 加入全部搜尋結果")); self.btn_add_all.clicked.connect(self.add_all_results)
            self.btn_add_page.setStyleSheet("color: #4AA4FF; font-weight: bold;")
            self.btn_add_all.setStyleSheet("color: #FF5A9B; font-weight: bold;")
            h_nav.addWidget(self.btn_add_page); h_nav.addWidget(self.btn_add_all)
            
        main_layout.addWidget(self.nav_bar)

        # 綁定事件觸發搜尋與徽章更新
        all_checks = [
            self.chk_m_enable, self.chk_m_eff, self.chk_m_norm, self.chk_m_fus, self.chk_m_syn, self.chk_m_xyz, self.chk_m_link, self.chk_m_rit, self.chk_m_pen, self.chk_m_tok,
            self.chk_s_enable, self.chk_s_norm, self.chk_s_qp, self.chk_s_cont, self.chk_s_field, self.chk_s_equip, self.chk_s_rit,
            self.chk_t_enable, self.chk_t_norm, self.chk_t_count, self.chk_t_cont,
            self.chk_visual, self.chk_fuzzy_name, self.chk_fuzzy_desc
        ]
        for cb in all_checks:
            cb.toggled.connect(lambda dummy_state: self.update_badge_and_state())
            
        self.edit_inc.textChanged.connect(lambda dummy_text: self.update_badge_and_state())
        self.edit_exc.textChanged.connect(lambda dummy_text: self.update_badge_and_state())
        self.cb_page_limit.currentTextChanged.connect(lambda dummy_text: self.update_badge_and_state())

    def _get_current_limit(self):
        """
        DRY 核心解析器：支援真・多語系解耦與自訂數值防禦
        """
        # 1. 優先判定：是否選取了下拉選項（透過 itemData 綁定的整數值）
        data_val = self.cb_page_limit.currentData()
        current_text = self.cb_page_limit.currentText().strip()
        current_idx = self.cb_page_limit.currentIndex()
        
        if isinstance(data_val, int) and data_val > 0:
            # 確保目前輸入框文字確實等於該項目的顯示文字（防止使用者手動輸入其他字但 index 未變）
            if current_idx >= 0 and current_text == self.cb_page_limit.itemText(current_idx).strip():
                return data_val

        # 2. 多語系防線：若文字與翻譯標籤完全相符（或預設繁中/英文）
        if current_text in (_("全部 (All)"), "全部 (All)", "All", "全部"):
            return 999999

        # 3. 使用者手動輸入純數字（強制至少為 1，100% 杜絕 ZeroDivisionError）
        if current_text.isdigit():
            return max(1, int(current_text))

        # 4. 防呆預設值
        return 200

    def _on_lang_changed(self, text):
        self.config.set("search_lang", text.strip().lower())
        self.trigger_search()

    def toggle_filter_panel(self):
        self.panel_filter.setVisible(self.btn_toggle_filter.isChecked())

    def reset_filters(self):
        self.chk_m_enable.setChecked(False); self.chk_s_enable.setChecked(False); self.chk_t_enable.setChecked(False)
        for cb in [self.chk_m_eff, self.chk_m_norm, self.chk_m_fus, self.chk_m_syn, self.chk_m_xyz, self.chk_m_link, self.chk_m_rit, self.chk_m_pen, self.chk_m_tok,
                   self.chk_s_norm, self.chk_s_qp, self.chk_s_cont, self.chk_s_field, self.chk_s_equip, self.chk_s_rit,
                   self.chk_t_norm, self.chk_t_count, self.chk_t_cont]: cb.setChecked(False)
        self.chk_visual.setChecked(False)
        self.edit_inc.clear()
        self.edit_exc.clear()
        self.chk_fuzzy_name.setChecked(False); self.chk_fuzzy_desc.setChecked(False)
        self.cb_page_limit.setCurrentText("200")
        self.update_badge_and_state()

    def update_badge_and_state(self):
        # 統計非預設條件
        active_count = 0
        if self.chk_m_enable.isChecked() or self.chk_s_enable.isChecked() or self.chk_t_enable.isChecked(): active_count += 1
        if any(cb.isChecked() for cb in [self.chk_m_eff, self.chk_m_norm, self.chk_m_fus, self.chk_m_syn, self.chk_m_xyz, self.chk_m_link, self.chk_m_rit, self.chk_m_pen, self.chk_m_tok]): active_count += 1
        if any(cb.isChecked() for cb in [self.chk_s_norm, self.chk_s_qp, self.chk_s_cont, self.chk_s_field, self.chk_s_equip, self.chk_s_rit]): active_count += 1
        if any(cb.isChecked() for cb in [self.chk_t_norm, self.chk_t_count, self.chk_t_cont]): active_count += 1
        if self.chk_visual.isChecked(): active_count += 1
        if self.edit_inc.text().strip(): active_count += 1
        if self.edit_exc.text().strip(): active_count += 1
        if self.chk_fuzzy_name.isChecked(): active_count += 1
        if self.chk_fuzzy_desc.isChecked(): active_count += 1

        if active_count > 0:
            self.btn_toggle_filter.setText(_("⚙️ 篩選 (已套用: {count})").format(count=active_count))
            theme_color = self.config.get("ui_theme_color", "#2CC985")
            self.btn_toggle_filter.setStyleSheet(f"color: {theme_color}; font-weight: bold;")
        else:
            self.btn_toggle_filter.setText(_("⚙️ 篩選"))
            self.btn_toggle_filter.setStyleSheet("")
            
        self.config.set("enable_visual_only_filter", self.chk_visual.isChecked())
        self.trigger_search()

    def get_search_params(self):
        limit = self._get_current_limit()
        
        m_subs = []
        if self.chk_m_eff.isChecked(): m_subs.append("效果")
        if self.chk_m_norm.isChecked(): m_subs.append("通常")
        if self.chk_m_fus.isChecked(): m_subs.append("融合")
        if self.chk_m_syn.isChecked(): m_subs.append("同步")
        if self.chk_m_xyz.isChecked(): m_subs.append("超量")
        if self.chk_m_link.isChecked(): m_subs.append("連結")
        if self.chk_m_rit.isChecked(): m_subs.append("儀式")
        if self.chk_m_tok.isChecked(): m_subs.append("衍生物")
        
        s_subs = []
        if self.chk_s_norm.isChecked(): s_subs.append("通常")
        if self.chk_s_qp.isChecked(): s_subs.append("速攻")
        if self.chk_s_cont.isChecked(): s_subs.append("永續")
        if self.chk_s_field.isChecked(): s_subs.append("場地")
        if self.chk_s_equip.isChecked(): s_subs.append("裝備")
        if self.chk_s_rit.isChecked(): s_subs.append("儀式")
        
        t_subs = []
        if self.chk_t_norm.isChecked(): t_subs.append("通常")
        if self.chk_t_count.isChecked(): t_subs.append("反制")
        if self.chk_t_cont.isChecked(): t_subs.append("永續")

        # 👈 只要有勾選子標籤或靈擺，就自動視為主開關啟用，體驗更直覺
        m_enabled = self.chk_m_enable.isChecked() or bool(m_subs) or self.chk_m_pen.isChecked()
        s_enabled = self.chk_s_enable.isChecked() or bool(s_subs)
        t_enabled = self.chk_t_enable.isChecked() or bool(t_subs)

        return {
            "query": self.edit_search.text().strip(),
            "visual_only": self.chk_visual.isChecked(),
            "inc_words": self.edit_inc.text().strip(),
            "exc_words": self.edit_exc.text().strip(),
            "fuzzy_name": self.chk_fuzzy_name.isChecked(),
            "fuzzy_desc": self.chk_fuzzy_desc.isChecked(),
            "limit_per_page": limit,
            "filters": {
                "怪獸": {"enabled": m_enabled, "pendulum": self.chk_m_pen.isChecked(), "subs": m_subs},
                "魔法": {"enabled": s_enabled, "subs": s_subs},
                "陷阱": {"enabled": t_enabled, "subs": t_subs}
            }
        }

    def trigger_search(self):
        self.current_page = 1 # 重置頁碼
        self.signals.search_requested.emit(self.get_search_params())

    def update_pagination_ui(self, all_matches_data, limit_per_page):
        self.all_matches = all_matches_data
        self.current_page = 1 # 重新搜尋後強制作為第一頁
        total_hits = len(self.all_matches)
        
        if limit_per_page >= total_hits:
            self.total_pages = 1
        else:
            self.total_pages = (total_hits + limit_per_page - 1) // limit_per_page
            
        if self.enable_batch_add:
            self.btn_add_all.setText(_("＋ 加入全部 {hits} 筆").format(hits=total_hits))
            
        self._refresh_page_display(limit_per_page)

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self._refresh_page_display(self._get_current_limit())

    def next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self._refresh_page_display(self._get_current_limit())

    def _refresh_page_display(self, limit_per_page):
        # 核心：0ms 記憶體切片並發送更新訊號，不重新檢索資料庫
        total_hits = len(self.all_matches)
        self.lbl_page_info.setText(_("第 {curr} / {total} 頁 (共 {hits} 筆)").format(curr=self.current_page, total=self.total_pages, hits=total_hits))
        self.btn_prev.setEnabled(self.current_page > 1)
        self.btn_next.setEnabled(self.current_page < self.total_pages)

        start_idx = (self.current_page - 1) * limit_per_page
        end_idx = start_idx + limit_per_page
        page_slice = self.all_matches[start_idx:end_idx]
        
        self.signals.page_display_updated.emit(page_slice)

    def add_current_page(self):
        self.signals.add_current_page_requested.emit(self._get_current_page_slice())

    def add_all_results(self):
        total = len(self.all_matches)
        if total >= 1000:
            reply = QMessageBox.question(self, _("危險操作警告"), _("搜尋結果共 {count} 筆，全數加入可能會使下方提取清單過長。\n確定要將全部 {count} 筆卡片加入清單嗎？").format(count=total), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No: return
        self.signals.add_all_results_requested.emit(self.all_matches)

    def _get_current_page_slice(self):
        limit = self._get_current_limit()
        start_idx = (self.current_page - 1) * limit
        end_idx = start_idx + limit
        return self.all_matches[start_idx:end_idx]

# ==================== 分頁 0: 新手指南 ====================
class TabGuide(BaseTab):
    def __init__(self, main_app):
        super().__init__(main_app)
        self.layout.addWidget(QLabel(_("📖 Master Duel 資源改造指南")))
        
        desc = QLabel(_("歡迎使用本工具，本工具為免費工具。本工具不僅能修改卡圖，只要是遊戲中的卡套、場地、頭像、背景等所有 2D 貼圖資源，只要屬於 Texture2D 類別，皆能替換。"))
        desc.setWordWrap(True)
        self.layout.addWidget(desc)
        
        text_guide = QPlainTextEdit()
        text_guide.setReadOnly(True)
        text_guide.setPlainText(
            _("📋 【全分頁功能指引說明書】\n\n"
              "【最高指導原則】：把路徑貼上然後按執行\n\n"
              "🛠️ 1~5 步：標準批次修改專案（適合多檔案或大型模組包製作）\n"
              "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
              "【1. 爆搜與補齊】：掃描遊戲 0000 檔案，生成亂碼檔名（Hash）與卡片真實名稱的對照表（CSV 字典）。\n"
              "也可利用此功能快速提取模組檔案的卡片編號txt檔案\n\n"
              "【2. 找出檔案】：借助對照表搜尋卡片，並將對應的遊戲檔案複製出來集中管理。\n"
              "可以智慧讀取上一頁生成的txt檔案，並且可以切換為快速遊戲原檔轉超框功能(點擊選擇模式切換)\n"
              "想要把自己的模組超框話請使用靈擺與超框卡圖後處理\n"
              "以防你不知道，點擊右鍵也可以移動選取的項目\n"
              "視覺化篩選可以讓你用圖片的方式檢查有沒有挑錯圖\n\n"
              "【3. 提取資料】：提取出檔案中的2D紋理，並留下原始備份。\n"
              "你可以順帶生成csv(從母csv中複製出來的)\n"
              "你可能會注意到為什麼好像有兩個備份功能的資料夾，問就是有意為之\n\n"
              "【4. 更改卡圖】：將你在「卡圖改(你可以改名)」中修改好的圖片裝到卡片檔案中。\n"
              "卡圖命名請保留[編號前綴與底線]後面隨便你取什麼都可以。\n"
              "例如這樣 \"12345_這裡取什麼名字隨便你.png\"\n\n"
              "【5. 封裝模組】：自動將改完的加密檔整理成符合官方路徑的資料夾結構，以便套用或分享給他人。\n"
              "打包你的檔案!\n\n\n"
              "⚡ 進階效能與自動化調度\n"
              "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
              "【6. 智慧串連執行】：一鍵自動連鎖執行上述 2 至 5 的所有步驟，徹底省去手動一步步操作的時間。\n"
              "但是你還是需要填好你的路徑\n\n\n"
              "🎨 視覺效果與進階卡面美化\n"
              "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
              "【7. 靈擺與超框卡圖後處理】：自動修復正方形靈擺卡圖比例 / 自動把你的卡片進行超框化的模板套用(點擊處理模式切換)\n"
              "靈擺圖片是針對正方形卡圖的，他會在圖片下方填充透明框，防止卡圖在遊戲中變形。\n"
              "超框化模板會自動將你的圖片並置中裁切將其變成11:16的形式\n\n"
              "【8. 快捷單卡改圖】：免去建立專案的步驟，直接搜尋指定卡片、選擇新圖片即可一鍵替換遊戲內原檔。\n"
              "要替換多張卡圖強烈建議去使用上半部的功能，這個功能十分受限，但很簡單\n\n"
              "【9. 超框卡片註冊器】：修改超框卡的名單(of_card_asset)。將卡片 ID 寫入遊戲的註冊表中，使其能突破邊框限制。\n"
              "可以從這邊跳轉去第二頁搜尋(或自動填入txt)來找到你想要的卡片\n\n"
              "【10. 圖形化瀏覽器】：提供場地、硬幣、頭像、卡套、大廳背景等2D資產的縮圖檢視，可將 ID 直接傳送至提取清單。\n\n\n"
              "🔧 模組維護、救援與虛擬管理\n"
              "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
              "【11. 模組串流修復器】：當遊戲大更新導致舊模組失效時，直接將舊模組的貼圖串流移植到最新版的官方原檔中。\n"
              "這個功能理論上能生效，但如果K社修改了檔案儲存格式的就沒得救\n\n"
              "【12. 虛擬模組管理器】：使用系統符號連結（Symlink）技術，免安裝、免佔空間即可一鍵啟用或還原多個模組。\n"
              "需要管理員權限才能使用此功能\n"
              "用來測試模組非常方便\n\n"
              "【13. 設定與外觀】：自訂程式強調色、自訂背景圖片與透明度，並可在此調整左側目錄的分頁順序與名稱。\n"
              "大部分全域的設定值都擺在這邊了，修改完記得按儲存設定!\n"
              "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
              "【來自作者的靈魂吶喊】：納西妲世界第一可愛!!")
        )
        self.layout.addWidget(text_guide)

# ==================== 分頁 1: 爆搜與補齊 ====================
class TabScan(BaseTab):
    def __init__(self, main_app):
        super().__init__(main_app)
        self.layout.addWidget(QLabel(_("【第 1 步】資料源分析與字典生成")))
        
        grp_paths = QGroupBox(_("路徑設定"))
        form_paths = QFormLayout(grp_paths)
        self.t1_target_edit = self.make_path_row(form_paths, _("目標資料夾 (0000)"), "t1_target_dir", placeholder="你的槽:\\SteamLibrary\\steamapps\\common\\Yu-Gi-Oh! Master Duel\\LocalData\\你的八字編號\\0000")
        self.t1_target_edit.textChanged.connect(lambda p: self.config.set("t1_out_dir", os.path.dirname(os.path.normpath(clean_path(p)))) if clean_path(p) else None)
        self.t1_out_edit = self.make_path_row(form_paths, _("儲存根目錄"), "t1_out_dir", sync_type="root", placeholder="請輸入或選擇此專案的工作根目錄...")
        self.layout.addWidget(grp_paths)

        grp_opt = QGroupBox(_("過濾與生成選項"))
        form_opt = QFormLayout(grp_opt)
        
        box_names = QHBoxLayout()
        self.t1_txt = QLineEdit(); self.bind_text("t1_txt_name", self.t1_txt); box_names.addWidget(QLabel("TXT:")); box_names.addWidget(self.t1_txt)
        self.t1_csv = QLineEdit(); self.bind_text("t1_csv_name", self.t1_csv); box_names.addWidget(QLabel("CSV:")); box_names.addWidget(self.t1_csv)
        form_opt.addRow(_("輸出檔名命名:"), box_names)
        
        box_size = QHBoxLayout()
        self.t1_min = QLineEdit(); self.bind_text("t1_min_size", self.t1_min); box_size.addWidget(QLabel(_("下限(KB):"))); box_size.addWidget(self.t1_min)
        self.t1_max = QLineEdit(); self.bind_text("t1_max_size", self.t1_max); box_size.addWidget(QLabel(_("上限(KB):"))); box_size.addWidget(self.t1_max)
        form_opt.addRow(self.bind_check("t1_size_filter", _("啟用大小過濾")), box_size)
        
        # 🛡️ 使用整齊的三欄 QGridLayout 網格對齊所有勾選框
        grid_cb = QGridLayout()
        grid_cb.setSpacing(8)

        # 第一列：基礎目標與檔名產生
        grid_cb.addWidget(self.bind_check("t1_only_numbers", _("只搜卡片")), 0, 0)
        grid_cb.addWidget(self.bind_check("t1_gen_txt", _("產生內容物列表(TXT)")), 0, 1)
        grid_cb.addWidget(self.bind_check("t1_gen_csv", _("產生對照表(CSV)")), 0, 2)

        # 第二列：CSV 細部資料內容
        grid_cb.addWidget(self.bind_check("t1_ext_name", _("附帶卡片名稱")), 1, 0)
        grid_cb.addWidget(self.bind_check("t1_ext_desc", _("附帶卡片效果")), 1, 1)
        grid_cb.addWidget(self.bind_check("t1_parse_meta", _("附帶配件名稱")), 1, 2)

        # 第三列：效能與深度掃描
        grid_cb.addWidget(self.bind_check("t1_use_cache", _("優先使用暫存")), 2, 0)
        grid_cb.addWidget(self.bind_check("t1_deep_scan", _("🔥深度掃描 (提取場地/卡套等大檔物件)")), 2, 1, 1, 2)

        # 第四列：黃色強調的視覺配件過濾器
        cb_vis = QCheckBox(_("⚠️ 僅處理場地/卡套/頭像等物件"))
        cb_vis.setStyleSheet("color: #E0C030; font-weight: bold;")
        cb_vis.setChecked(self.config.get("enable_visual_only_filter", False))
        cb_vis.toggled.connect(lambda state: self.config.set("enable_visual_only_filter", state))
        grid_cb.addWidget(cb_vis, 3, 0, 1, 3)

        form_opt.addRow(_("功能選項:"), grid_cb)
        
        box_keys = QHBoxLayout()
        self.t1_lang = QComboBox()
        self.t1_lang.addItems(["zh-tw", "zh-cn", "en-us", "ja-jp", "ko-kr", "fr-fr", "de-de", "it-it", "es-es", "pt-br"])
        self.t1_lang.setEditable(True)
        self.t1_lang.setCurrentText(str(self.config.get("t1_lang", "zh-tw")))
        self.t1_lang.currentTextChanged.connect(lambda t: self.config.set("t1_lang", t.strip().lower()))
        self.t1_lang.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.block_wheelEvent(self.t1_lang)
        
        box_keys.addWidget(QLabel(_("語系:")))
        box_keys.addWidget(self.t1_lang, 1) # 🛡️ 設定權重比例 1，保障獨立空間
        self.t1_xor = QLineEdit(); self.bind_text("t1_xor_key", self.t1_xor)
        box_keys.addWidget(QLabel(_("XOR 密鑰(不知道就別動):")))
        box_keys.addWidget(self.t1_xor, 1) # 🛡️ 設定權重比例 1，平分平坐
        form_opt.addRow(_("語言選項:"), box_keys)
        self.layout.addWidget(grp_opt)

        grp_enrich = QGroupBox(_("補齊/擴充 原有對照表(CSV)"))
        form_enrich = QFormLayout(grp_enrich)
        self.t1_inc_csv_edit = self.make_path_row(form_enrich, _("待擴充的 CSV"), "t1_incomplete_csv", is_file=True, ftype="CSV", placeholder="請選擇待擴充的對照表 CSV 檔案...")
        self.layout.addWidget(grp_enrich)
        
        btns = QHBoxLayout()
        self.btn_run = QPushButton(_("開始掃描")); self.btn_run.clicked.connect(self.run_task)
        self.btn_enrich = QPushButton(_("執行補齊 / 擴充")); self.btn_enrich.clicked.connect(self.run_enrich)
        self.btn_stop = QPushButton(_("停止爆搜 / 中斷作業"))
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet("color: #D83C3C; font-weight: bold;")
        self.btn_stop.clicked.connect(self.stop_task)
        
        btns.addWidget(self.btn_run); btns.addWidget(self.btn_enrich); btns.addWidget(self.btn_stop)
        self.layout.addLayout(btns)
        
        # 🛡️ 宣告 Manager 佔位符
        self._scan_manager = None
        self._scan_stop_event = None

    def stop_task(self):
        if self._scan_stop_event:
            self._scan_stop_event.set()
            self.btn_stop.setEnabled(False)
            self.app.status_lbl.setText(_("狀態：正在中斷作業並釋放資源，請稍候..."))

    def run_task(self):
        c = self.config
        if not os.path.isdir(clean_path(c.get("t1_target_dir"))):
            return QMessageBox.critical(self, _("錯誤"), _("目標資料夾不存在！請確認路徑。"))
            
        import multiprocessing
        self._scan_manager = multiprocessing.Manager()
        self._scan_stop_event = self._scan_manager.Event()
        self.btn_stop.setEnabled(True)
        
        opts = {
            'size_filter': c.get("t1_size_filter"), 
            'min_b': self.get_safe_int("t1_min_size", 50) * 1024, 
            'max_b': self.get_safe_int("t1_max_size", 2400) * 1024,
            'only_num': c.get("t1_only_numbers") and not c.get("enable_visual_only_filter", True),
            'visual_only': c.get("enable_visual_only_filter", True),
            'gen_txt': c.get("t1_gen_txt"), 
            'gen_csv': c.get("t1_gen_csv"),
            'gen_name': c.get("t1_ext_name"), 
            'gen_desc': c.get("t1_ext_desc"), 
            'lang': str(c.get("t1_lang", "")).strip().lower(),
            'use_cache': c.get("t1_use_cache"), 
            'xor_key': self.get_safe_int("t1_xor_key", 61), 
            'parse_meta': c.get("t1_parse_meta"),
            'deep_scan': c.get("t1_deep_scan"),
            'max_workers': c.get("max_threads", "Auto"),
            'stop_event': self._scan_stop_event # 🛡️ 將安全煞車傳遞給底層
        }
        
        def on_scan_finish(count, extra):
            self.btn_stop.setEnabled(False)
            is_aborted = self._scan_stop_event and self._scan_stop_event.is_set()
            
            if self._scan_manager:
                self._scan_manager.shutdown()
                self._scan_manager = None
                
            err_path = None
            if isinstance(extra, dict):
                new_key = extra.get("new_key")
                err_path = extra.get("err_path")
                if new_key is not None and str(new_key) != str(c.get("t1_xor_key")):
                    self.t1_xor.setText(str(new_key))
                    c.save_single_key("t1_xor_key", str(new_key))
            else:
                err_path = extra
                
            if is_aborted:
                msg = _("掃描已由使用者中斷！成功提取數量：{count}").format(count=count)
            else:
                msg = _("掃描完成！成功提取數量：{count}").format(count=count)
                
            ex_json = os.path.join(c.get("t1_out_dir"), "Unknown_Cards_Report.json")
            if os.path.exists(ex_json):
                msg += _("\n\n🚨 發現無法辨識類別的特殊卡片！\n系統已將這些卡片標記為例外，並預設套用 [Effect] 效果怪獸相框。\n已在儲存目錄生成 Unknown_Cards_Report.json，請將此檔回報給開發者。\n若需手動挑選處理，請參考同目錄的 Exception_IDs_List.txt")
                
            if err_path:
                msg += _("\n\n⚠️ 注意：部分檔案解碼發生異常，詳細錯誤日誌已儲存至：\n{path}").format(path=err_path)
            return msg

        self.app.execute_task(self.btn_run, _("掃描中"), MDEngine.task_scan, 
            (c.get("t1_target_dir"), c.get("t1_out_dir"), c.get("t1_txt_name"), c.get("t1_csv_name"), opts), 
            on_scan_finish, next_tab_id="t2_find")

    def run_enrich(self):
        c = self.config
        if not os.path.isfile(clean_path(self.config.get("t1_incomplete_csv"))):
            return QMessageBox.critical(self, _("錯誤"), _("請先選擇有效的待擴充 CSV 檔案！"))
            
        import multiprocessing
        self._scan_manager = multiprocessing.Manager()
        self._scan_stop_event = self._scan_manager.Event()
        self.btn_stop.setEnabled(True)
        
        opts = {
            'size_filter': c.get("t1_size_filter"), 
            'min_b': self.get_safe_int("t1_min_size", 50) * 1024, 
            'max_b': self.get_safe_int("t1_max_size", 2400) * 1024,
            'only_num': c.get("t1_only_numbers") and not c.get("enable_visual_only_filter", True),
            'visual_only': c.get("enable_visual_only_filter", True),
            'gen_txt': False,
            'gen_csv': True, 
            'gen_name': c.get("t1_ext_name"),
            'gen_desc': c.get("t1_ext_desc"),
            'lang': str(c.get("t1_lang", "")).strip().lower(),
            'use_cache': c.get("t1_use_cache"), 
            'xor_key': self.get_safe_int("t1_xor_key", 61), 
            'parse_meta': c.get("t1_parse_meta"),
            'deep_scan': c.get("t1_deep_scan"),
            'max_workers': c.get("max_threads", "Auto"),
            'stop_event': self._scan_stop_event # 🛡️ 將安全煞車傳遞給底層
        }
        
        def on_enrich_finish(ct, e):
            self.btn_stop.setEnabled(False)
            is_aborted = self._scan_stop_event and self._scan_stop_event.is_set()
            
            if self._scan_manager:
                self._scan_manager.shutdown()
                self._scan_manager = None
                
            if is_aborted:
                return _("補齊作業已中斷！共匯出 {count} 筆").format(count=ct)
            return _("CSV 已成功補齊與擴充！共匯出 {count} 筆").format(count=ct)

        self.app.execute_task(self.btn_enrich, _("補齊 CSV 中"), MDEngine.task_enrich, 
            (c.get("t1_incomplete_csv"), c.get("t1_target_dir"), opts), 
            on_enrich_finish)

# ==================== 分頁 2: 找出檔案 ====================
class TabFind(BaseTab):
    def __init__(self, main_app):
        super().__init__(main_app)
        self.layout.addWidget(QLabel(_("【第 2 步】搜尋你想要的內容")))

        grp_mode = QGroupBox(_("操作模式"))
        box_mode = QHBoxLayout(grp_mode)
        
        self.cb_mode = QComboBox()
        # ✨ UI/Data解耦：骨子裡改存為絕對不變的英文邏輯代號
        modes = [
            (_("常規提取"), "MODE_NORMAL"),
            (_("快捷超框切換(這是用來快速替換遊戲原檔的!)"), "MODE_QUICK")
        ]
        for display_name, logic_id in modes:
            self.cb_mode.addItem(display_name, logic_id)
        self.block_wheelEvent(self.cb_mode)
        
        def on_mode_change(idx):
            logic_id = self.cb_mode.itemData(idx) # 取得底層邏輯代號
            is_quick = (logic_id == "MODE_QUICK")
            txt = _("開始自動化超框更改") if is_quick else _("開始提取原檔")
            self.btn_run_top.setText(txt); self.btn_run_bottom.setText(txt)
            
        self.cb_mode.currentIndexChanged.connect(on_mode_change)
        box_mode.addWidget(QLabel(_("選擇模式:"))); box_mode.addWidget(self.cb_mode)
        self.layout.addWidget(grp_mode)

        # 👈 頂部大按鈕
        self.btn_run_top = QPushButton(_("開始提取原檔")); self.btn_run_top.clicked.connect(self.run_task)
        self.layout.addWidget(self.btn_run_top)
        
        grp1 = QGroupBox(_("路徑與儲存"))
        form1 = QFormLayout(grp1)
        self.make_path_row(form1, _("對照表 (CSV)"), "t2_csv_dir", True, "CSV", "csv", placeholder="請選擇全域對照表 CSV 檔案（可於「設定與外觀」保存預設值）...")
        self.make_path_row(form1, _("載入用 TXT"), "t2_txt_dir", True, "TXT", "txt", placeholder="請選擇提取清單 TXT 檔案...")
        self.make_path_row(form1, _("檔案來源 (0000)"), "t2_src_dir", sync_type="src", placeholder="你的槽:\\SteamLibrary\\steamapps\\common\\Yu-Gi-Oh! Master Duel\\LocalData\\你的八字編號\\0000")
        self.make_path_row(form1, _("儲存根目錄"), "t2_out_dir", sync_type="root", placeholder="請輸入或選擇此專案的工作根目錄...")
        self.t2_fold = QLineEdit()
        self.t2_fold.setPlaceholderText(_("\"原檔\"，可依需求自訂名稱(記得去設定按儲存)"))
        self.bind_text("t2_folder_name", self.t2_fold)
        # 【解耦連動】當 Settings 修改原檔名稱時，透過訊號安全更新此 LineEdit
        self.config.signals.sync_folder.connect(lambda p: self.t2_fold.setText(p) if self.t2_fold.text() != p else None)
        form1.addRow(_("新建資料夾名稱:"), self.t2_fold)
        self.layout.addWidget(grp1)
        
        grp2 = QGroupBox(_("物件搜尋與提取清單"))
        vbox2 = QVBoxLayout(grp2)

        self.search_widget = GoogleSearchFilterWidget(self.config, enable_batch_add=True)
        self.search_widget.signals.search_requested.connect(self.execute_advanced_search)
        self.search_widget.signals.page_display_updated.connect(self.update_list_display)
        self.search_widget.signals.add_current_page_requested.connect(lambda page_list: self.append_to_extraction_list("\n".join(page_list)))
        self.search_widget.signals.add_all_results_requested.connect(lambda all_list: self.append_to_extraction_list("\n".join(all_list)))
        vbox2.addWidget(self.search_widget)
        
        self.t2_list = QListWidget()
        self.t2_list.setMinimumHeight(250)
        self.t2_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.t2_list.setSelectionRectVisible(True)       # 👈 啟用藍色選取方框
        self.t2_list.setDragDropMode(QAbstractItemView.NoDragDrop) # 👈 關閉拖動排序以防干擾多選
        self.t2_list.setAutoScroll(False) # 🛡️ 關閉 Qt 預設拖曳捲動，徹底根除與外層海報打架的震盪源頭
        self._t2_drag_filter = LinearDragScrollFilter(self.t2_list, speed_boost=0.15)
        
        # 👈 批次右鍵快速加入
        def batch_add_to_list(pos):
            items = self.t2_list.selectedItems()
            if not items and self.t2_list.itemAt(pos):
                items = [self.t2_list.itemAt(pos)]
            for item in items:
                self.t2_text.appendPlainText(item.text())
        self.t2_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.t2_list.customContextMenuRequested.connect(batch_add_to_list)
        self.t2_list.itemDoubleClicked.connect(lambda item: self.t2_text.appendPlainText(item.text()))
        self.prevent_scroll_propagation(self.t2_list)
        
        btn_add = QPushButton(_("▼ 加入至下方提取清單 ▼")); btn_add.clicked.connect(lambda: [self.t2_text.appendPlainText(i.text()) for i in self.t2_list.selectedItems()])
        
        box_ctrl = QHBoxLayout()
        box_ctrl.addWidget(QLabel(_("欲提取的 ID (換行分隔)")))
        btn_ld = QPushButton(_("載入 TXT")); btn_ld.clicked.connect(self.load_txt); box_ctrl.addWidget(btn_ld)
        btn_nm = QPushButton(_("正規化補名")); btn_nm.clicked.connect(self.norm_txt); box_ctrl.addWidget(btn_nm)

        btn_filter = QPushButton(_("🔍 視覺化篩選")); btn_filter.clicked.connect(self.request_visual_filter); box_ctrl.addWidget(btn_filter)

        self.btn_return_overframe = QPushButton(_("✨ 確認 ID 並返回超框註冊器"))
        self.btn_return_overframe.setStyleSheet("color: #E0C030; font-weight: bold;")
        self.btn_return_overframe.hide() # 預設隱藏，只有從註冊器過來才會顯示
        self.btn_return_overframe.clicked.connect(lambda: [
            self.config.signals.sync_extraction_list.emit(self.t2_text.toPlainText()),
            self.config.signals.request_overframe_return.emit()
        ])
        box_ctrl.addWidget(self.btn_return_overframe)

        # 接收主控台的顯示/隱藏與文字同步指令
        self.config.signals.toggle_overframe_return.connect(self.btn_return_overframe.setVisible)
        self.config.signals.sync_extraction_list.connect(lambda t: self.t2_text.setPlainText(t) if self.t2_text.toPlainText() != t else None)
        
        self.t2_text = QPlainTextEdit()
        self.t2_text.setMinimumHeight(200) # 👈 高度增加至 200px
        self.prevent_scroll_propagation(self.t2_text)
        self.bind_text("t2_extraction_list", self.t2_text)
        vbox2.addWidget(self.t2_list); vbox2.addWidget(btn_add); vbox2.addLayout(box_ctrl); vbox2.addWidget(self.t2_text)
        self.layout.addWidget(grp2)
        
        # 👈 底部大按鈕
        self.btn_run_bottom = QPushButton(_("開始提取原檔")); self.btn_run_bottom.clicked.connect(self.run_task)
        self.layout.addWidget(self.btn_run_bottom)

        # 註冊監聽：當收到其他分頁傳來的追加清單指令時執行
        self.config.signals.append_extraction_list.connect(self.handle_append_extraction)

    def handle_append_extraction(self, new_text):
        """專屬接收器：合併新文字並去重"""
        current_text = self.t2_text.toPlainText().strip()
        combined = (current_text + "\n" + new_text).strip()
        self.t2_text.setPlainText(combined)

    def execute_advanced_search(self, params):
        dummy_map, db = MDEngine.get_csv_data(clean_path(self.config.get("t2_csv_dir")))
        # ✨ 接收全量清單
        all_matches = MDEngine.search_cards_advanced(params, db, search_lang=self.config.get("search_lang", "zh-tw"))
        # 交付給 Widget 處理切片與分頁
        self.search_widget.update_pagination_ui(all_matches, params.get("limit_per_page", 200))

    def update_list_display(self, page_slice):
        # ✨ 0ms 瞬間更新 UI
        self.t2_list.clear()
        for item in page_slice:
            self.t2_list.addItem(item)

    def append_to_extraction_list(self, text_to_add):
        if not text_to_add: return
        current_text = self.t2_text.toPlainText().strip()
        combined = (current_text + "\n" + text_to_add).strip() if current_text else text_to_add
        self.t2_text.setPlainText(combined) 

    def load_txt(self):
        try:
            with open(clean_path(self.config.get("t2_txt_dir")), "r", encoding="utf-8") as f:
                self.t2_text.setPlainText("\n".join([line_text.strip() for line_text in f if MDEngine.extract_id_from_line(line_text)]))
        except Exception: pass

    def norm_txt(self):
        c = self.config
        csv_path = clean_path(c.get("t2_csv_dir"))
        search_lang = c.get("search_lang", "zh-tw")
        
        lookup = {}
        # 🛡️ 安全防護結界：確保 CSV 存在且格式正確，防止無效路徑導致介面崩潰
        if os.path.exists(csv_path):
            try:
                # 遵循約定，使用 dummy_map 接收不需要的回傳值，絕不使用 _ 作為空變數
                dummy_map, db = MDEngine.get_csv_data(csv_path)
                
                # 建立 ID -> (名稱, Hash) 的速查字典 (完美支援字串、副檔名與小寫校驗)
                for card in db:
                    header = card.get('header', [])
                    row = card.get('full_row', [])
                    n_idx = MDEngine.find_lang_column_index(header, search_lang, "Name")
                    
                    c_id = str(card.get('id', '')).strip().lower()
                    c_hash = str(card.get('hash', '')).strip()
                    c_name = row[n_idx] if n_idx != -1 and len(row) > n_idx else ""
                    
                    lookup[c_id] = (c_name, c_hash)
            except Exception:
                pass

        lines = []
        for line in self.t2_text.toPlainText().splitlines():
            line = line.strip()
            if not line:
                lines.append(line)
                continue
                
            # ✨ 直接從原始字串萃取 ID 
            # (避開原本正規表示式切爛巢狀括號導致崩潰的問題)
            card_id_str = MDEngine.extract_id_from_line(line)
            
            if card_id_str:
                card_id_lower = card_id_str.lower()
                # 🛡️ 嚴格精準比對：只比對完全相符的項目，絕對不進行純數字的模糊降級
                if card_id_lower in lookup:
                    c_name, c_hash = lookup[card_id_lower]
                    
                    # 依照有無卡名，精準拼裝出 [Hash] 碼，完美對齊搜尋清單的視覺格式
                    if c_name:
                        lines.append(f"{card_id_str} ({c_name}) [{c_hash}]")
                    else:
                        lines.append(f"{card_id_str} [{c_hash}]")
                else:
                    # 匹配失敗：查無此項目，原封不動保留使用者輸入的原始字串
                    lines.append(line)
            else:
                lines.append(line)
                
        self.t2_text.setPlainText("\n".join(lines))

    def request_visual_filter(self):
        text = self.t2_text.toPlainText().strip()
        if not text:
            return QMessageBox.warning(self, _("警告"), _("提取清單目前是空的，無法進行視覺化篩選！"))
            
        # 呼叫集中化萃取器，利用海象運算子過濾空值
        ids = [extracted for line in text.splitlines() if (extracted := MDEngine.extract_id_from_line(line))]
        
        # 透過 ConfigManager 廣播中介訊號，徹底解耦
        self.config.signals.request_filter_view.emit(ids)

    def run_task(self):
        # 🛡️ 完全使用邏輯代號判斷，免疫翻譯干擾
        if hasattr(self, 'cb_mode') and self.cb_mode.currentData() == "MODE_QUICK":
            return self.run_quick_overframe_chain()
        if not self.t2_text.toPlainText().strip(): self.load_txt()
        
        # 呼叫集中化萃取器
        ids = [extracted for line in self.t2_text.toPlainText().splitlines() if (extracted := MDEngine.extract_id_from_line(line))]
        
        if not ids or not os.path.isfile(clean_path(self.config.get("t2_csv_dir"))) or not os.path.isdir(clean_path(self.config.get("t2_src_dir"))):
            return QMessageBox.critical(self, _("錯誤"), _("請確認提取清單、CSV 字典以及來源目錄皆正確填入！"))
        folder_name = self.config.get("t2_folder_name", "").strip() or "原檔"
        out_d = os.path.join(self.config.get("t2_out_dir"), folder_name)
        # 🛡️ 傳遞 Tuple 同步控制頂部與底部按鈕！
        self.app.execute_task((self.btn_run_top, self.btn_run_bottom), _("提取對應檔案中"), MDEngine.task_find, (self.config.get("t2_csv_dir"), self.config.get("t2_src_dir"), out_d, ids, self.config.get("enable_visual_only_filter", True)), lambda c, e: _("原檔提取完成！成功: {count} 個").format(count=c), next_tab_id="t3_extract")

    def run_quick_overframe_chain(self):
        if not self.t2_text.toPlainText().strip(): self.load_txt()
        
        # 呼叫集中化萃取器
        ids = [extracted for line in self.t2_text.toPlainText().splitlines() if (extracted := MDEngine.extract_id_from_line(line))]
        
        if not ids: return QMessageBox.critical(self, _("錯誤"), _("清單為空！請先加入卡片。"))
        
        c = self.config
        
        # 🛡️ 智慧路徑解析：層層降級，優先參考全域設定，完美落實 DRY 原則
        folder_name = c.get("t2_folder_name", "").strip() or c.get("s_folder_raw", "").strip() or "原檔"
        out_raw_dir = os.path.join(c.get("t2_out_dir"), folder_name)
        
        img_folder = c.get("t3_img_folder", "").strip() or c.get("s_folder_img", "").strip() or "原卡圖"
        out_img_dir = os.path.join(c.get("t2_out_dir"), img_folder)
        
        # 🛡️ 擷取同步的根目錄，供後續封裝回 Bundle 時使用
        root_dir = clean_path(c.get("t4_root_dir")) or clean_path(c.get("t2_out_dir"))
        mod_folder = c.get("t4_mod_name", "").strip() or c.get("s_folder_mod", "").strip() or "卡圖改"
        mod_dir = MDEngine.resolve_path(root_dir, mod_folder)
        
        def step1_find_done(s, ct, e):
            if not s: return QMessageBox.critical(self, _("錯誤"), _("尋找檔案失敗: ") + str(ct))
            # 💡 修復：將 exp_backup 重新設定為 True，確實產出「文件備份」。
            # 💡 同時確保 visual_only 為 False，避免純數字 ID 被過濾掉。
            self.app.execute_task((self.btn_run_top, self.btn_run_bottom), _("[自動化] 提取圖片與備份中"), MDEngine.task_extract,
                (out_raw_dir, img_folder, c.get("s_folder_backup", "").strip() or "文件備份", c.get("s_csv_mapping", "").strip() or "2DTexture_Mapping.csv",
                 False, True, False, True, c.get("t2_csv_dir"), False), step2_extract_done, is_chain=True)

        def step2_extract_done(s, ct, e):
            if not s: return QMessageBox.critical(self, _("錯誤"), _("提取圖片失敗: ") + str(ct))
            os.makedirs(mod_dir, exist_ok=True)
            targets = []
            for file in os.listdir(out_img_dir):
                base_id = os.path.splitext(file)[0].split('_')[0]
                if base_id in ids and file.lower().endswith(('.png', '.jpg')):
                    try:
                        shutil.copy2(os.path.join(out_img_dir, file), os.path.join(mod_dir, file))
                        targets.append(file)
                    except Exception: pass
            if not targets:
                return QMessageBox.warning(self, _("警告"), _("提取後沒有找到符合 ID 的圖片。"))
            
            full_options = {
                "opacities": {
                    "periframe": float(c.get("t8_op_periframe", 1.0)), "namebox": float(c.get("t8_op_namebox", 1.0)),
                    "artframe": float(c.get("t8_op_artframe", 1.0)), "effframe": float(c.get("t8_op_effframe", 1.0)),
                    "effbox": float(c.get("t8_op_effbox", 1.0)), "background": float(c.get("t8_op_background", 1.0))
                },
                "ch_x": c.get("t8_adv_ch_x", 0), "ch_y": c.get("t8_adv_ch_y", 0), "ch_s": c.get("t8_adv_ch_s", 100), "ch_rot": c.get("t8_adv_ch_rot", 0),
                "bg_x": c.get("t8_adv_bg_x", 0), "bg_y": c.get("t8_adv_bg_y", 0), "bg_s": c.get("t8_adv_bg_s", 100), "bg_rot": c.get("t8_adv_bg_rot", 0),
                "bg_color": c.get("t8_adv_bg_color", "#FF000000"),
                "z_order": c.get("t8_adv_z_order", ["CH_LAYER", "PeriFrame", "NameBox", "EffFrame", "ArtFrame", "EffBox", "BackGround", "BG_LAYER"]),
                "masks": {
                    cat: {
                        p: c.get(f"t8_{prefix}_{p}", d)
                        for p, d in zip(
                            ["PeriFrame", "NameBox", "ArtFrame", "EffFrame", "EffBox", "BackGround"],
                            [True, False, True, True, False, False]
                        )
                    }
                    for cat, prefix in [("prev", "foil_prev"), ("bake", "foil_bake"), ("dirty", "adv_mask")]
                },
                "foil_params": {
                    "sim_enable": c.get("t8_adv_foil_sim", False),
                    "bake_enable": c.get("t8_foil_bake_enable", False),
                    "palette": c.get("t8_foil_palette", "PALETTE_OPAL"),
                    "base_light": c.get("t8_foil_base_light", 40),
                    "sharpness": c.get("t8_foil_sharpness", 10),
                    "blend_mode": c.get("t8_foil_blend_mode", "BLEND_SOFT"),
                    "intensity": c.get("t8_foil_intensity", 100),
                    "saturation": c.get("t8_foil_saturation", 120),
                    "frequency": c.get("t8_foil_frequency", 10.0),
                    "angle": c.get("t8_foil_angle", 45)
                },
                "is_preview": False
            }
            
            bk_folder = c.get("t8_backup_folder", "").strip() or "修改前原檔"
            bk_dir_img = os.path.join(mod_dir, bk_folder)
            
            self.app.execute_task((self.btn_run_top, self.btn_run_bottom), _("[自動化] 超框處理中"), MDEngine.task_post_process,
                (mod_dir, bk_dir_img, c.get("t8_enable_backup"), int(self.get_safe_int("t8_padding_pct", 25)), targets, "quick_overframe", clean_path(c.get("t2_csv_dir")), full_options), step3_process_done, is_chain=True)

        def step3_process_done(s, ct, e):
            if not s: return QMessageBox.critical(self, _("錯誤"), _("超框處理失敗: ") + str(ct))
            
            # 💡 修復：將目標重新導回真正的「文件備份」資料夾，確實遵從你的工具設計
            bk_folder = c.get("t4_backup_name", "").strip() or c.get("s_folder_backup", "").strip() or "文件備份"
            bk_dir = MDEngine.resolve_path(root_dir, bk_folder)
            out_folder = c.get("s_folder_out", "").strip() or "改完的文件"
            
            self.app.execute_task((self.btn_run_top, self.btn_run_bottom), _("[自動化] 替換圖片至檔案中"), MDEngine.task_replace,
                (c.get("t2_csv_dir"), root_dir, bk_dir, mod_dir, out_folder), step4_replace_done, is_chain=True)
                
        def step4_replace_done(s, ct, e):
            if not s: return QMessageBox.critical(self, _("錯誤"), _("替換圖檔失敗: ") + str(ct))
            
            # 任務全部大功告成！發送訊號並跳轉
            self.config.signals.request_overframe_register.emit("\n".join(ids))
            QMessageBox.information(self, _("自動化完成"), _("超框處理與圖檔替換皆已完畢！\n修改後的 Bundle 檔案已輸出至「改完的文件」。\n已為您跳轉至超框註冊器，請確認並輸出註冊表。"))
            self.app.select_tab("t13_overframe")
            
        # 🚀 啟動第一步 (強制將 visual_only 設為 False 確保卡片不被過濾)
        self.app.execute_task((self.btn_run_top, self.btn_run_bottom), _("[自動化] 尋找原檔中"), MDEngine.task_find, 
            (c.get("t2_csv_dir"), c.get("t2_src_dir"), out_raw_dir, ids, False), step1_find_done, is_chain=True)

# ==================== 分頁 3: 提取資料 ====================
class TabExtract(BaseTab):
    def __init__(self, main_app):
        super().__init__(main_app)
        self.layout.addWidget(QLabel(_("【第 3 步】內容物提取")))
        grp = QGroupBox(_("設定"))
        form = QFormLayout(grp)
        self.t3_src_edit = self.make_path_row(form, _("欲提取檔案所在資料夾"), "t3_src_var", placeholder="這裡輸入你的工作路徑根目錄\\原檔")
        self.config.signals.sync_t3_src.connect(lambda p: self.t3_src_edit.setText(p) if self.t3_src_edit.text() != p else None)
        
        box = QHBoxLayout()
        box.addWidget(self.bind_check("t3_exp_csv", _("匯出 CSV")))
        box.addWidget(self.bind_check("t3_exp_img", _("匯出圖片")))
        box.addWidget(self.bind_check("t3_exp_txt", _("匯出文字資料")))
        box.addWidget(self.bind_check("t3_exp_backup", _("備份檔案")))
        form.addRow(self.bind_visual_filter())
        form.addRow(box)
        
        self.t3_img = QLineEdit(); self.bind_text("t3_img_folder", self.t3_img)
        self.t3_img.setPlaceholderText(_("\"原卡圖\"，可依需求自訂名稱(記得去設定按儲存)"))
        self.layout.addWidget(grp)
        
        self.btn_run = QPushButton(_("開始提取內容物")); self.btn_run.clicked.connect(self.run_task)
        self.layout.addWidget(self.btn_run)

    def run_task(self):
        c = self.config
        src_dir = clean_path(c.get("t3_src_var"))

        # 🛡️ 危險路徑防呆：偵測是否指向遊戲 0000 總目錄
        src_lower = src_dir.lower().replace("  ", " ") # 處理雙空白
        if "yu-gi-oh! master duel" in src_lower or ("steamapps" in src_lower and "0000" in src_lower):
            reply = QMessageBox.warning(
                self, _("危險操作警告"), 
                _("您目前選擇的來源似乎是遊戲的原裝 0000 目錄！\n\n強烈建議不要直接對整個遊戲目錄進行提取，這將耗費極長的時間並產生數十 GB 的碎小檔案，極可能導致電腦卡死。\n\n您確定要強制繼續嗎 (風險自負)？"),
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        def on_succ(ct, e):
            if c.get("auto_switch_tab"):
                csv_path = clean_path(c.get("t2_csv_dir"))
                img_dir = os.path.join(os.path.dirname(src_dir), c.get("t3_img_folder", "原卡圖"))
                if MDEngine.get_pendulum_list(csv_path, img_dir):
                    QTimer.singleShot(500, lambda: [
                        self.config.signals.set_t8_mode.emit("MODE_PENDULUM"), # 🛡️ 傳遞底層邏輯代號
                        self.app.select_tab("t8_pendulum"),
                        self.config.signals.request_pendulum_reload.emit()
                    ])
                else:
                    QTimer.singleShot(500, lambda: self.app.select_tab("t4_replace"))
            return _("提取完成！成功: {count} 筆").format(count=ct)

        # 🛡️ 精準注入主對照表路徑給底層
        self.app.execute_task(self.btn_run, _("提取中"), MDEngine.task_extract, 
            (c.get("t3_src_var"), c.get("t3_img_folder"), c.get("s_folder_backup"), c.get("s_csv_mapping"), 
             c.get("t3_exp_csv"), c.get("t3_exp_img"), c.get("t3_exp_txt", True), c.get("t3_exp_backup"), c.get("t2_csv_dir"), c.get("enable_visual_only_filter", True)), on_succ)

# ==================== 分頁 4: 更改卡圖 ====================
class TabReplace(BaseTab):
    def __init__(self, main_app):
        super().__init__(main_app)
        self.layout.addWidget(QLabel(_("【第 4 步】圖檔替換")))
        grp = QGroupBox(_("路徑設定"))
        form = QFormLayout(grp)
        self.make_path_row(form, _("字典 (CSV) 檔案"), "t4_csv_dir", True, "CSV", "csv", placeholder="請選擇全域對照表 CSV 檔案（可於「設定與外觀」保存預設值）...")
        self.make_path_row(form, _("專案根目錄位置"), "t4_root_dir", sync_type="root", placeholder="請輸入或選擇此專案的工作根目錄...")
        
        self.t4_bk = QLineEdit(); self.bind_text("t4_backup_name", self.t4_bk); form.addRow(_("備份位置:"), self.t4_bk)
        self.t4_bk.setPlaceholderText(_("\"文件備份\"，可依需求自訂名稱(記得去設定按儲存)"))
        
        self.t4_mod = QLineEdit(); self.bind_text("t4_mod_name", self.t4_mod); form.addRow(_("改圖位置:"), self.t4_mod)
        self.t4_mod.setPlaceholderText(_("\"卡圖改\"，可依需求自訂名稱(記得去設定按儲存)"))
        self.layout.addWidget(grp)
        
        self.btn_run = QPushButton(_("開始替換")); self.btn_run.clicked.connect(self.run_task)
        self.layout.addWidget(self.btn_run)

    def run_task(self):
        c = self.config
        root = clean_path(c.get("t4_root_dir"))
        if not os.path.isdir(root) or not os.path.isfile(clean_path(c.get("t4_csv_dir"))):
            return QMessageBox.critical(self, _("錯誤"), _("根目錄或 CSV 字典路徑設定有誤！"))
        
        # 🛡️ 加入 .strip() or "預設名稱" 防呆，防止輸出到根目錄
        bk_dir = MDEngine.resolve_path(root, c.get("t4_backup_name", "").strip() or "文件備份")
        mod_dir = MDEngine.resolve_path(root, c.get("t4_mod_name", "").strip() or "卡圖改")
        
        self.app.execute_task(self.btn_run, _("圖片替換中"), MDEngine.task_replace, 
            (c.get("t4_csv_dir"), root, bk_dir, mod_dir, c.get("s_folder_out", "").strip() or "改完的文件"), 
            lambda ct, e: _("替換完成！產出 {count} 個檔案").format(count=ct), next_tab_id="t5_package")

# ==================== 分頁 5: 封裝模組 ====================
class TabPackage(BaseTab):
    def __init__(self, main_app):
        super().__init__(main_app)
        self.layout.addWidget(QLabel(_("【第 5 步】打包檔案")))
        grp = QGroupBox(_("設定"))
        form = QFormLayout(grp)
        self.make_path_row(form, _("字典 (CSV) 檔案"), "t5_csv_dir", True, "CSV", "csv", placeholder="請選擇全域對照表 CSV 檔案（可於「設定與外觀」保存預設值）...")
        self.make_path_row(form, _("專案根目錄"), "t5_root_dir", sync_type="root", placeholder="請輸入或選擇此專案的工作根目錄...")
        
        self.t5_mod = QLineEdit(); self.bind_text("t5_mod_folder_name", self.t5_mod); form.addRow(_("資料夾命名:"), self.t5_mod)
        self.t5_mod.setPlaceholderText(_("可依需求自訂資料夾名稱(記得去設定按儲存)"))
        box_options = QHBoxLayout()
        box_options.addWidget(self.bind_check("t5_include_mod_folder", _("附帶「卡圖改」")))
        box_options.addWidget(self.bind_check("t5_include_readme", _("附帶 ReadMe.txt")))
        box_options.addWidget(self.bind_check("t5_pack_zip", _("同時壓縮成 ZIP")))
        form.addRow(box_options)
        
        if not self.config.get("t5_readme_text"): self.config.set("t5_readme_text", DEFAULT_README)
        self.t5_readme = QPlainTextEdit(); self.bind_text("t5_readme_text", self.t5_readme)
        form.addRow(_("ReadMe 預設文字:"), self.t5_readme)
        self.layout.addWidget(grp)
        
        self.btn_run = QPushButton(_("開始打包")); self.btn_run.clicked.connect(self.run_task)
        self.layout.addWidget(self.btn_run)

    def run_task(self):
        c = self.config
        root = clean_path(c.get("t5_root_dir"))
        mod_dir = MDEngine.resolve_path(root, c.get("t4_mod_name", "").strip() or "卡圖改")
        
        self.app.execute_task(self.btn_run, _("自動建立前綴目錄"), MDEngine.task_package, 
            (root, c.get("t5_mod_folder_name", "").strip() or "ModFolder", c.get("t5_readme_text"), mod_dir, 
             c.get("t5_pack_zip"), c.get("t5_csv_dir"), c.get("s_folder_backup", "").strip() or "文件備份", 
             c.get("s_folder_out", "").strip() or "改完的文件", c.get("t8_backup_folder", "").strip() or "修改前原檔",
             c.get("t5_include_mod_folder"), c.get("t5_include_readme"), c.get("s_csv_mapping", "2DTexture_Mapping.csv")), 
            lambda ct, e: _("打包完成！"))

# ==================== 分頁 8: 靈擺與超框卡圖後處理 ====================
class TabPendulum(BaseTab):
    def __init__(self, main_app):
        super().__init__(main_app)
        from PySide6.QtWidgets import QSpinBox, QDoubleSpinBox, QColorDialog
        
        self.layout.addWidget(QLabel(_("【第 8 步】靈擺、超框與卡片動畫後處理")))
        
        # 🛡️ 狀態鎖初始化：防範滑桿連動與預覽暴衝
        self._preview_running = False
        self._pending_preview = False
        
        # ─── 1. 專案與路徑設定區 (全模式共用) ───
        grp = QGroupBox(_("專案與路徑設定"))
        form = QFormLayout(grp)
        
        self.cb_mode = QComboBox()
        modes = [
            (_("靈擺卡圖後處理 (卡圖改)"), "MODE_PENDULUM"),
            (_("超框卡圖後處理 (卡圖改)"), "MODE_OVERFRAME"),
            (_("卡片動畫後處理 (卡圖改)"), "MODE_CUTIN"),
            (_("靈擺原卡圖處理 (原卡圖)"), "MODE_PENDULUM_ORIGINAL_CROP")
        ]
        for display_name, logic_id in modes:
            self.cb_mode.addItem(display_name, logic_id)
        self.block_wheelEvent(self.cb_mode)
        form.addRow(_("處理模式:"), self.cb_mode)

        self.t8_csv = self.make_path_row(form, _("字典 (CSV)"), "t8_csv_dir", True, "CSV", "csv", placeholder="請選擇全域對照表 CSV 檔案（可於「設定與外觀」保存預設值）...")
        self.t8_root = self.make_path_row(form, _("專案根目錄"), "t8_root_dir", sync_type="root", placeholder="請輸入或選擇此專案的工作根目錄...")
        
        # 動態雙欄位設計
        self.lbl_mod = QLabel(_("改圖位置:"))
        self.t8_mod = QLineEdit(); self.bind_text("t8_mod_dir", self.t8_mod)
        self.t8_mod.setPlaceholderText(_("\"卡圖改\"，可依需求自訂名稱(記得去設定按儲存)"))
        form.addRow(self.lbl_mod, self.t8_mod)

        self.lbl_img = QLabel(_("原卡圖位置:"))
        self.t8_img = QLineEdit(); self.bind_text("s_folder_img", self.t8_img)
        self.t8_img.setPlaceholderText(_("\"原卡圖\"，可依需求自訂名稱(記得去設定按儲存)"))
        form.addRow(self.lbl_img, self.t8_img)
        
        self.t8_pad = QLineEdit(); self.bind_text("t8_padding_pct", self.t8_pad)
        form.addRow(_("靈擺填充比例 (%):"), self.t8_pad)
        
        box_bk = QHBoxLayout(); box_bk.addWidget(self.bind_check("t8_enable_backup", _("啟用備份  ")))
        self.t8_bk = QLineEdit(); self.bind_text("t8_backup_folder", self.t8_bk)
        self.t8_bk.setPlaceholderText(_("\"修改前原檔\"，可依需求自訂名稱(記得去設定按儲存)"))
        box_bk.addWidget(QLabel(_("備份資料夾命名:"))); box_bk.addWidget(self.t8_bk)
        form.addRow(box_bk)
        self.layout.addWidget(grp)

        # ─── 2. 超框要素透明度控制區 (僅超框) ───
        self.grp_op = QGroupBox(_("超框要素透明度控制 (0~100%) - PSD 專用"))
        form_op = QFormLayout(self.grp_op)
        
        def add_op_row(label_text, config_key):
            sl = QSlider(Qt.Horizontal); sl.setRange(0, 100)
            sp = QSpinBox(); sp.setRange(0, 100); sp.setSuffix(" %")
            val = int(self.config.get(config_key, 1.0) * 100)
            sl.setValue(val); sp.setValue(val)
            sl.valueChanged.connect(sp.setValue); sp.valueChanged.connect(sl.setValue)
            sl.valueChanged.connect(lambda v, k=config_key: [self.config.set(k, v / 100.0), self.preview_timer.start() if hasattr(self, 'preview_timer') else None])
            self.block_slider_wheel(sl); self.block_wheelEvent(sp)
            box = QHBoxLayout(); box.addWidget(sl); box.addWidget(sp)
            form_op.addRow(label_text, box)

        add_op_row(_("外框 (PeriFrame):"), "t8_op_periframe")
        add_op_row(_("卡名欄 (NameBox):"), "t8_op_namebox")
        add_op_row(_("卡圖框 (ArtFrame):"), "t8_op_artframe")
        add_op_row(_("效果框 (EffFrame):"), "t8_op_effframe")
        add_op_row(_("效果文字欄 (EffBox):"), "t8_op_effbox")
        add_op_row(_("卡底背景 (BackGround):"), "t8_op_background")
        self.layout.addWidget(self.grp_op)

        # ─── 動態雙重控制項輔助器 (DRY) ───
        def add_dual(lbl_text, cfg_key, min_v, max_v, is_float, suffix, target_layout):
            box = QHBoxLayout()
            sl = QSlider(Qt.Horizontal)
            sl.setRange(int(min_v*100) if is_float else min_v, int(max_v*100) if is_float else max_v)
            sp = QDoubleSpinBox() if is_float else QSpinBox()
            sp.setRange(min_v, max_v); sp.setSuffix(suffix)
            if is_float:
                sp.setDecimals(2)
                sp.setSingleStep(0.01)
            
            val = self.config.get(cfg_key, min_v)
            sp.setValue(val); sl.setValue(int(val*100) if is_float else int(val))
            
            def on_sl_change(v):
                target = v/100.0 if is_float else v
                if abs(sp.value() - target) > 0.001: sp.setValue(target)
                
            def on_sp_change(v):
                target = int(v*100) if is_float else int(v)
                if sl.value() != target: sl.setValue(target)
                self.config.set(cfg_key, v)
                
            sl.valueChanged.connect(on_sl_change)
            sp.valueChanged.connect(on_sp_change)
            self.block_slider_wheel(sl); self.block_wheelEvent(sp)
            box.addWidget(sl); box.addWidget(sp)
            target_layout.addRow(lbl_text, box)
            
            # 連動預覽
            sl.valueChanged.connect(lambda dummy_val: self.preview_timer.start() if hasattr(self, 'preview_timer') else None)
            sp._slider = sl
            return sp

        # ─── 3. 閃卡光澤與遮罩設定 ───
        self.btn_toggle_foil_studio = QPushButton(_("▼ 閃卡光澤與遮罩設定  [展開]"))
        self.btn_toggle_foil_studio.setCheckable(True)
        self.btn_toggle_foil_studio.setChecked(False)
        self.btn_toggle_foil_studio.setStyleSheet("color: #FF5A9B; font-weight: bold; margin-top: 5px;")
        
        self.grp_foil_studio = QGroupBox(_("閃卡光澤與遮罩設定"))
        v_foil = QVBoxLayout(self.grp_foil_studio)

        grid_matrix = QGridLayout()
        headers = [_("目標部件"), _("預覽模擬 (Preview)"), _("寫入貼圖 (Bake)"), _("透明化遮罩 (Alpha 0)")]
        for col, text in enumerate(headers):
            lbl = QLabel(text); lbl.setStyleSheet("color: #2CC985; font-weight: bold;")
            grid_matrix.addWidget(lbl, 0, col)
            
        parts = [
            ("PeriFrame", _("外框 (PeriFrame)")), ("NameBox", _("卡名欄 (NameBox)")),
            ("ArtFrame", _("卡圖框 (ArtFrame)")), ("EffFrame", _("效果框 (EffFrame)")),
            ("EffBox", _("效果文字欄 (EffBox)")), ("BackGround", _("卡底背景 (BackGround)"))
        ]
        
        self.matrix_cbs = {"prev": {}, "bake": {}, "dirty": {}}
        for row, (logic_id, label_text) in enumerate(parts, start=1):
            grid_matrix.addWidget(QLabel(label_text), row, 0)
            
            cb_p = self.bind_check(f"t8_foil_prev_{logic_id}", "")
            cb_b = self.bind_check(f"t8_foil_bake_{logic_id}", "")
            cb_d = self.bind_check(f"t8_adv_mask_{logic_id}", "")
            
            self.matrix_cbs["prev"][logic_id] = cb_p
            self.matrix_cbs["bake"][logic_id] = cb_b
            self.matrix_cbs["dirty"][logic_id] = cb_d
            
            for cb in (cb_p, cb_b, cb_d):
                cb.toggled.connect(lambda dummy_state: self.preview_timer.start() if hasattr(self, 'preview_timer') else None)
                
            grid_matrix.addWidget(cb_p, row, 1); grid_matrix.addWidget(cb_b, row, 2); grid_matrix.addWidget(cb_d, row, 3)
            
        v_foil.addLayout(grid_matrix)
        
        h_matrix_btn = QHBoxLayout()
        btn_std_frames = QPushButton(_("✨ 標準三大框 (推薦)")); btn_std_frames.setStyleSheet("color: #4AA4FF;")
        def set_std_frames():
            for cat in ["prev", "bake", "dirty"]:
                for logic_id, cb in self.matrix_cbs[cat].items():
                    cb.setChecked(logic_id in ["PeriFrame", "ArtFrame", "EffFrame"])
        btn_std_frames.clicked.connect(set_std_frames)
        
        btn_sync_dirty = QPushButton(_("🔗 同步套用至透明化")); btn_sync_dirty.setStyleSheet("color: #E0C030;")
        def sync_dirty():
            for logic_id, cb in self.matrix_cbs["dirty"].items():
                cb.setChecked(self.matrix_cbs["bake"][logic_id].isChecked())
        btn_sync_dirty.clicked.connect(sync_dirty)
        
        btn_all_true = QPushButton(_("全選")); btn_all_true.clicked.connect(lambda dummy_val=False: [cb.setChecked(True) for cat in self.matrix_cbs.values() for cb in cat.values()])
        btn_all_false = QPushButton(_("全清")); btn_all_false.clicked.connect(lambda dummy_val=False: [cb.setChecked(False) for cat in self.matrix_cbs.values() for cb in cat.values()])
        
        h_matrix_btn.addWidget(btn_std_frames); h_matrix_btn.addWidget(btn_sync_dirty); h_matrix_btn.addWidget(btn_all_true); h_matrix_btn.addWidget(btn_all_false)
        v_foil.addLayout(h_matrix_btn)
        
        form_foil = QFormLayout()
        
        self.cb_foil_palette = QComboBox()
        for disp_name, logic_id in [
            (_("珍珠粉彩 (Pastel Opal)"), "PALETTE_OPAL"),
            (_("霓虹光譜 (Vivid Rainbow)"), "PALETTE_RAINBOW"),
            (_("香檳金 (Champagne Gold)"), "PALETTE_GOLD"),
            (_("白金鑽 (Platinum Silver)"), "PALETTE_SILVER")
        ]: self.cb_foil_palette.addItem(disp_name, logic_id)
        idx_pal = self.cb_foil_palette.findData(self.config.get("t8_foil_palette", "PALETTE_OPAL"))
        if idx_pal >= 0: self.cb_foil_palette.setCurrentIndex(idx_pal)
        self.cb_foil_palette.currentIndexChanged.connect(lambda idx: [self.config.set("t8_foil_palette", self.cb_foil_palette.itemData(idx)), self.preview_timer.start() if hasattr(self, 'preview_timer') else None])
        self.block_wheelEvent(self.cb_foil_palette)
        form_foil.addRow(_("光譜風格:"), self.cb_foil_palette)

        self.cb_foil_blend = QComboBox()
        for disp_name, logic_id in [
            (_("柔光混合 (Soft Blend)"), "BLEND_SOFT"),
            (_("強光疊加 (Vivid Glow)"), "BLEND_VIVID")
        ]: self.cb_foil_blend.addItem(disp_name, logic_id)
        idx_blend = self.cb_foil_blend.findData(self.config.get("t8_foil_blend_mode", "BLEND_SOFT"))
        if idx_blend >= 0: self.cb_foil_blend.setCurrentIndex(idx_blend)
        self.cb_foil_blend.currentIndexChanged.connect(lambda idx: [self.config.set("t8_foil_blend_mode", self.cb_foil_blend.itemData(idx)), self.preview_timer.start() if hasattr(self, 'preview_timer') else None])
        self.block_wheelEvent(self.cb_foil_blend)
        form_foil.addRow(_("混色模式:"), self.cb_foil_blend)

        self.foil_base_light = add_dual(_("珠光基底明度:"), "t8_foil_base_light", 0, 100, False, " %", form_foil)
        self.foil_sharpness = add_dual(_("高光聚光度:"), "t8_foil_sharpness", 10, 100, False, "", form_foil)
        self.foil_intensity = add_dual(_("光澤強度:"), "t8_foil_intensity", 0, 500, False, " %", form_foil)
        self.foil_intensity.setRange(0, 9999)
        self.foil_saturation = add_dual(_("色彩濃度/飽和度:"), "t8_foil_saturation", 0, 500, False, " %", form_foil)
        self.foil_saturation.setRange(0, 9999)
        self.foil_frequency = add_dual(_("光斑頻率:"), "t8_foil_frequency", 0.1, 100.0, True, "", form_foil)
        self.foil_frequency.setRange(0.01, 999.0)
        self.foil_angle = add_dual(_("光照角度:"), "t8_foil_angle", -360, 360, False, " °", form_foil)
        self.foil_angle.setRange(-360, 360)
        
        btn_foil_rst = QPushButton(_("🔄 重設參數"))
        def reset_foil_params():
            idx_pal = self.cb_foil_palette.findData(self.config.get("t8_foil_palette", "PALETTE_OPAL"))
            if idx_pal >= 0: self.cb_foil_palette.setCurrentIndex(idx_pal)
            idx_blend = self.cb_foil_blend.findData(self.config.get("t8_foil_blend_mode", "BLEND_SOFT"))
            if idx_blend >= 0: self.cb_foil_blend.setCurrentIndex(idx_blend)
            
            self.foil_base_light.setValue(self.config.get("t8_foil_base_light", 60))
            self.foil_sharpness.setValue(self.config.get("t8_foil_sharpness", 20))
            self.foil_intensity.setValue(self.config.get("t8_foil_intensity", 200))
            self.foil_saturation.setValue(self.config.get("t8_foil_saturation", 130))
            self.foil_frequency.setValue(self.config.get("t8_foil_frequency", 5.0))
            self.foil_angle.setValue(self.config.get("t8_foil_angle", 60))
            if hasattr(self, 'preview_timer'): self.preview_timer.start()
            
        btn_foil_rst.clicked.connect(lambda dummy_val=False: reset_foil_params())
        form_foil.addRow(btn_foil_rst)
        
        v_foil.addLayout(form_foil)
        
        self.btn_toggle_foil_studio.toggled.connect(lambda checked: [
            self.grp_foil_studio.setVisible(checked),
            self.btn_toggle_foil_studio.setText(_("▲ 閃卡光澤與遮罩設定  [收合]") if checked else _("▼ 閃卡光澤與遮罩設定  [展開]"))
        ])
        
        self.layout.addWidget(self.btn_toggle_foil_studio)
        self.grp_foil_studio.hide()
        self.layout.addWidget(self.grp_foil_studio)

        # ─── 4. 統一即時預覽畫布區 (超框/動畫共用) ───
        self.btn_toggle_preview = QPushButton(_("👁️ 展開/隱藏 即時預覽面板"))
        self.btn_toggle_preview.setCheckable(True); self.btn_toggle_preview.setChecked(False)
        self.btn_toggle_preview.setStyleSheet("color: #2CC985; font-weight: bold; margin-top: 15px;")
        
        def on_preview_toggled(checked):
            self.preview_widget.setVisible(checked)
            if checked: self.update_preview()
            
        self.btn_toggle_preview.toggled.connect(on_preview_toggled)
        self.layout.addWidget(self.btn_toggle_preview)

        self.preview_widget = QWidget(); v_prev = QVBoxLayout(self.preview_widget)
        h_prev_path = QHBoxLayout()
        self.edit_prev_path = QLineEdit()
        self.edit_prev_path.setPlaceholderText(_("請選擇測試圖片或素材 (動畫後處理支援 PSD/MP4/GIF/靜態圖)"))
        btn_prev_browse = QPushButton(_("📂 瀏覽")); btn_prev_browse.clicked.connect(self.browse_preview)
        h_prev_path.addWidget(QLabel(_("測試素材:"))); h_prev_path.addWidget(self.edit_prev_path); h_prev_path.addWidget(btn_prev_browse)
        v_prev.addLayout(h_prev_path)

        self.lbl_preview = QLabel(_("載入素材後將在此顯示預覽 (處理中請勿頻繁切換分頁)"))
        self.lbl_preview.setAlignment(Qt.AlignCenter); self.lbl_preview.setMinimumHeight(400)
        self.lbl_preview.setStyleSheet("background-color: #1A1A1A; border: 1px dashed #444; border-radius: 8px;")
        v_prev.addWidget(self.lbl_preview)
        self.chk_foil_sim = self.bind_check("t8_adv_foil_sim", _("模擬遊戲內閃卡光澤"))
        self.chk_foil_sim.setStyleSheet("color: #4AA4FF; font-weight: bold;")
        self.chk_foil_sim.toggled.connect(lambda dummy_state: self.preview_timer.start() if hasattr(self, 'preview_timer') else None)
        v_prev.addWidget(self.chk_foil_sim)
        self.layout.addWidget(self.preview_widget)

        self.preview_timer = QTimer(self); self.preview_timer.setInterval(200); self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self.update_preview)
        self.edit_prev_path.textChanged.connect(lambda dummy_val: self.preview_timer.start())
        self.cb_mode.currentTextChanged.connect(lambda dummy_val: self.preview_timer.start())

        # ─── 5. 進階雙圖層超框工坊 ───
        self.btn_toggle_adv = QPushButton(_("▼ 進階雙圖層超框工坊  [展開]"))
        self.btn_toggle_adv.setCheckable(True); self.btn_toggle_adv.setChecked(False)
        self.btn_toggle_adv.setStyleSheet("color: #E0C030; font-weight: bold; margin-top: 5px;")
        self.btn_toggle_adv.toggled.connect(lambda checked: [
            self.grp_adv_studio.setVisible(checked),
            self.btn_toggle_adv.setText(_("▲ 進階雙圖層超框工坊  [收合]") if checked else _("▼ 進階雙圖層超框工坊  [展開]"))
        ])
        self.layout.addWidget(self.btn_toggle_adv)

        self.grp_adv_studio = QWidget()
        v_adv = QVBoxLayout(self.grp_adv_studio)

        grp_ch = QGroupBox(_("角色圖層設定 (-ch)")); form_ch = QFormLayout(grp_ch)
        self.adv_ch_x = add_dual(_("X 軸平移:"), "t8_adv_ch_x", -2000, 2000, False, " px", form_ch)
        self.adv_ch_y = add_dual(_("Y 軸平移:"), "t8_adv_ch_y", -2000, 2000, False, " px", form_ch)
        self.adv_ch_s = add_dual(_("縮放比例:"), "t8_adv_ch_s", 1, 500, False, " %", form_ch)
        self.adv_ch_rot = add_dual(_("旋轉角度:"), "t8_adv_ch_rot", -360, 360, False, " °", form_ch)
        btn_reset_ch = QPushButton(_("🔄 重設參數"))
        btn_reset_ch.clicked.connect(lambda dummy_val=False: [self.adv_ch_x.setValue(0), self.adv_ch_y.setValue(0), self.adv_ch_s.setValue(100), self.adv_ch_rot.setValue(0)])
        form_ch.addRow(btn_reset_ch); v_adv.addWidget(grp_ch)

        grp_bg = QGroupBox(_("背景圖層設定 (-bg)")); form_bg = QFormLayout(grp_bg)
        self.adv_bg_x = add_dual(_("X 軸平移:"), "t8_adv_bg_x", -2000, 2000, False, " px", form_bg)
        self.adv_bg_y = add_dual(_("Y 軸平移:"), "t8_adv_bg_y", -2000, 2000, False, " px", form_bg)
        self.adv_bg_s = add_dual(_("縮放比例:"), "t8_adv_bg_s", 1, 500, False, " %", form_bg)
        self.adv_bg_rot = add_dual(_("旋轉角度:"), "t8_adv_bg_rot", -360, 360, False, " °", form_bg)
        
        self.btn_adv_bg_color = QPushButton(_("🎨 選擇無背景純色板顏色"))
        self.btn_adv_bg_color.setStyleSheet(f"background-color: {self.config.get('t8_adv_bg_color', '#FF000000')}; color: white;")
        def pick_adv_bg_color():
            from PySide6.QtGui import QColor
            from PySide6.QtWidgets import QColorDialog
            c = QColorDialog.getColor(QColor(self.config.get("t8_adv_bg_color", "#FF000000")), self, _("選擇純色板顏色"), QColorDialog.ShowAlphaChannel)
            if c.isValid():
                self.config.set("t8_adv_bg_color", c.name(QColor.HexArgb))
                self.btn_adv_bg_color.setStyleSheet(f"background-color: {c.name(QColor.HexArgb)}; color: white;")
                if hasattr(self, 'preview_timer'): self.preview_timer.start()
        self.btn_adv_bg_color.clicked.connect(pick_adv_bg_color)
        form_bg.addRow(self.btn_adv_bg_color)
        
        btn_reset_bg = QPushButton(_("🔄 重設參數"))
        btn_reset_bg.clicked.connect(lambda dummy_val=False: [self.adv_bg_x.setValue(0), self.adv_bg_y.setValue(0), self.adv_bg_s.setValue(100), self.adv_bg_rot.setValue(0)])
        form_bg.addRow(btn_reset_bg); v_adv.addWidget(grp_bg)

        grp_z = QGroupBox(_("圖層自由排序面板 (由頂至底)")); v_z = QVBoxLayout(grp_z)
        self.list_z_order = QListWidget(); self.list_z_order.setDragDropMode(QAbstractItemView.InternalMove)
        self.list_z_order.setFixedHeight(180); self.prevent_scroll_propagation(self.list_z_order)
        z_name_map = {
            "CH_LAYER": _("角色圖層 (-ch)"), "PeriFrame": _("外框 (PeriFrame)"),
            "NameBox": _("卡名欄 (NameBox)"), "EffFrame": _("效果框 (EffFrame)"),
            "ArtFrame": _("卡圖框 (ArtFrame)"), "EffBox": _("效果文字欄 (EffBox)"),
            "BackGround": _("卡底背景 (BackGround)"), "BG_LAYER": _("自訂背景/純色底板 (-bg)")
        }
        def refresh_z_order_list():
            self.list_z_order.clear()
            for logic_id in self.config.get("t8_adv_z_order", ["CH_LAYER", "PeriFrame", "NameBox", "EffFrame", "ArtFrame", "EffBox", "BackGround", "BG_LAYER"]):
                item = QListWidgetItem(z_name_map.get(logic_id, logic_id)); item.setData(Qt.UserRole, logic_id)
                self.list_z_order.addItem(item)
        refresh_z_order_list()
        
        def save_z_order():
            self.config.set("t8_adv_z_order", [self.list_z_order.item(i).data(Qt.UserRole) for i in range(self.list_z_order.count())])
            if hasattr(self, 'preview_timer'): self.preview_timer.start()
        self.list_z_order.model().rowsMoved.connect(save_z_order)
        
        h_z_btn = QHBoxLayout()
        btn_z_up = QPushButton(_("▲ 上移")); btn_z_up.clicked.connect(lambda dummy_val=False: [UIHelper.move_list_items(self.list_z_order, -1), save_z_order()])
        btn_z_dn = QPushButton(_("▼ 下移")); btn_z_dn.clicked.connect(lambda dummy_val=False: [UIHelper.move_list_items(self.list_z_order, 1), save_z_order()])
        btn_z_rst = QPushButton(_("🔄 恢復預設圖層順序"))
        btn_z_rst.clicked.connect(lambda dummy_val=False: [self.config.set("t8_adv_z_order", ["CH_LAYER", "PeriFrame", "NameBox", "EffFrame", "ArtFrame", "EffBox", "BackGround", "BG_LAYER"]), refresh_z_order_list(), save_z_order()])
        h_z_btn.addWidget(btn_z_up); h_z_btn.addWidget(btn_z_dn); h_z_btn.addWidget(btn_z_rst)
        v_z.addWidget(self.list_z_order); v_z.addLayout(h_z_btn); v_adv.addWidget(grp_z)

        self.grp_adv_studio.hide()
        self.layout.addWidget(self.grp_adv_studio)

        # ─── 3. 素材與畫布設定區 (僅動畫) ───
        self.grp_c_canvas = QGroupBox(_("素材與畫布設定區"))
        form_c_canvas = QFormLayout(self.grp_c_canvas)
        self.c_hd_size = QComboBox(); self.c_hd_size.addItems(["FHD 1920x1080", "HD 1280x720"])
        self.c_hd_size.setCurrentText(self.config.get("c_hd_res", "HD 1280x720"))
        self.c_hd_size.currentTextChanged.connect(lambda t: [self.config.set("c_hd_res", t), self.preview_timer.start()])
        cb_disk_cache = self.bind_check("use_disk_cache", _("啟用硬碟暫存 (防記憶體溢出)"))
        cb_disk_cache.setToolTip(_("批次生成圖集時將影格寫入硬碟，適合處理長影片或記憶體小於 8GB 之用戶。"))
        form_c_canvas.addRow(cb_disk_cache)
        
        self.c_fill_mode = QComboBox()
        fill_modes = [
            (_("裁切滿版 (Crop Fill)"), "Crop"),
            (_("等比留邊 (Contain)"), "Contain"),
            (_("拉伸 (Stretch)"), "Stretch")
        ]
        for display_name, logic_id in fill_modes:
            self.c_fill_mode.addItem(display_name, logic_id)
            
        # 🛡️ 讀取設定與向下相容防呆 (將舊設定檔儲存的中文轉為新的邏輯代號)
        saved_fill_mode = self.config.get("c_fill_mode", "Crop")
        legacy_map = {"裁切滿版 (Crop Fill)": "Crop", "等比留邊 (Contain)": "Contain", "拉伸 (Stretch)": "Stretch"}
        if saved_fill_mode in legacy_map: saved_fill_mode = legacy_map[saved_fill_mode]
        
        idx = self.c_fill_mode.findData(saved_fill_mode)
        if idx >= 0: self.c_fill_mode.setCurrentIndex(idx)
        
        # 🛡️ 改用 currentIndexChanged 取代 currentTextChanged，綁定 .itemData(idx) 取出邏輯代號
        self.c_fill_mode.currentIndexChanged.connect(lambda idx: [self.config.set("c_fill_mode", self.c_fill_mode.itemData(idx)), self.preview_timer.start()])
        self.block_wheelEvent(self.c_hd_size); self.block_wheelEvent(self.c_fill_mode)
        
        form_c_canvas.addRow(_("HD 目標解析度:"), self.c_hd_size)
        form_c_canvas.addRow(_("畫布填充模式:"), self.c_fill_mode)
        self.c_rot = add_dual(_("旋轉角度校正:"), "c_rot", -360, 360, False, "°", form_c_canvas)
        self.c_off_x = add_dual(_("X 軸平移:"), "c_offset_x", -2000, 2000, False, " px", form_c_canvas)
        self.c_off_y = add_dual(_("Y 軸平移:"), "c_offset_y", -2000, 2000, False, " px", form_c_canvas)
        
        lbl_hint = QLabel(_("ℹ️ 提示：SD 規格會自動完美降轉為 854x480 的 16:9 比例，避免變形。"))
        lbl_hint.setStyleSheet("color: #2CC985;")
        form_c_canvas.addRow(lbl_hint)
        self.layout.addWidget(self.grp_c_canvas)

        # ─── 5. 關鍵幀預覽時間控制區 (僅動畫 & 預覽展開時) ───
        self.grp_c_prev = QGroupBox(_("關鍵幀預覽時間控制區"))
        form_c_prev = QFormLayout(self.grp_c_prev)
        self.c_prev_time = add_dual(_("預覽時間點 (秒):"), "c_prev_time_val", 0.0, 60.0, True, " s", form_c_prev)
        
        h_prev_point = QHBoxLayout()
        for name, widget_name in [(_("[跳至初始點]"), "c_pt1_t"), (_("[跳至峰值]"), "c_pt2_t"), (_("[跳至沉澱]"), "c_pt3_t"), (_("[跳至結束]"), "c_pt4_t")]:
            btn_jump = QPushButton(name)
            # 動態透過 getattr 讀取下方生成的 UI 元件即時數值，徹底解決時間軸不同步與前向參照問題
            btn_jump.clicked.connect(lambda dummy_checked=False, wn=widget_name: self.c_prev_time.setValue(getattr(self, wn).value() if hasattr(self, wn) else 0.0))
            h_prev_point.addWidget(btn_jump)
        form_c_prev.addRow(_("快速跳轉:"), h_prev_point)
        self.layout.addWidget(self.grp_c_prev)

        # ─── 6. 綠幕去背與色彩修飾區 (僅動畫) ───
        self.grp_c_color = QGroupBox(_("綠幕去背與色彩修飾區"))
        form_c_color = QFormLayout(self.grp_c_color)
        
        h_chroma = QHBoxLayout()
        self.c_chk_chroma = self.bind_check("c_chroma_en", _("啟用色彩去背"))
        self.c_chk_chroma.toggled.connect(lambda dummy_val: self.preview_timer.start())
        
        self.c_chk_despill = QCheckBox(_("啟用防溢色修飾"))
        self.c_chk_despill.setChecked(self.config.get("c_despill_en", False))
        self.c_chk_despill.toggled.connect(lambda state: [self.config.set("c_despill_en", state), self.preview_timer.start() if hasattr(self, 'preview_timer') else None])
        
        self.btn_color = QPushButton(_("🎨 選擇去背色"))
        self.btn_color.setStyleSheet(f"background-color: {self.config.get('c_chroma_color', '#00FF00')}; color: black;")
        def pick_color():
            c = QColorDialog.getColor(QColor(self.config.get("c_chroma_color", "#00FF00")), self)
            if c.isValid():
                self.config.set("c_chroma_color", c.name().upper())
                self.btn_color.setStyleSheet(f"background-color: {c.name()}; color: black;")
                self.preview_timer.start()
        self.btn_color.clicked.connect(pick_color)
        
        h_chroma.addWidget(self.c_chk_chroma); h_chroma.addWidget(self.c_chk_despill); h_chroma.addWidget(self.btn_color)
        form_c_color.addRow(h_chroma)
        
        self.c_tol = add_dual(_("去背容錯度 (Tolerance):"), "c_chroma_tol", 0, 100, False, "%", form_c_color)
        self.c_feather = add_dual(_("去背邊緣羽化 (Feather):"), "c_chroma_feather", 0, 100, False, "%", form_c_color)
        self.c_despill = add_dual(_("溢色修正強度 (Despill):"), "c_chroma_despill", 0, 100, False, "%", form_c_color)
        self.c_bright = add_dual(_("亮度調整:"), "c_bright", -100, 100, False, "%", form_c_color)
        self.c_contrast = add_dual(_("對比度調整:"), "c_contrast", -100, 100, False, "%", form_c_color)
        self.c_vignette = add_dual(_("暗角邊框強度 (Vignette):"), "c_vignette", 0, 100, False, "%", form_c_color)
        self.layout.addWidget(self.grp_c_color)

        # ─── 7. 時間控制與 POP UP 特效區 (僅動畫) ───
        self.grp_c_time = QGroupBox(_("時間控制與 POP UP 彈出特效"))
        form_c_time = QFormLayout(self.grp_c_time)
        self.c_st_time = add_dual(_("剪輯起點 (秒):"), "c_start_time", 0.0, 36000.0, True, " s", form_c_time)
        self.c_dur = add_dual(_("動畫總長度 (秒):"), "c_duration", 0.1, 10.0, True, " s", form_c_time)        
        # 🔗 動態同步：動畫長度變更時，自動更新預覽時間軸的最大值
        def sync_prev_time_max(duration_val):
            target_widgets = ['c_prev_time', 'c_pt1_t', 'c_pt2_t', 'c_pt3_t', 'c_pt4_t']
            for w_name in target_widgets:
                if hasattr(self, w_name):
                    widget = getattr(self, w_name)
                    widget.setMaximum(duration_val)
                    # 🛡️ 確保 _slider 已正確掛載才操作，防範初始化 AttributeError
                    if hasattr(widget, '_slider'):
                        widget._slider.setMaximum(int(duration_val * 100))
                    if widget.value() > duration_val:
                        widget.setValue(duration_val)
                    
        self.c_dur.valueChanged.connect(sync_prev_time_max)

        self.c_fps = add_dual(_("輸出影格率 (FPS):"), "c_fps", 1, 120, False, " FPS", form_c_time)
        self.c_speed = add_dual(_("播放倍速:"), "c_speed", 0.1, 4.0, True, " x", form_c_time)
        
        form_c_time.addRow(QLabel(_("--- 4 點 Spine 縮放曲線 ---")))
        
        self.c_pt1_t = add_dual(_("1. 初始點 時間:"), "c_pt1_t", 0.0, 10.0, True, " s", form_c_time)
        self.c_pt1_s = add_dual(_("   初始點 尺寸:"), "c_pt1_s", 0, 500, False, " %", form_c_time)
        self.c_pt2_t = add_dual(_("2. 峰值點 時間:"), "c_pt2_t", 0.0, 10.0, True, " s", form_c_time)
        self.c_pt2_s = add_dual(_("   峰值點 尺寸:"), "c_pt2_s", 0, 500, False, " %", form_c_time)
        self.c_pt3_t = add_dual(_("3. 沉澱點 時間:"), "c_pt3_t", 0.0, 10.0, True, " s", form_c_time)
        self.c_pt3_s = add_dual(_("   沉澱點 尺寸:"), "c_pt3_s", 0, 500, False, " %", form_c_time)
        self.c_pt4_t = add_dual(_("4. 結束點 時間:"), "c_pt4_t", 0.0, 10.0, True, " s", form_c_time)
        self.c_pt4_s = add_dual(_("   結束點 尺寸:"), "c_pt4_s", 0, 500, False, " %", form_c_time)
        
        self.btn_c_preview = QPushButton(_("👁️ 生成全尺寸真實預覽 GIF")); self.btn_c_preview.setStyleSheet("color: #E0C030;")
        self.btn_c_preview.clicked.connect(self.run_cutin_preview)
        form_c_time.addRow(self.btn_c_preview)
        self.layout.addWidget(self.grp_c_time)

        # ─── 8. 待處理清單區 (全模式共用) ───
        self.grp_pendulum_batch = QGroupBox(_("待處理清單 (手動輸入 ID 或自動掃描)"))
        v2 = QVBoxLayout(self.grp_pendulum_batch)
        btn_scan = QPushButton(_("自動掃描目標目錄")); btn_scan.clicked.connect(self.auto_load)
        v2.addWidget(btn_scan)
        self.t8_text = QPlainTextEdit(); v2.addWidget(self.t8_text)
        self.t8_text.cursorPositionChanged.connect(self._auto_fill_preview_path) # 綁定連動
        self.prevent_scroll_propagation(self.t8_text)
        self.layout.addWidget(self.grp_pendulum_batch)
        
        # ─── 9. 最底部統一執行按鈕 (全模式共用) ───
        self.btn_run = QPushButton(_("🚀 開始執行後處理")); self.btn_run.clicked.connect(self.run_task)
        self.btn_run.setStyleSheet("font-size: 15px; padding: 10px; color: #EBEBEC; font-weight: bold;")
        self.layout.addWidget(self.btn_run)
        
        # 初始化隱藏狀態
        self.preview_widget.hide()
        self.grp_c_prev.hide()

        self.timer = QTimer(); self.timer.setSingleShot(True); self.timer.timeout.connect(self.auto_load)
        self.t8_mod.textChanged.connect(lambda dummy_val: self.timer.start(800))
        self.t8_img.textChanged.connect(lambda dummy_val: self.timer.start(800))
        self.t8_csv.textChanged.connect(lambda dummy_val: self.timer.start(800))

        self._is_shortcut_flow = False
        self._shortcut_root_dir = ""
        self._shortcut_card_id = ""
        self.config.signals.request_overframe_shortcut.connect(self.handle_shortcut_request)
        self.config.signals.request_pendulum_reload.connect(self.auto_load)
        self.config.signals.set_t8_mode.connect(lambda mode_data: self.cb_mode.setCurrentIndex(self.cb_mode.findData(mode_data)) if self.cb_mode.findData(mode_data) != -1 else None)
        
        # 執行首次模式初始化
        self.cb_mode.currentIndexChanged.connect(lambda idx: self.on_mode_changed(self.cb_mode.itemData(idx)))
        self.on_mode_changed(self.cb_mode.currentData())
        if hasattr(self, 'c_dur'): self.c_dur.valueChanged.emit(self.c_dur.value()) # 🛡️ 觸發時間軸連動初始化

    def hideEvent(self, event):
        """🛡️ 生命週期防禦：當使用者離開此分頁時，自動重置捷徑狀態，防止殘留污染"""
        super().hideEvent(event)
        self._is_shortcut_flow = False

    def handle_shortcut_request(self, card_id, img_path, root_dir):
        self._is_shortcut_flow = True
        self._shortcut_root_dir = root_dir
        self._shortcut_card_id = card_id
        idx = self.cb_mode.findData("MODE_OVERFRAME")
        if idx >= 0: self.cb_mode.setCurrentIndex(idx)
        if not self.btn_toggle_preview.isChecked(): self.btn_toggle_preview.setChecked(True)
        self.edit_prev_path.setText(img_path)

        mod_folder_name = self.config.get("s_folder_mod", "").strip() or "卡圖改"
        mod_dir = MDEngine.resolve_path(root_dir, mod_folder_name)
        os.makedirs(mod_dir, exist_ok=True)
        
        ext = os.path.splitext(img_path)[1] or ".png"
        target_filename = f"{card_id}{ext}"
        target_path = os.path.join(mod_dir, target_filename)
        
        try: shutil.copy2(img_path, target_path)
        except Exception: pass
        
        self.t8_text.setPlainText(target_filename)
        self.app.status_lbl.setText(_("狀態：已無縫接收來自快捷改圖的卡片，請調整超框參數後點擊執行。"))

    def on_mode_changed(self, logic_id):
        """🧠 切換大腦：精準調度容器顯隱，保護主結構不塌陷"""
        is_pendulum_pad = (logic_id == "MODE_PENDULUM")
        is_pendulum_orig = (logic_id == "MODE_PENDULUM_ORIGINAL_CROP")
        is_overframe = (logic_id == "MODE_OVERFRAME")
        is_cutin = (logic_id == "MODE_CUTIN")

        # 針對路徑區的細微切換
        self.lbl_mod.setVisible(not is_pendulum_orig)
        self.t8_mod.setVisible(not is_pendulum_orig)
        self.lbl_img.setVisible(is_pendulum_orig)
        self.t8_img.setVisible(is_pendulum_orig)

        self.t8_pad.setVisible(is_pendulum_pad)
        if self.t8_pad.parentWidget():
            label = self.t8_pad.parentWidget().layout().labelForField(self.t8_pad)
            if label: label.setVisible(is_pendulum_pad)

        # 以容器為單位的顯隱調度
        self.grp_op.setVisible(is_overframe)
        self.btn_toggle_adv.setVisible(is_overframe)
        self.grp_adv_studio.setVisible(is_overframe and self.btn_toggle_adv.isChecked())
        
        # 🛡️ 閃卡工坊的獨立生命週期接管
        self.btn_toggle_foil_studio.setVisible(is_overframe)
        self.grp_foil_studio.setVisible(is_overframe and self.btn_toggle_foil_studio.isChecked())
        
        self.grp_c_canvas.setVisible(is_cutin)
        self.grp_c_prev.setVisible(is_cutin) # ✅ 修復：關鍵幀控制區改為動畫模式下常駐顯示
        self.grp_c_color.setVisible(is_cutin)
        self.grp_c_time.setVisible(is_cutin)

        # 預覽畫布只有超框與 Cut-In 模式能用
        self.btn_toggle_preview.setVisible(is_overframe or is_cutin)
        if not (is_overframe or is_cutin):
            self.btn_toggle_preview.setChecked(False)
            self.preview_widget.setVisible(False)
            MDEngine.clear_psd_cache()

    def _get_cutin_src_dir(self):
        """輔助函式：精準回傳「卡圖改」的實體路徑"""
        c = self.config
        mod_folder_name = c.get("t8_mod_dir", "").strip() or c.get("s_folder_mod", "").strip() or "卡圖改"
        return MDEngine.resolve_path(clean_path(c.get("t8_root_dir")), mod_folder_name)

    def _resolve_cutin_preview_path(self, target):
        """✨ 智慧雙軌路徑解析器：預覽時同時搜尋「卡圖改」與其內部的「備份區」"""
        if not target: return ""
        c = self.config
        mod_dir = self._get_cutin_src_dir()
        bk_folder = c.get("t8_backup_folder", "").strip() or "修改前原檔"
        bk_dir = MDEngine.resolve_path(mod_dir, bk_folder)
        
        # 優先找備份區 (已被處理並移動的原始素材)
        if os.path.exists(bk_dir):
            bk_path = MDEngine.resolve_cutin_material_path(bk_dir, target)
            if os.path.exists(bk_path) and not any(suffix in bk_path.lower() for suffix in ['-hd', '-sd', 'js-']): 
                return bk_path
                
        # 再找卡圖改
        return MDEngine.resolve_cutin_material_path(mod_dir, target)

    def _auto_fill_preview_path(self):
        """✨ 智慧連動：點擊批次清單時，自動補全模糊路徑並觸發預覽"""
        mode = self.cb_mode.currentData()
        if mode not in ("MODE_CUTIN", "MODE_OVERFRAME"): return
        
        cursor = self.t8_text.textCursor()
        cursor.select(cursor.SelectionType.LineUnderCursor)
        raw_line = cursor.selectedText().strip()
        if not raw_line: return
        
        line_parts = raw_line.split()
        if not line_parts: return
        
        line_text = line_parts[0]
        if line_text:
            full_path = ""
            if mode == "MODE_OVERFRAME":
                c = self.config
                mod_dir = c.get("t8_mod_dir", "").strip() or c.get("s_folder_mod", "").strip() or "卡圖改"
                root_dir = clean_path(c.get("t8_root_dir"))
                mod_dir = MDEngine.resolve_path(root_dir, mod_dir)
                bk_dir = MDEngine.resolve_path(mod_dir, c.get("t8_backup_folder", "").strip() or "修改前原檔")
                full_path, dummy_bg, dummy_adv = MDEngine.resolve_overframe_material_path(mod_dir, bk_dir, line_text)
            else:
                full_path = self._resolve_cutin_preview_path(line_text)
            
            if full_path and self.edit_prev_path.text() != full_path:
                self.edit_prev_path.setText(full_path)
                
            if self.preview_widget.isVisible():
                self.preview_timer.start()

    def _get_adv_options(self):
        c = self.config
        return {
            "ch_x": self.adv_ch_x.value(), "ch_y": self.adv_ch_y.value(), "ch_s": self.adv_ch_s.value(), "ch_rot": self.adv_ch_rot.value(),
            "bg_x": self.adv_bg_x.value(), "bg_y": self.adv_bg_y.value(), "bg_s": self.adv_bg_s.value(), "bg_rot": self.adv_bg_rot.value(),
            "bg_color": c.get("t8_adv_bg_color", "#FF000000"),
            "z_order": c.get("t8_adv_z_order", ["CH_LAYER", "PeriFrame", "NameBox", "EffFrame", "ArtFrame", "EffBox", "BackGround", "BG_LAYER"]),
            "masks": {
                # 🛡️ 使用推導式大幅簡化 3x6 矩陣打包，遵循 DRY 原則
                cat: {
                    p: c.get(f"t8_{prefix}_{p}", d)
                    for p, d in zip(
                        ["PeriFrame", "NameBox", "ArtFrame", "EffFrame", "EffBox", "BackGround"],
                        [True, False, True, True, False, False]
                    )
                }
                for cat, prefix in [("prev", "foil_prev"), ("bake", "foil_bake"), ("dirty", "adv_mask")]
            },
            "foil_params": {
                "sim_enable": c.get("t8_adv_foil_sim", False),
                "palette": self.cb_foil_palette.currentData(),
                "base_light": self.foil_base_light.value(),
                "sharpness": self.foil_sharpness.value(),
                "blend_mode": self.cb_foil_blend.currentData(),
                "intensity": self.foil_intensity.value(),
                "saturation": self.foil_saturation.value(),
                "frequency": self.foil_frequency.value(),
                "angle": self.foil_angle.value()
            }
        }

    def auto_load(self):
        c = self.config
        logic_id = self.cb_mode.currentData()
        
        if logic_id == "MODE_PENDULUM_ORIGINAL_CROP":
            folder_name = c.get("s_folder_img", "").strip() or "原卡圖"
        else:
            folder_name = c.get("t8_mod_dir", "").strip() or c.get("s_folder_mod", "").strip() or "卡圖改"
            
        target_dir = MDEngine.resolve_path(clean_path(c.get("t8_root_dir")), folder_name)
        
        if logic_id in ("MODE_PENDULUM", "MODE_PENDULUM_ORIGINAL_CROP"):
            lines = MDEngine.get_pendulum_list(clean_path(c.get("t8_csv_dir")), target_dir)
        else:
            lines = []
            if os.path.exists(target_dir):
                if logic_id == "MODE_CUTIN":
                    bk_folder = c.get("t8_backup_folder", "").strip() or "修改前原檔"
                    bk_dir = MDEngine.resolve_path(target_dir, bk_folder)
                    found_ids = set()
                    
                    if os.path.exists(bk_dir):
                        for f in os.listdir(bk_dir):
                            f_lower = f.lower()
                            if re.match(r'^p\d+', f, re.IGNORECASE):
                                if any(suffix in f_lower for suffix in ['-hd', '-sd', 'js-', '.atlas', '.json']):
                                    continue
                                lines.append(f)
                                found_ids.add(os.path.splitext(f)[0].lower())
                                
                    for f in os.listdir(target_dir):
                        f_path = os.path.join(target_dir, f)
                        f_lower = f.lower()
                        
                        if os.path.isdir(f_path):
                            if f_lower == bk_folder.lower() or not re.match(r'^p\d+', f, re.IGNORECASE):
                                continue 
                        
                        if re.match(r'^p\d+', f, re.IGNORECASE):
                            if any(suffix in f_lower for suffix in ['-hd', '-sd', 'js-', '.atlas', '.json']):
                                continue
                            
                            stem = os.path.splitext(f)[0].lower()
                            if not any(stem.startswith(fid) or fid.startswith(stem) for fid in found_ids):
                                lines.append(f)
                                found_ids.add(stem)
                else:
                    found_ch, found_bg, found_norm = set(), set(), set()
                    bk_folder = c.get("t8_backup_folder", "").strip() or "修改前原檔"
                    bk_dir = MDEngine.resolve_path(target_dir, bk_folder)
                    search_dirs = [target_dir]
                    if os.path.exists(bk_dir): search_dirs.insert(0, bk_dir)
                    
                    for d in search_dirs:
                        if not os.path.exists(d): continue
                        for f in os.listdir(d):
                            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.bmp')):
                                f_lower = f.lower()
                                if '-bg.' in f_lower: found_bg.add(f)
                                elif '-ch.' in f_lower: found_ch.add(f)
                                else: found_norm.add(f)
                            
                    for f in sorted(found_ch):
                        base = re.sub(r'-ch\..+$', '', f, flags=re.IGNORECASE)
                        has_bg = any(bg.lower().startswith(base.lower() + '-bg.') for bg in found_bg)
                        if has_bg: lines.append(f"{f}  # [{_('雙層合成: 角色 + 背景')}]")
                        else: lines.append(f"{f}  # [{_('單層精修: 僅角色 (套用純色板)')}]")
                        
                    ch_bases = {re.sub(r'-ch\..+$', '', f, flags=re.IGNORECASE) for f in found_ch}
                    for f in sorted(found_norm):
                        base = os.path.splitext(f)[0]
                        if base not in ch_bases:
                            lines.append(f"{f}  # [{_('傳統單圖')}]")
                        
        self.t8_text.setPlainText("\n".join(lines) if lines else "")
        if lines: self.app.status_lbl.setText(_("狀態：自動掃描完成，找到 {count} 個符合條件的項目。").format(count=len(lines)))

    def _get_cutin_options(self):
        c = self.config
        sz_str = self.c_hd_size.currentText()
        hd_sz = (1920, 1080) if "1920" in sz_str else (1280, 720)
        options = {
            "use_disk_cache": c.get("use_disk_cache", False),
            "max_threads": c.get("max_threads", "Auto"),
            "s_folder_mod": c.get("s_folder_mod", "卡圖改"), "fill_mode": self.c_fill_mode.currentData(),
            "start_time": self.c_st_time.value(), "duration": self.c_dur.value(),
            "fps": self.c_fps.value(), "speed": self.c_speed.value(),
            "rot": self.c_rot.value(), "offset_x": self.c_off_x.value(), "offset_y": self.c_off_y.value(),
            "enable_chroma": self.c_chk_chroma.isChecked(), 
            "enable_despill": self.c_chk_despill.isChecked(),
            "chroma_color": c.get("c_chroma_color", "#00FF00"),
            "chroma_tol": self.c_tol.value(), "chroma_feather": self.c_feather.value(), "chroma_despill": self.c_despill.value(),
            "bright": self.c_bright.value(), "contrast": self.c_contrast.value(), "vignette": self.c_vignette.value(),
            "popup_curve": [
                {"time": self.c_pt1_t.value(), "x": self.c_pt1_s.value()/100.0, "y": self.c_pt1_s.value()/100.0},
                {"time": self.c_pt2_t.value(), "x": self.c_pt2_s.value()/100.0, "y": self.c_pt2_s.value()/100.0},
                {"time": self.c_pt3_t.value(), "x": self.c_pt3_s.value()/100.0, "y": self.c_pt3_s.value()/100.0},
                {"time": self.c_pt4_t.value(), "x": self.c_pt4_s.value()/100.0, "y": self.c_pt4_s.value()/100.0}
            ]
        }
        return "", hd_sz, options

    def run_cutin_preview(self):
        raw_input = clean_path(self.edit_prev_path.text())
        
        # 先嘗試解析文字框中的實體素材路徑
        src_path = self._resolve_cutin_preview_path(raw_input)
        
        # 若預覽欄位為空或無效，才退回從待處理清單游標處讀取
        if not src_path or not os.path.exists(src_path):
            cursor = self.t8_text.textCursor()
            cursor.select(cursor.SelectionType.LineUnderCursor)
            target = cursor.selectedText().strip().split()[0] if cursor.selectedText().strip() else ""
            if target:
                src_path = self._resolve_cutin_preview_path(target)
                
        if not src_path or not os.path.exists(src_path):
            return QMessageBox.warning(self, _("錯誤"), _("請先選擇或在上方欄位填入有效的測試素材路徑！"))
            
        dummy_cid, hd_sz, opts = self._get_cutin_options()
        
        def on_preview_done(res_path, extra_msg):
            QMessageBox.information(self, _("預覽生成成功"), extra_msg)
            try: os.startfile(res_path)
            except Exception: pass
                
        self.app.execute_task(self.btn_c_preview, _("生成預覽 GIF 中"), MDEngine.task_generate_cutin_preview, (src_path, hd_sz, opts), on_preview_done)

    def run_task(self):
        targets = [line.strip().split()[0] for line in self.t8_text.toPlainText().strip().splitlines() if line.strip()]
        if not targets: return QMessageBox.warning(self, _("警告"), _("目前沒有待處理的項目！"))
        
        c = self.config
        logic_id = self.cb_mode.currentData()
        
        if getattr(self, '_is_shortcut_flow', False):
            root_dir = self._shortcut_root_dir
            mod_folder_name = c.get("s_folder_mod", "").strip() or "卡圖改"
        else:
            root_dir = clean_path(c.get("t8_root_dir"))
            if logic_id == "MODE_PENDULUM_ORIGINAL_CROP":
                mod_folder_name = c.get("s_folder_img", "").strip() or "原卡圖"
            else:
                mod_folder_name = c.get("t8_mod_dir", "").strip() or "卡圖改"
                
        # 🚀 Cut-In 動畫後處理專屬路線
        if logic_id == "MODE_CUTIN":
            src_dir = self._get_cutin_src_dir()
            bk_folder = c.get("t8_backup_folder", "").strip() or "修改前原檔"
            enable_backup = c.get("t8_enable_backup", True)
            
            dummy_cid, hd_sz, opts = self._get_cutin_options()
            
            # 🛡️ 3.0 秒防呆警告
            max_curve_time = max((pt['time'] for pt in opts.get('popup_curve', [])), default=0)
            duration = max(opts.get("duration", 0.0), max_curve_time)
            if duration > 3.0:
                reply = QMessageBox.question(self, _("過長動畫警告"), _("ℹ️ 提示：您設定的動畫長度為 {d} 秒。\n過長的動畫可能會影響遊戲節奏。確定要繼續嗎？").format(d=duration), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply == QMessageBox.No: return
            
            def on_cutin_finish(count, errors):
                msg = _("處理完成！成功生成 {count} 個 Spine 召喚動畫 Bundle。").format(count=count)
                if errors:
                    msg += "\n\n" + _("⚠️ 以下項目處理失敗：\n") + "\n".join(errors)
                
                # 🛡️ 自動跳轉
                if c.get("auto_switch_tab"):
                    self.app.select_tab("t4_replace")
                    
                # 讓 execute_task 中央調度器來統一處理訊息彈窗，落實去耦合
                return msg
                
            self.app.execute_task(self.btn_run, _("批次生成動畫 Bundle 中"), MDEngine.task_post_process_cutin_batch, 
                (src_dir, root_dir, mod_folder_name, bk_folder, enable_backup, targets, hd_sz, opts), 
                on_cutin_finish)
            return
            
        # 🚀 舊版超框/靈擺處理路線
        target_dir = MDEngine.resolve_path(root_dir, mod_folder_name)
        bk_dir = os.path.join(target_dir, c.get("t8_backup_folder", "").strip() or "修改前原檔")
        
        if logic_id == "MODE_PENDULUM_ORIGINAL_CROP": mode_val = "pendulum_orig"
        elif logic_id == "MODE_PENDULUM": mode_val = "pendulum"
        else: mode_val = "overframe"
        
        opacities = {
            "periframe": float(c.get("t8_op_periframe", 1.0)), "namebox": float(c.get("t8_op_namebox", 1.0)),
            "artframe": float(c.get("t8_op_artframe", 1.0)), "effframe": float(c.get("t8_op_effframe", 1.0)),
            "effbox": float(c.get("t8_op_effbox", 1.0)), "background": float(c.get("t8_op_background", 1.0))
        }

        options = {"pad_pct": self.get_safe_int("t8_padding_pct", 25), "opacities": opacities}
        if mode_val == "overframe":
            options.update(self._get_adv_options())
            options["is_preview"] = False
        
        def on_finish(ct, e):
            if getattr(self, '_is_shortcut_flow', False):
                self._is_shortcut_flow = False
                base_name = os.path.splitext(targets[0])[0]
                self.config.signals.return_to_quick_mod.emit(os.path.join(target_dir, f"{base_name}.png"))
                self.app.select_tab("t9_quick_mod")
                return

            if mode_val == "overframe":
                raw_ids = [os.path.splitext(t)[0].split('_')[0] for t in targets]
                ids = [re.sub(r'-ch$', '', i, flags=re.IGNORECASE) for i in raw_ids]
                ids = [i for i in ids if i.isdigit()]
                self.config.signals.request_overframe_register.emit("\n".join(ids))
                self.config.signals.set_return_to_tab4.emit(True)
                QMessageBox.information(self, _("完成"), _("超框後處理完成！已為您準備好資料並自動跳轉至「超框註冊器」進行白名單註冊。"))
                self.app.select_tab("t13_overframe")
            elif mode_val == "pendulum_orig":
                QMessageBox.information(self, _("完成"), _("原卡圖靈擺裁切處理完成！\n成功將 {count} 張圖片拉伸裁切，並已覆寫回原卡圖目錄。").format(count=ct))
            else:
                msg = _("處理完成！成功填充 {count} 張").format(count=ct)
                if e: msg += "\n\n" + _("⚠️ 以下項目處理發生錯誤：\n") + str(e)
                QMessageBox.information(self, _("完成"), msg)
                
                if self.config.get("auto_switch_tab") and not e:
                    self.app.select_tab("t4_replace")

        self.app.execute_task(self.btn_run, _("進行圖像處理中"), MDEngine.task_post_process, 
            (target_dir, bk_dir, c.get("t8_enable_backup"), self.get_safe_int("t8_padding_pct", 25), targets, mode_val, clean_path(c.get("t8_csv_dir")), options), 
            on_finish)
        
    def browse_preview(self):
        # 🛡️ 支援所有強大的素材格式，無論是超框的圖片還是動畫的影片
        path, dummy_ext = QFileDialog.getOpenFileName(self, _("選擇測試素材 (若要選圖片序列資料夾請取消此對話框)"), "", "All Supported (*.psd *.mp4 *.gif *.png *.jpg *.jpeg *.bmp *.avi);;Images (*.png *.jpg *.jpeg *.bmp)")
        if not path: path = QFileDialog.getExistingDirectory(self, _("或者選擇圖片序列資料夾"))
        if path: self.edit_prev_path.setText(path)

    def update_preview(self):
        if not self.preview_widget.isVisible(): return
        
        # 🛡️ 防暴衝節流閥 (Throttling)：如果在渲染中，則掛起標記，確保同時間只有一個 Worker 在消耗記憶體
        if getattr(self, '_preview_running', False):
            self._pending_preview = True
            return
            
        raw_input = clean_path(self.edit_prev_path.text())
        img_path = self._resolve_cutin_preview_path(raw_input)
        
        if not os.path.isfile(img_path) and not os.path.isdir(img_path):
            return self.lbl_preview.setText(_("請先選擇有效的圖片或素材路徑！\n(點擊上方批次清單項目可自動匯入)"))

        self._preview_running = True
        self._pending_preview = False
        
        mode_val = self.cb_mode.currentData()
        c = self.config

        if mode_val == "MODE_CUTIN":
            self.lbl_preview.setText(_("⏳ 關鍵幀預覽渲染中..."))
            dummy_cid, hd_sz, opts = self._get_cutin_options()
            preview_time_sec = self.c_prev_time.value()
            
            worker = TaskWorker(MDEngine.task_generate_cutin_single_frame_preview, (img_path, hd_sz, opts, preview_time_sec))
        else:
            self.lbl_preview.setText(_("⏳ 預覽生成中..."))
            s_mode = "pendulum" if mode_val == "MODE_PENDULUM" else "overframe"
            opacities = {
                "periframe": float(c.get("t8_op_periframe", 1.0)), "namebox": float(c.get("t8_op_namebox", 1.0)),
                "artframe": float(c.get("t8_op_artframe", 1.0)), "effframe": float(c.get("t8_op_effframe", 1.0)),
                "effbox": float(c.get("t8_op_effbox", 1.0)), "background": float(c.get("t8_op_background", 1.0))
            }
            options = {"pad_pct": self.get_safe_int("t8_padding_pct", 25), "opacities": opacities}
            if mode_val == "MODE_OVERFRAME":
                options.update(self._get_adv_options())
                options["is_preview"] = True
                
            worker = TaskWorker(MDEngine.task_generate_preview, (img_path, clean_path(c.get("t8_csv_dir")), s_mode, self.get_safe_int("t8_padding_pct", 25), options))

        if not hasattr(self.app, '_active_workers'): self.app._active_workers = set()
        self.app._active_workers.add(worker)
        
        def on_preview_done(succ, qimg, err):
            self.app._active_workers.discard(worker) 
            self._preview_running = False # 🛡️ 釋放狀態鎖
            
            if succ and qimg: self.lbl_preview.setPixmap(QPixmap.fromImage(qimg).scaledToHeight(400, Qt.SmoothTransformation))
            else: self.lbl_preview.setText(_("❌ 預覽失敗: ") + str(err if err else qimg))
            
            # 🛡️ 節流閥收尾：如果在處理期間有新的預覽請求，立刻觸發最新的一次，不浪費效能渲染中間過程
            if getattr(self, '_pending_preview', False):
                self.update_preview()
                
        worker.signals.finished.connect(on_preview_done)
        self.app.thread_pool.start(worker)  

# ==================== 分頁 9: 快捷單卡 ====================
class TabQuickMod(BaseTab):
    def __init__(self, main_app):
        super().__init__(main_app)
        self.layout.addWidget(QLabel(_("【單卡捷徑】一鍵自動完成備份與新圖注入")))        

        # ========== 分類選單 (一般 / 超框 / 大廳背景) ==========
        grp_mode = QGroupBox(_("操作模式"))
        box_mode = QHBoxLayout(grp_mode)
        self.cb_mod_category = QComboBox()
        modes = [
            (_("一般改圖"), "MODE_NORMAL"),
            (_("超框改圖"), "MODE_OVERFRAME"),
            (_("修改大廳背景"), "MODE_LOBBY_BG") # 🌿 修正：括號現在正確包在翻譯字串外面了
        ]
        for display_name, raw_name in modes:
            self.cb_mod_category.addItem(display_name, raw_name)
        self.block_wheelEvent(self.cb_mod_category)
        box_mode.addWidget(QLabel(_("選擇分類:"))); box_mode.addWidget(self.cb_mod_category)
        self.layout.addWidget(grp_mode)

        self.grp_search = QGroupBox(_("搜尋與選取"))
        v1 = QVBoxLayout(self.grp_search)
        
        self.search_widget = GoogleSearchFilterWidget(self.config, enable_batch_add=False)
        self.search_widget.signals.search_requested.connect(self.execute_advanced_search)
        self.search_widget.signals.page_display_updated.connect(self.update_list_display)
        v1.addWidget(self.search_widget)
        
        self.t9_list = QListWidget()
        self.t9_list.setMinimumHeight(250) 
        self.prevent_scroll_propagation(self.t9_list)
        self.t9_list.itemDoubleClicked.connect(lambda item: self.t9_id.setText(item.text().split()[0]))
        self.t9_list.setAutoScroll(False)
        self._t9_drag_filter = LinearDragScrollFilter(self.t9_list, speed_boost=0.15)

        v1.addWidget(self.t9_list)
        self.layout.addWidget(self.grp_search)

        grp2 = QGroupBox(_("路徑與目標"))
        self.form2 = QFormLayout(grp2)
        self.t9_csv_edit = self.make_path_row(self.form2, _("字典 (CSV)"), "t9_csv_dir", True, "CSV", "csv")
        self.make_path_row(self.form2, _("原檔來源 (0000)"), "t9_src_dir", sync_type="src")
        self.make_path_row(self.form2, _("儲存根目錄"), "t9_out_dir", sync_type="root")
        self.t9_id = QLineEdit(); self.form2.addRow(_("目標卡片 ID:"), self.t9_id)
        
        self.t9_img_edit = self.make_path_row(self.form2, _("新圖片路徑"), "t9_img_path", True, "IMG")
        
        cb_overwrite = self.bind_check("t9_overwrite_game", _("直接覆蓋遊戲檔案\n⚠ 警告：此操作將直接修改原廠遊戲目錄\n請確保檔案已備份"))
        cb_overwrite.setStyleSheet("color: #D83C3C; font-weight: bold;")
        self.form2.addRow(cb_overwrite)
        self.layout.addWidget(grp2)
        
        # ========== 雙按鈕動態切換配置 ==========
        box_btns = QHBoxLayout()
        self.btn_run = QPushButton(_("開始替換"))
        self.btn_run.clicked.connect(self.run_task)
        
        self.btn_send_post = QPushButton(_("傳送到超框改圖後處理"))
        self.btn_send_post.setStyleSheet("color: #E0C030; font-weight: bold;")
        self.btn_send_post.clicked.connect(self.send_to_post_process)

        box_btns.addWidget(self.btn_run)
        box_btns.addWidget(self.btn_send_post)
        self.layout.addLayout(box_btns)

        # 動態顯隱控制機制 (去耦合處理)
        self.cb_mod_category.currentIndexChanged.connect(self.on_category_changed)
        self.on_category_changed(self.cb_mod_category.currentIndex()) # 初始化狀態

        self.config.signals.return_to_quick_mod.connect(self.on_return_from_post)        
        self.config.signals.set_quick_mod_id.connect(lambda tid: self.t9_id.setText(tid))

    def _set_row_visible(self, form, field_widget, visible):
        """強大的防呆函數：隱藏 QFormLayout 中的整列元件 (包含標籤與按鈕)"""
        for i in range(form.rowCount()):
            field_item = form.itemAt(i, QFormLayout.FieldRole)
            if field_item:
                match = False
                if field_item.widget() == field_widget:
                    match = True
                elif field_item.layout():
                    for j in range(field_item.layout().count()):
                        if field_item.layout().itemAt(j).widget() == field_widget:
                            match = True
                            break
                if match:
                    label_item = form.itemAt(i, QFormLayout.LabelRole)
                    if label_item and label_item.widget(): label_item.widget().setVisible(visible)
                    if field_item.widget(): field_item.widget().setVisible(visible)
                    elif field_item.layout():
                        for j in range(field_item.layout().count()):
                            w = field_item.layout().itemAt(j).widget()
                            if w: w.setVisible(visible)
                    break

    def on_category_changed(self, idx):
        mode = self.cb_mod_category.itemData(idx)
        is_lobby = (mode == "MODE_LOBBY_BG")
        is_overframe = (mode == "MODE_OVERFRAME")
        
        self.grp_search.setVisible(not is_lobby)
        self.btn_send_post.setVisible(is_overframe)
        
        # 精準隱藏不需要的路徑欄與 ID 欄
        self._set_row_visible(self.form2, self.t9_csv_edit, not is_lobby)
        self._set_row_visible(self.form2, self.t9_id, not is_lobby)

    def execute_advanced_search(self, params):
        dummy_map, db = MDEngine.get_csv_data(clean_path(self.config.get("t9_csv_dir")))
        # ✨ 接收全量清單
        all_matches = MDEngine.search_cards_advanced(params, db, search_lang=self.config.get("search_lang", "zh-tw"))
        # 交付給 Widget 處理切片與分頁
        self.search_widget.update_pagination_ui(all_matches, params.get("limit_per_page", 200))

    def update_list_display(self, page_slice):
        # ✨ 0ms 瞬間更新 UI
        self.t9_list.clear()
        for item in page_slice:
            self.t9_list.addItem(item)

    def on_return_from_post(self, new_img_path):
        self.t9_img_edit.setText(new_img_path)
        self.config.set("t9_img_path", new_img_path)
        QMessageBox.information(self, _("準備就緒"), _("已成功接收超框處理後的圖片！\n請確認資訊後點擊左側「開始替換」完成最後步驟。"))

    def run_task(self):
        c = self.config
        mode = self.cb_mod_category.currentData()
        is_overframe = (mode == "MODE_OVERFRAME")
        
        # ✨ 大廳背景裸檔專屬路由
        if mode == "MODE_LOBBY_BG":
            target_name = "ShopBGBase02"
            data_path = MDEngine.get_data_unity3d_safe(clean_path(c.get("t9_src_dir")))
            
            if not os.path.isfile(clean_path(c.get("t9_img_path"))) or not os.path.isdir(clean_path(c.get("t9_out_dir"))):
                return QMessageBox.critical(self, _("錯誤"), _("請確認「新圖片路徑」與「儲存目錄」皆正確填寫！"))
                
            def on_lobby_finish(ct, e):
                QMessageBox.information(self, _("成功"), _("大廳背景修改成功！\n備份與新檔已儲存於設定好的資料夾中。"))
                
            self.app.execute_task(self.btn_run, _("大廳背景替換中"), MDEngine.task_direct_replace,
                (data_path, target_name, c.get("t9_out_dir"), c.get("t9_img_path"), c.get("t9_overwrite_game"), c.get("s_folder_backup"), c.get("s_folder_out")), on_lobby_finish)
            return

        # 常規 / 超框卡片修改路由
        tid = self.t9_id.text().strip()
        if not tid or not os.path.isfile(clean_path(c.get("t9_csv_dir"))) or not os.path.isdir(clean_path(c.get("t9_src_dir"))) or not os.path.isfile(clean_path(c.get("t9_img_path"))):
            return QMessageBox.critical(self, _("錯誤"), _("請確認所有欄位皆已正確填寫！"))
            
        def on_finish(ct, e):
            if is_overframe:
                self.config.signals.quick_mod_to_overframe_reg.emit(tid)
                QMessageBox.information(self, _("成功"), _("超框圖片替換成功！\n已自動為您跳轉至「超框註冊器」並帶入卡片 ID，請記得輸出註冊表。"))
            else:
                QMessageBox.information(self, _("成功"), _("成功！共修改了 {count} 個檔案。").format(count=ct))

        self.app.execute_task(self.btn_run, _("資源替換中"), MDEngine.task_quick_replace, 
            (tid, c.get("t9_csv_dir"), c.get("t9_src_dir"), c.get("t9_out_dir"), c.get("t9_img_path"), 
             c.get("t9_overwrite_game"), c.get("s_folder_backup"), c.get("s_folder_out")), 
            on_finish)

    def send_to_post_process(self):
        c = self.config
        card_id = self.t9_id.text().strip()
        img_path = clean_path(c.get("t9_img_path"))
        root_dir = clean_path(c.get("t9_out_dir"))
        
        if not card_id or not os.path.isfile(img_path) or not os.path.isdir(root_dir):
            return QMessageBox.critical(self, _("錯誤"), _("請確認「目標卡片 ID」、「新圖片路徑」與「儲存根目錄」皆已填寫且有效！"))
        
        # 發射訊號傳遞給 Tab 8 進行超框處理，並自動跳轉至 Tab 8
        self.config.signals.request_overframe_shortcut.emit(card_id, img_path, root_dir)
        self.app.select_tab("t8_pendulum")
        
# ==================== 分頁 9: 圖形化瀏覽器 (Gallery) ====================
class TabGallery(BaseTab):
    def __init__(self, main_app):
        super().__init__(main_app)
        self.layout.addWidget(QLabel(_("【第 9 步】圖形化瀏覽器 (視覺資產過濾器)")))
        
        grp = QGroupBox(_("圖庫檢視"))
        v = QVBoxLayout(grp)
        
        h = QHBoxLayout()
        self.cb_cat = QComboBox()
        # ✨ 將字串宣告在陣列中，讓 AST 解析器能成功抓到 _("...")
        categories = [
            (_("場地 (Mat)"), "CAT_MAT"),
            (_("硬幣 (Coin)"), "CAT_COIN"),
            (_("卡盒 (Deck Case)"), "CAT_DECKCASE"),
            (_("頭像框 (Frame)"), "CAT_FRAME"),
            (_("頭像 (Icon)"), "CAT_ICON"),
            (_("卡套 (Sleeve)"), "CAT_SLEEVE"),
            (_("大廳背景 (Wallpaper)"), "CAT_WALLPAPER"),
            (_("檔案篩選 (File Filter)"), "CAT_FILTER")
        ]
        for display_name, raw_name in categories:
            self.cb_cat.addItem(display_name, raw_name)
            
        self.block_wheelEvent(self.cb_cat) 
        self.cb_cat.currentIndexChanged.connect(lambda idx: self.on_cat_changed(self.cb_cat.itemData(idx)))
        h.addWidget(QLabel(_("選擇分類:"))); h.addWidget(self.cb_cat)
        
        btn_load = QPushButton(_("載入所選分類縮圖")); btn_load.clicked.connect(self.load_gallery)
        # 🛡️ 新增清除快取按鈕
        btn_clear = QPushButton(_("🧹 清除圖庫快取")); btn_clear.setStyleSheet("color: #D83C3C; font-weight: bold;")
        btn_clear.clicked.connect(self.clear_cache)
        h.addWidget(btn_load); h.addWidget(btn_clear)
        v.addLayout(h)
        
        self.list_widget = QListWidget()
        self.list_widget.setViewMode(QListWidget.IconMode)
        self.list_widget.setResizeMode(QListWidget.Adjust)
        self.list_widget.setSpacing(10)
        self.list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_widget.setWordWrap(True) # 🛡️ 啟用文字換行，防止文字過長撐破網格導致錯位
        
        # 🛡️ 修正：移除 QAbstractItemView 的局部引入，直接使用最上方的全域引入
        from PySide6.QtWidgets import QListView
        self.list_widget.setMovement(QListView.Movement.Static)
        self.list_widget.setDragEnabled(False)
        self.list_widget.setAcceptDrops(False)
        self.list_widget.setAutoScroll(False) # 🛡️ 切斷內建拖曳慣性，消除震盪
        self._gallery_drag_filter = LinearDragScrollFilter(self.list_widget, speed_boost=1.5)
        
        # 🛡️ 修改滾輪邏輯：設定為按項目滾動 (無慣性)，並將步長鎖定為 1 (一格滾輪一列)
        self.list_widget.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)

        self.undo_stack = []
        self.shortcut_undo = QShortcut(QKeySequence("Ctrl+Z"), self)
        self.shortcut_undo.activated.connect(self.undo_delete)
        
        old_keyPressEvent = self.list_widget.keyPressEvent
        def custom_keyPressEvent(event):
            if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
                self.delete_selected_items()
                event.accept()
            else:
                old_keyPressEvent(event)
        self.list_widget.keyPressEvent = custom_keyPressEvent
        
        # 🛡️ 徹底接管滾動引擎：抹除 Qt 所有的物理加減速動畫，實現網頁式的「直上直下」
        def instant_wheel_scroll(event):
            v_bar = self.list_widget.verticalScrollBar()
            delta = event.angleDelta().y()
            if delta != 0:
                # 網頁式線性滾動：按物理滾動量等比例直接遞增/遞減，毫秒級反應，完全沒有平滑動畫與慣性累積
                # 使用 1.25 倍率能讓滑鼠滾輪非常靈敏，且觸控板雙指滑動時順暢無比、即停即止
                scroll_amount = int(delta * 1.25)
                v_bar.setValue(v_bar.value() - scroll_amount)
            # 強制吸收事件，防止滾動向父視窗傳遞
            event.accept()
            
        self.list_widget.wheelEvent = instant_wheel_scroll
        
        self.list_widget.itemDoubleClicked.connect(lambda i: self.send_to_tab9(i))
        v.addWidget(self.list_widget)
        
        h2 = QHBoxLayout()
        self.btn_t2 = QPushButton(_("傳送至「找出檔案」")); self.btn_t2.clicked.connect(self.send_to_tab2)
        self.btn_t9 = QPushButton(_("傳送至「快捷單卡改圖」")); self.btn_t9.clicked.connect(lambda: self.send_to_tab9())
        
        self.btn_send_back = QPushButton(_("✨ 確認修改並返回(可選取並刪除不想要的項目)"))
        self.btn_send_back.setStyleSheet("color: #2CC985; font-weight: bold; font-size: 15px; padding: 10px;")
        self.btn_send_back.clicked.connect(self.send_back_to_extract)
        self.btn_send_back.hide() # 預設隱藏
        
        h2.addWidget(self.btn_t2); h2.addWidget(self.btn_t9); h2.addWidget(self.btn_send_back)
        v.addLayout(h2)
        self.layout.addWidget(grp)

    def on_cat_changed(self, logic_id):
        # 🛡️ UX Bug 修復：切換分類時強制清空清單與還原堆疊，避免幽靈圖片與錯亂
        self.list_widget.clear()
        self.undo_stack.clear()
        
        is_filter = (logic_id == "CAT_FILTER")
        self.btn_send_back.setVisible(is_filter)
        self.btn_t2.setVisible(not is_filter)
        self.btn_t9.setVisible(not is_filter)

    def set_filter_mode(self, id_list):
        self._filter_target_ids = id_list
        # 改用 findData 尋找底層資料，免疫翻譯系統帶來的字串變動
        idx = self.cb_cat.findData("CAT_FILTER")
        if idx >= 0:
            self.cb_cat.setCurrentIndex(idx)
        self.load_gallery()

    def delete_selected_items(self):
        selected = self.list_widget.selectedItems()
        if not selected: return
        action = []
        # 降冪排列索引，這樣在 takeItem 時才不會導致下方項目的索引發生偏移錯亂
        for item in sorted(selected, key=lambda i: self.list_widget.row(i), reverse=True):
            row = self.list_widget.row(item)
            taken = self.list_widget.takeItem(row)
            action.append((row, taken))
        self.undo_stack.append(action)

    def undo_delete(self):
        if getattr(self, 'undo_stack', None):
            action = self.undo_stack.pop()
            # 因為存入時是降冪(由底到頂)，復原時必須反轉為升冪(由頂到底)，才能讓項目回到完美的最初位置
            for row, item in reversed(action):
                self.list_widget.insertItem(row, item)

    def send_back_to_extract(self):
        ids = []
        for i in range(self.list_widget.count()):
            ids.append(self.list_widget.item(i).data(Qt.UserRole))
        # 廣播更新，並清除專屬沙盒
        self.config.signals.sync_filter_result.emit(ids)
        self.undo_stack.clear()
        self.list_widget.clear()
        cache_dir = os.path.join(MDEngine.TEMP_DIR, "filter_sandbox")
        if os.path.exists(cache_dir):
            import shutil
            shutil.rmtree(cache_dir, ignore_errors=True)
            
    def load_gallery(self):
        c = self.config
        csv_path = clean_path(c.get("t2_csv_dir"))
        if not os.path.exists(csv_path): return QMessageBox.warning(self, _("錯誤"), _("請先確認「找出檔案」分頁的 CSV 對照表已載入！"))
        mapping, _db = MDEngine.get_csv_data(csv_path)
        
        cat_name = self.cb_cat.currentData()

        # 👇 攔截「檔案篩選」模式，改用專屬沙盒邏輯
        if cat_name == "CAT_FILTER":
            if not hasattr(self, '_filter_target_ids') or not self._filter_target_ids:
                return QMessageBox.warning(self, _("提示"), _("請先從「找出檔案」分頁點擊「🔍 視覺化篩選」來載入資料。"))
            items_to_fetch = {}
            render_list = {}
            for tid in self._filter_target_ids:
                if tid in mapping:
                    entries = mapping[tid]
                    hash_val = entries[0]['hash']
                    for entry in entries: items_to_fetch.setdefault(entry['hash'], []).append(tid)
                    render_list[tid] = hash_val
            
            if not items_to_fetch: return QMessageBox.information(self, _("提示"), _("在對照表中找不到這些項目的對應檔案。"))
            
            self._gallery_render_list = render_list
            src_dir, cache_dir = clean_path(c.get("t2_src_dir")), os.path.join(MDEngine.TEMP_DIR, "filter_sandbox")
            self.app.execute_task(None, _("生成篩選縮圖中"), MDEngine.task_gallery_cache, (items_to_fetch, src_dir, cache_dir), self.render_gallery)
            return
        
        cat_map = {
            "CAT_MAT": lambda n: 'basecolor' in n.lower() and 'mat_' in n.lower(),
            "CAT_COIN": lambda n: 'coin01tex' in n.lower() or 'cointossicon' in n.lower(),
            "CAT_DECKCASE": lambda n: 'deckcase' in n.lower(),
            "CAT_FRAME": lambda n: 'profileframe' in n.lower(),
            "CAT_ICON": lambda n: 'profileicon' in n.lower(),
            "CAT_SLEEVE": lambda n: 'protectoricon' in n.lower(),
            "CAT_WALLPAPER": lambda n: 'wallpaper' in n.lower() and not any(b in n.lower() for b in ['wallpapericon', 'wallpaperthumb', 'gui_wallpaperbg', 'productthumbbgwallpaperprofile', 'sactx-0-2048x1024-bc7', 'wallpapersale', 'wallpapertopicsthumb'])
        }
        filter_fn = cat_map.get(cat_name)
        
        items_to_fetch = {}
        render_list = {}
        for item_id, entries in mapping.items():
            if filter_fn(item_id):
                hash_val = entries[0]['hash']
                for entry in entries: items_to_fetch.setdefault(entry['hash'], []).append(item_id)
                render_list[item_id] = hash_val
                    
        if not items_to_fetch: return QMessageBox.information(self, _("提示"), _("在對照表中找不到該分類的項目。請確認已掃描並補齊對照表！"))
            
        self._gallery_render_list = render_list
        src_dir, cache_dir = clean_path(c.get("t2_src_dir")), os.path.join(MDEngine.TEMP_DIR, "gallery_cache")
        self.app.execute_task(None, _("生成縮圖快取中"), MDEngine.task_gallery_cache, (items_to_fetch, src_dir, cache_dir), self.render_gallery)
            
    def render_gallery(self, ct, cache_dir):
        self.list_widget.clear()
        cat_name = self.cb_cat.currentData()
        is_sleeve = (cat_name == "CAT_SLEEVE")
        
        # 🛡️ 鎖死網格大小 (GridSize)，給予充裕的高度空間
        if is_sleeve:
            self.list_widget.setIconSize(QSize(100, 150))
            self.list_widget.setGridSize(QSize(130, 230))
        else:
            self.list_widget.setIconSize(QSize(128, 128))
            self.list_widget.setGridSize(QSize(155, 215))
        
        render_dict = getattr(self, '_gallery_render_list', {})
        all_ids = set(render_dict.keys())
        
        for item_id, hash_val in render_dict.items():
            if item_id.startswith("ProfileFrame") or item_id.startswith("ProfileIcon"):
                if not item_id.endswith("_L") and not item_id.endswith("_l"):
                    if f"{item_id}_L" in all_ids or f"{item_id}_l" in all_ids:
                        continue 
                        
            img_path = os.path.join(cache_dir, f"{item_id}.png")
            if os.path.exists(img_path):
                pix = QPixmap(img_path)
                pix = pix.scaled(100, 150, Qt.IgnoreAspectRatio, Qt.SmoothTransformation) if is_sleeve else pix.scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                
                # 🛡️ 破解 Qt 愚蠢的換行機制：強制依據字元長度切割並換行
                # width=16 代表大約每 16 個字母就強制換行，break_long_words=True 允許切斷沒有空白的長單字
                wrapped_name = textwrap.fill(item_id, width=16, break_long_words=True)
                
                # 將換行處理後的名字與 Hash 碼組合
                item = QListWidgetItem(QIcon(pix), f"{wrapped_name}\n[{hash_val[:8]}]")
                item.setData(Qt.UserRole, item_id)
                
                # 🛡️ 設定文字置中對齊，讓換行後的文字看起來像是整齊的碑文，而不是歪七扭八的
                item.setTextAlignment(Qt.AlignCenter)
                
                # 終極防線：保留 ToolTip 讓玩家依然能輕易複製或查看最原始的單行名稱
                item.setToolTip(_("完整名稱: {item_id}\nHash檔名: {hash_val}").format(item_id=item_id, hash_val=hash_val))
                
                self.list_widget.addItem(item)
        return _("圖庫載入完成！")
        
    def send_to_tab2(self):
        selected = self.list_widget.selectedItems()
        if not selected: return
        mapping, _db = MDEngine.get_csv_data(self.config.get("t2_csv_dir"))
        all_ids = set(mapping.keys())
        to_extract = set()
        
        for item in selected:
            item_id = item.data(Qt.UserRole)
            base_name = MDEngine.get_base_item_name(item_id) # 🛡️ 主幹辨識
            
            # 廣域聯想：整株拔起所有變體
            for k in all_ids:
                if k.startswith(base_name): to_extract.add(k)
                    
            # 🛡️ 硬幣特別追加：自動加入反面
            if "cointossicon" in item_id.lower() or "coin01tex" in item_id.lower():
                if "CoinTossIcon_Tails" in all_ids: to_extract.add("CoinTossIcon_Tails")
                    
        self.config.signals.append_extraction_list.emit("\n".join(to_extract))
        
        QMessageBox.information(self, _("成功"), _("已成功傳送 {count} 個關聯項目至「找出檔案」清單！").format(count=len(to_extract)))
        self.app.select_tab("t2_find")
        
    def send_to_tab9(self, item=None):
        if not item:
            selected = self.list_widget.selectedItems()
            if not selected: return
            item = selected[0]
            
        # 🛡️ 解耦：發射設定 ID 的訊號
        self.config.signals.set_quick_mod_id.emit(item.data(Qt.UserRole))
        self.app.select_tab("t9_quick_mod")

    def clear_cache(self):
        """安全地清除所有生成的圖庫快取檔"""
        cache_dir = os.path.join(MDEngine.TEMP_DIR, "gallery_cache")
        if not os.path.exists(cache_dir) or not os.listdir(cache_dir): 
            return QMessageBox.information(self, _("提示"), _("目前沒有任何快取檔案，不需要清理！"))
        
        reply = QMessageBox.question(self, _("清除快取"), _("確定要清除所有圖庫快取嗎？\n(下次載入時將會重新生成縮圖)"), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                import shutil
                shutil.rmtree(cache_dir)
                self.list_widget.clear()
                QMessageBox.information(self, _("成功"), _("快取已全數清除完畢！"))
            except Exception as e:
                QMessageBox.critical(self, _("錯誤"), _("清除快取失敗：{error}").format(error=e))

# ==================== 分頁 10: 串流修復 ====================
class TabUpdater(BaseTab):
    def __init__(self, main_app):
        super().__init__(main_app)
        self.layout.addWidget(QLabel(_("【模組救援】將舊模組卡圖自動替換到最新版遊戲原檔中")))
        grp = QGroupBox(_("設定"))
        form = QFormLayout(grp)
        self.make_path_row(form, _("1. 舊模組目錄"), "t10_old_mod_dir", placeholder="請輸入舊模組資料夾(子資料夾需要包含0000)")
        self.make_path_row(form, _("2. 遊戲原檔 (0000)"), "t10_clean_src_dir", sync_type="src", placeholder="你的槽:\\SteamLibrary\\steamapps\\common\\Yu-Gi-Oh! Master Duel\\LocalData\\你的八字編號\\0000")
        self.make_path_row(form, _("3. 輸出根目錄"), "t10_out_dir", sync_type="root", placeholder="請輸入或選擇此專案的工作根目錄...")
        form.addRow(self.bind_check("t10_overwrite", _("覆蓋舊模組 (不建議使用)")))
        self.layout.addWidget(grp)
        
        self.btn_run = QPushButton(_("開始串流修復")); self.btn_run.clicked.connect(self.run_task)
        self.layout.addWidget(self.btn_run)

    def run_task(self):
        c = self.config
        old_mod, clean_src, out_root, overwrite = clean_path(c.get("t10_old_mod_dir")), clean_path(c.get("t10_clean_src_dir")), clean_path(c.get("t10_out_dir")), c.get("t10_overwrite")
        if not os.path.isdir(old_mod) or not os.path.isdir(clean_src):
            return QMessageBox.critical(self, _("錯誤"), _("請確認「舊模組目錄」與「遊戲原檔目錄」皆存在！"))
        if not overwrite and not os.path.isdir(out_root):
            return QMessageBox.critical(self, _("錯誤"), _("請設定一個有效的「輸出儲存根目錄」。"))
        if overwrite:
            reply = QMessageBox.question(self, _("風險警告"), _("你選擇了「直接覆蓋掉舊模組」。\n請問是否繼續？"), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No: return
        self.app.execute_task(self.btn_run, _("記憶體單檔串流修復中"), MDEngine.task_stream_update, 
            (old_mod, clean_src, out_root, overwrite), 
            lambda ct, e: _("修復完成！共修復 {count} 個檔案。").format(count=ct) + ("" if overwrite else _("\n\n存放在：\n{extra}").format(extra=e)))

# ==================== 分頁 11: 虛擬掛載 ====================
class TabVirtualMount(BaseTab):
    log_signal = Signal(str)

    def __init__(self, main_app):
        super().__init__(main_app)
        self.layout.addWidget(QLabel(_("【模組管理】建立檔案系統軟連結，免開工具亦生效")))
        is_admin = _check_admin()
        warn_text = _("✅ 管理員權限已確認。您可以安全使用此掛載功能。") if is_admin else _("⚠️ 警告：尚未取得管理員權限！為防止誤觸與錯誤，部分功能已自動鎖定。")
        warn_lbl = QLabel(warn_text)
        warn_lbl.setStyleSheet("color: #2CC985;" if is_admin else "color: #D83C3C;")
        self.layout.addWidget(warn_lbl)
        grp = QGroupBox(_("掛載設定"))
        form = QFormLayout(grp)
        self.t11_root = self.make_path_row(form, _("模組存放根目錄"), "t11_mod_root_dir", placeholder="輸入統一存放模組的資料夾(子資料夾需要包含0000)")
        self.make_path_row(form, _("遊戲 0000 資料夾"), "t11_game_0000_dir", placeholder="你的槽:\\SteamLibrary\\steamapps\\common\\Yu-Gi-Oh! Master Duel\\LocalData\\你的八字編號\\0000")
        
        cb_depth = QComboBox(); cb_depth.addItems(["1","2","3","4","5"]); cb_depth.setCurrentText(str(self.config.get("t11_scan_depth", "3")))
        cb_depth.currentTextChanged.connect(lambda t: self.config.set("t11_scan_depth", t))
        
        box_d = QHBoxLayout(); box_d.addWidget(cb_depth); btn_ref = QPushButton(_("重新整理")); btn_ref.clicked.connect(self.refresh_list)
        box_d.addWidget(btn_ref)
        form.addRow(_("掃描深度 (穿透n層資料夾):"), box_d)
        self.layout.addWidget(grp)

        grp_list = QGroupBox(_("模組優先權排序 (左側啟用，右側停用)"))
        h = QHBoxLayout(grp_list)
        
        self.list_en = QListWidget(); self.list_en.setDragDropMode(QAbstractItemView.InternalMove)
        self.list_dis = QListWidget(); self.list_dis.setDragDropMode(QAbstractItemView.InternalMove)

        self.prevent_scroll_propagation(self.list_en)
        self.prevent_scroll_propagation(self.list_dis)

        for lst in [self.list_en, self.list_dis]:
            lst.setSelectionMode(QAbstractItemView.ExtendedSelection)
            lst.setSelectionRectVisible(True)
            lst.setDragDropMode(QAbstractItemView.NoDragDrop)
        
        # 雙擊互相移動
        self.list_en.itemDoubleClicked.connect(lambda item: self.list_dis.addItem(self.list_en.takeItem(self.list_en.row(item))))
        self.list_dis.itemDoubleClicked.connect(lambda item: self.list_en.addItem(self.list_dis.takeItem(self.list_dis.row(item))))
        
        v_btn = QVBoxLayout()
        btn_to_dis = QPushButton(">>"); btn_to_dis.clicked.connect(lambda: [self.list_dis.addItem(self.list_en.takeItem(r)) for r in reversed(range(self.list_en.count())) if self.list_en.item(r).isSelected()])
        btn_to_en = QPushButton("<<"); btn_to_en.clicked.connect(lambda: [self.list_en.addItem(self.list_dis.takeItem(r)) for r in reversed(range(self.list_dis.count())) if self.list_dis.item(r).isSelected()])
        btn_up = QPushButton("▲"); btn_up.clicked.connect(lambda: UIHelper.move_list_items(self.list_en, -1))
        btn_dn = QPushButton("▼"); btn_dn.clicked.connect(lambda: UIHelper.move_list_items(self.list_en, 1))

        for btn in [btn_to_dis, btn_to_en, btn_up, btn_dn]: btn.setEnabled(is_admin)

        v_btn.addWidget(btn_to_dis); v_btn.addWidget(btn_to_en); v_btn.addSpacing(15); v_btn.addWidget(btn_up); v_btn.addWidget(btn_dn)
        
        h.addWidget(self.list_en); h.addLayout(v_btn); h.addWidget(self.list_dis)
        self.layout.addWidget(grp_list)
        
        self.log_txt = QPlainTextEdit(); self.log_txt.setFixedHeight(100); self.log_txt.setReadOnly(True)
        self.layout.addWidget(self.log_txt)
        self.prevent_scroll_propagation(self.log_txt)
        self.log_signal.connect(self.log_txt.appendPlainText)

        UIHelper.setup_quick_transfer(self.list_en, self.list_dis)
        UIHelper.setup_quick_transfer(self.list_dis, self.list_en)
        
        self.btn_run = QPushButton(_("▶ 套用並儲存")); self.btn_run.clicked.connect(self.run_apply)
        self.btn_run.setEnabled(is_admin)
        self.layout.addWidget(self.btn_run)
        
        self._last_root = clean_path(self.config.get("t11_mod_root_dir"))
        self.t11_root.textChanged.connect(self.check_and_refresh_root)
        self.refresh_list()

    def check_and_refresh_root(self, text):
        new_path = clean_path(text)
        state = MDEngine.t11_load_state()
        if hasattr(self, '_last_root') and self._last_root != new_path:
            if state:
                reply = QMessageBox.warning(
                    self, _("風險警告"), 
                    _("偵測到您目前有虛擬模組正在掛載中！\n此時更改模組根目錄，可能會導致後續「解除掛載失敗」或「遊戲原檔迷失」。\n強烈建議您先點擊「卸載並還原原檔」後，再更改模組路徑。\n\n確定要強制切換路徑嗎？"),
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if reply == QMessageBox.No:
                    # 玩家拒絕切換，安全地將 UI 上的路徑退回原狀 (切斷訊號以防無限迴圈)
                    self.t11_root.blockSignals(True)
                    self.t11_root.setText(self._last_root)
                    self.t11_root.blockSignals(False)
                    return
                    
        self._last_root = new_path
        if os.path.isdir(new_path):
            self.refresh_list()

    def refresh_list(self):
        self.list_en.clear(); self.list_dis.clear()
        root = clean_path(self.config.get("t11_mod_root_dir"))
        if not os.path.isdir(root): return
        folders = [f for f in os.listdir(root) if os.path.isdir(os.path.join(root, f))]
        for am in self.config.get("t11_active_mods", []):
            if am in folders: self.list_en.addItem(am); folders.remove(am)
        for f in folders: self.list_dis.addItem(f)

    def log(self, text):
        self.log_signal.emit(text)

    def run_apply(self):
        c = self.config
        root, game = clean_path(c.get("t11_mod_root_dir")), clean_path(c.get("t11_game_0000_dir"))
        if not os.path.isdir(root) or not os.path.isdir(game): return QMessageBox.warning(self, _("錯誤"), _("請確認路徑存在！"))
        
        raw_active = [self.list_en.item(i).text() for i in range(self.list_en.count())]
        
        valid_active, ghosts = MDEngine.filter_valid_mods(root, raw_active)
        if ghosts:
            self.list_en.clear()
            self.list_en.addItems(valid_active)
            self.log(_("⚠️ 自動剔除不存在的幽靈模組：{ghosts}").format(ghosts=", ".join(ghosts)))
            
        self.log_txt.clear(); self.log(_("🔄 套用中..."))
        
        # 🛡️ 智慧收集使用者在「設定」填寫的所有自訂資料夾名稱，轉為小寫集合交給底層排除
        ignore_list = {
            str(c.get("s_folder_raw", "")).strip().lower(),
            str(c.get("s_folder_backup", "")).strip().lower(),
            str(c.get("s_folder_mod", "")).strip().lower(),
            str(c.get("s_folder_out", "")).strip().lower(),
            str(c.get("t8_backup_folder", "")).strip().lower()
        }
        ignore_list.discard("") # 清除可能產生的空字串
        
        # 使用 c_num 避免變數與上面的 Config (c) 撞名
        def on_unmount(c_num, e):
            if not valid_active: 
                self.config.set("t11_active_mods", [])
                self.config.save_t11_only([])
                self.log(_("✅ 所有模組已解除掛載。"))
                # 透過回傳字串，讓外層 execute_task 自動呼叫 QMessageBox 彈出提示，不破壞模組化
                return _("已徹底清除所有模組捷徑並還原官方原裝檔案。")
                
            self.log(_("🔍 開始掛載..."))
            self.app.execute_task(self.btn_run, _("建立連結中"), MDEngine.task_virtual_mount, 
                (root, game, valid_active, self.get_safe_int("t11_scan_depth", 3), ignore_list, self.log), 
                lambda ct, ex: self._on_mount_success(valid_active, ct))
            
            # 回傳空字串，防止 execute_task 在此階段提早彈出完成視窗
            return "" 
                
        self.app.execute_task(self.btn_run, _("解除掛載中"), MDEngine.task_virtual_unmount, (True, self.log), on_unmount)

    def _on_mount_success(self, valid_active, success_count):
        # 🛡️ 狀態完美同步：掛載成功後才安全寫入 JSON，並顯示掛載數量
        self.config.set("t11_active_mods", valid_active)
        self.config.save_t11_only(valid_active)
        msg = _("✨ 套用成功！\n共成功建立並連結了 {count} 個檔案。").format(count=success_count)
        self.log(msg)
        return msg

# ==================== 分頁 6: 自動化調度 ====================
class TabChain(BaseTab):
    def __init__(self, main_app):
        super().__init__(main_app)
        self.layout.addWidget(QLabel(_("【流程自動化】一鍵完成繁瑣流程 (請先確保路徑已經填好，需要有對應的TXT)")))
        grp = QGroupBox(_("欲連鎖的任務"))
        v = QVBoxLayout(grp)
        v.addWidget(self.bind_check("c_t2", _("[2] 找出檔案"))); v.addWidget(self.bind_check("c_t3", _("[3] 提取資料")))
        v.addWidget(self.bind_check("c_t8", _("[8] 靈擺後處理"))); v.addWidget(self.bind_check("c_t4", _("[4] 更改卡圖")))
        v.addWidget(self.bind_check("c_t5", _("[5] 封裝模組")))
        self.layout.addWidget(grp)
        
        self.btn_run = QPushButton(_("▶ 開始自動化作業")); self.btn_run.clicked.connect(self.start_chain)
        self.layout.addWidget(self.btn_run)

    def start_chain(self):
        c = self.config
        if c.get("c_t4"):
            mod_dir = MDEngine.resolve_path(clean_path(c.get("t4_root_dir")), c.get("t4_mod_name", "").strip() or "卡圖改")
            if not os.path.isdir(mod_dir) or not any(f.lower().endswith(('.png', '.jpg')) for f in os.listdir(mod_dir)):
                return QMessageBox.critical(self, _("防呆錯誤"), _("偵測到勾選了「更改卡圖」，但您的「欲替換的圖片」資料夾內沒有圖片！已終止。"))
        
        queue = []
        if c.get("c_t2"): queue.append("T2")
        if c.get("c_t3"): queue.append("T3")
        if c.get("c_t8"): queue.append("T8")
        if c.get("c_t4"): queue.append("T4")
        if c.get("c_t5"): queue.append("T5")
        
        if not queue: return
        self.btn_run.setEnabled(False)
        self.run_next(queue, True, 0, None)

    def run_next(self, queue, success, count, extra):
        if not success:
            self.btn_run.setEnabled(True)
            return QMessageBox.critical(self, _("錯誤"), _("某個環節發生錯誤，已終止後續任務。"))
        if not queue:
            self.btn_run.setEnabled(True)
            return QMessageBox.information(self, _("完成"), _("所選任務皆滿意地執行完畢！"))
            
        task = queue.pop(0)
        c = self.config
        
        if task == "T2":
            folder_name = c.get("t2_folder_name", "").strip() or "原檔"
            out_d = os.path.join(c.get("t2_out_dir", ""), folder_name)
            
            # 【完美解耦】直接由 ConfigManager 獲取暫存清單，並使用 or 運算子避免 "None" 轉化為實體字串
            ui_text = str(c.get("t2_extraction_list") or "")
            if not ui_text.strip():
                try:
                    with open(clean_path(c.get("t2_txt_dir")), "r", encoding="utf-8") as f:
                        ui_text = f.read()
                except: pass
                
            # 呼叫集中化萃取器
            ids = [extracted for line in ui_text.splitlines() if (extracted := MDEngine.extract_id_from_line(line))]
            
            self.app.execute_task(None, _("[自動化] 尋找檔案"), MDEngine.task_find, (c.get("t2_csv_dir"), c.get("t2_src_dir"), out_d, ids, c.get("enable_visual_only_filter", True)), lambda s,c_num,x: self.run_next(queue, s, c_num, x), is_chain=True)
            
        elif task == "T3":
            folder_name = c.get("t2_folder_name", "").strip() or "原檔" 
            hash_dir = os.path.join(c.get("t2_out_dir", ""), folder_name)
            
            # 🛡️ 確保自動化流程也具備主對照表的映射能力
            self.app.execute_task(None, _("[自動化] 提取資料"), MDEngine.task_extract, 
                (hash_dir, c.get("t3_img_folder"), c.get("s_folder_backup"), c.get("s_csv_mapping"), 
                 c.get("t3_exp_csv"), c.get("t3_exp_img"), c.get("t3_exp_txt", True), c.get("t3_exp_backup"), c.get("t2_csv_dir"), c.get("enable_visual_only_filter", True)), lambda s,c_num,x: self.run_next(queue, s, c_num, x), is_chain=True)
                 
        elif task == "T8":
            mod_dir = MDEngine.resolve_path(clean_path(c.get("t8_root_dir")), c.get("t8_mod_dir", "").strip() or "卡圖改")
            lines = MDEngine.get_pendulum_list(clean_path(c.get("t8_csv_dir")), mod_dir)
            targets = [line.strip().split()[0] for line in lines if line.strip()]
            if targets:
                bk_dir = os.path.join(mod_dir, c.get("t8_backup_folder", "").strip() or "修改前原檔")
                # 🛡️ 補齊引擎需要的透明度參數
                opacities = {
                    "periframe": float(c.get("t8_op_periframe", 1.0)), "namebox": float(c.get("t8_op_namebox", 1.0)),
                    "artframe": float(c.get("t8_op_artframe", 1.0)), "effframe": float(c.get("t8_op_effframe", 1.0)),
                    "effbox": float(c.get("t8_op_effbox", 1.0)), "background": float(c.get("t8_op_background", 1.0))
                }
                self.app.execute_task(None, _("[自動化] 靈擺處理"), MDEngine.task_post_process, 
                    (mod_dir, bk_dir, c.get("t8_enable_backup"), self.get_safe_int("t8_padding_pct", 25), targets, "pendulum", clean_path(c.get("t8_csv_dir")), opacities), lambda s,c_num,x: self.run_next(queue, s, c_num, x), is_chain=True)
            else: 
                self.run_next(queue, True, 0, None)
            
        elif task == "T4":
            root = clean_path(c.get("t4_root_dir"))
            bk_dir = MDEngine.resolve_path(root, c.get("t4_backup_name", "").strip() or "文件備份")
            mod_dir = MDEngine.resolve_path(root, c.get("t4_mod_name", "").strip() or "卡圖改")
            self.app.execute_task(None, _("[自動化] 更改卡圖"), MDEngine.task_replace, 
                (c.get("t4_csv_dir"), root, bk_dir, mod_dir, c.get("s_folder_out", "").strip() or "改完的文件"), lambda s,c_num,x: self.run_next(queue, s, c_num, x), is_chain=True)
                
        elif task == "T5":
            root = clean_path(c.get("t5_root_dir"))
            mod_dir = MDEngine.resolve_path(root, c.get("t4_mod_name", "").strip() or "卡圖改")
            self.app.execute_task(None, _("[自動化] 封裝模組"), MDEngine.task_package, 
                (root, c.get("t5_mod_folder_name", "").strip() or "ModFolder", c.get("t5_readme_text"), mod_dir, 
                 c.get("t5_pack_zip"), c.get("t5_csv_dir"), c.get("s_folder_backup", "").strip() or "文件備份", 
                 c.get("s_folder_out", "").strip() or "改完的文件", c.get("t8_backup_folder", "").strip() or "修改前原檔",
                 c.get("t5_include_mod_folder", True), c.get("t5_include_readme", True), c.get("s_csv_mapping", "2DTexture_Mapping.csv")), lambda s,c_num,x: self.run_next(queue, s, c_num, x), is_chain=True)

# ==================== 分頁 13: 超框註冊器 ====================
class TabOverFrame(BaseTab):
    def __init__(self, main_app):
        super().__init__(main_app)
        self.config.signals.quick_mod_to_overframe_reg.connect(self.handle_quick_mod_reg)
        
        lbl_title = QLabel(_("【專屬工具】超框立體卡圖白名單註冊器 (Over-Frame Art)"))
        lbl_title.setWordWrap(True) # 🛡️ 修復：防止標題過長撐破視窗
        self.layout.addWidget(lbl_title)

        warn_lbl = QLabel(_("⚠️ 溫馨提醒：超框立體卡圖請使用 11:16 寬高比（例如 704 x 1024）的圖片。\n寫入此註冊表後，遊戲會把該圖「覆蓋在整張卡片之上」，使用傳統方形卡圖會嚴重變形！\n目前的註冊表會隨著遊戲更新自動尋找替換。"))
        warn_lbl.setStyleSheet("color: #E0C030; font-weight: bold; font-size: 14px; margin-bottom: 5px;")
        warn_lbl.setWordWrap(True) # 🛡️ 修復：開啟自動換行，防止英文翻譯過長無限延伸
        self.layout.addWidget(warn_lbl)

        grp_paths = QGroupBox(_("路徑設定 (與其他分頁同步)"))
        form = QFormLayout(grp_paths)
        self.make_path_row(form, _("字典 (CSV) 檔案"), "t13_csv_dir", True, "CSV", "csv", placeholder="請選擇全域對照表 CSV 檔案（可於「設定與外觀」保存預設值）...")
        self.make_path_row(form, _("遊戲原檔來源 (0000)"), "t13_src_dir", sync_type="src", placeholder="你的槽:\\SteamLibrary\\steamapps\\common\\Yu-Gi-Oh! Master Duel\\LocalData\\你的八字編號\\0000")
        self.make_path_row(form, _("儲存根目錄"), "t13_out_dir", sync_type="root", placeholder="請輸入或選擇此專案的工作根目錄...")
        
        self.cb_gate_hash = QComboBox()
        self.cb_gate_hash.setEditable(True)
        self._load_hash_history()
        self.cb_gate_hash.setCurrentText(self.config.get("t13_gate_hash", "22817d01"))
        self.cb_gate_hash.currentTextChanged.connect(lambda t: self.config.set("t13_gate_hash", t.strip()))
        self.block_wheelEvent(self.cb_gate_hash)
        form.addRow(_("目標註冊表 (Hash):"), self.cb_gate_hash)
        
        self.make_path_row(form, _("欲合併用註冊表 (可選)"), "t13_merge_gate_path", True, "All", placeholder="請選擇做好的of_card_asset註冊表(將會合併另存新檔)")
        self.layout.addWidget(grp_paths)

        # 第一部分：註冊項目讀取器
        grp1 = QGroupBox(_("第一部分：現有白名單讀取與管理"))
        v1 = QVBoxLayout(grp1)
        
        h_lang = QHBoxLayout()
        self.cb_lang = QComboBox()
        self.cb_lang.addItems(["zh-tw", "zh-cn", "en-us", "ja-jp"])
        self.cb_lang.setEditable(True)
        self.cb_lang.setMinimumWidth(100) # 🛡️ 對齊快捷單卡：設定選單最小寬度 100px，徹底杜絕擠壓
        self.cb_lang.setCurrentText(self.config.get("search_lang", "zh-tw"))
        self.cb_lang.currentTextChanged.connect(lambda t: [self.config.set("search_lang", t), self.load_gate_if_possible()])
        self.block_wheelEvent(self.cb_lang)

        lbl_lang_t13 = QLabel(_("顯示對照語系:"))
        lbl_lang_t13.setMinimumWidth(90) # 🛡️ 設定標籤最小寬度，防止字被擠壓

        btn_manual_sync = QPushButton(_("🛠️ 手動爆搜修正 (大更新後專用)"))
        btn_manual_sync.setStyleSheet("color: #D83C3C; font-weight: bold;")
        btn_manual_sync.clicked.connect(self.run_manual_sync)

        # 🛡️ 權重皆設為 0，確保元件維持正常尺寸，由最後的 addStretch(1) 來吸收剩餘寬度
        h_lang.addWidget(lbl_lang_t13, 0)
        h_lang.addWidget(self.cb_lang, 0)
        h_lang.addWidget(btn_manual_sync, 0)
        h_lang.addStretch(1)
        v1.addLayout(h_lang)

        grid1 = QGridLayout() # 👈 改用 Grid 網格佈局
        btn_load = QPushButton(_("📥 讀取現有原檔")); btn_load.clicked.connect(self.load_gate)
        btn_clear = QPushButton(_("🧹 清除快取註冊表")); btn_clear.setStyleSheet("color: #D83C3C; font-weight: bold;")
        btn_clear.clicked.connect(self.clear_cache)
        btn_save_ext = QPushButton(_("💾 儲存現有白名單")); btn_save_ext.setStyleSheet("color: #2CC985; font-weight: bold;")
        btn_save_ext.clicked.connect(self.save_existing_only)
        btn_merge = QPushButton(_("🔗 與「欲合併用註冊表」合併")); btn_merge.clicked.connect(self.merge_gate)

        # 第一列 (Row 0)
        grid1.addWidget(btn_load, 0, 0)
        grid1.addWidget(btn_clear, 0, 1)
        # 第二列 (Row 1)
        grid1.addWidget(btn_save_ext, 1, 0)
        grid1.addWidget(btn_merge, 1, 1)

        v1.addLayout(grid1)

        mono_font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        if mono_font.pointSize() <= 0: mono_font.setPointSize(10)
        
        self.txt_existing = QPlainTextEdit()
        self.txt_existing.setFont(mono_font)
        self.txt_existing.setMinimumHeight(200)
        self.prevent_scroll_propagation(self.txt_existing)
        v1.addWidget(self.txt_existing)
        self.layout.addWidget(grp1)

        # 第二部分：新增註冊
        grp3 = QGroupBox(_("第二部分：新增註冊與寫入"))
        v3 = QVBoxLayout(grp3)
        
        # 👈 改用 2x2 網格佈局 (QGridLayout)，釋放雙倍的水平寬度
        grid3 = QGridLayout()
        btn_goto_t2 = QPushButton(_("🔍 前往「找出檔案」頁面挑選卡片"))
        btn_goto_t2.clicked.connect(self.goto_tab2)
        btn_hist = QPushButton(_("📜 讀取過去成功註冊的歷史紀錄"))
        btn_hist.clicked.connect(self.load_history)
        btn_norm = QPushButton(_("✨ 正規化補名"))
        btn_norm.clicked.connect(self.norm_txt)
        btn_clear_hist = QPushButton(_("🧹 清除歷史紀錄"))
        btn_clear_hist.setStyleSheet("color: #D83C3C; font-weight: bold;")
        btn_clear_hist.clicked.connect(self.clear_history)

        # 第一列 (Row 0)：主要挑選與讀取功能
        grid3.addWidget(btn_goto_t2, 0, 0)
        grid3.addWidget(btn_hist, 0, 1)
        # 第二列 (Row 1)：格式整理與清除功能
        grid3.addWidget(btn_norm, 1, 0)
        grid3.addWidget(btn_clear_hist, 1, 1)

        v3.addLayout(grid3)

        self.txt_new = QPlainTextEdit()
        self.txt_new.setFont(mono_font)
        self.txt_new.setMinimumHeight(200)
        self.txt_new.setPlaceholderText(_("請輸入欲註冊超框的卡片 ID (一行一個)。\n支援直接貼上第二頁的格式！\n範例：\n20570\n22811 -> 17069 (冰劍龍借用異圖)"))
        self.prevent_scroll_propagation(self.txt_new)
        v3.addWidget(self.txt_new)
        self.layout.addWidget(grp3)

        self.btn_run = QPushButton(_("🚀 驗證衝突並輸出檔案")); self.btn_run.setStyleSheet("font-size: 15px; padding: 10px; color: #2CC985; font-weight: bold;")
        self.btn_run.clicked.connect(self.run_task)
        self.layout.addWidget(self.btn_run)

        self.config.signals.sync_extraction_list.connect(lambda t: self.txt_new.setPlainText(t) if self.txt_new.toPlainText() != t else None)
        self.config.signals.request_overframe_return.connect(lambda: [
            self.config.signals.toggle_overframe_return.emit(False),
            self.app.select_tab("t13_overframe")
        ])

        self._return_to_tab4 = False
        self.config.signals.set_return_to_tab4.connect(lambda val: setattr(self, '_return_to_tab4', val))
        self.config.signals.request_overframe_register.connect(lambda t: self.txt_new.setPlainText(t))

    def _load_hash_history(self):
        hist_file = os.path.join(MDEngine.TEMP_DIR, "of_card_asset_backups", "hash_history.json")
        hashes = ["22817d01", "a589d3b5"]
        if os.path.exists(hist_file):
            try:
                with open(hist_file, "r") as f:
                    data = json.load(f)
                    if isinstance(data, list): hashes = data
            except: pass
        self.cb_gate_hash.addItems(hashes)
        
    def _add_hash_to_history(self, new_hash):
        hist_file = os.path.join(MDEngine.TEMP_DIR, "of_card_asset_backups", "hash_history.json")
        hashes = [self.cb_gate_hash.itemText(i) for i in range(self.cb_gate_hash.count())]
        if new_hash not in hashes:
            hashes.insert(0, new_hash)
            self.cb_gate_hash.insertItem(0, new_hash)
            try:
                os.makedirs(os.path.dirname(hist_file), exist_ok=True)
                with open(hist_file, "w") as f: json.dump(hashes, f)
            except: pass

    def handle_quick_mod_reg(self, card_id):
        current_text = self.txt_new.toPlainText().strip()
        if card_id not in current_text:
            new_text = current_text + "\n" + card_id if current_text else card_id
            self.txt_new.setPlainText(new_text)
            self.norm_txt()
        self.app.select_tab("t13_overframe")

    def load_gate_if_possible(self):
        if self.txt_existing.toPlainText().strip(): self.load_gate()

    def run_manual_sync(self):
        c = self.config
        src_dir, out_root = clean_path(c.get("t13_src_dir")), clean_path(c.get("t13_out_dir"))
        if not os.path.isdir(src_dir) or not os.path.isdir(out_root):
            return QMessageBox.critical(self, _("錯誤"), _("來源或輸出目錄設定無效！"))
        
        curr_hash = c.get("t13_gate_hash", "22817d01")
        out_folder = c.get("s_folder_out", "改完的文件")
        backup_folder = c.get("s_folder_backup", "文件備份")
        
        def finish_handler(ct, hash_name):
            if isinstance(ct, bool) and not ct:
                return _("手動修正失敗：{hash}").format(hash=hash_name)
                
            self.config.set("t13_gate_hash", hash_name)
            self.cb_gate_hash.setCurrentText(hash_name)
            self.config.save_single_key("t13_gate_hash", hash_name)
            
            self._add_hash_to_history(hash_name)
            self._render_gate(os.path.join(out_root, out_folder, hash_name))
            return _("✨ 手動爆搜與合併修正成功！\n已找到最新版註冊表並成功寫入您的自訂名單。\n新的 Hash 為：{hash}").format(hash=hash_name)

        self.app.execute_task(self.btn_run, _("掃描與修正中"), MDEngine.task_manual_sync_overframe, 
            (src_dir, out_root, out_folder, backup_folder, curr_hash), finish_handler)

    def load_gate(self):
        c = self.config
        src_dir = clean_path(c.get("t13_src_dir"))
        current_hash = clean_path(c.get("t13_gate_hash", "22817d01"))
        
        gate_path = MDEngine.get_actual_bundle_path(src_dir, current_hash)
        if not os.path.exists(gate_path):
            gate_path = MDEngine.get_actual_source_path(src_dir, current_hash, "StreamingAssets")
            
        is_valid = MDEngine.validate_gate_file(gate_path)
            
        # 🛡️ 順位 2：檢查使用者輸入是否為絕對路徑
        if not is_valid and os.path.isabs(current_hash) and os.path.isfile(current_hash):
            if MDEngine.validate_gate_file(current_hash):
                gate_path = current_hash
                is_valid = True

        if not is_valid:
            out_root = clean_path(c.get("t13_out_dir"))
            out_folder = c.get("s_folder_out", "改完的文件")
            backup_folder = c.get("s_folder_backup", "文件備份")
            
            def on_found(ct, hash_name):
                if isinstance(ct, bool) and not ct: 
                    return _("自動修復失敗：{hash}").format(hash=hash_name)
                
                self.config.set("t13_gate_hash", hash_name)
                self.cb_gate_hash.setCurrentText(hash_name)
                self.config.save_single_key("t13_gate_hash", hash_name)
                self._add_hash_to_history(hash_name)
                self._render_gate(os.path.join(out_root, out_folder, hash_name))
                return _("偵測到遊戲更新，已自動爆搜並無縫轉移您的自訂名單！\n新的 Hash 為：{hash}").format(hash=hash_name)
                
            return self.app.execute_task(None, _("發現遊戲更新！自動無縫修復中"), MDEngine.task_auto_repair_gate, 
                                         (src_dir, out_root, out_folder, backup_folder, current_hash), on_found)

        self._render_gate(gate_path)

    def _get_rendered_gate_text(self, records):
        c = self.config
        target_hash = clean_path(c.get("t13_gate_hash", "22817d01"))
        clean_hash = os.path.basename(target_hash)
        pristine_path = os.path.join(MDEngine.TEMP_DIR, "of_card_asset_backups", f"{clean_hash}.pristine")
        name_map = MDEngine.get_id_to_name_map(clean_path(c.get("t13_csv_dir")), c.get("search_lang", "zh-tw"))
        
        separator = _("\n\n# ===以上為原始檔案內容，建議不要修改===")
        
        if os.path.exists(pristine_path):
            pristine_records = MDEngine.read_overframe_bytes(pristine_path)
            p_list = {t: b for t, b in records.items() if t in pristine_records and pristine_records[t] == b}
            a_list = {t: b for t, b in records.items() if t not in pristine_records or pristine_records[t] != b}
            
            p_text = MDEngine.format_overframe_records(p_list, name_map)
            a_text = MDEngine.format_overframe_records(a_list, name_map)
            
            final_text = p_text + separator
            if a_text: final_text += "\n\n" + a_text
            return final_text
        else:
            final_text = MDEngine.format_overframe_records(records, name_map)
            final_text += separator
            return final_text

    def _render_gate(self, gate_path):
        records = MDEngine.read_overframe_bytes(gate_path)
        self.txt_existing.setPlainText(self._get_rendered_gate_text(records))
        self.app.status_lbl.setText(_("狀態：遊戲現有白名單已成功載入！"))

    def clear_cache(self):
        target_hash = clean_path(self.config.get("t13_gate_hash", "22817d01"))
        clean_hash = os.path.basename(target_hash)
        pristine_path = os.path.join(MDEngine.TEMP_DIR, "of_card_asset_backups", f"{clean_hash}.pristine")
        if not os.path.exists(pristine_path):
            return QMessageBox.information(self, _("提示"), _("目前不存在任何快取基準檔案，不需清除！"))
            
        abs_path = os.path.abspath(pristine_path)
        reply = QMessageBox.warning(
            self, _("危險操作警告"), 
            _("警告：您即將刪除官方原廠的純淨基準檔 (.pristine)！\n\n如果失去此基準，後續任何異常將無法本地還原，您只能依賴 Steam 的「驗證檔案完整性」來修復。\n\n備份實體位置：\n{path}\n\n您確定要強制刪除嗎？").format(path=abs_path), 
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                os.remove(pristine_path)
                QMessageBox.information(self, _("成功"), _("快取基準檔已徹底刪除。下次載入檔案時將自動建立新的基準。"))
            except Exception as e:
                QMessageBox.critical(self, _("錯誤"), _("刪除失敗：{error}").format(error=e))

    def load_history(self):
        history_file = os.path.join(MDEngine.TEMP_DIR, "of_card_asset_backups", "registered_history.json")
        if not os.path.exists(history_file):
            return QMessageBox.information(self, _("提示"), _("找不到任何註冊歷史紀錄。"))
        try:
            with open(history_file, "r", encoding="utf-8") as f: raw_hist = json.load(f)
            if not raw_hist: return QMessageBox.information(self, _("提示"), _("歷史紀錄是空的。"))
            
            hist_recs = {}
            if isinstance(raw_hist, list):
                for k in raw_hist:
                    if str(k).isdigit(): hist_recs[int(k)] = int(k)
            elif isinstance(raw_hist, dict):
                for k, v in raw_hist.items():
                    if str(k).isdigit() and str(v).isdigit(): hist_recs[int(k)] = int(v)
            
            curr_recs, confs = MDEngine.parse_overframe_text(self.txt_new.toPlainText())
            curr_recs.update(hist_recs)
            
            name_map = MDEngine.get_id_to_name_map(clean_path(self.config.get("t13_csv_dir")), self.config.get("search_lang", "zh-tw"))
            final_text = MDEngine.format_overframe_records(curr_recs, name_map)
            
            self.txt_new.setPlainText(final_text)
            self.config.signals.sync_extraction_list.emit(self.txt_new.toPlainText())
            QMessageBox.information(self, _("成功"), _("已成功載入歷史紀錄並自動補齊卡片名稱！"))
        except Exception as e:
            QMessageBox.critical(self, _("錯誤"), _("讀取歷史紀錄失敗：{error}").format(error=e))

    def norm_txt(self):
        c = self.config
        name_map = MDEngine.get_id_to_name_map(clean_path(c.get("t13_csv_dir")), c.get("search_lang", "zh-tw"))
        curr_recs, confs = MDEngine.parse_overframe_text(self.txt_new.toPlainText())
        
        if confs:
            QMessageBox.warning(self, _("警告"), _("部分內容格式異常，正規化將跳過這些無效行：\n") + "\n".join(confs))
            
        if not curr_recs: return
        
        formatted_text = MDEngine.format_overframe_records(curr_recs, name_map)
        self.txt_new.setPlainText(formatted_text)
        self.config.signals.sync_extraction_list.emit(formatted_text)

    def save_existing_only(self):
        c = self.config
        src_dir, out_root = clean_path(c.get("t13_src_dir")), clean_path(c.get("t13_out_dir"))
        if not os.path.isdir(src_dir) or not os.path.isdir(out_root):
            return QMessageBox.critical(self, _("錯誤"), _("來源或輸出目錄設定無效！"))
            
        rec_curr, conf_curr = MDEngine.parse_overframe_text(self.txt_existing.toPlainText())
        if conf_curr:
            return QMessageBox.critical(self, _("語法錯誤"), _("文字框中存在格式錯誤，請檢查：\n") + "\n".join(conf_curr))
            
        out_folder = c.get("s_folder_out", "改完的文件")
        backup_folder = c.get("s_folder_backup", "文件備份")
        target_hash = c.get("t13_gate_hash", "22817d01")
        
        # 💡 將原本容易出錯的 lambda 替換為標準、安全的回呼函式
        def finish_handler(ct, hash_name):
            self._render_gate(os.path.join(out_root, out_folder, hash_name))
            return _("獨立儲存成功！共保留 {count} 筆。\n已將 `{hash}` 存放在：\n{folder}").format(count=ct, hash=hash_name, folder=out_folder)
            
        # 🛡️ 傳遞 None 防止鎖死錯誤的按鈕
        self.app.execute_task(None, _("獨立儲存白名單中"), MDEngine.task_locate_and_write_overframe, 
            (src_dir, out_root, out_folder, backup_folder, rec_curr, {}, target_hash), finish_handler)

    def merge_gate(self):
        c = self.config
        merge_path = clean_path(c.get("t13_merge_gate_path"))
        if not os.path.isfile(merge_path):
            return QMessageBox.warning(self, _("錯誤"), _("請先在上方設定中選擇有效的「欲合併用註冊表」路徑！"))

        ext_records = MDEngine.read_overframe_bytes(merge_path)
        if not ext_records:
            return QMessageBox.warning(self, _("錯誤"), _("無法解析該檔案，請確認是否為正常的 of_card_asset 資源！"))

        curr_records, conflicts = MDEngine.parse_overframe_text(self.txt_existing.toPlainText())
        if conflicts:
            return QMessageBox.warning(self, _("內部衝突"), _("文字方塊中已經存在邏輯衝突，請先修復：\n") + "\n".join(conflicts))

        merge_conf = []
        for t, b in ext_records.items():
            if t in curr_records and curr_records[t] != b:
                conf_msg = _("❌ 衝突項目 ID：[{t}]\n   - 現有清單指向：[{curr}]\n   - 欲合併檔案指向：[{new_b}]").format(t=t, curr=curr_records[t], new_b=b)
                merge_conf.append(conf_msg)
            curr_records[t] = b

        if merge_conf:
            return QMessageBox.critical(self, _("合併失敗"), _("🚨 偵測到「同項目指向不同目標」的衝突，為保護檔案已中斷合併：\n\n") + "\n\n".join(merge_conf))

        self.txt_existing.setPlainText(self._get_rendered_gate_text(curr_records))
        QMessageBox.information(self, _("合併成功"), _("外部設定已合併至上方的編輯框中！請點擊「儲存現有白名單」來完成寫入。"))

    def goto_tab2(self):
        self.config.signals.sync_extraction_list.emit(self.txt_new.toPlainText())
        self.config.signals.toggle_overframe_return.emit(True)
        self.app.select_tab("t2_find")

    def run_task(self):
        c = self.config
        src_dir, out_root = clean_path(c.get("t13_src_dir")), clean_path(c.get("t13_out_dir"))
        if not os.path.isdir(src_dir) or not os.path.isdir(out_root):
            return QMessageBox.critical(self, _("錯誤"), _("來源或輸出目錄設定無效！"))
            
        rec_curr, conf_curr = MDEngine.parse_overframe_text(self.txt_existing.toPlainText())
        rec_new, conf_new = MDEngine.parse_overframe_text(self.txt_new.toPlainText())
        if conf_curr + conf_new:
            return QMessageBox.critical(self, _("語法錯誤"), _("輸入框中存在格式錯誤，請檢查。"))
            
        out_folder = c.get("s_folder_out", "改完的文件")
        backup_folder = c.get("s_folder_backup", "文件備份")
        
        def finish_handler(ct, hash_name):
            self.txt_new.clear()
            self._render_gate(os.path.join(out_root, out_folder, hash_name))
            msg = _("✨ 輸出成功！共寫入 {count} 筆。\n已將 `{hash}` 存放在：\n{folder}").format(count=ct, hash=hash_name, folder=out_folder)
            
            if getattr(self, '_return_to_tab4', False):
                self._return_to_tab4 = False
                QTimer.singleShot(100, lambda: self.app.select_tab("t4_replace"))
            return msg

        target_hash = c.get("t13_gate_hash", "22817d01")
        self.app.execute_task(self.btn_run, _("註冊與輸出中"), MDEngine.task_locate_and_write_overframe, 
            (src_dir, out_root, out_folder, backup_folder, rec_curr, rec_new, target_hash), finish_handler)
        
    def clear_history(self):
        history_file = os.path.join(MDEngine.TEMP_DIR, "of_card_asset_backups", "registered_history.json")
        if not os.path.exists(history_file):
            return QMessageBox.information(self, _("提示"), _("目前沒有歷史紀錄需要清除！"))
            
        reply = QMessageBox.warning(
            self, _("危險操作警告"), 
            _("確定要徹底清除所有成功註冊的歷史紀錄嗎？\n此操作無法復原，清除後將失去過去的所有註冊足跡。"), 
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                os.remove(history_file)
                self.txt_new.clear()
                QMessageBox.information(self, _("成功"), _("歷史紀錄已成功清除！"))
            except Exception as e:
                QMessageBox.critical(self, _("錯誤"), _("清除失敗：{error}").format(error=e))

# ==================== 分頁 7: 設定與外觀 ====================
class TabSettings(BaseTab):
    def __init__(self, main_app):
        super().__init__(main_app)
        self.layout.addWidget(QLabel(_("【外觀與系統預設值保存】")))
        
        # 👈 頂部儲存大按鈕
        self.btn_save_top = QPushButton(_("寫入 JSON 設定檔 (儲存所有變更)")); self.btn_save_top.clicked.connect(self.save_all)
        self.layout.addWidget(self.btn_save_top)
        
        grp1 = QGroupBox(_("介面與全域行為"))
        form1 = QFormLayout(grp1)
        form1.addRow(self.bind_check("sync_paths", _("跨分頁路徑同步")), self.bind_check("auto_switch_tab", _("完成後自動切換分頁")))
        
        cb_lang = QComboBox()
        default_langs = ["zh-tw", "en-us"]
        
        # 智慧探測：自動掃描 Languages 資料夾，將已存在的自訂語言檔案自動加入下拉選項中
        lang_dir = os.path.join(os.getcwd(), "MD_Tool_Essential", "Languages")
        if os.path.isdir(lang_dir):
            try:
                for f in os.listdir(lang_dir):
                    if f.lower().endswith(".json"):
                        lang_name = os.path.splitext(f)[0].lower()
                        if lang_name not in default_langs:
                            default_langs.append(lang_name)
            except Exception:
                pass

        cb_lang.addItems(default_langs)
        cb_lang.setEditable(True)  # 👈 開放手動輸入，使用者可任意打字
        cb_lang.setCurrentText(self.config.get("ui_language"))
        
        # 連結文字變更，自動轉換為小寫並存入設定檔
        cb_lang.currentTextChanged.connect(lambda t: self.config.set("ui_language", t.strip().lower()))
        self.block_wheelEvent(cb_lang)

        btn_gen_raw = QPushButton(_("📝 匯出待翻譯樣板 (raw.json)"))
        btn_gen_raw.clicked.connect(self.generate_raw_lang)
        
        box_lang = QHBoxLayout()
        box_lang.addWidget(cb_lang)
        box_lang.addWidget(btn_gen_raw)

        cb_thread = QComboBox()
        cb_thread.setEditable(True)
        max_cores = os.cpu_count() or 2
        cb_thread.addItems(["Auto"] + [str(i) for i in range(1, max_cores + 1)])
        cb_thread.setCurrentText(str(self.config.get("max_threads", "Auto")))
        self.block_wheelEvent(cb_thread)
        
        warn_lbl = QLabel(_("⚠️ 警告：設定過高的執行緒可能導致記憶體耗盡甚至系統當機。"))
        warn_lbl.setStyleSheet("color: #D83C3C; font-weight: bold;")
        warn_lbl.setVisible(False)

        def on_thread_change():
            txt = cb_thread.currentText().strip()
            if txt.lower() == "auto": val = "Auto"
            elif txt.isdigit(): val = str(max(1, min(int(txt), max_cores))) # 防呆壓回上下限
            else: val = "Auto"
            cb_thread.setCurrentText(val)
            self.config.set("max_threads", val)
            warn_lbl.setVisible(val != "Auto" and int(val) > 16)

        cb_thread.lineEdit().editingFinished.connect(on_thread_change)
        cb_thread.currentIndexChanged.connect(lambda dummy_val: on_thread_change()) # 🌿 修正：將 _ 替換為 dummy_val，嚴格保護翻譯函數
        on_thread_change() # 觸發初始檢查
        
        form1.addRow(_("最大算力(執行緒):"), cb_thread)
        form1.addRow(warn_lbl)

        cb_font = QComboBox()
        fonts = [f for f in ["微軟正黑體", "Microsoft JhengHei", "Arial", "Consolas"] if f in QFontDatabase.families()]
        curr_font = self.config.get("font_family", "") or "Microsoft JhengHei"
        if curr_font not in fonts: fonts.insert(0, curr_font)
        cb_font.addItems(fonts)
        cb_font.setCurrentText(curr_font)
        cb_font.currentTextChanged.connect(lambda t: self.config.set("font_family", t))
        self.block_wheelEvent(cb_font)
        form1.addRow(_("語系 (重啟生效):"), box_lang); form1.addRow(_("指定字體:"), cb_font)
        
        # 🎨 超自由調色盤選色按鈕
        from PySide6.QtWidgets import QColorDialog
        def pick_color(key, default_hex, label_title):
            init_color = QColor(self.config.get(key, default_hex))
            color = QColorDialog.getColor(init_color, self, label_title, QColorDialog.ShowAlphaChannel)
            if color.isValid():
                self.config.set(key, color.name(QColor.HexArgb)) 
                self.app.apply_theme()
                
        btn_theme = QPushButton(_("🎨 更改強調色")); btn_theme.clicked.connect(lambda: pick_color("ui_theme_color", "#2CC985", _("選擇強調色")))
        btn_bg = QPushButton(_("🎨 更改背景色")); btn_bg.clicked.connect(lambda: pick_color("ui_bg_color", "#1C1C1C", _("選擇背景色")))
        btn_txt = QPushButton(_("🎨 更改文字色")); btn_txt.clicked.connect(lambda: pick_color("ui_text_color", "#EBEBEC", _("選擇文字顏色")))
        btn_wbg = QPushButton(_("🎨 更改側邊欄背景色")); btn_wbg.clicked.connect(lambda: pick_color("ui_widget_bg_color", "#2B2B2B", _("選擇側邊欄背景色")))
        btn_bor = QPushButton(_("🎨 更改邊框色")); btn_bor.clicked.connect(lambda: pick_color("ui_border_color", "#444444", _("選擇邊框與分界線顏色")))
        
        box_colors = QGridLayout()
        box_colors.addWidget(btn_theme, 0, 0); box_colors.addWidget(btn_bg, 0, 1)
        box_colors.addWidget(btn_txt, 1, 0); box_colors.addWidget(btn_mod := btn_wbg, 1, 1)
        box_colors.addWidget(btn_bor, 2, 0)
        form1.addRow(_("自訂五維度調色盤:"), box_colors)
        self.layout.addWidget(grp1)
        
        grp_names = QGroupBox(_("全域專案資料夾命名設定"))
        form_n = QFormLayout(grp_names)
        self.n_raw = QLineEdit(); self.bind_text("s_folder_raw", self.n_raw); form_n.addRow(_("原檔:"), self.n_raw)
        self.n_img = QLineEdit(); self.bind_text("s_folder_img", self.n_img); form_n.addRow(_("原卡圖:"), self.n_img)
        self.n_bk = QLineEdit(); self.bind_text("s_folder_backup", self.n_bk); form_n.addRow(_("文件備份:"), self.n_bk)
        self.n_mod = QLineEdit(); self.bind_text("s_folder_mod", self.n_mod); form_n.addRow(_("卡圖改:"), self.n_mod)
        self.n_out = QLineEdit(); self.bind_text("s_folder_out", self.n_out); form_n.addRow(_("改完的文件:"), self.n_out)
        self.n_csv = QLineEdit(); self.bind_text("s_csv_mapping", self.n_csv); form_n.addRow(_("對照表 CSV:"), self.n_csv)
        self.layout.addWidget(grp_names)

        grp_tab = QGroupBox(_("側邊欄分頁排序與命名 (拖曳或按鈕調整排序)"))
        v_tab = QVBoxLayout(grp_tab)
        self.list_tab = QListWidget(); self.list_tab.setDragDropMode(QAbstractItemView.InternalMove)
        self.list_tab.setMinimumHeight(220) # 👈 加高至 220px 寬大視野
        self.prevent_scroll_propagation(self.list_tab) # 👈 阻擋滾輪穿透背景
        
        self.tab_ids = self.config.get("tab_order", [])
        names = self.config.get("tab_names", {})
        for tid in self.tab_ids:
            custom_name = names.get(tid)
            default_name = next((t["name"] for t in DEFAULT_TABS if t["id"] == tid), tid)
            
            # 🛡️ 同步修復：設定頁面中的清單也要套用同樣的翻譯判定邏輯
            if custom_name == default_name or not custom_name:
                display_name = _(default_name)
            else:
                display_name = custom_name
            
            item = QListWidgetItem(display_name)
            item.setData(Qt.UserRole, tid) 
            self.list_tab.addItem(item)
            
        box_t = QHBoxLayout()
        btn_up = QPushButton("▲"); btn_up.clicked.connect(lambda: UIHelper.move_list_items(self.list_tab, -1))
        btn_dn = QPushButton("▼"); btn_dn.clicked.connect(lambda: UIHelper.move_list_items(self.list_tab, 1))
        self.edit_ren = QLineEdit()
        btn_ren = QPushButton(_("重命名")); btn_ren.clicked.connect(self.rename_tab)
        self.list_tab.itemClicked.connect(lambda i: self.edit_ren.setText(i.text()))
        box_t.addWidget(btn_up); box_t.addWidget(btn_dn); box_t.addWidget(self.edit_ren); box_t.addWidget(btn_ren)
        v_tab.addWidget(self.list_tab); v_tab.addLayout(box_t)
        self.layout.addWidget(grp_tab)
        
        grp2 = QGroupBox(_("自訂背景與透明度"))
        form2 = QFormLayout(grp2)
        edit_bg = self.make_path_row(form2, _("背景圖片"), "bg_image", True, "IMG")
        edit_bg.textChanged.connect(lambda *args: self.config.signals.bg_changed.emit()) # 👈 防止 lambda 引數崩潰
        
        # 👈 透明度下限改為 0
        sl_op = QSlider(Qt.Horizontal); sl_op.setRange(0, 100); sl_op.setValue(int(self.config.get("bg_opacity", 1.0)*100))
        sl_op.valueChanged.connect(lambda v: [self.config.set("bg_opacity", v/100.0), self.app.apply_opacity()])
        sl_br = QSlider(Qt.Horizontal); sl_br.setRange(10, 200); sl_br.setValue(int(self.config.get("bg_brightness", 0.5)*100))
        sl_br.valueChanged.connect(lambda v: [self.config.set("bg_brightness", v/100.0), self.config.signals.bg_changed.emit()])
        form2.addRow(_("透明度:"), sl_op); form2.addRow(_("亮度:"), sl_br)
        self.block_slider_wheel(sl_op) # 👈 阻擋滑桿滾輪誤觸
        self.block_slider_wheel(sl_br) # 👈 阻擋滑桿滾輪誤觸
        
        self.link_picker = LinkAnchorPicker(self.config.get("bg_anchor", "center"))
        self.link_picker.anchorChanged.connect(lambda a: [self.config.set("bg_anchor", a), self.config.signals.bg_changed.emit()])
        form2.addRow(_("九宮格錨點:"), self.link_picker)
        self.layout.addWidget(grp2)
        
        # 👈 底部儲存大按鈕
        self.btn_save_bottom = QPushButton(_("寫入 JSON 設定檔 (儲存所有變更)"))
        self.btn_save_bottom.clicked.connect(self.save_all)
        self.layout.addWidget(self.btn_save_bottom)

    def rename_tab(self):
        row = self.list_tab.currentRow()
        if row != -1 and self.edit_ren.text().strip():
            self.list_tab.item(row).setText(self.edit_ren.text().strip())

    def save_all(self):
        names = {}
        new_tab_ids = []
        for i in range(self.list_tab.count()): 
            item = self.list_tab.item(i)
            tid = item.data(Qt.UserRole)
            new_tab_ids.append(tid)
            
            # 只有當使用者修改的名稱「不等於」當前翻譯的預設名稱時，才存入 JSON
            default_name = next((t["name"] for t in DEFAULT_TABS if t["id"] == tid), tid)
            if item.text() != _(default_name):
                names[tid] = item.text()
                
        self.config.set("tab_order", new_tab_ids)
        self.config.set("tab_names", names)
        self.config.save()
        QMessageBox.information(self, _("完成"), _("設定已成功保存至硬碟。切換語系或分頁名稱需重啟生效。"))

    def generate_raw_lang(self):
        # 自動取得當前執行的腳本名稱
        source_file = sys.argv[0]
        # 若為打包後的 EXE 執行環境，嘗試指向預設的腳本名稱
        if not source_file.endswith('.py'):
            source_file = os.path.join(os.getcwd(), "MD_tool_full_NEW.py")
            
        out_dir = os.path.join(os.getcwd(), "MD_Tool_Essential", "Languages")
        
        # 移除原本在 UI 層的硬性阻擋，全權交由 MDEngine 大腦判定是否啟用方案 B 備用機制
        success, msg = MDEngine.task_generate_translation_template(source_file, out_dir)
        
        if success:
            QMessageBox.information(self, _("成功"), msg)
        else:
            QMessageBox.critical(self, _("錯誤"), _("匯出失敗：\n{error}").format(error=msg))

# =========================================================================
# ==================== 第五區：主視窗骨架 (背景管理與任務調度) ===============
# =========================================================================
class MDToolBoxApp(QMainWindow):
    def __init__(self, config_manager):
        super().__init__()
        self.config_mgr = config_manager
        self.thread_pool = QThreadPool()
        
        self.setWindowTitle(_("MD 阿斯特婭工具箱"))
        self.resize(1100, 820); self.setMinimumSize(900, 700)
        
        self.bg_label = QLabel(self); self.bg_label.lower()
        self.resize_timer = QTimer(self); self.resize_timer.setSingleShot(True); self.resize_timer.timeout.connect(self.update_bg_logic)
        self.config_mgr.signals.bg_changed.connect(lambda: self.resize_timer.start(50))
        
        self.init_ui()

    def apply_theme(self):
        theme_color = self.config_mgr.get("ui_theme_color", "#2CC985")
        bg_color = self.config_mgr.get("ui_bg_color", "#1C1C1C")
        text_color = self.config_mgr.get("ui_text_color", "#EBEBEC")
        widget_bg_color = self.config_mgr.get("ui_widget_bg_color", "#2B2B2B")
        border_color = self.config_mgr.get("ui_border_color", "#444444")
        
        # 動態將樣式表中的色碼全數替換
        new_qss = DARK_QSS.replace("#2CC985", theme_color)\
                          .replace("#1C1C1C", bg_color)\
                          .replace("#EBEBEC", text_color)\
                          .replace("#2B2B2B", widget_bg_color)\
                          .replace("#444", border_color)\
                          .replace("#555", border_color)
                          
        self.setStyleSheet(new_qss)
        QTimer.singleShot(50, self.apply_opacity)

    def init_ui(self):
        cen = QWidget(); self.setCentralWidget(cen)
        mlay = QHBoxLayout(cen); mlay.setContentsMargins(0,0,0,0); mlay.setSpacing(0)
        
        self.sidebar_frame = QWidget(); self.sidebar_frame.setFixedWidth(220)
        vlay = QVBoxLayout(self.sidebar_frame); vlay.setContentsMargins(0,20,0,20)
        vlay.setSpacing(0)
        lbl = QLabel(_("頁面目錄"))
        ff = self.config_mgr.get("font_family", "") or "Microsoft JhengHei"
        lbl.setFont(QFont(ff, 18, QFont.Bold))
        lbl.setContentsMargins(15, 0, 15, 10)
        vlay.addWidget(lbl)
        
        self.tab_btns = {}
        for tid in self.config_mgr.get("tab_order", []):
            custom_name = self.config_mgr.get("tab_names", {}).get(tid)
            default_name = next((t["name"] for t in DEFAULT_TABS if t["id"] == tid), tid)
            
            # 🛡️ 修復 1：判斷如果所謂的「自訂名稱」跟「預設中文名」一模一樣，代表玩家根本沒改名，此時強制套用翻譯！
            if custom_name == default_name or not custom_name:
                display_name = _(default_name)
            else:
                display_name = custom_name
                
            # 🛡️ 修復 2 (你的隱性BUG)：啟用智慧換行，大約每 22 個字元自動換行，防止英文過長撐破側邊欄
            wrapped_name = textwrap.fill(display_name, width=22)
            
            btn = QPushButton(wrapped_name)
            btn.setStyleSheet("text-align: left; padding: 15px 20px; border: none; background: transparent; margin: 0px;") 
            btn.clicked.connect(lambda checked=False, t=tid: self.select_tab(t))
            self.tab_btns[tid] = btn
            vlay.addWidget(btn)
        vlay.addStretch()

        right_widget = QWidget(); rlay = QVBoxLayout(right_widget); rlay.setContentsMargins(20,20,20,20)
        self.content_frame = QWidget(); self.content_frame.setStyleSheet("background-color: #1C1C1C; border-radius: 10px;")
        clay = QVBoxLayout(self.content_frame)
        self.stacked = QStackedWidget(); clay.addWidget(self.stacked)
        
        self.status_frame = QWidget(); self.status_frame.setFixedHeight(45); self.status_frame.setStyleSheet("background-color: #2B2B2B; border-radius: 10px;")
        slay = QHBoxLayout(self.status_frame)
        self.status_lbl = QLabel(_("狀態：等待指令...")); self.pbar = QProgressBar(); self.pbar.setRange(0,0); self.pbar.setFixedWidth(200); self.pbar.hide()
        slay.addWidget(self.status_lbl); slay.addWidget(self.pbar)
        
        rlay.addWidget(self.content_frame); rlay.addWidget(self.status_frame)
        mlay.addWidget(self.sidebar_frame); mlay.addWidget(right_widget)
        
        self.apply_theme()
        
        self.tabs = {
            "t0_guide": TabGuide(self),
            "t1_scan": TabScan(self), "t2_find": TabFind(self),
            "t3_extract": TabExtract(self), "t4_replace": TabReplace(self),
            "t5_package": TabPackage(self), "t8_pendulum": TabPendulum(self),
            "t9_quick_mod": TabQuickMod(self), 
            "t13_overframe": TabOverFrame(self),
            "t12_gallery": TabGallery(self),
            "t10_updater": TabUpdater(self),
            "t11_virtual": TabVirtualMount(self), "t6_chain": TabChain(self),
            "t7_settings": TabSettings(self)
        }
        # 使用字典精準記錄每一個外層 QScrollArea 容器
        self.tab_wrappers = {}
        for tid, t in self.tabs.items():
            if tid == "t12_gallery":
                # 🛡️ 畫廊分頁本身內建高動態網格捲軸，直接放入 stacked 容器，絕不包裹外層 QScrollArea！
                # 這能讓 QListWidget 的可視區域受到硬性邊界限制，完美啟用 Qt 內建的 UI 虛擬化，效能大幅躍升！
                self.stacked.addWidget(t)
                self.tab_wrappers[tid] = t
            else:
                s = QScrollArea()
                s.setWidgetResizable(True)
                s.setWidget(t)
                self.stacked.addWidget(s)
                self.tab_wrappers[tid] = s
            
        if self.config_mgr.get("tab_order"): self.select_tab(self.config_mgr.get("tab_order")[0])
        self.update_bg_logic()
        self.config_mgr.signals.request_filter_view.connect(self.handle_request_filter_view)
        self.config_mgr.signals.sync_filter_result.connect(self.handle_sync_filter_result)

    # 👇 在 init_ui 下方，新增這兩個調度函數
    def handle_request_filter_view(self, id_list):
        self.select_tab("t12_gallery")
        self.tabs["t12_gallery"].set_filter_mode(id_list)

    def handle_sync_filter_result(self, id_list):
        self.select_tab("t2_find")
        tab2 = self.tabs["t2_find"]
        # 直接完美覆寫回第二頁
        tab2.t2_text.setPlainText("\n".join(id_list))
        # 觸發一次正規化補名，讓它整齊漂亮！
        tab2.norm_txt()

    def select_tab(self, tid):
        if tid not in self.tabs: return
        for k, b in self.tab_btns.items(): 
            b.setStyleSheet(f"text-align: left; padding: 15px 20px; margin: 0px; border: none; background: {'#3B8E8E' if k==tid else 'transparent'};")
        # 精準指向記錄好的 QScrollArea 實體，徹底解決 QStackedWidget 遺失錯誤
        self.stacked.setCurrentWidget(self.tab_wrappers[tid])

    def resizeEvent(self, event): super().resizeEvent(event); self.resize_timer.start(200)

    def update_bg_logic(self):
        path = clean_path(self.config_mgr.get("bg_image", ""))
        if not os.path.exists(path): return self.bg_label.hide()

        if getattr(self, "_cached_bg_path", "") != path or not getattr(self, "_cached_bg_img", None):
            self._cached_bg_path = path
            self._cached_bg_img = QImage(path)
        
        img = self._cached_bg_img; w, h = self.width(), self.height()
        if w <= 0 or h <= 0: return
        scaled = img.scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        b_val = float(self.config_mgr.get("bg_brightness", 0.5))
        
        tmp = QPixmap(scaled.size()); tmp.fill(Qt.transparent)
        p = QPainter(tmp); p.drawImage(0,0,scaled)
        p.setCompositionMode(QPainter.CompositionMode_SourceAtop)
        if b_val < 1.0: p.fillRect(tmp.rect(), QColor(0,0,0, int(255*(1-b_val))))
        else: p.fillRect(tmp.rect(), QColor(255,255,255, int(255*(b_val-1)/2)))
        p.end()
        
        self.bg_label.setPixmap(tmp)
        self.bg_label.setGeometry(0, 0, w, h)
        
        align_map = {
            "nw": Qt.AlignTop | Qt.AlignLeft, "n": Qt.AlignTop | Qt.AlignHCenter, "ne": Qt.AlignTop | Qt.AlignRight,
            "w": Qt.AlignVCenter | Qt.AlignLeft, "center": Qt.AlignCenter, "e": Qt.AlignVCenter | Qt.AlignRight,
            "sw": Qt.AlignBottom | Qt.AlignLeft, "s": Qt.AlignBottom | Qt.AlignHCenter, "se": Qt.AlignBottom | Qt.AlignRight
        }
        self.bg_label.setAlignment(align_map.get(self.config_mgr.get("bg_anchor", "center"), Qt.AlignCenter))
        self.bg_label.show(); self.bg_label.lower()

    def apply_opacity(self):
        v = float(self.config_mgr.get("bg_opacity", 1.0))
        
        # 🛡️ 智慧動態轉換：將使用者在調色盤選定的色碼轉為 RGBA 渲染
        bg_hex = self.config_mgr.get("ui_bg_color", "#1C1C1C")
        widget_hex = self.config_mgr.get("ui_widget_bg_color", "#2B2B2B")
        
        def hex_to_rgba_str(h, opacity_multiplier, default_rgb_str):
            color = QColor(h)
            if color.isValid():
                # 完美保留調色盤的 Alpha 通道，並與底層的透明度滑桿 (opacity_multiplier) 相乘融合
                final_alpha = (color.alpha() / 255.0) * opacity_multiplier
                return f"rgba({color.red()}, {color.green()}, {color.blue()}, {final_alpha})"
            return f"rgba({default_rgb_str}, {opacity_multiplier})"
            
        bg_rgba = hex_to_rgba_str(bg_hex, v, "28, 28, 28")
        widget_rgba = hex_to_rgba_str(widget_hex, v, "43, 43, 43")
        
        # 套用動態變更，主畫面的底色與按鈕周圍的邊框底板現在會隨著你的調色盤同步變色了！
        self.sidebar_frame.setStyleSheet(f"background-color: {widget_rgba};") 
        self.content_frame.setStyleSheet(f"background-color: {bg_rgba}; border-radius: 10px;")
        self.status_frame.setStyleSheet(f"background-color: {widget_rgba}; border-radius: 10px;")

    def execute_task(self, btn, msg, func, args, succ_msg_cb, is_chain=False, next_tab_id=None):
        # 🛡️ 智慧判定：允許傳入單一按鈕或按鈕清單 (Tuples/List)
        btns = btn if isinstance(btn, (list, tuple)) else ([btn] if btn else [])
        for b in btns:
            if b: b.setEnabled(False)
            
        self.status_lbl.setText(_("{message}... (準備啟動)").format(message=msg))
        self.pbar.setRange(0, 0) # 維持 0,0 走馬燈模式，確保沒有明確總量時也不會視覺凍結
        self.pbar.show()
        
        worker = TaskWorker(func, args)
        self._active_workers = getattr(self, '_active_workers', set())
        self._active_workers.add(worker)
        
        # 🛡️ 解耦設計：底層只傳遞純數字(count)，由 UI 負責多語言字串的合成與替換
        def update_progress(count):
            self.status_lbl.setText(_("{message}... (進度: {count})").format(message=msg, count=count))
            
        worker.signals.progress.connect(update_progress)
        
        def finish(s, c, e):
            self._active_workers.discard(worker)
            self.pbar.hide()
            for b in btns:
                if b: b.setEnabled(True)
                
            self.status_lbl.setText(_("狀態：任務完成！") if s else _("狀態：發生錯誤已停止。"))
            if is_chain:
                if callable(succ_msg_cb): succ_msg_cb(s, c, e)
            else:
                if s: 
                    msg_text = succ_msg_cb(c, e) if callable(succ_msg_cb) else ""
                    if msg_text: QMessageBox.information(self, _("完成"), msg_text)
                    if next_tab_id and self.config_mgr.get("auto_switch_tab"):
                        self.select_tab(next_tab_id)
                else: 
                    QMessageBox.critical(self, _("錯誤"), str(c))
                    
        worker.signals.finished.connect(finish)
        self.thread_pool.start(worker)
        

if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = QApplication(sys.argv)
    cfg = ConfigManager()
    win = MDToolBoxApp(cfg)
    win.show()
    sys.exit(app.exec())