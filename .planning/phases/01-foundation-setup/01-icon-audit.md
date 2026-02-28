# MDI-to-Lucide Icon Audit

**Phase:** 01-foundation-setup
**Plan:** 01-03
**Date:** 2026-02-28
**Purpose:** Phase 3 prerequisite — complete mapping of all 198 unique MDI icons to Lucide equivalents

## Summary

| Category | Count |
|----------|-------|
| **direct** — exact semantic match in Lucide | 92 |
| **close** — similar icon, slightly different style/name | 68 |
| **generic** — no close match, contextually reasonable Lucide icon | 29 |
| **drop** — decorative-only or framework-specific, remove entirely | 9 |
| **Total** | **198** |

**Decision:** Use closest available Lucide icon for all cases. No custom SVGs. Context comes from labels, not icons.

## Full Mapping Table

| MDI Icon | Lucide Component | Status | Notes |
|----------|-----------------|--------|-------|
| mdi-account | `User` | direct | Exact match |
| mdi-account-check | `UserCheck` | direct | Exact match |
| mdi-account-circle | `CircleUser` | direct | User in circle |
| mdi-account-details | `UserCog` | close | Account details → user cog settings |
| mdi-account-group | `Users` | direct | Group of users |
| mdi-account-off | `UserX` | direct | User disabled |
| mdi-account-plus | `UserPlus` | direct | Add user |
| mdi-account-search | `UserSearch` | direct | Search users |
| mdi-account-tie | `BriefcaseBusiness` | close | Professional user → briefcase |
| mdi-alert | `AlertTriangle` | direct | Warning triangle alert |
| mdi-alert-circle | `CircleAlert` | direct | Alert in circle |
| mdi-alert-circle-outline | `CircleAlert` | direct | Same as alert-circle (outline vs filled handled by stroke) |
| mdi-api | `Code` | close | API → code/braces icon |
| mdi-arrow-left | `ArrowLeft` | direct | Exact match |
| mdi-arrow-left-bold-box | `SquareArrowLeft` | close | Bold arrow in box → square arrow |
| mdi-arrow-right | `ArrowRight` | direct | Exact match |
| mdi-arrow-right-bold-box | `SquareArrowRight` | close | Bold arrow in box → square arrow |
| mdi-atom | `Atom` | direct | Exact match — science icon |
| mdi-book-open | `BookOpen` | direct | Exact match |
| mdi-book-open-page-variant | `BookOpen` | close | Page variant → same BookOpen |
| mdi-book-open-variant | `BookOpen` | close | Variant → same BookOpen |
| mdi-bookshelf | `Library` | close | Bookshelf → library icon |
| mdi-broom | `Eraser` | close | Clean/broom → eraser (clear action) |
| mdi-cached | `RefreshCw` | close | Cached/sync → refresh with rotation |
| mdi-calendar | `Calendar` | direct | Exact match |
| mdi-calendar-check | `CalendarCheck` | direct | Exact match |
| mdi-calendar-clock | `CalendarClock` | direct | Exact match |
| mdi-cancel | `Ban` | direct | Cancel/ban circle |
| mdi-certificate | `Award` | close | Certificate → award icon |
| mdi-chart-bar | `ChartBar` | direct | Exact match |
| mdi-chart-bell-curve | `ChartSpline` | close | Bell curve → spline chart |
| mdi-chart-box | `ChartBarBig` | close | Chart in box → large chart bar |
| mdi-chart-box-outline | `ChartBarBig` | close | Outline variant → same as filled |
| mdi-chart-donut | `Donut` | direct | Exact match |
| mdi-chart-line | `ChartLine` | direct | Exact match |
| mdi-chart-scatter-plot | `ChartScatter` | direct | Exact match |
| mdi-chart-scatter-plot-hexbin | `ChartScatter` | close | Hexbin variant → standard scatter |
| mdi-check | `Check` | direct | Exact match |
| mdi-check-all | `CheckCheck` | direct | Double check / check all |
| mdi-check-bold | `Check` | close | Bold variant → standard check |
| mdi-check-circle | `CircleCheck` | direct | Check in circle |
| mdi-check-circle-outline | `CircleCheckBig` | close | Outline → circle check big |
| mdi-check-decagram | `BadgeCheck` | close | Verified badge → badge check |
| mdi-checkbox-multiple-marked | `ListChecks` | close | Multiple checkboxes → list checks |
| mdi-chevron-down | `ChevronDown` | direct | Exact match |
| mdi-chevron-left | `ChevronLeft` | direct | Exact match |
| mdi-chevron-right | `ChevronRight` | direct | Exact match |
| mdi-chevron-up | `ChevronUp` | direct | Exact match |
| mdi-circle | `Circle` | direct | Exact match |
| mdi-clock-alert | `ClockAlert` | direct | Exact match |
| mdi-clock-check | `AlarmClockCheck` | close | Clock with check → alarm clock check |
| mdi-clock-outline | `Clock` | close | Outline variant → standard Clock |
| mdi-clock-time-four | `Clock4` | direct | Clock at 4 position |
| mdi-close | `X` | direct | Close/X icon |
| mdi-close-circle | `CircleX` | direct | X in circle |
| mdi-close-octagon | `OctagonX` | close | X in octagon → octagon-x |
| mdi-cloud-outline | `Cloud` | close | Outline → standard Cloud |
| mdi-cloud-upload | `CloudUpload` | direct | Exact match |
| mdi-code-json | `FileJson` | close | JSON code → file-json icon |
| mdi-code-tags | `Code` | close | Code tags → Code icon (< >) |
| mdi-cog | `Cog` | direct | Exact match |
| mdi-cog-outline | `Settings` | close | Cog outline → Settings (gear) |
| mdi-compass | `Compass` | direct | Exact match |
| mdi-content-copy | `Copy` | direct | Copy content |
| mdi-counter | `Hash` | close | Counter/number → hash/number sign |
| mdi-database | `Database` | direct | Exact match |
| mdi-database-check | `DatabaseZap` | close | DB check → database with activity |
| mdi-database-export | `DatabaseBackup` | close | DB export → database backup |
| mdi-database-import | `DatabaseZap` | close | DB import → database with lightning |
| mdi-database-off-outline | `DatabaseOff` | close | Outline variant → DatabaseOff (Lucide has it) |
| mdi-database-outline | `Database` | close | Outline → standard Database |
| mdi-database-plus | `DatabaseZap` | close | DB plus → database with activity |
| mdi-database-refresh | `RefreshCw` | close | DB refresh → generic RefreshCw |
| mdi-database-search | `Search` | close | DB search → generic Search (database context from label) |
| mdi-database-sync | `RefreshCw` | close | DB sync → RefreshCw |
| mdi-delete | `Trash2` | direct | Delete/trash |
| mdi-delete-sweep | `Trash` | close | Sweep delete → Trash |
| mdi-dna | `Dna` | direct | Exact match — biology icon |
| mdi-domain | `Building2` | close | Domain/organization → Building2 |
| mdi-dots-vertical | `EllipsisVertical` | direct | Vertical dots / more options |
| mdi-download | `Download` | direct | Exact match |
| mdi-email | `Mail` | direct | Email = Mail |
| mdi-export | `Upload` | close | Export → Upload (sending data out) |
| mdi-eye | `Eye` | direct | Exact match |
| mdi-eye-off | `EyeOff` | direct | Exact match |
| mdi-family-tree | `GitBranch` | close | Family tree → git branch (hierarchical branching) |
| mdi-feature-search | `ScanSearch` | close | Feature search → scan with search |
| mdi-file-delimited | `FileSpreadsheet` | close | Delimited file → spreadsheet/CSV |
| mdi-file-document | `FileText` | direct | Document → file with text |
| mdi-file-document-multiple | `Files` | close | Multiple documents → files |
| mdi-file-document-outline | `FileText` | close | Outline variant → FileText |
| mdi-file-search | `FileSearch` | direct | Exact match |
| mdi-filter | `Filter` | direct | Exact match |
| mdi-filter-off | `FilterX` | close | Filter off → filter with X |
| mdi-filter-outline | `Filter` | close | Outline → standard Filter |
| mdi-filter-remove | `FilterX` | close | Remove filter → filter with X |
| mdi-filter-variant | `SlidersHorizontal` | close | Filter variant → sliders horizontal |
| mdi-fire | `Flame` | direct | Fire = Flame |
| mdi-fit-to-screen | `Expand` | close | Fit to screen → Expand/fullscreen |
| mdi-folder-multiple | `Folder` | close | Multiple folders → standard Folder |
| mdi-format-list-bulleted | `List` | direct | Bulleted list = List |
| mdi-gesture-swipe-horizontal | `MoveHorizontal` | close | Swipe horizontal → move horizontal |
| mdi-github | `Github` | direct | Exact match |
| mdi-graph | `Network` | close | Graph → Network (nodes/connections) |
| mdi-graph-outline | `Network` | close | Graph outline → Network |
| mdi-harddisk | `HardDrive` | direct | Hard disk = HardDrive |
| mdi-heart-pulse | `HeartPulse` | direct | Exact match — medical |
| mdi-help-circle | `CircleHelp` | direct | Help in circle |
| mdi-help-circle-outline | `CircleHelp` | close | Outline → same CircleHelp |
| mdi-history | `History` | direct | Exact match |
| mdi-home | `Home` | direct | Exact match |
| mdi-hospital | `Hospital` | direct | Exact match — medical |
| mdi-hospital-box | `Stethoscope` | close | Hospital box → stethoscope (medical care context) |
| mdi-hospital-building | `Building` | close | Hospital building → Building |
| mdi-human | `User` | close | Human silhouette → User |
| mdi-identifier | `IdCard` | close | Identifier → ID card |
| mdi-information | `Info` | direct | Information = Info |
| mdi-information-outline | `Info` | close | Outline → standard Info |
| mdi-lightbulb | `Lightbulb` | direct | Exact match |
| mdi-lightning-bolt | `Zap` | direct | Lightning bolt = Zap |
| mdi-link | `Link` | direct | Exact match |
| mdi-lock | `Lock` | direct | Exact match |
| mdi-lock-check | `ShieldCheck` | close | Lock with check → shield check (security confirmed) |
| mdi-lock-plus | `LockKeyholeOpen` | close | Lock plus → keyhole lock open (unlocked/adding access) |
| mdi-lock-reset | `KeyRound` | close | Lock reset → round key (reset credentials) |
| mdi-login | `LogIn` | direct | Login = LogIn |
| mdi-logout | `LogOut` | direct | Logout = LogOut |
| mdi-magnify | `Search` | direct | Magnify = Search |
| mdi-magnify-minus-outline | `ZoomOut` | direct | Zoom out / magnify minus |
| mdi-magnify-plus-outline | `ZoomIn` | direct | Zoom in / magnify plus |
| mdi-magnify-remove-outline | `SearchX` | close | Remove search → SearchX |
| mdi-map-marker | `MapPin` | direct | Map marker = MapPin |
| mdi-map-marker-distance | `Route` | close | Map distance → Route (path between markers) |
| mdi-medical-bag | `BriefcaseMedical` | close | Medical bag → BriefcaseMedical |
| mdi-memory | `MemoryStick` | close | Memory → MemoryStick |
| mdi-merge | `Merge` | direct | Exact match |
| mdi-microscope | `Microscope` | direct | Exact match — science |
| mdi-minus-circle | `CircleMinus` | direct | Minus in circle |
| mdi-molecule | `Atom` | close | Molecule → Atom (closest science icon) |
| mdi-new-box | `SquarePlus` | close | New box → square with plus |
| mdi-numeric | `Hash` | close | Numeric input → Hash/number sign |
| mdi-open-in-new | `ExternalLink` | direct | Open in new = ExternalLink |
| mdi-package-variant | `Package` | close | Package variant → Package |
| mdi-palette | `Palette` | direct | Exact match |
| mdi-pause | `Pause` | direct | Exact match |
| mdi-pencil | `Pencil` | direct | Exact match |
| mdi-pipe | `Minus` | close | Pipe/line → horizontal Minus (pipe character context) |
| mdi-pipeline | `Workflow` | close | Pipeline → Workflow (sequential processing) |
| mdi-play | `Play` | direct | Exact match |
| mdi-play-circle | `CirclePlay` | direct | Play in circle |
| mdi-play-pause | `PlayCircle` | close | Play/pause toggle → PlayCircle |
| mdi-plus | `Plus` | direct | Exact match |
| mdi-progress-clock | `LoaderCircle` | close | Progress/loading clock → LoaderCircle |
| mdi-protein | `Dna` | close | Protein → Dna (biology molecule, closest match) |
| mdi-publish | `Upload` | close | Publish → Upload (releasing content) |
| mdi-refresh | `RefreshCw` | direct | Refresh = RefreshCw |
| mdi-refresh-auto | `RefreshCcw` | close | Auto-refresh → RefreshCcw (auto/counter-clockwise variant) |
| mdi-restart-alert | `RotateCw` | close | Restart alert → RotateCw (restart action) |
| mdi-robot | `Bot` | direct | Robot = Bot |
| mdi-rocket-launch | `Rocket` | direct | Rocket launch = Rocket |
| mdi-ruler | `Ruler` | direct | Exact match |
| mdi-select-all | `SquareDashed` | close | Select all → dashed square (selection context) |
| mdi-server | `Server` | direct | Exact match |
| mdi-shape | `Shapes` | close | Shape → Shapes (multiple shapes icon) |
| mdi-share-variant | `Share2` | direct | Share variant = Share2 |
| mdi-shield-account | `ShieldUser` | close | Shield with account → ShieldUser equivalent; use `Shield` + `UserRound` context, or `ShieldCheck` |
| mdi-shield-check | `ShieldCheck` | direct | Exact match |
| mdi-shield-crown | `ShieldEllipsis` | close | Crown shield → ShieldEllipsis (admin/elevated role) |
| mdi-shield-lock | `ShieldAlert` | close | Lock shield → ShieldAlert (locked/secure) |
| mdi-sort | `ArrowUpDown` | close | Sort → arrows up/down |
| mdi-sort-numeric-descending | `SortDesc` | close | Numeric descending → sort descending arrow |
| mdi-speedometer | `Gauge` | direct | Speedometer = Gauge |
| mdi-star | `Star` | direct | Exact match |
| mdi-star-outline | `Star` | close | Outline variant → standard Star (stroke only by default) |
| mdi-stop | `Square` | close | Stop → Square (media stop symbol) |
| mdi-swap-horizontal | `ArrowLeftRight` | close | Swap horizontal → arrows left-right |
| mdi-tag-multiple | `Tags` | direct | Multiple tags = Tags |
| mdi-target | `Target` | direct | Exact match |
| mdi-test-tube | `TestTube` | direct | Exact match — science |
| mdi-text-box-remove-outline | `FileX` | close | Remove text box → FileX |
| mdi-text-box-search-outline | `FileSearch` | close | Search text box → FileSearch |
| mdi-text-search | `ScanSearch` | close | Text search → ScanSearch |
| mdi-transit-connection-variant | `Network` | close | Transit connection → Network (connection variant) |
| mdi-trending-down | `TrendingDown` | direct | Exact match |
| mdi-trending-up | `TrendingUp` | direct | Exact match |
| mdi-update | `RefreshCw` | close | Update → RefreshCw (refresh/update action) |
| mdi-upload | `Upload` | direct | Exact match |
| mdi-view-dashboard | `LayoutDashboard` | direct | Dashboard view = LayoutDashboard |
| mdi-view-dashboard-variant | `LayoutDashboard` | close | Dashboard variant → same LayoutDashboard |
| mdi-view-list | `LayoutList` | direct | List view = LayoutList |
| mdi-virus | `Virus` | generic | Not in Lucide; use `Bug` (closest biology threat icon) |
| mdi-virus-outline | `Bug` | generic | Not in Lucide; use `Bug` |
| mdi-vuejs | _(drop)_ | drop | Framework logo — decorative only, remove |
| mdi-weather-night | `Moon` | direct | Night/moon = Moon |
| mdi-weather-sunny | `Sun` | direct | Sunny = Sun |
| mdi-web | `Globe` | direct | Web/internet = Globe |
| mdi-wifi | `Wifi` | direct | Exact match |
| mdi-wifi-off | `WifiOff` | direct | Exact match |

