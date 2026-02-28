/**
 * MDI-to-Lucide Icon Mapping Module
 *
 * Complete mapping of all MDI icon strings used in the codebase to their
 * Lucide component equivalents. Based on the Phase 1 icon audit
 * (.planning/phases/01-foundation-setup/01-icon-audit.md).
 *
 * Usage:
 *   import { MdiToLucide, resolveMdiIcon } from '@/utils/icons'
 *   // Direct component import for templates:
 *   import { Search, Filter, Dna } from 'lucide-vue-next'
 */

import type { Component } from 'vue'
import {
  AlertTriangle,
  AlarmClockCheck,
  ArrowLeft,
  ArrowLeftRight,
  ArrowRight,
  ArrowUpDown,
  Atom,
  Award,
  BadgeCheck,
  Ban,
  BookOpen,
  Bot,
  BriefcaseBusiness,
  BriefcaseMedical,
  Bug,
  Building,
  Building2,
  Calendar,
  CalendarCheck,
  CalendarClock,
  ChartBar,
  ChartBarBig,
  ChartLine,
  ChartScatter,
  ChartSpline,
  Check,
  CheckCheck,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  Circle,
  CircleAlert,
  CircleCheck,
  CircleCheckBig,
  CircleHelp,
  CircleMinus,
  CirclePlay,
  CircleUser,
  CircleX,
  Clock,
  Clock4,
  ClockAlert,
  Cloud,
  CloudUpload,
  Code,
  Cog,
  Compass,
  Copy,
  Database,
  DatabaseBackup,
  DatabaseZap,
  Dna,
  Download,
  EllipsisVertical,
  Eraser,
  Expand,
  ExternalLink,
  Eye,
  EyeOff,
  FileJson,
  FileSearch,
  FileSpreadsheet,
  FileText,
  FileX,
  Files,
  Filter,
  FilterX,
  Flame,
  Folder,
  Gauge,
  GitBranch,
  Github,
  Globe,
  HardDrive,
  Hash,
  HeartPulse,
  History,
  Home,
  Hospital,
  IdCard,
  Info,
  KeyRound,
  LayoutDashboard,
  LayoutList,
  Library,
  Lightbulb,
  Link,
  List,
  ListChecks,
  LoaderCircle,
  Lock,
  LockKeyholeOpen,
  LogIn,
  LogOut,
  Mail,
  MapPin,
  MemoryStick,
  Merge,
  Microscope,
  Minus,
  Moon,
  MoveHorizontal,
  Network,
  OctagonX,
  Package,
  Palette,
  Pause,
  Pencil,
  Play,
  PlayCircle,
  Plus,
  RefreshCcw,
  RefreshCw,
  Rocket,
  RotateCw,
  Route,
  Ruler,
  ScanSearch,
  Search,
  SearchX,
  Server,
  Settings,
  Shapes,
  Share2,
  ShieldAlert,
  ShieldCheck,
  ShieldEllipsis,
  SlidersHorizontal,
  Square,
  SquareArrowLeft,
  SquareArrowRight,
  SquareDashed,
  SquarePlus,
  Star,
  Stethoscope,
  Sun,
  Tags,
  Target,
  TestTube,
  Trash,
  Trash2,
  TrendingDown,
  TrendingUp,
  Upload,
  User,
  UserCheck,
  UserCog,
  UserPlus,
  UserSearch,
  UserX,
  Users,
  Wifi,
  WifiOff,
  Workflow,
  X,
  Zap,
  ZoomIn,
  ZoomOut
} from 'lucide-vue-next'

/**
 * Complete MDI icon name → Lucide component mapping (197 entries).
 * Keys are mdi-* strings as used in Vuetify templates.
 * Values are Lucide Vue components for direct rendering.
 */
