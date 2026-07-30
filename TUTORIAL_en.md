[繁體中文](TUTORIAL.md) | [English](TUTORIAL_en.md)

***

# MD AstellarTool Operation and Technical Manual

This manual serves as the complete operation guide for "MD AstellarTool". It details the file environments, image naming conventions, interface settings, operational workflows of individual modules, and the underlying logic required to run the tool. This guide aims to provide clear instructions for general users while revealing the technical architecture and security mechanisms for advanced developers.

---

## I. System Prerequisites & Image Naming Conventions

Before using this tool to make any modifications, please ensure your computer environment has the following directories and files ready, and strictly adhere to the image naming rules.

### 1. Essential Game and System Paths
* **Game 0000 File Directory**:
  The storage location for the main game assets and cards. The path format is typically:
  `[Your Drive]:\SteamLibrary\steamapps\common\Yu-Gi-Oh! Master Duel\LocalData\[8-digit Player ID]\0000\`
* **Game StreamingAssets Directory** (for some large assets):
  `[Your Drive]:\SteamLibrary\steamapps\common\Yu-Gi-Oh! Master Duel\masterduel_Data\StreamingAssets\AssetBundle\`
* **Game Lobby Background Data File** (exclusive for lobby background modifications):
  `[Your Drive]:\SteamLibrary\steamapps\common\Yu-Gi-Oh! Master Duel\masterduel_Data\data.unity3d`

### 2. Image Naming Rules and Extraction Mechanism
The tool's automated batch replacement engine identifies the corresponding card or asset ID based on the "file name prefix".

* **Standard Card Art Naming Format**: `[Card ID]_[Any Custom Text].png` or `[Card ID].png`
  * Valid Examples: `20570_Blazing Cartesia, the Virtuous.png`, `4364.png`, `Alt17069_123.jpg`
  * Invalid Example: `Blazing Cartesia, the Virtuous_20570.png` (Cannot be recognized; prefix is not a number).
  * [Technical Details] The underlying system uses the regular expression `^([a-zA-Z]*)(\d+)(.*)$` for precise extraction. The engine automatically filters out starting English letters, directly targets the continuous number block as the card ID, and treats the trailing string as a label, thereby reducing the chance of user naming errors.
* **Non-Card Visual Asset Naming Format**:
  For items like card sleeves, icons, or duel fields, the file name must remain exactly identical to the name in the reference mapping table.
  * Examples: `ProfileIcon1020001.png`, `Mat_001_BaseColor.png`

---

## II. Settings & Appearance (System Settings First Stop)

This module manages global environment variables, cross-tab path synchronization, multi-process compute scheduling, interface theme appearance, and the multilingual translation system. It is highly recommended to configure this page first during your initial use.

<img width="1095" height="847" alt="Settings" src="https://github.com/user-attachments/assets/c87beb83-5276-48bf-b9c5-3f5c7a3ef661" />

### 1. Interface & Global Behavior Settings
* **Write to JSON Config (Save All Changes)**:
  Clicking this button will save all current interface input box paths, checkbox states, color settings, and custom folder names into the `md_tool_config.json` file all at once.
  * [Technical Details] The underlying implementation features a pollution-free storage mechanism (`save_single_key`) and massive cache eviction (`.pop`). When users load tens of thousands of lines of Card IDs in other tabs, these massive temporary drafts will absolutely not pollute the JSON config file. This design significantly reduces parsing error rates and protects Solid State Drives (SSDs) from unnecessary massive read/write wear.
* **Cross-Tab Path Synchronization**:
  When enabled, changing the "Project Root Directory", "0000 Original File Source", or "CSV Mapping Table" paths on any page will synchronously update the corresponding input boxes across all other related modules.
* **Language Selection & Dynamic Expansion**:
  Set the UI display language. The dropdown menu allows users to manually input language codes. As long as the corresponding JSON translation file is placed in the `MD_Tool_Essential/Languages/` folder, the system will automatically read it. If some keys are missing, the system features a safe fallback mechanism, defaulting to Traditional Chinese to prevent program crashes.
* **Export Translation Template**:
  Upon clicking, the tool launches a Python `ast` (Abstract Syntax Tree) parser, traverses the main program source code, automatically finds all tagged strings and UI placeholders, and generates a blank translation template `raw.json` in the `Languages/` directory while safely updating `zh-tw.json`.
* **Max Compute Power (Threads/Processes)**:
  Set the number of cores for multi-process parallel computing. When set to `Auto`, the program will automatically optimize allocation based on your computer's total CPU core count.

### 2. Appearance & Interactive Experience Settings
* **5-Dimension Color Palette**:
  Provides five independent selectors for "Accent Color", "Background Color", "Text Color", "Sidebar Background Color", and "Border Color", supporting Alpha channel transparency adjustment and real-time dynamic QSS stylesheet application.
* **Global Project Folder Naming Settings**:
  Allows unified configuration of default workspace folder names (e.g., Original Files, Original Card Art, File Backups, Modded Card Art, etc.). The underlying system will strictly reference these settings during packaging and reading.
* **Sidebar Tab Sorting & Renaming**:
  You can adjust the order of the left-hand directory via dragging or using up/down buttons, and rename the display name of selected items.
* **Custom Background & 9-Grid Anchor**:
  Choose a local image as the UI background. Sliders adjust background transparency (0\~100%) and brightness (10\~200%). Provides a 9-grid selector (Northwest, North, Southeast, etc.) to determine the background image alignment anchor during window resizing.

---

## III. Beginner's Guide & User Journey

The tool divides asset modification into two mainstream modes. You can choose the corresponding module based on your current needs:
* **Standard Project Pipeline**: Suitable for large mods or multi-file changes. Adopts the structure: "Brute-Force Scan Table -> Find Files -> Extract Images -> Modify Images -> Write Back to Bundle -> Package & Release".
* **Quick & Automated Pipeline**: Suitable for fast single-card replacement, lobby background modification, one-click automated Over-Frame processing, and mod recovery/virtual mounting.

---

## IV. Brute-Force Scan & Supplement (Database Creation & Multilingual Expansion)

This module is the data core of the entire tool. It scans game original binary data, decrypts text, and builds a structured CSV mapping table of file Hash codes and card contents.

<img width="1093" height="844" alt="Scan" src="https://github.com/user-attachments/assets/9b6cfa84-eaf0-4183-8976-28b62c36321a" />

### 1. Basic Mapping Generation (Full Scan)
* **Execution Method**: Fill in the target 0000 folder and output root directory, set the required language, and click "Start Scan".
* **Exception Card Handling**:
  [Note] After scanning, if special cards with unrecognized categories are found, the system will automatically generate `Unknown_Cards_Report.json` and `Exception_IDs_List.txt` in the output directory. The system will not crash; instead, it categorizes these cards as "Exceptions" and applies standard frames by default. Users can manually review them using the list.
* **Memory Protection Mechanism**:
  [Technical Details] During the scan, the system monitors physical memory using the Windows `GlobalMemoryStatusEx` API. When RAM usage exceeding 85% is detected, the multi-process pool automatically enters dynamic hibernation waiting for resource release, ensuring your computer will absolutely not freeze or crash due to the brute-force scan.
* **XOR Obfuscation Decryption & Auto-Cracking**:
  [Technical Details] The game database utilizes dynamic XOR obfuscation encryption. If a game update invalidates the default key, the system activates the `auto_crack_key` brute-force engine, iterating through keys from 0 to 1023 for bit inversion and attempting zlib decompression. As long as decompression succeeds without errors, the system automatically captures the new key and updates the config, achieving permanent immunity to official encryption updates.
* **IL2CPP Metadata Reverse Mapping**:
  [Technical Details] Non-card assets (like icons, fields) only have Hash names. This tool reads `global-metadata.dat`, extracts ID strings, calculates CRC32 hashes, and performs a two-way collision comparison with `ids_item.bytes` to accurately restore their text names.
* **TCG/OCG Dual Card Face Auto-Detection**:
  [Technical Details] During scanning, the tool automatically parses Unity Container paths. If a path contains `/tcg/` or `/ocg/`, the system automatically annotates this in the Container column of the CSV mapping table, making it easier for advanced players to categorize censored and uncensored variant card arts.

### 2. Multilingual Horizontal Expansion
When you switch languages in-game and download a new text pack, you can paste the old CSV into the "CSV to be Expanded" field, modify the language code, and click "Execute Supplement / Expansion". The tool will compare old and new data, automatically adding new language names and effect columns on the right side of the CSV without needing to rescan the entire database.

---

## V. Find Files (File Location & Visual Filtering)

Based on the CSV mapping table, this module accurately locates and copies the specified target Hash files from the massive 0000 directory.

<img width="1096" height="842" alt="Find" src="https://github.com/user-attachments/assets/3f22366e-02d1-465c-a389-159fdeea75b0" />

### 1. Operation Mode Menu
* **Normal Extraction Mode**: Only copies the target card's Hash file from the game directory to the project workspace.
* **Quick Over-Frame Switch Mode**: One-click automated mode. Add the ID and click execute. The system sequentially completes the full workflow: "Copy Original File -> Extract Image -> 11:16 Over-Frame Crop & PSD Comp -> Write Back to Bundle -> Jump to Over-Frame Register".

### 2. Search & Visual Sandbox Filtering
* **Search Engine**: Supports Unicode normalization and fuzzy search. Through dual-mode language search, even with minor spelling errors, it can calculate similarity and list results. Double-click list items to add them to the extraction list below.
* **Visual Filtering (Sandbox Mode)**:
  Click "Visual Filter", and the system sends the IDs in the extraction list to a dedicated sandbox in the graphical browser. Users can view card art in a grid, select unwanted cards, and press `Delete` to remove them. Clicking "Confirm Changes and Return" will overwrite the extraction list with the filtered roster.

---

## VI. Extract Data (Texture2D Export & Protection Mechanism)

Unpacks the copied binary Bundle files and exports 2D texture resources.

<img width="1076" height="842" alt="Extract" src="https://github.com/user-attachments/assets/91e4e574-9103-4825-9c8a-2a18666cf79e" />

### 1. High-Resolution Area Comparison Protection Mechanism
[Description] If a player repeatedly executes extraction for the same card, there is no need to worry about the high-resolution modified image being overwritten by the official original low-resolution image.
[Technical Details] Before writing the image, the underlying tool compares the total pixel area of the old and new images `(w * h) <= (ext_img.w * ext_img.h)`. Overwrites only execute when the new resolution is greater than or equal to the old image, completely protecting your HD card art.

### 2. Smart Noise Filter (`is_valuable_texture`)
[Technical Details] Game Bundles are filled with massive amounts of 3D rendering textures (Normal, Metallic, Roughness, etc.). This tool has a built-in precise black/whitelist filtering engine. When useless Shader materials are read, they are directly discarded; as long as the file name matches visual asset characteristics, it is retained, ensuring the extracted folder remains clean and noise-free.

### 3. Output Control
Supports simultaneous export of dedicated CSV sub-mapping tables, images, and retention of original Bundle backups (for later restoration or comparison).

---

## VII. Modify Card Art (Bundle Binary Replacement)

Stitches the externally modified new images back into the binary Bundle files.

<img width="1093" height="845" alt="Modify" src="https://github.com/user-attachments/assets/da18dfc5-efeb-470a-904e-b9bb1584c97b" />

### 1. Execution Logic & Visual Classification Protection
After filling in the dictionary and project root directory, click "Start Replacement". The program will write the images from the "Modded Card Art" folder into the backup files and output them to the "Modified Files" folder.

[Technical Details] The tool does not perform simple binary overwriting. It has an internal `is_visual_asset` classification engine. If the replacement is the "Card Body", the engine maintains the original resolution of the new image (protecting HD card art); if the replacement involves "Card Sleeves, Lobby Backgrounds, Profile Frames" (UI interfaces), the engine triggers the `MODE_FIT_VISUAL` strategy, forcing the use of the Lanczos resampling algorithm (top-tier in image processing) to losslessly scale the image to strictly match the official dimensions, preventing UI breakage.

---

## VIII. Package Mod (Directory Restructuring & Release Packaging)

Automatically assembles the modified Bundle files into the directory structure required by the official game.

<img width="1089" height="843" alt="Package" src="https://github.com/user-attachments/assets/3fa4427a-a506-4be0-b216-30cd440d5573" />

The tool reads the CSV mapping table to determine whether each file belongs to the standard `0000` or `StreamingAssets`. The system precisely creates `0000/xx/` folders (split by the first two characters of the Hash) in the output folder. It supports one-click compression into a ZIP file with an appended ReadMe documentation file, facilitating direct overwriting to the game directory or public release.

---

## IX. Smart Chained Execution (One-Click Automated Pipeline)

Provides factory scheduling functions, chaining five steps: "Find Files, Extract Data, Pendulum Post-Processing, Modify Card Art, Package Mod". Relying on an asynchronous Callback Queue, as long as the input paths on all tabs are filled correctly, you can complete all workflows with one click entirely unattended.

<img width="1097" height="847" alt="Chain" src="https://github.com/user-attachments/assets/e7c4eb7d-f103-42f6-bb21-b08d96276016" />

---

## X. Pendulum & Over-Frame Art Post-Processing (Comprehensive Analysis of Three Modes)

An image processing hub specifically designed for card deformation repair and 11:16 ratio Over-Frame 3D card art.

<img width="1095" height="853" alt="Post-Processing" src="https://github.com/user-attachments/assets/59a8b6b5-fd86-4b94-ab31-a6a1a9eb0c65" />

### 1. Pendulum Art Post-Processing (Modded Art)
The aspect ratio of Pendulum card art frames in-game differs from regular cards. After setting the "Pendulum Fill Ratio", the program will add a completely transparent background of corresponding proportion to the bottom of the image, increasing the total image height to prevent rendering stretching in-game.

[Technical Details] Pendulum detection is extremely difficult, hence the underlying "Hybrid Dual-Track Detection Engine". The first line of defense extracts the 6-bit physical mask from binaries to compare feature codes; the second line of defense uses NLP semantic parsing to scan effect texts for keywords. The union of both defenses completely solves the issue of Pendulum card classification omissions.

### 2. Over-Frame Art Post-Processing (Modded Art)
Over-Frame card art requires an 11:16 ratio.
[Technical Details] The tool integrates the `psd-tools` parsing engine and `_psd_cache` memory caching. It deconstructs the PSD files in the `CardFrame/` directory into five independent Alpha mask layers. When you adjust transparency, the engine recalculates the Alpha channel in memory and performs `Image.alpha_composite` Alpha blending following a strict Z-axis order (`Base -> EffBox -> EffFrame -> ArtFrame -> NameBox -> PeriFrame`) with the 11:16 center-cropped image, achieving Photoshop-level composite effects.

### 3. Pendulum Original Art Processing (Original Art)
Performs dimensional correction for original Pendulum card art extracted directly from the game.
[Technical Details] Official Pendulum card art is severely squeezed and deformed within game files. This mode first applies a "1.25x horizontal forced stretch" to restore normal visual proportions, followed by a `1:1` perfect square crop from the top. This allows artists looking to create fan-art to directly obtain correctly proportioned base templates.

---

## XI. Quick Single Card Modification (Single Card Injection & Lobby Background Overwrite)

Bypass the creation of a full project pipeline, providing quick single card testing and bare-file system overwriting.

<img width="1095" height="848" alt="Single" src="https://github.com/user-attachments/assets/d357a412-561b-413a-9225-cfda5ad694aa" />

* **Single Card Quick Injection**:
  Search for the target card ID, select the new image path, and click Start Replacement to directly modify it. For Over-Frame mods, you can click "Send to Over-Frame Mod Post-Processing", and the system will automatically guide you to adjust frame transparency and complete subsequent actions.
* **Lobby Background Modification (Direct Replace)**:
  Switch to this mode specifically for modifying the game lobby background. The system precisely targets the `ShopBGBase02` texture asset in `masterduel_Data/data.unity3d`, automatically performs adaptive width/height scaling, and completes the binary overwrite.
  [Note] `data.unity3d` is an extremely large file. During replacement, the program triggers `gc.collect()` for forced memory garbage collection to prevent system crashes. Therefore, processing takes longer; please be patient.

---

## XII. Over-Frame Card Register (Whitelist Management & External Registry Merge)

The underlying game uses the `of_card_asset` binary registry to determine which cards should apply 11:16 Over-Frame borderless rendering. This module handles reading, writing, and merging of this file.

<img width="1092" height="845" alt="Register" src="https://github.com/user-attachments/assets/900b1745-7aa6-4d1e-8a13-690644eacbf2" />

### 1. Existing Whitelist Reading & Cache Baseline (`.pristine`)
[Note] When reading the official registry for the first time, the system creates a `.pristine` pure baseline file in `MD_Tool_Temp/of_card_asset_backups/`. This is the absolute baseline for the tool's operation, **please absolutely do not delete it manually**. Every time a new registry is written, the tool merges your new IDs based on this baseline file. Deleting it will result in the inability to safely restore files in the future.

### 2. External Registry Merging & Conflict Analysis
When you obtain an `of_card_asset` file provided by other creators, you can select it in the "Registry to Merge" section above and click merge.
[Description] If conflicts occur, the program automatically analyzes them. If a user-registered ID points to `0` in official records, the tool identifies it as an "Official Reserved Placeholder" and prompts you to keep official settings; if it points to a different target, a prompt will appear with deletion suggestions, actively blocking the merge to protect file structures.

### 3. Add Registration & History
Enter the card ID you wish to register in the lower text box, or click "Load Previously Successful Registration History" to load past footprints. Click "Verify Conflicts and Output File", and the tool will merge and write the roster into a new Bundle.

---

## XIII. Graphical Browser (Visual Asset Filter & Sandbox System)

Provides visual thumbnail grids for quickly browsing non-card assets like fields, sleeves, and icons.

<img width="1053" height="837" alt="Browser" src="https://github.com/user-attachments/assets/2f553750-194c-4165-8ce7-420b45f93171" />

* **Memory Lookup & Cache Generation**:
  [Technical Details] When loading hundreds of thumbnails, frequent mechanical hard drive reads cause interface freezing. The tool's solution: scan the cache folder to build a set, and when new images need rendering, utilize a memory lookup method with `O(1)` time complexity instead of time-consuming Disk I/O.
* **Decimal Pixel Smooth Scrolling Engine**:
  [Technical Details] To achieve the ultimate UI experience, the tool features a hand-coded linear drag filter (`LinearDragScrollFilter`). When a player drags the mouse slowly, the generated decimal pixel steps are stored in an internal accumulator until a full 1 pixel is accumulated to trigger a screen redraw. This completely eliminates the native stickiness and inertial oscillation of Qt, achieving precise stop-and-go handling.
* **Cross-Page Teleportation**:
  After selecting a thumbnail, clicking send will trigger the program to globally associate and uproot the entire branch, including the main trunk and all variants (e.g., both sides of a coin).
* **Incognito Sandbox Mode**:
  In "File Filtering" mode, when a player presses `Delete` to remove an image on the interface, it merely manipulates the roster in memory. Only upon clicking "Confirm Changes and Return" will the results be synced back to the main window, followed by the system automatically destroying the sandbox.

---

## XIV. Mod Stream Fixer (Legacy Mod Cross-Version Porting)

When major game updates cause legacy Mod Bundle files to fail, display black screens, or crash, this provides a quick fix without the need to remake the mod.

<img width="1101" height="841" alt="Fixer" src="https://github.com/user-attachments/assets/6434cb46-c528-48d8-a799-486f0e45e16c" />

[Description] Why do old mods break? Usually, because official major updates overwrite files or change the asset's Hash filename and internal offsets.
[Technical Details] This tool does not merely unpack and repack; it executes binary-level "surgery" (Inline Texture Injection). The program reads the latest official original file, forcefully zeroes out the external paths and offsets of its `m_StreamData` (severing the official external resource links), and then forcibly embeds the binary pixel data (`image_data`) of the old Mod into the new file, thereby completing a lossless upgrade.

---

## XV. Virtual Mod Manager (Symlink Zero-Footprint Mounting)

Utilizes Windows Symbolic Link (Symlink) technology to achieve instant mod mounting with no file copying and zero hard drive space consumption.

<img width="1065" height="841" alt="Virtual" src="https://github.com/user-attachments/assets/53fa520d-d56b-43b5-ad74-b7a9a06cd143" />

### 1. Mount Filtering & Phantom Mod Eviction
After setting the scan depth, the manager automatically locates internal 0000 folders.
[Note] The system automatically blacklists workspace folders named "Modded Card Art", "Original Files", "File Backups", etc., to prevent players from accidentally mounting unfinished works.
[Technical Details] Before executing a mount, the system runs a pre-check (`filter_valid_mods`). If it finds that mods on the active list have been deleted from the hard drive, the tool deems them "Phantom Mods" and automatically evicts them, preventing system crashes caused by missing paths.

### 2. Transaction Rollback & Vanilla Backup Mechanism
This is a system-level security safeguard.
[Technical Details] Before the tool mounts and replaces any game original files, it creates a `.vanilla_backup` for that original file and writes operation steps to `symlink_state.json`. If abnormalities like antivirus interception, insufficient drive permissions, or file locks occur during the mounting process, the system instantaneously triggers a "Global Rollback". It will delete all partially created shortcuts according to the JSON record and perfectly restore the `.vanilla_backup`. This guarantees that even in the event of a power outage or error, your base game remains 100% absolutely safe.

---

## Appendix: FAQ & Troubleshooting

* **Encountering `PermissionError`?**
  If you encounter permission errors during scanning, extraction, or modification, it is usually because you have the CSV mapping table open in software like Excel. Please close the file and execute again.
* **Cannot open the program or getting errors when running from source code?**
  If you didn't download the compiled executable and are running from the source code, and encounter a missing audio library error, please ensure you have installed dependencies like `msgpack`. A `MockModule` patch is built into the top of the source code to intercept most missing dependency errors.
* **Card IDs are not generating mapped names?**
  Please check if the language you set in the "Brute-Force Scan & Supplement" tab matches the in-game language, or try clicking "Execute Supplement / Expansion" to update your CSV file.