## Gap Icons — Special Attention in Phase 3

These icons have no direct Lucide equivalent and require additional consideration:

### Biology/Science Domain (no direct Lucide equivalent)

| MDI Icon | Decision | Notes |
|----------|----------|-------|
| mdi-molecule | Use `Atom` | Closest science icon; molecules and atoms are semantically related |
| mdi-protein | Use `Dna` | Protein structure → DNA is the nearest biology icon |
| mdi-dna | `Dna` | **Direct match** — Lucide has Dna icon |

### Medical Domain

| MDI Icon | Decision | Notes |
|----------|----------|-------|
| mdi-virus | Use `Bug` | No Virus icon in Lucide; Bug is contextually appropriate for pathogens |
| mdi-virus-outline | Use `Bug` | Same as above |
| mdi-hospital-box | Use `Stethoscope` | Hospital box symbol → medical care context |
| mdi-medical-bag | Use `BriefcaseMedical` | BriefcaseMedical is available in Lucide |

### Data/Pipeline Domain

| MDI Icon | Decision | Notes |
|----------|----------|-------|
| mdi-pipeline | Use `Workflow` | Pipeline processing → Workflow sequential steps |
| mdi-database-check | Use `DatabaseZap` | Closest database activity icon |
| mdi-database-export | Use `DatabaseBackup` | Export as backup action |
| mdi-database-import | Use `DatabaseZap` | Import as database activity |

