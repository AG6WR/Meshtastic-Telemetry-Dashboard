# Architecture Overview

## Current Structure (Before Refactoring)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           dashboard.py (~4050 lines)                        │
│                              "God Object"                                   │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ EnhancedDashboard class contains EVERYTHING:                          │  │
│  │                                                                       │  │
│  │  • Window setup & layout          • Message protocol parsing          │  │
│  │  • Color definitions              • Notification banners              │  │
│  │  • Font definitions               • Card rendering (800+ lines)       │  │
│  │  • Button handlers                • Table rendering                   │  │
│  │  • State management               • Temperature conversion            │  │
│  │  • Refresh logic                  • Voltage/battery formatting        │  │
│  │  • Card click handlers            • SNR color calculation             │  │
│  │  • Context menus                  • Duration formatting               │  │
│  │  • Settings dialog (600 lines)    • Fullscreen toggle                 │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
        │
        │ imports & uses
        ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                          Supporting Modules                                   │
│                                                                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐               │
│  │ config_manager  │  │ data_collector  │  │connection_manager│              │
│  │    (170 lines)  │  │   (841 lines)   │  │   (441 lines)   │               │
│  │                 │  │                 │  │                 │               │
│  │ • Load/save JSON│  │ • Packet parsing│  │ • TCP/Serial    │               │
│  │ • Dot notation  │  │ • CSV logging   │  │ • Auto-reconnect│               │
│  │   access        │  │ • pubsub events │  │                 │               │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘               │
│                                                                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐               │
│  │ message_manager │  │  alert_system   │  │    plotter      │               │
│  │   (360 lines)   │  │   (310 lines)   │  │   (623 lines)   │               │
│  │                 │  │                 │  │                 │               │
│  │ • JSON storage  │  │ • Alert rules   │  │ • Matplotlib    │               │
│  │ • Retrieval     │  │ • Email alerts  │  │ • CSV loading   │               │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘               │
│                                                                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐               │
│  │ card_field_     │  │ virtual_        │  │                 │               │
│  │ registry        │  │ keyboard        │  │                 │               │
│  │   (171 lines)   │  │                 │  │                 │               │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘               │
└───────────────────────────────────────────────────────────────────────────────┘
        │
        │ imports & uses
        ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                        Tkinter UI Windows (Modal Dialogs)                     │