export const MdiToLucide: Record<string, Component> = {
  // Account / User icons
  'mdi-account': User,
  'mdi-account-check': UserCheck,
  'mdi-account-circle': CircleUser,
  'mdi-account-details': UserCog,
  'mdi-account-group': Users,
  'mdi-account-off': UserX,
  'mdi-account-plus': UserPlus,
  'mdi-account-search': UserSearch,
  'mdi-account-tie': BriefcaseBusiness,

  // Alert icons
  'mdi-alert': AlertTriangle,
  'mdi-alert-circle': CircleAlert,
  'mdi-alert-circle-outline': CircleAlert,

  // API / Code
  'mdi-api': Code,

  // Arrow icons
  'mdi-arrow-left': ArrowLeft,
  'mdi-arrow-left-bold-box': SquareArrowLeft,
  'mdi-arrow-right': ArrowRight,
  'mdi-arrow-right-bold-box': SquareArrowRight,

  // Science / Biology
  'mdi-atom': Atom,
  'mdi-dna': Dna,
  'mdi-microscope': Microscope,
  'mdi-molecule': Atom,
  'mdi-protein': Dna,
  'mdi-test-tube': TestTube,

  // Book / Literature
  'mdi-book-open': BookOpen,
  'mdi-book-open-page-variant': BookOpen,
  'mdi-book-open-variant': BookOpen,
  'mdi-bookshelf': Library,

  // Action icons
  'mdi-broom': Eraser,
  'mdi-cached': RefreshCw,
  'mdi-cancel': Ban,

  // Calendar
  'mdi-calendar': Calendar,
  'mdi-calendar-check': CalendarCheck,
  'mdi-calendar-clock': CalendarClock,

  // Certificate / Award
  'mdi-certificate': Award,

  // Chart icons
  'mdi-chart-bar': ChartBar,
  'mdi-chart-bell-curve': ChartSpline,
  'mdi-chart-box': ChartBarBig,
  'mdi-chart-box-outline': ChartBarBig,
  'mdi-chart-donut': Circle,
  'mdi-chart-line': ChartLine,
  'mdi-chart-scatter-plot': ChartScatter,
  'mdi-chart-scatter-plot-hexbin': ChartScatter,

  // Check icons
  'mdi-check': Check,
  'mdi-check-all': CheckCheck,
  'mdi-check-bold': Check,
  'mdi-check-circle': CircleCheck,
  'mdi-check-circle-outline': CircleCheckBig,
  'mdi-check-decagram': BadgeCheck,
  'mdi-checkbox-multiple-marked': ListChecks,

  // Chevron icons
  'mdi-chevron-down': ChevronDown,
  'mdi-chevron-left': ChevronLeft,
  'mdi-chevron-right': ChevronRight,
  'mdi-chevron-up': ChevronUp,

  // Circle
  'mdi-circle': Circle,

  // Clock icons
  'mdi-clock-alert': ClockAlert,
  'mdi-clock-check': AlarmClockCheck,
  'mdi-clock-outline': Clock,
  'mdi-clock-time-four': Clock4,

  // Close / X icons
  'mdi-close': X,
  'mdi-close-circle': CircleX,
  'mdi-close-octagon': OctagonX,

  // Cloud
  'mdi-cloud-outline': Cloud,
  'mdi-cloud-upload': CloudUpload,

  // Code
  'mdi-code-json': FileJson,
  'mdi-code-tags': Code,

  // Settings / Cog
  'mdi-cog': Cog,
  'mdi-cog-outline': Settings,

  // Compass
  'mdi-compass': Compass,

  // Copy
  'mdi-content-copy': Copy,

  // Counter / Hash
  'mdi-counter': Hash,
  'mdi-numeric': Hash,

  // Database icons
  'mdi-database': Database,
  'mdi-database-check': DatabaseZap,
  'mdi-database-export': DatabaseBackup,
  'mdi-database-import': DatabaseZap,
  'mdi-database-off-outline': Database,
  'mdi-database-outline': Database,
  'mdi-database-plus': DatabaseZap,
  'mdi-database-refresh': RefreshCw,
  'mdi-database-search': Search,
  'mdi-database-sync': RefreshCw,

  // Delete
  'mdi-delete': Trash2,
  'mdi-delete-sweep': Trash,

  // Domain / Building
  'mdi-domain': Building2,

  // Dots / Ellipsis
  'mdi-dots-vertical': EllipsisVertical,

  // Download
  'mdi-download': Download,

  // Email
  'mdi-email': Mail,

  // Export / Upload
  'mdi-export': Upload,
  'mdi-publish': Upload,
  'mdi-upload': Upload,

  // Eye
  'mdi-eye': Eye,
  'mdi-eye-off': EyeOff,

  // Family / Tree
  'mdi-family-tree': GitBranch,

  // Feature search
  'mdi-feature-search': ScanSearch,
  'mdi-text-search': ScanSearch,

  // File icons
  'mdi-file-delimited': FileSpreadsheet,
  'mdi-file-document': FileText,
  'mdi-file-document-multiple': Files,
  'mdi-file-document-outline': FileText,
  'mdi-file-search': FileSearch,
  'mdi-text-box-remove-outline': FileX,
  'mdi-text-box-search-outline': FileSearch,

  // Filter icons
  'mdi-filter': Filter,
  'mdi-filter-off': FilterX,
  'mdi-filter-outline': Filter,
  'mdi-filter-remove': FilterX,
  'mdi-filter-variant': SlidersHorizontal,

  // Fire / Flame
  'mdi-fire': Flame,

  // Fit / Expand
  'mdi-fit-to-screen': Expand,

  // Folder
  'mdi-folder-multiple': Folder,

  // Format / List
  'mdi-format-list-bulleted': List,

  // Gesture
  'mdi-gesture-swipe-horizontal': MoveHorizontal,

  // GitHub
  'mdi-github': Github,

  // Graph / Network
  'mdi-graph': Network,
  'mdi-graph-outline': Network,
  'mdi-transit-connection-variant': Network,

  // Hardware
  'mdi-harddisk': HardDrive,
  'mdi-memory': MemoryStick,
  'mdi-server': Server,

  // Health / Medical
  'mdi-heart-pulse': HeartPulse,
  'mdi-hospital': Hospital,
  'mdi-hospital-box': Stethoscope,
  'mdi-hospital-building': Building,
  'mdi-medical-bag': BriefcaseMedical,

  // Help
  'mdi-help-circle': CircleHelp,
  'mdi-help-circle-outline': CircleHelp,

  // History
  'mdi-history': History,

  // Home
  'mdi-home': Home,

  // Human
  'mdi-human': User,

  // Identifier
  'mdi-identifier': IdCard,

  // Information
  'mdi-information': Info,
  'mdi-information-outline': Info,

  // Lightbulb
  'mdi-lightbulb': Lightbulb,

  // Lightning / Zap
  'mdi-lightning-bolt': Zap,

  // Link
  'mdi-link': Link,

  // Lock / Security
  'mdi-lock': Lock,
  'mdi-lock-check': ShieldCheck,
  'mdi-lock-plus': LockKeyholeOpen,
  'mdi-lock-reset': KeyRound,

  // Login / Logout
  'mdi-login': LogIn,
  'mdi-logout': LogOut,

  // Magnify / Search
  'mdi-magnify': Search,
  'mdi-magnify-minus-outline': ZoomOut,
  'mdi-magnify-plus-outline': ZoomIn,
  'mdi-magnify-remove-outline': SearchX,

  // Map
  'mdi-map-marker': MapPin,
  'mdi-map-marker-distance': Route,

  // Merge
  'mdi-merge': Merge,

  // Minus
  'mdi-minus-circle': CircleMinus,

  // New
  'mdi-new-box': SquarePlus,

  // Open in new
  'mdi-open-in-new': ExternalLink,

  // Package
  'mdi-package-variant': Package,

  // Palette
  'mdi-palette': Palette,

  // Pause
  'mdi-pause': Pause,

  // Pencil / Edit
  'mdi-pencil': Pencil,

  // Pipe / Pipeline
  'mdi-pipe': Minus,
  'mdi-pipeline': Workflow,

  // Play
  'mdi-play': Play,
  'mdi-play-circle': CirclePlay,
  'mdi-play-pause': PlayCircle,

  // Plus
  'mdi-plus': Plus,

  // Progress
  'mdi-progress-clock': LoaderCircle,

  // Refresh / Update
  'mdi-refresh': RefreshCw,
  'mdi-refresh-auto': RefreshCcw,
  'mdi-restart-alert': RotateCw,
  'mdi-update': RefreshCw,

  // Robot
  'mdi-robot': Bot,

  // Rocket
  'mdi-rocket-launch': Rocket,

  // Ruler
  'mdi-ruler': Ruler,

  // Select
  'mdi-select-all': SquareDashed,

  // Shape
  'mdi-shape': Shapes,

  // Share
  'mdi-share-variant': Share2,

  // Shield
  'mdi-shield-account': ShieldCheck,
  'mdi-shield-check': ShieldCheck,
  'mdi-shield-crown': ShieldEllipsis,
  'mdi-shield-lock': ShieldAlert,

  // Sort
  'mdi-sort': ArrowUpDown,
  'mdi-sort-numeric-descending': ArrowUpDown,

  // Speedometer
  'mdi-speedometer': Gauge,

  // Star
  'mdi-star': Star,
  'mdi-star-outline': Star,

  // Stop
  'mdi-stop': Square,

  // Swap
  'mdi-swap-horizontal': ArrowLeftRight,

  // Tag
  'mdi-tag-multiple': Tags,

  // Target
  'mdi-target': Target,

  // Trending
  'mdi-trending-down': TrendingDown,
  'mdi-trending-up': TrendingUp,

  // View
  'mdi-view-dashboard': LayoutDashboard,
  'mdi-view-dashboard-variant': LayoutDashboard,
  'mdi-view-list': LayoutList,

  // Virus (no Lucide equivalent — use Bug)
  'mdi-virus': Bug,
  'mdi-virus-outline': Bug,

  // Weather
  'mdi-weather-night': Moon,
  'mdi-weather-sunny': Sun,

  // Web
  'mdi-web': Globe,

  // Wifi
  'mdi-wifi': Wifi,
  'mdi-wifi-off': WifiOff
}