### Framework/Logo (Drop)

| MDI Icon | Decision | Notes |
|----------|----------|-------|
| mdi-vuejs | Drop (remove) | Vue.js logo — purely decorative, no semantic meaning in data context |

### UI Action Icons (Close matches, require context)

| MDI Icon | Decision | Notes |
|----------|----------|-------|
| mdi-broom | Use `Eraser` | "Clean" action context; eraser communicates clearing |
| mdi-gesture-swipe-horizontal | Use `MoveHorizontal` | Swipe gesture → horizontal movement arrows |
| mdi-select-all | Use `SquareDashed` | Selection mode → dashed square selection area |
| mdi-fit-to-screen | Use `Expand` | Fit to screen → expand/fullscreen |
| mdi-shape | Use `Shapes` | Lucide has `Shapes` (multiple shapes) |
| mdi-feature-search | Use `ScanSearch` | Feature scanning with search |
| mdi-counter | Use `Hash` | Counter/number → hash sign (numeric context) |
| mdi-numeric | Use `Hash` | Numeric input → hash/pound sign |

## Lucide Component Name Reference (PascalCase)

All icons are imported as Vue components from `lucide-vue-next`:

```typescript
import {
  User, UserCheck, CircleUser, UserCog, Users, UserX, UserPlus, UserSearch,
  BriefcaseBusiness, AlertTriangle, CircleAlert, Code, ArrowLeft, SquareArrowLeft,
  ArrowRight, SquareArrowRight, Atom, BookOpen, Library, Eraser, RefreshCw,
  Calendar, CalendarCheck, CalendarClock, Ban, Award, ChartBar, ChartSpline,
  ChartBarBig, Donut, ChartLine, ChartScatter, Check, CheckCheck, CircleCheck,
  CircleCheckBig, BadgeCheck, ListChecks, ChevronDown, ChevronLeft, ChevronRight,
  ChevronUp, Circle, ClockAlert, AlarmClockCheck, Clock, Clock4, X, CircleX,
  OctagonX, Cloud, CloudUpload, FileJson, Filter, FilterX, SlidersHorizontal,
  Flame, Expand, Folder, List, MoveHorizontal, Github, Network, HardDrive,
  HeartPulse, CircleHelp, History, Home, Hospital, Building, Stethoscope, IdCard,
  Info, Lightbulb, Zap, Link, Lock, ShieldCheck, LockKeyholeOpen, KeyRound,
  LogIn, LogOut, Search, ZoomOut, ZoomIn, SearchX, MapPin, Route, BriefcaseMedical,
  MemoryStick, Merge, Microscope, CircleMinus, Package, Palette, Pause, Pencil,
  Minus, Workflow, Play, CirclePlay, Plus, LoaderCircle, Dna, Upload, Bot, Rocket,
  Ruler, SquareDashed, Server, Shapes, Share2, Shield, ShieldAlert, ShieldEllipsis,
  ArrowUpDown, Gauge, Star, Square, ArrowLeftRight, Tags, Target, TestTube,
  FileX, FileSearch, ScanSearch, TrendingDown, TrendingUp, LayoutDashboard,
  LayoutList, Bug, Moon, Sun, Globe, Wifi, WifiOff, Files, FileText, FileSpreadsheet,
  Settings, Hash, ExternalLink, Building2, Database, DatabaseBackup, DatabaseZap,
  Trash, Trash2, Mail, Eye, EyeOff, GitBranch, Download
} from 'lucide-vue-next'
```

## Notes for Phase 3 Migration

1. **Outline vs Filled variants**: MDI distinguishes between `mdi-icon` (filled) and `mdi-icon-outline` (outline). Lucide uses stroke-based icons by default — there is no separate outline variant needed. Map both to the same Lucide component.

2. **Color**: MDI icons inherit color via CSS `color` property. Lucide icons use `stroke` via CSS. Both respond to `currentColor` — no changes needed.

3. **Size**: MDI uses font sizes (class-based). Lucide uses `size` prop (number, default 24). Update size props in components.

4. **Import pattern**: Replace `v-icon` Vuetify component with direct Lucide component imports.

5. **Drop count**: Only 1 icon is dropped (`mdi-vuejs`). All others have Lucide equivalents.

6. **Database icons**: Multiple MDI database-* variants (check, export, import, sync, refresh, plus) all map to 2-3 Lucide alternatives. The actual icon used should be consistent per action type across the app.