│                                                                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐               │
│  │node_detail_     │  │ message_dialog  │  │ message_viewer  │               │
│  │window (650 ln)  │  │   (340 lines)   │  │   (297 lines)   │               │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘               │
│                                                                               │
│  ┌─────────────────────────────────────────┐                                 │
│  │     message_list_window (701 lines)     │                                 │
│  │         "Message Center"                │                                 │
│  └─────────────────────────────────────────┘                                 │
└───────────────────────────────────────────────────────────────────────────────┘
```

### Problems with Current Structure:

1. **dashboard.py is too big** - 4050 lines, impossible to navigate
2. **Mixed concerns** - UI code mixed with business logic
3. **Hard to test** - Can't test formatting without launching GUI
4. **Hard to port** - Qt rewrite requires rewriting everything at once
5. **Duplicated logic** - Same formatting code in multiple places

---

## Proposed Structure (After Refactoring)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              APPLICATION LAYER                              │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    dashboard.py (~1500 lines)                         │  │
│  │                    "Orchestrator Only"                                │  │
│  │                                                                       │  │
│  │  • Window setup & main layout    • Event routing                      │  │
│  │  • Startup/shutdown              • Refresh scheduling                 │  │
│  │  • View mode switching           • pubsub subscriptions               │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│              │                    │                     │                   │
│              │ uses               │ uses                │ uses              │
│              ▼                    ▼                     ▼                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │ dashboard_state │  │ settings_dialog │  │     UI Renderers            │  │
│  │   (new file)    │  │   (extracted)   │  │  ┌─────────────────────┐    │  │
│  │                 │  │   (~600 lines)  │  │  │ card_renderer.py    │    │  │
│  │ • nodes_data    │  │                 │  │  │ (card creation)     │    │  │
│  │ • selected_node │  │ • All settings  │  │  └─────────────────────┘    │  │
│  │ • view_mode     │  │   tabs/fields   │  │  ┌─────────────────────┐    │  │
│  │ • unread_msgs   │  │ • Validation    │  │  │ table_renderer.py   │    │  │
│  │ • flash_state   │  │ • Apply/Cancel  │  │  │ (table view)        │    │  │
│  └─────────────────┘  └─────────────────┘  │  └─────────────────────┘    │  │
│                                            └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ imports
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            BUSINESS LOGIC LAYER                             │
│                         (Framework-Independent)                             │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │   formatters    │  │message_protocol │  │   theme         │             │
│  │   (new file)    │  │   (new file)    │  │   (new file)    │             │
│  │                 │  │                 │  │                 │             │
│  │ • format_       │  │ • parse_message │  │ • colors dict   │             │
│  │   duration()    │  │ • parse_receipt │  │ • get_color()   │             │
│  │ • format_       │  │ • format_       │  │ • font specs    │             │
│  │   time_ago()    │  │   outgoing()    │  │                 │             │
│  │ • convert_      │  │ • is_structured │  │                 │             │
│  │   temperature() │  │                 │  │                 │             │
│  │ • get_voltage_  │  │                 │  │                 │             │
│  │   display()     │  │                 │  │                 │             │
│  │ • get_battery_  │  │                 │  │                 │             │
│  │   percentage()  │  │                 │  │                 │             │
│  │ • get_snr_      │  │                 │  │                 │             │
│  │   bar_colors()  │  │                 │  │                 │             │
│  │ • get_*_color() │  │                 │  │                 │             │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ imports
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA LAYER                                     │
│                    (Already Well-Structured - No Changes)                   │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │ config_manager  │  │ data_collector  │  │connection_manager│            │
│  │       ✅        │  │       ✅        │  │       ✅        │             │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘             │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │ message_manager │  │  alert_system   │  │    plotter      │             │
│  │       ✅        │  │       ✅        │  │       ✅        │             │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ imports
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TKINTER UI WINDOWS                                  │
│                   (Keep for now, replace with Qt later)                     │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │node_detail_     │  │ message_dialog  │  │ message_viewer  │             │
│  │window           │  │                 │  │                 │             │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘             │
│                                                                             │
│  ┌──────────────────────────────────────┐  ┌─────────────────┐             │
│  │     message_list_window              │  │ virtual_keyboard│             │
│  └──────────────────────────────────────┘  └─────────────────┘             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram

```
                    ┌─────────────────┐
                    │   Meshtastic    │
                    │     Radio       │
                    └────────┬────────┘
                             │ packets
                             ▼
                    ┌─────────────────┐
                    │  connection_    │
                    │    manager      │
                    │  (TCP/Serial)   │
                    └────────┬────────┘
                             │ raw data
                             ▼
                    ┌─────────────────┐
                    │ data_collector  │──────────────┐
                    │                 │              │
                    │ • Parse packets │              │ CSV
                    │ • Extract telem │              │ logging
                    │ • Cache nodes   │              │
                    └────────┬────────┘              ▼
                             │                 ┌──────────┐
                             │ pubsub          │  logs/   │
                             │ "data.changed"  │  *.csv   │
                             ▼                 └──────────┘
┌────────────────────────────────────────────────────────────────────────┐
│                          dashboard.py                                  │
│                                                                        │
│   on_data_changed() ─────────────────────────────────────────────┐    │
│         │                                                         │    │
│         ▼                                                         │    │
│   ┌───────────┐    ┌────────────┐    ┌─────────────┐             │    │
│   │  State    │───▶│ formatters │───▶│  Renderer   │─────────────┤    │
│   │  Object   │    │            │    │(card/table) │             │    │
│   └───────────┘    └────────────┘    └─────────────┘             │    │
│                                              │                    │    │
│                                              ▼                    │    │
│                                     ┌─────────────────┐          │    │
│                                     │   Tkinter UI    │◀─────────┘    │
│                                     │   (or Qt UI)    │               │
│                                     └─────────────────┘               │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Module Extraction Order