/** Resolve an mdi-* string to a Lucide component (returns null if not found) */
export function resolveMdiIcon(mdiName: string): Component | null {
  return MdiToLucide[mdiName] ?? null
}

// Re-export all Lucide components used in the mapping for direct import convenience
export {
  AlertTriangle,
  AlarmClockCheck,
  ArrowLeft,
  ArrowLeftRight,
  ArrowRight,
  ArrowUpDown,
  Atom,
  Award,
  BadgeCheck,
  Ban,
  BookOpen,
  Bot,
  BriefcaseBusiness,
  BriefcaseMedical,
  Bug,
  Building,
  Building2,
  Calendar,
  CalendarCheck,
  CalendarClock,
  ChartBar,
  ChartBarBig,
  ChartLine,
  ChartScatter,
  ChartSpline,
  Check,
  CheckCheck,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  Circle,
  CircleAlert,
  CircleCheck,
  CircleCheckBig,
  CircleHelp,
  CircleMinus,
  CirclePlay,
  CircleUser,
  CircleX,
  Clock,
  Clock4,
  ClockAlert,
  Cloud,
  CloudUpload,
  Code,
  Cog,
  Compass,
  Copy,
  Database,
  DatabaseBackup,
  DatabaseZap,
  Dna,
  Download,
  EllipsisVertical,
  Eraser,
  Expand,
  ExternalLink,
  Eye,
  EyeOff,
  FileJson,
  FileSearch,
  FileSpreadsheet,
  FileText,
  FileX,
  Files,
  Filter,
  FilterX,
  Flame,
  Folder,
  Gauge,
  GitBranch,
  Github,
  Globe,
  HardDrive,
  Hash,
  HeartPulse,
  History,
  Home,
  Hospital,
  IdCard,
  Info,
  KeyRound,
  LayoutDashboard,
  LayoutList,
  Library,
  Lightbulb,
  Link,
  List,
  ListChecks,
  LoaderCircle,
  Lock,
  LockKeyholeOpen,
  LogIn,
  LogOut,
  Mail,
  MapPin,
  MemoryStick,
  Merge,
  Microscope,
  Minus,
  Moon,
  MoveHorizontal,
  Network,
  OctagonX,
  Package,
  Palette,
  Pause,
  Pencil,
  Play,
  PlayCircle,
  Plus,
  RefreshCcw,
  RefreshCw,
  Rocket,
  RotateCw,
  Route,
  Ruler,
  ScanSearch,
  Search,
  SearchX,
  Server,
  Settings,
  Shapes,
  Share2,
  ShieldAlert,
  ShieldCheck,
  ShieldEllipsis,
  SlidersHorizontal,
  Square,
  SquareArrowLeft,
  SquareArrowRight,
  SquareDashed,
  SquarePlus,
  Star,
  Stethoscope,
  Sun,
  Tags,
  Target,
  TestTube,
  Trash,
  Trash2,
  TrendingDown,
  TrendingUp,
  Upload,
  User,
  UserCheck,
  UserCog,
  UserPlus,
  UserSearch,
  UserX,
  Users,
  Wifi,
  WifiOff,
  Workflow,
  X,
  Zap,
  ZoomIn,
  ZoomOut
} from 'lucide-vue-next'
