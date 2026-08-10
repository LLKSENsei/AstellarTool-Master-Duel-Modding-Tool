[繁體中文](TUTORIAL.md) | [English](TUTORIAL_en.md)

***

# MD AstellarTool Engineering Operation & In-Depth Technical Manual

This manual serves as the comprehensive engineering specification and technical operating guide for *MD AstellarTool*. Free of exaggerated language or unnecessary emotional expressions, this document aims to precisely, deeply, and rigorously disclose the tool's underlying operating mechanisms, image processing algorithms, memory management strategies, binary data streams, and security architecture.

Through this document, users will understand the physical meaning of every input parameter, system-level behaviors triggered by all buttons and switches, step-by-step SOPs for independent tabs, and cross-module real-world case combinations.

---

## Chapter 1: System Paths and Resource Naming Specifications

The automated batch engine of this tool relies heavily on accurate path mounting and Regular Expression extraction. Ensure full compliance with the following specifications before operation.

### 1.1 Core Physical Path Definitions
* **Game 0000 Directory (`0000 Directory`)**
  The root directory storing base game cards and primary binary AssetBundle assets.
  Default path format: `[Drive]:\SteamLibrary\steamapps\common\Yu-Gi-Oh! Master Duel\LocalData\[8-digit Player ID]\0000\`
* **Game StreamingAssets Directory (`StreamingAssets Directory`)**
  The directory storing high-resolution visual assets or large data packages.
  Default path format: `[Drive]:\SteamLibrary\steamapps\common\Yu-Gi-Oh! Master Duel\masterduel_Data\StreamingAssets\AssetBundle\`
* **Game Lobby Background Data File (`Lobby Background Data`)**
  A single binary asset package file storing interface resources, including the lobby background texture `ShopBGBase02`.
  Default path format: `[Drive]:\SteamLibrary\steamapps\common\Yu-Gi-Oh! Master Duel\masterduel_Data\data.unity3d`

### 1.2 Resource Naming & Normalization Parsing Mechanism
When performing binary packaging or database lookups, the tool strips user-defined affix tags using Python's `re` module.

* **Card Image Naming Specification**
  * **Rule**: `[Card ID]_[Any Custom Tag].[extension]` or `[Card ID].[extension]`
  * **Underlying Mechanism**: Extracted using the regex pattern `^([a-zA-Z]*)(\d+)(.*)$`. Any standard English prefix characters are ignored; the system locks onto the "contiguous numeric block" as the Card ID and strips all subsequent characters (including underscores, spaces, etc.) as invalid suffixes.
  * **Correct Examples**: `20570.png`, `20570_Cartesia.png`, `Alt17069_Custom.jpg`.
  * **Incorrect Example**: `Cartesia_20570.png` (The parser cannot capture numbers at the start of the string, causing match failure).
* **Non-Card Visual Assets (UI / Field / Sleeves)**
  * **Rule**: Must strictly match the lookup table names extracted from the game (case-insensitive).
  * **Underlying Mechanism**: Uses `unicodedata.normalize('NFKC', text).lower()` for bidirectional normalization matching, eliminating full-width/half-width and case differences.
  * **Examples**: `Mat_001_BaseColor.png`, `ProfileIcon1020001.png`.

---

## Chapter 2: Comprehensive UI Tab Functional Analysis & Single-Tab Operation SOPs

This chapter breaks down all interface components, input fields, switches, buttons, and operational SOPs following the default layout sequence of the software interface.

---

### 1. Settings & Appearance (Tab 7, `t7_settings`) [Primary Configuration Page]

<img width="1095" height="847" alt="Settings" src="https://github.com/user-attachments/assets/c87beb83-5276-48bf-b9c5-3f5c7a3ef661" />

#### Technical Mechanism & Operating Principles
This module serves as the global configuration hub, responsible for reading/writing JSON configuration files, emitting cross-tab path synchronization signals (`Signal`), and dynamically rendering QSS stylesheets.
* **Atomic Write Anti-Pollution Mechanism (`_atomic_write_json`)**: Upon saving settings, the system locks the thread using `RLock`, strips massive memory caches (such as `t2_extraction_list`), writes a clean dictionary to a `.tmp` file, and performs a physical atomic swap using `os.replace`. This guarantees that even if a power failure occurs during writing, configuration files will not corrupt into 0KB files.
* **AST (Abstract Syntax Tree) Source Code Parser (`task_generate_translation_template`)**: Upon execution, calls Python's `ast` module to traverse main program source code, capturing all strings wrapped in `_("...")` and UI `placeholder` attributes. It generates the `MD_Tool_Essential/Languages/raw.json` localization template and fills missing entries in `zh-tw.json` without data loss.

#### Full UI Elements & Input Fields Detail
* **Cross-Tab Path Synchronization (Checkbox)**: When enabled, modifying the "Project Root", "0000 Source", or "CSV Dictionary" paths on any tab broadcasts updates across matching input fields on all tabs via `ConfigSignals`.
* **Auto-Switch Tab Upon Completion (Checkbox)**: When enabled, completing a single task automatically redirects the interface to the next processing tab.
* **Language (Restart Required) (ComboBox)**: Configures interface language (`zh-tw` and `en-us` default). Entering custom language codes (such as `ja-jp`) attempts to load `Languages/[code].json`.
* **Max Compute Power (Threads) (ComboBox)**: Sets CPU core limits for the multi-process pool (`ProcessPoolExecutor`). Accepts numeric inputs or `Auto`. `Auto` reserves 1 to 4 cores for the OS to prevent UI freeze caused by 100% CPU utilization.
* **Custom Font (ComboBox)**: Selects interface display font.
* **Custom 5-Dimension Palette (Buttons)**: Provides 5 color blocks: "Accent Color", "Background Color", "Text Color", "Sidebar BG Color", and "Border Color". Clicking opens `QColorDialog` with Alpha channel support, dynamically rebuilding and applying QSS stylesheets across the window.
* **Global Project Directory Naming (LineEdits)**: Defines default names for directories such as "Raw Files", "Raw Card Images", "File Backup", "Modified Card Images", "Modified Files", and "Mapping CSV".
* **Sidebar Tab Reordering & Renaming (ListWidget & LineEdit)**: Lists all tabs. Reorder items using the [▲] and [▼] buttons, or enter a new label and click [Rename].
* **Background Image (Path Row)**: Specifies a local image file as the GUI background.
* **Opacity (Slider)**: Adjusts GUI transparency (0 to 100%).
* **Brightness (Slider)**: Adjusts background image brightness (10 to 200%).
* **Nine-Grid Anchor Picker (LinkAnchorPicker)**: Selects a anchor point for background positioning during window resizing.

#### Button Functions
* **[Write to JSON Configuration File (Save All Changes)]** (Top and Bottom): Saves active settings to `md_tool_config.json`.
* **[Export Template to be Translated (raw.json)]**: Runs AST syntax parsing to generate language template files.

#### Single-Tab Operation SOP & Path Preservation Standard
1. In "Global Project Directory Naming", verify that folder labels conform to your workflow.
2. **Important Path Preservation Standard**: Clicking [Write to JSON Configuration File] logs all active fields on the interface. To prevent writing temporary project paths to the global config, clear temporary subdirectories in other tabs prior to saving, retaining only "0000 Game Directory", "Main CSV Mapping Path", and "Default Directory Names".
3. Click **[Write to JSON Configuration File (Save All Changes)]**. Upon subsequent launches, temporary fields remain blank for direct insertion of new project paths.

---

### 2. Getting Started & User Journey (Tab 0, `t0_guide`)

#### Technical Mechanism & Operating Principles
A static information display tab utilizing read-only `QPlainTextEdit` to render system instructions and disclaimers without consuming CPU/GPU rendering resources.

#### Interface Elements & Operations
* Houses complete feature guides where users can review standard project workflows, quick automation pipelines, and functional descriptions for each tab.

---

### 3. Scan & Expand (Tab 1, `t1_scan`)

<img width="1093" height="844" alt="Scan" src="https://github.com/user-attachments/assets/9b6cfa84-eaf0-4183-8976-28b62c36321a" />

#### Technical Mechanism & Operating Principles
Traverses binary files under the `0000` directory to construct a relational CSV dictionary containing Card IDs, real names, effect text, and Hash encodings.
* **XOR Dynamic Decryption Engine**: Game card text databases are encrypted. The system defaults to XOR bitwise inversion using `0x3D (61)`. If an official update causes decryption to fail, the engine triggers the `auto_crack_key` function, iterating across the range `0` to `1023` to decompress and validate zlib package structures, capturing and writing new keys back to the configuration file upon success.
* **6-Bit Physical Mask Classification**: Reads `card_prop.bytes` binary offsets directly for attribute identification. Bit values of `0x020D` indicate Spell Cards; Monster Cards extract the first 6 bits (6-bit mask) for physical feature code matching (e.g., `0x19` and `0x24` map to Pendulum), supplemented by NLP effect text keyword scanning for precise card classification.
* **IL2CPP Metadata Collision**: For non-card assets without IDs (e.g., avatars, fields), reads `global-metadata.dat` to extract ID strings, computes CRC32 hashes, and executes bidirectional collision matching against `ids_item.bytes` to restore asset names.
* **Memory Anti-Crash Monitoring**: Calls the Windows `GlobalMemoryStatusEx` API during multi-process scanning. When physical RAM load hits the 85% threshold, forces execution sleep and GC collection to prevent system crashes.

#### Full UI Elements & 10 Toggle Switches Detail
* **Target Folder (0000)**: Specifies the path to the game's `0000` folder.
* **Save Root Directory**: Output location for project files; all subsequent operations reference this path.
* **TXT / CSV Naming (LineEdits)**: Configures file names for exported list and dictionary files.
* **1. Enable Size Filter (Checkbox, `t1_size_filter`)**:
  * **ON**: Restricts scanning strictly to Bundle files within "Min (KB)" and "Max (KB)" limits, filtering out unrelated micro-files and giant archives.
  * **OFF**: Scans all Bundle files in target directory unconditionally.
* **2. Search Cards Only (Checkbox, `t1_only_numbers`)**:
  * **ON**: Extracts numeric Card ID assets only; ignores non-numeric accessory assets like fields and sleeves.
  * **OFF**: Extracts numeric card assets and non-numeric accessory assets simultaneously.
* **3. Generate Content List (TXT) (Checkbox, `t1_gen_txt`)**:
  * **ON**: Automatically exports a TXT list containing all extracted IDs.
  * **OFF**: Skips TXT list generation.
* **4. Generate Mapping Table (CSV) (Checkbox, `t1_gen_csv`)**:
  * **ON**: Automatically exports a primary CSV dictionary containing directory, Container, Hash, and ID mappings.
  * **OFF**: Skips CSV export (used when reverse-exporting TXT lists from modified directories).
* **5. Include Card Names (Checkbox, `t1_ext_name`)**:
  * **ON**: Writes card names in the selected language to the CSV.
  * **OFF**: Omits card names from CSV output.
* **6. Include Card Descriptions (Checkbox, `t1_ext_desc`)**:
  * **ON**: Writes card effect text into CSV, enabling keyword searches later.
  * **OFF**: Omits effect text, reducing CSV size and speeding up load times.
* **7. Include Accessory Names (Checkbox, `t1_parse_meta`)**:
  * **ON**: Reads `global-metadata.dat` to restore accessory names (sleeves, icons, etc.).
  * **OFF**: Skips Metadata parsing; accessories display raw codes.
* **8. Prioritize Cache (Checkbox, `t1_use_cache`)**:
  * **ON**: Reads cached files in `MD_Tool_Temp/` from prior decryptions for sub-second scans.
  * **OFF**: Forces complete re-decryption of game Bundles. Must be turned OFF after major game updates to fetch new data.
* **9. Deep Scan (Checkbox, `t1_deep_scan`)**:
  * **ON**: Deeply unpacks inner objects within Bundles to extract field textures or lobby backgrounds inside huge asset packs.
  * **OFF**: Matches top-level Container paths only; extremely fast.
* **10. Process Fields/Sleeves/Icons Objects Only (Checkbox, `enable_visual_only_filter`)**:
  * **ON**: Filters out standard numeric cards, retaining only non-card accessory assets in results.
  * **OFF**: Scans all assets per standard rules.
* **Language (ComboBox) / XOR Key (LineEdit)**: Decryption language and key.
* **CSV to Expand (Path Row)**: Path to legacy CSV used by expansion features.

#### Button Functions
* **[Start Scanning]**: Launches multi-process scanning, producing TXT lists and CSV dictionaries.
* **[Execute Expansion / Supplement]**: Reads "CSV to Expand" and appends new language columns to the right side of the CSV.
* **[Stop Scanning / Abort Operation]**: Emits a `multiprocessing.Event()` signal to terminate child processes.

#### Single-Tab Operation SOPs
* **SOP 1.1: Complete Game 0000 Directory Scan**
  1. Fill in "Target Folder (0000)" and "Save Root Directory".
  2. Check "Generate Mapping Table (CSV)", "Include Card Names", and "Include Accessory Names".
  3. Click **[Start Scanning]**. Outputs `2DTexture_Mapping.csv` in root upon completion.
* **SOP 1.2: Expanding Legacy CSV with Multi-Language Mapping**
  1. Select a previously created CSV file in "CSV to Expand".
  2. Switch "Language" to target new language (e.g., `ja-jp`).
  3. Click **[Execute Expansion / Supplement]**. Automatically appends new language columns and saves.

---

### 4. Find Files (Tab 2, `t2_find`)

<img width="1096" height="842" alt="Find" src="https://github.com/user-attachments/assets/3f22366e-02d1-465c-a389-159fdeea75b0" />

#### Technical Mechanism & Operating Principles
Locates and copies binary Hash files from the `0000` directory based on the CSV dictionary.
* **Smooth Drag Scrolling (`LinearDragScrollFilter`)**: Injects an EventFilter converting mouse dragging to fractional step increments, triggering scroll movement per accumulated whole pixel to eliminate UI jitter.
* **Path Coupling & Spacebar Refresh Trick**: Modifying "Save Root Directory" or "New Folder Name" automatically updates paths and syncs to Tab 3 source inputs and TXT paths. If paths fail to update immediately, **click spacebar once inside the input box and delete it** to forcibly trigger the `textChanged` signal.

#### Full UI Elements & Input Fields Detail
* **Selection Mode (ComboBox)**:
  * `MODE_NORMAL` (Standard Extraction): Copies Hash files directly into the "Raw Files" directory.
  * `MODE_QUICK` (Quick Overframe Pipeline): Activates an automated overframe conversion pipeline. **Important constraint: Quick Overframe Pipeline mode applies ONLY to original game card images**. Custom images must use Tab 8.
* **Mapping Table (CSV) / Loading TXT / File Source (0000) / Save Root Directory (Path Rows)**: Configures read/write paths for all stages.
* **New Folder Name (LineEdit)**: Directory name storing copied binary files (default `RawFiles`).
* **Target Language (ComboBox) / Search Box (LineEdit)**: Searches card names, effect text, or IDs.
* **Process Fields/Sleeves/Icons Only (Checkbox)**: Filters search results to visual assets only.
* **Search Results List (ListWidget) / Extraction List (PlainTextEdit)**: Displays search results and final extraction IDs.

#### Button Functions
* **[Start Extracting Raw Files] / [Start Automatic Overframe Processing]** (Top and Bottom): Executes file copying or launches automated overframe pipeline.
* **[Load TXT]**: Imports IDs from an external text file into extraction list.
* **[Normalize Name]**: Queries CSV dictionary to reformat entries into `ID (Name) [Hash]` format.
* **[Search / Visual Filter]**: Launches Sandbox Mode, sending IDs to Tab 12 to generate thumbnail cache for manual filtering.
* **[Confirm IDs & Return to Overframe Register]**: (Contextual) Passes list IDs and returns to Tab 13.
* **List Right-Click Menu**: Highlight search results and right-click to add items directly to extraction list.

#### Single-Tab Operation SOPs
* **SOP 2.1: Standard Raw File Extraction**
  1. Set Selection Mode to "Standard Extraction".
  2. Search keywords, double-click results (or right-click) to add to Extraction List.
  3. Click **[Start Extracting Raw Files]**. Target binary files copy to `ProjectDir/RawFiles/`.
* **SOP 2.2: Automated Overframe Pipeline for Official Card Images**
  1. Set Selection Mode to "Quick Overframe Pipeline".
  2. Enter official Card IDs into Extraction List.
  3. Click **[Start Automatic Overframe Processing]**.
  4. **Internal Causal Chain**: Auto-extract raw files to `RawFiles/` -> Auto-unpack images to `RawCardImages/` and back up Bundles to `FileBackup/` -> Auto-copy images to `ModifiedCardImages/` -> Auto-crop 11:16 and synthesize PSD frame -> Auto-repack Bundle to `ModifiedFiles/` -> Auto-transfer Card IDs to Tab 13 Register and switch tab.

---

### 5. Extract Data (Tab 3, `t3_extract`)

<img width="1076" height="842" alt="Extract" src="https://github.com/user-attachments/assets/91e4e574-9103-4825-9c8a-2a18666cf79e" />

#### Technical Mechanism & Operating Principles
Uses UnityPy to unpack Bundles, exporting `Texture2D` (image assets) and `TextAsset` (text descriptions).
* **Area Protection Mechanism**: Compares total pixel area `(w * h) <= (ext_img.w * ext_img.h)` before writing images. If unpacked image resolution is smaller than the file on disk, skips write to protect existing high-resolution graphics.
* **Texture Filter (`is_valuable_texture`)**: Blocks 3D rendering textures, exporting only 2D visual assets.

#### Full UI Elements & Input Fields Detail
* **Folder Containing Target Files (Path Row)**: Specifies input path (typically `RawFiles`).
* **Export CSV / Export Images / Export Text Assets / Backup Files (Checkboxes)**: Controls unpacking export types.
* **Process Fields/Sleeves/Icons Only (Checkbox)**: Filters out card assets.
* **Image Directory Name (LineEdit)**: Directory name for extracted images (default `RawCardImages`).

#### Button Functions
* **[Start Extracting Contents]**: Launches multi-process unpacking. Images save to `RawCardImages/`, original Bundles copy to `FileBackup/`.

#### Single-Tab Operation SOP: Unpacking & Exporting
1. Ensure "Folder Containing Target Files" points to `ProjectDir/RawFiles`.
2. Check "Export Images" and "Backup Files".
3. Click **[Start Extracting Contents]**. Extracted PNGs save to `ProjectDir/RawCardImages/`.

---

### 6. Replace Card Artwork (Tab 4, `t4_replace`)

<img width="1093" height="845" alt="Replace" src="https://github.com/user-attachments/assets/da18dfc5-efeb-470a-904e-b9bb1584c97b" />

#### Technical Mechanism & Operating Principles
Injects and repackages modified external images back into binary Bundles.
* **Lanczos Resampling (`MODE_FIT_VISUAL`)**: For non-card UI assets, forcibly applies Lanczos scaling to match official asset specs exactly, preventing UI glitching.
* **Color Space Correction**: For Spine animation textures (`p[Number]`), forces `m_ColorSpace` to `0` (Gamma space) during write to resolve neon color distortion.
* **Atomic Replacement**: Writes to `.tmp` file prior to physical replacement via `os.replace`, preventing 0KB file corruption during power outages.

#### Full UI Elements & Input Fields Detail
* **Dictionary (CSV) File / Project Root Path (Path Rows)**: Global path settings.
* **Backup Location (LineEdit)**: Unmodified Bundle directory (default `FileBackup`).
* **Modified Artwork Location (LineEdit)**: Modified PNG/JPG directory (default `ModifiedCardImages`).

#### Button Functions
* **[Start Replacing]**: Reads images from `ModifiedCardImages`, injects them into matching Bundles in `FileBackup`, and outputs result to `ModifiedFiles/`.

#### Single-Tab Operation SOP: Injecting Images Back to Bundles
1. Place modified images named `[CardID].png` into `ProjectDir/ModifiedCardImages/`.
2. Ensure Backup Location points to `FileBackup`.
3. Click **[Start Replacing]**. Modified Bundles generate in `ProjectDir/ModifiedFiles/`.

---

### 7. Package Module (Tab 5, `t5_package`)

<img width="1089" height="843" alt="Package" src="https://github.com/user-attachments/assets/3fa4427a-a506-4be0-b216-30cd440d5573" />

#### Technical Mechanism & Operating Principles
Restructures modified Bundles into directory structures matching Master Duel native asset specs.
* **Hash Subdirectory Chunking**: Based on CSV table, extracts the first two characters of Hash values for `0000` assets (e.g., `a589...` -> `a5`), creates `0000/a5/` subdirectories, and moves files into position.

#### Full UI Elements & Input Fields Detail
* **Dictionary (CSV) File / Project Root (Path Rows)**: Path settings.
* **Folder Name (LineEdit)**: Output mod directory name (default `ModFolder`).
* **Include "Modified Card Images" / Include ReadMe.txt / Compress into ZIP (Checkboxes)**: Packaging controls.
* **ReadMe Default Text (PlainTextEdit)**: Custom ReadMe document text.

#### Button Functions
* **[Start Packaging]**: Builds directory structure, copies files, and compresses into ZIP archive.

#### Single-Tab Operation SOP: Packaging for Release
1. Set "Folder Name" and check "Compress into ZIP".
2. Click **[Start Packaging]**. Output mod ZIP archive generates in project root directory.

---

### 8. Chained Task Execution (Tab 6, `t6_chain`)

<img width="1097" height="847" alt="Chain" src="https://github.com/user-attachments/assets/e7c4eb7d-f103-42f6-bb21-b08d96276016" />

#### Technical Mechanism & Operating Principles
Implements an asynchronous Callback Queue execution loop for unattended automation across multiple pipeline steps.

#### Full UI Elements & Buttons
* Checkboxes: [2] Find Files, [3] Extract Data, [8] Pendulum Post-processing, [4] Replace Artwork, [5] Package Module.
* **[▶ Start Automated Pipeline]**: Sequentially executes selected tasks.

#### Single-Tab Operation SOP: One-Click Automation
1. Ensure corresponding path configurations and settings across involved tabs are configured.
2. Check desired pipeline steps (e.g., [2], [3], [4], [5]).
3. Click **[▶ Start Automated Pipeline]**.

---

### 9. Pendulum & Overframe Artwork Post-Processing (Tab 8, `t8_pendulum`)

<img width="1095" height="853" alt="Post-Processing" src="https://github.com/user-attachments/assets/59a8b6b5-fd86-4b94-ab31-a6a1a9eb0c65" />

#### Technical Mechanism & Operating Principles
Provides 4 image processing modes:
1. **Pendulum Artwork Processing (`MODE_PENDULUM`)**: Fills image bottom with transparent padding (based on `pad_pct` ratio) to correct Pendulum card art stretching.
2. **Overframe Artwork Processing (`MODE_OVERFRAME`)**: Crops image to 11:16 ratio and reads 5 PSD layers (`PeriFrame`, `NameBox`, `ArtFrame`, `EffFrame`, `EffBox`, `BackGround`) from `CardFrame/`, synthesizing Alpha matrices along the Z-axis.
3. **Card Cut-In Animation Processing (`MODE_CUTIN`)**: Reads PSD, MP4, GIF, or **single static images (PNG/JPG)**. Uses Numpy for green screen keying and Despill spill suppression, generating Spine 4.2.43 JSON and PMA (Premultiplied Alpha) textures via a 4-point `popup_curve` timeline.
4. **Pendulum Original Artwork Processing (`MODE_PENDULUM_ORIGINAL_CROP`)**: Applies 1.25x horizontal stretch to extracted official distorted Pendulum images, cropping a 1:1 square from the top.

#### Full UI Elements & Input Fields Detail
* **Processing Mode (ComboBox)**: Toggles between the 4 processing pipelines above.
* **Dictionary (CSV) / Project Root (Path Rows)**: Path settings.
* **Modified Location / Raw Location / Pendulum Pad Ratio / Enable Backup / Backup Directory Name (Controls)**: Mode-specific parameters.
* **Overframe Element Alpha Controls (Sliders & SpinBoxes)**: Adjusts Alpha transparency for 5 PSD layers (0 to 100%).
* **Asset & Canvas Settings (Cut-In Specific)**: HD resolution (`1280x720`/`1920x1080`), disk caching toggle, canvas fill mode, rotation, X/Y translation.
* **Keyframe Preview Time Controls (Cut-In Specific)**: Preview time step input and jump buttons.
* **Chroma Keying & Color Polish (Cut-In Specific)**: Keying switch, Despill switch, color picker, tolerance, feathering, Despill intensity, brightness, contrast, Vignette.
* **Timeline & POP UP Effects (Cut-In Specific)**: Start time, duration, FPS, speed multiplier, 4-point Spine scaling curve (time and scale).
* **Pending Processing List (PlainTextEdit)**: Manual input or auto-scanned Target Card IDs.

#### Button Functions
* **[Expand/Hide Real-Time Preview Panel]**: Toggles live canvas preview panel.
* **[Browse]**: Selects test assets (PSD/MP4/GIF/PNG/Folder).
* **[Jump to Initial / Peak / Settle / End]**: Quick timeline keyframe navigation.
* **[Select Keying Color]**: Opens ColorDialog to pick background keying color.
* **[Generate Full-Size Real Preview GIF]**: Exports full animation GIF and opens player automatically.
* **[Auto-Scan Target Directory]**: Scans target folder, populating matching IDs into text box.
* **[🚀 Execute Post-Processing]**: Runs batch image operations and overrides output files.

#### Single-Tab Operation SOPs
* **SOP 8.1: Pendulum Image Padding & Raw Image Repair**
  1. Select Mode: "Pendulum Artwork Processing" or "Pendulum Original Artwork Processing".
  2. Click **[Auto-Scan Target Directory]** to load IDs.
  3. Click **[🚀 Execute Post-Processing]**.
* **SOP 8.2: Overframe Artwork 11:16 Synthesis**
  1. Select Mode: "Overframe Artwork Processing".
  2. Click **[Auto-Scan Target Directory]** to load IDs.
  3. Expand preview panel, click **[Browse]** to select test image, adjust 5 layer alpha sliders.
  4. Click **[🚀 Execute Post-Processing]**, generating 11:16 composite images and switching to Tab 13.
* **SOP 8.3: Single Image/Video/PSD/Folder Spine Cut-In Animation**
  1. Select Mode: "Card Cut-In Animation Processing".
  2. Place asset image or video (e.g., `p18533.png` or `p18533.mp4`) into `ProjectDir/ModifiedCardImages/`.
  3. Click **[Auto-Scan Target Directory]** to populate IDs. Clicking an ID in text box loads preview path.
  4. Click **[Browse]** to load preview, adjust canvas bounds, rotation, and X/Y offset.
  5. Enable "Chroma Keying", click **[Select Keying Color]** for green screen removal, tweak tolerance & Despill.
  6. Configure 4-point POP UP scaling curve, click **[Generate Full-Size Real Preview GIF]** to verify.
  7. Click **[🚀 Execute Post-Processing]**, generating `-hd.png`, `-hd.atlas.txt`, and `js-hd.json` animation assets to `ModifiedCardImages/`.

---

### 10. Quick Single Card Mod (Tab 9, `t9_quick_mod`)

<img width="1095" height="848" alt="Quick Mod" src="https://github.com/user-attachments/assets/d357a412-561b-413a-9225-cfda5ad694aa" />

#### Technical Mechanism & Operating Principles
Bypasses project initialization, performing binary injection directly on single target files.
* **Lobby Background Overwrite (`MODE_LOBBY_BG`)**: Targets `ShopBGBase02` texture in `masterduel_Data/data.unity3d`, executes binary injection, and calls `gc.collect()` to free memory.

#### Full UI Elements & Input Fields Detail
* **Select Category (ComboBox)**: "Standard Mod", "Overframe Mod", "Modify Lobby Background".
* **Search & Selection Area**: Target language dropdown, search box, visual assets only switch, search list.
* **Dictionary (CSV) / Raw Source (0000) / Save Root Directory / New Image Path (Path Rows)**: Path settings.
* **Target Card ID (LineEdit)**: Target Card ID to replace.
* **Directly Overwrite Game Files (Checkbox)**: Dangerous operation; overwrites original `0000` game files directly.

#### Button Functions
* **[Start Replacement]**: Executes single-file binary injection.
* **[Transfer to Overframe Post-Processing]**: Passes paths and ID to Tab 8 under Overframe mode.

#### Single-Tab Operation SOPs
* **SOP 9.1: Quick Single Card Replacement**
  1. Select Category "Standard Mod".
  2. Search card in search box, double-click to populate "Target Card ID".
  3. Select replacement image in "New Image Path", click **[Start Replacement]**.
* **SOP 9.2: Lobby Background Overwrite**
  1. Select Category "Modify Lobby Background".
  2. Set "Raw Source (0000)" and "Save Root Directory".
  3. Select high-res image in "New Image Path".
  4. Click **[Start Replacement]**. Modified `data.unity3d` outputs to `ModifiedFiles/`.

---

### 11. Overframe Card Register (Tab 13, `t13_overframe`)

<img width="1092" height="845" alt="Overframe" src="https://github.com/user-attachments/assets/900b1745-7aa6-4d1e-8a13-690644eacbf2" />

#### Technical Mechanism & Operating Principles
Reads and decodes the `of_card_asset` registry controlling in-game overframe rendering.
* **Pristine Baseline Reference (`.pristine`)**: Generates a `.pristine` read-only backup on initial read. Subsequent writes calculate net differences (`UI Content - Pristine Baseline`), merging with official update data to eliminate conflicts.

#### Full UI Elements & Input Fields Detail
* **Dictionary (CSV) / Game Source (0000) / Save Root Directory (Path Rows)**: Path settings.
* **Target Registry (Hash) (ComboBox)**: Hash identifier for active `of_card_asset`.
* **Registry to Merge (Path Row)**: External registry file path for merging.
* **Existing Whitelist Display & Management (Box 1)**: Displays registered overframe data in active game files.
* **New Registrations & Modifications (Box 2)**: Entry text area for registering card mappings (format: `TriggerID -> TargetBaseID`).

#### Button Functions (10 Buttons)
1. **[🛠️ Manual Search & Repair (For Major Game Updates)]**: Scans 0000 directory for updated `of_card_asset` and migrates mappings automatically.
2. **[📥 Read Existing Raw File]**: Decodes binary asset and loads into Box 1.
3. **[🧹 Clear Cached Registry]**: Deletes `.pristine` baseline file.
4. **[💾 Save Existing Whitelist]**: Saves modifications made within Box 1 only.
5. **[🔗 Merge with External Registry]**: Merges external registry file and resolves conflicts.
6. **[🔍 Go to "Find Files" to Pick Cards]**: Switches to Tab 2 while retaining state.
7. **[📜 Load Historical Registration Logs]**: Populates historical registration logs into Box 2.
8. **[✨ Normalize Name]**: Queries CSV dictionary to auto-append card names and format alignment.
9. **[🧹 Clear History Logs]**: Deletes `registered_history.json`.
10. **[🚀 Validate Conflicts & Export File]**: Merges Box 1 & 2 entries and compiles output Bundle.

#### Single-Tab Operation SOPs
* **SOP 13.1: Register New Overframe Cards**
  1. Configure paths, click **[📥 Read Existing Raw File]** to verify Box 1 contents.
  2. Input IDs into Box 2 (or click **[🔍 Go to "Find Files" to Pick Cards]**, or **[📜 Load Historical Registration Logs]**).
  3. Click **[✨ Normalize Name]** to format and verify entries.
  4. Click **[🚀 Validate Conflicts & Export File]**. Registered AssetBundle generates in `ProjectDir/ModifiedFiles/`.
  5. **Crucial Physical Overwrite Step**: Copy `of_card_asset` Bundle from `ModifiedFiles/` back to game `0000` directory (or mount via Tab 11 virtual manager).
* **SOP 13.2: Delete Whitelist Entries**
  1. Click **[📥 Read Existing Raw File]**.
  2. Manually delete targeted card lines directly inside Box 1.
  3. Click **[💾 Save Existing Whitelist]** (or **[🚀 Validate Conflicts & Export File]**). Updated Bundle generates in `ModifiedFiles/`.
  4. **Crucial Physical Overwrite Step**: Copy updated Bundle back to `0000` directory (or mount via Tab 11).

---

### 12. Graphical Gallery Browser (Tab 12, `t12_gallery`)

<img width="1053" height="837" alt="Gallery" src="https://github.com/user-attachments/assets/2f553750-194c-4165-8ce7-420b45f93171" />

#### Technical Mechanism & Operating Principles
Provides thumbnail previews and sandbox filtering across 8 non-card visual asset categories.
* **Double-Click Quick Transfer**: Double-clicking any thumbnail automatically passes asset ID to Tab 9 (Quick Mod) and jumps tabs.

#### Full UI Elements & Buttons
* **Select Category (ComboBox)**: Field, Coin, Deck Box, Profile Frame, Profile Icon, Sleeve, Lobby BG, File Filter.
* **[Load Selected Category Thumbnails]**: Generates thumbnail cache and renders grid.
* **[🧹 Clear Gallery Cache]**: Deletes `gallery_cache` folder.
* **[Send to "Find Files"]**: Bundles selected items and variants (e.g., coin reverse side) to Tab 2.
* **[Send to "Quick Single Card Mod"]**: Sends selected ID to Tab 9.
* **[✨ Confirm Changes & Return]**: (Sandbox mode) Returns filtered IDs to Tab 2 and closes sandbox.
* **Shortcuts**: `Delete` key removes selected items; `Ctrl+Z` restores deleted items.

#### Single-Tab Operation SOPs
* **SOP 12.1: Double-Click Quick Transfer**
  1. Select category (e.g., "Profile Icon"), click **[Load Selected Category Thumbnails]**.
  2. Double-click target icon thumbnail to populate ID into Tab 9 and jump tabs.
* **SOP 12.2: Sandbox Visual Filtering**
  1. Click **[Search / Visual Filter]** in Tab 2 to jump here.
  2. Select unwanted thumbnails and press `Delete` (`Ctrl+Z` to undo).
  3. Click **[✨ Confirm Changes & Return]** to pass refined ID list back to Tab 2.

---

### 13. Streaming Module Updater / Repairer (Tab 10, `t10_updater`)

<img width="1101" height="841" alt="Repair" src="https://github.com/user-attachments/assets/6434cb46-c528-48d8-a799-486f0e45e16c" />

#### Technical Mechanism & Operating Principles
Resolves black texture or game crash issues caused by old mods after major game updates.
* **Inline Texture Injection**: Reads "Latest Official Game Asset", resets its `m_StreamData` external pointer, and injects binary pixel data from old mod directly into new Bundle structure.

#### Full UI Elements & Buttons
* **1. Old Mod Directory / 2. Official Game Source (0000) / 3. Output Root Directory (Path Rows)**: Path settings.
* **Overwrite Old Mod (Checkbox)**: Direct file replacement switch.
* **[Start Streaming Repair]**: Executes binary injection pipeline.

#### Single-Tab Operation SOP: Legacy Mod Cross-Version Repair
1. Set Old Mod Directory and latest 0000 Directory.
2. Click **[Start Streaming Repair]**. Repaired files export to `FIXED_MOD/` folder.

---

### 14. Virtual Mod Manager (Tab 11, `t11_virtual`)

<img width="1065" height="841" alt="Virtual" src="https://github.com/user-attachments/assets/53fa520d-d56b-43b5-ad74-b7a9a06cd143" />

#### Technical Mechanism & Operating Principles
Uses Windows Symbolic Links (`os.symlink`) to achieve zero disk footprint and instant mod toggling without file copying.
* **Transaction Rollback**: Renames original file to `.vanilla_backup` and logs state in `symlink_state.json` before link creation. Triggers global rollback if permissions fail.
* **Real-Time Hot-Reloading Advantage**: Symlinks point directly to physical files in mod folder. While game is running, exporting updated assets into active mod folder takes effect in-game instantly on next load—**no link re-creation, no manual copying, no game restart required**.

#### Full UI Elements & Buttons
* **Mod Root Directory / Game 0000 Directory (Path Rows)**: Path settings.
* **Scan Depth (ComboBox)**: Subdirectory penetration depth for `0000` structure (1 to 5).
* **Enabled / Disabled Lists (ListWidgets)**: Left = Enabled, Right = Disabled.
* **[Refresh]**: Rescans mod root directory.
* **[>>] / [<<]**: Enable / Disable all selected items.
* **[▲] / [▼]**: Adjust priority order (top overrides bottom).
* **[▶ Apply & Save]**: Creates symlinks and backups.

#### Single-Tab Operation SOP: Virtual Mounting & Real-Time Hot Testing
1. Place mod folders into "Mod Root Directory".
2. Click **[Refresh]**, double-click items to move desired mods to Enabled list.
3. Click **[▶ Apply & Save]** (Admin rights required).
4. **Real-Time Hot Testing**: Keep game open. Re-exporting assets from Tab 8 or Tab 4 into mod folder displays new visuals in-game immediately on next asset load.

---

## Chapter 3: Full-Scene Real-World Case Workflows

This chapter provides end-to-end combination workflows across multiple tabs.

### Case 1: Standard Artwork Replacement Mod Creation
1. **Tab 1 (Scan)**: Set 0000 directory, click **[Start Scanning]** to generate `2DTexture_Mapping.csv`.
2. **Tab 2 (Find)**: Search card name/ID, add to list, click **[Start Extracting Raw Files]** to output binary files to `RawFiles/`.
3. **Tab 3 (Extract)**: Click **[Start Extracting Contents]** to export editable PNGs to `RawCardImages/`.
4. **Artwork Modification**: Edit PNGs using external image editor, save to `ModifiedCardImages/`.
5. **Tab 4 (Replace)**: Click **[Start Replacing]** to write new artwork into Bundles, outputting to `ModifiedFiles/`.
6. **Tab 5 (Package)**: Check options, click **[Start Packaging]** to build mod archive.

### Case 2: Converting Standard Card Artwork into New Overframe Asset
1. **Tab 1 -> Tab 2 -> Tab 3**: Extract raw card artwork per Case 1 workflow.
2. **Tab 8 (Post-Processing)**: Select "Overframe Artwork Processing", adjust 5 PSD layer opacity values, click **[🚀 Execute Post-Processing]** to output 11:16 composite images to `ModifiedCardImages/`.
3. **Tab 4 (Replace)**: Click **[Start Replacing]** to inject overframe artwork into Bundles, saving to `ModifiedFiles/`.
4. **Tab 13 (Register)**: Click **[📥 Read Existing Raw File]**, enter Card ID into Box 2, click **[✨ Normalize Name]**, click **[🚀 Validate Conflicts & Export File]** to export `of_card_asset` to `ModifiedFiles/`.
5. **Physical Overwrite**: Copy all Bundles from `ModifiedFiles/` back to `0000` directory (or mount via Tab 11).

### Case 3: Creating and Replacing Card Entrance Animation (Spine Cut-In)
1. Prepare static image, green screen video, or image sequence in PSD/folder named `p18533.png` or `p18533.mp4`... Place into `ModifiedCardImages/`.
2. **Tab 8 (Post-Processing)**: Select "Card Cut-In Animation Processing", set keying color, adjust Despill & POP UP curve, click **[🚀 Execute Post-Processing]** to generate Spine asset files.
3. **Tab 4 (Replace)**: Click **[Start Replacing]** to build animation Bundles; Gamma color space is auto-corrected.
4. **Tab 5 (Package)**: Package and distribute.

### Case 4: Repairing Invalid Overframe Registries After Major Game Updates
1. Open **Tab 13 (Register)** after major game update.
2. Click **[🛠️ Manual Search & Repair (For Major Game Updates)]**. System scans 0000 directory for new Hash and transfers historical registrations.
3. Click **[🚀 Validate Conflicts & Export File]** to generate updated registry Bundle.
4. Copy exported Bundle back to `0000` directory.

### Case 5: Old Mod Rescue & Real-Time Hot Testing
1. **Tab 10 (Updater)**: Set Old Mod directory and latest 0000 directory, click **[Start Streaming Repair]** to generate repaired Bundles.
2. **Tab 11 (Virtual Manager)**: Move repaired mod into Mod Root Directory, click **[▶ Apply & Save]**. Launch game to verify without game restart.

---

## Chapter 4: Advanced Engineering Techniques Guide

### Technique 1: Reverse Scanning "Modified Files" to Export ID List (TXT)
* **Scenario**: Quick extraction of card IDs contained within a mod package or `ModifiedFiles/` folder.
* **SOP**:
  1. Go to **Tab 1 (Scan & Expand)**.
  2. Manually point "Target Folder (0000)" path to `ModifiedFiles` or mod directory.
  3. Check "Generate Content List (TXT)" only; uncheck "Generate Mapping Table (CSV)".
  4. Click **[Start Scanning]**.
  5. System reads Bundles, extracts texture and asset IDs, generating `Extracted_Names.txt` in output folder.
  6. Load TXT directly into Tab 2 or Tab 13.

### Technique 2: Instant Mod / Cut-In Hot Testing via Virtual Mounting (Tab 11)
* With symlinks active, re-exporting assets to active mod folder while game is running updates in-game graphics on next load without restart or re-linking.

### Technique 3: Tab 2 & Tab 12 Sandbox Visual Filtering Workflow
* Enter IDs in Tab 2 -> Click **[Search / Visual Filter]** -> Jump to Tab 12 -> Press `Delete` to remove unwanted items -> Click **[✨ Confirm Changes & Return]** to send refined list back to Tab 2. Alternatively, double-click an item to send directly to Quick Mod.

### Technique 4: Path Refresh Trigger via Spacebar Trick
* If paths fail to sync from Tab 2 to Tab 3, press spacebar inside input box and delete it to force a `textChanged` signal update.

---

## Chapter 5: System Troubleshooting Guide

1. **`PermissionError: Permission Denied`**
   * **Cause**: `2DTexture_Mapping.csv` is open in Excel or another editor, preventing Python write lock.
   * **Fix**: Close editing software and retry.

2. **Out of Memory (OOM) or Interface Freezing**
   * **Fix**: Go to **Tab 7 (Settings & Appearance)** and reduce "Max Compute Power (Threads)" from `Auto` to 2 or 4. Check "Enable Disk Caching" in Tab 8 when rendering animations.

3. **`.pristine` Baseline Protection & Restoration**
   * **Warning**: Do not delete `.pristine` baseline files in `MD_Tool_Temp/of_card_asset_backups/`. If baseline is lost or corrupted, click **[🛠️ Manual Search & Repair]** in Tab 13 to rebuild.