```
Phase 1: Pure Functions (Zero Risk)
════════════════════════════════════

  dashboard.py                           formatters.py (NEW)
  ┌─────────────────┐                   ┌─────────────────┐
  │                 │    EXTRACT        │                 │
  │ format_duration │ ──────────────▶   │ format_duration │
  │ format_time_ago │                   │ format_time_ago │
  │ convert_temp    │                   │ convert_temp    │
  │ get_*_color()   │                   │ get_*_color()   │
  │ get_*_display() │                   │ get_*_display() │
  │                 │                   │                 │
  └─────────────────┘                   └─────────────────┘


Phase 2: Self-Contained Class
════════════════════════════════════

  dashboard.py                           settings_dialog.py (NEW)
  ┌─────────────────┐                   ┌─────────────────┐
  │                 │    EXTRACT        │                 │
  │ SettingsDialog  │ ──────────────▶   │ SettingsDialog  │
  │ (600 lines)     │                   │ (entire class)  │
  │                 │                   │                 │
  └─────────────────┘                   └─────────────────┘


Phase 3: Message Protocol
════════════════════════════════════

  dashboard.py                           message_protocol.py (NEW)
  ┌─────────────────┐                   ┌─────────────────┐
  │                 │    EXTRACT        │                 │
  │ _parse_message  │ ──────────────▶   │ parse_message   │
  │ _parse_receipt  │                   │ parse_receipt   │
  │ _format_outgoing│                   │ format_outgoing │
  │                 │                   │                 │
  └─────────────────┘                   └─────────────────┘


Phase 4: Application State
════════════════════════════════════

  dashboard.py                           dashboard_state.py (NEW)
  ┌─────────────────┐                   ┌─────────────────┐
  │                 │    EXTRACT        │ @dataclass      │
  │ self.nodes = {} │ ──────────────▶   │ class State:    │
  │ self.selected.. │                   │   nodes_data    │
  │ self.view_mode  │                   │   selected_node │
  │ self.unread_... │                   │   view_mode     │
  │                 │                   │   unread_msgs   │
  └─────────────────┘                   └─────────────────┘
```

---

## Qt Migration Path

```
After Refactoring (main branch):
═══════════════════════════════

┌──────────────────────────────────────────────────────────────────────┐
│                         SHARED CODE                                  │
│              (Works with both Tkinter AND Qt)                        │
│                                                                      │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐        │
│  │ formatters │ │ message_   │ │ dashboard_ │ │   theme    │        │
│  │            │ │ protocol   │ │   state    │ │            │        │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘        │
│                                                                      │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐        │
│  │  config_   │ │   data_    │ │ connection_│ │  message_  │        │
│  │  manager   │ │ collector  │ │  manager   │ │  manager   │        │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘        │
│                                                                      │
│  ┌────────────┐ ┌────────────┐                                      │
│  │   alert_   │ │  plotter   │                                      │
│  │   system   │ │            │                                      │
│  └────────────┘ └────────────┘                                      │
└──────────────────────────────────────────────────────────────────────┘
                    │                           │
         ┌──────────┴──────────┐     ┌──────────┴──────────┐
         ▼                     ▼     ▼                     ▼
┌─────────────────────┐  ┌─────────────────────┐
│   Tkinter UI        │  │      Qt UI          │
│   (main branch)     │  │   (UI/QT branch)    │
│                     │  │                     │
│ • dashboard.py      │  │ • dashboard_qt.py   │
│ • node_detail_      │  │ • node_detail_qt.py │
│   window.py         │  │                     │
│ • message_dialog.py │  │ • message_dialog_   │
│ • message_viewer.py │  │   qt.py             │
│ • message_list_     │  │ • ...               │
│   window.py         │  │                     │
│ • settings_dialog.py│  │ • settings_qt.py    │
└─────────────────────┘  └─────────────────────┘
```

---

## File Size Comparison

```
BEFORE (Current):
═════════════════
dashboard.py        ████████████████████████████████████████  4050 lines
data_collector.py   ████████                                   841 lines
message_list_window ███████                                    701 lines
node_detail_window  ██████                                     650 lines
plotter.py          ██████                                     623 lines
connection_manager  ████                                       441 lines
message_manager.py  ███                                        360 lines
message_dialog.py   ███                                        340 lines
alert_system.py     ███                                        310 lines
message_viewer.py   ██                                         297 lines
card_field_registry █                                          171 lines
config_manager.py   █                                          170 lines


AFTER (Proposed):
═════════════════
dashboard.py        ███████████████                           1500 lines (orchestration only)
card_renderer.py    ████████                                   800 lines (extracted)
settings_dialog.py  ██████                                     600 lines (extracted)
formatters.py       ██                                         250 lines (extracted)
message_protocol.py █                                          100 lines (extracted)
dashboard_state.py  █                                           80 lines (extracted)
theme.py            █                                           80 lines (extracted)
                                                              ─────
                                                    Total:    3410 lines (same code, better organized)
```

---

## Benefits Summary

| Aspect | Before | After |
|--------|--------|-------|
| **Largest file** | 4050 lines | 1500 lines |
| **Testability** | Must launch GUI | Can unit test formatters |
| **Qt port effort** | Rewrite everything | Replace UI layer only |
| **Finding code** | Search 4000 lines | Go to specific module |
| **Bug isolation** | "Somewhere in dashboard.py" | "In formatters.py" |
| **Team work** | Merge conflicts | Work on separate files |
