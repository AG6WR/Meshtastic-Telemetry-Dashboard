# Changelog

All notable changes to the Meshtastic Telemetry Dashboard will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.2b] - 2025-12-14

### Fixed
- **Virtual Keyboard Improvements**: Enhanced keyboard behavior on Raspberry Pi touchscreens
  - Fixed keyboard auto-show/hide when focusing text fields
  - Improved key press handling and focus management
  - Better integration with compose message dialog

### Changed
- **Font Standardization**: Changed UI fonts from Liberation Sans Narrow to Liberation Sans 12pt for better readability on touchscreens
  - Buttons now use Liberation Sans 12pt (was Narrow 11pt)
  - Tabs now use Liberation Sans 12pt (was Narrow 12pt)  
  - Implemented global font references instead of hardcoded fonts throughout codebase
- **Dashboard Button Cleanup**: Simplified main button bar
  - Renamed "Node Alerts" to "Alerts"
  - Renamed "Open Logs" to "Logs"
  - Removed "Debug Log" button (accessible via context menu)
  - Removed "Today's CSV" button (accessible via node detail window)
  - Widened "Exit Fullscreen" button for better touch targeting
- **Message Center UI**: Removed emoji icons from Compose/Refresh/Close buttons for cleaner appearance
- **Button Style Consistency**: Standardized Send/Cancel/Compose buttons across all dialogs

## [1.2.0b] - 2025-12-14

### Fixed
- **Context Menu Dismissal**: Restored canvas click handler to properly dismiss menus when clicking blank areas
- **Message Display on Cards**: Added message_label to card_widgets dictionary so incoming message text displays correctly on node cards
- Both fixes restore functionality that was broken in post-merge cleanup commit

### Changed
- Default window size reduced from 1400x720 to 1200x660 for better fit on 1280x720 Raspberry Pi displays

## [1.2.0] - 2025-12-14

### Added
- **Direct Messaging System**: Send and receive private messages between nodes
  - Compose messages with recipient selection
  - View message history per node
  - Message list window showing all conversations
  - Unread message indicators on node cards
  - Message notifications with visual alerts
- **Message Management**: Archive, delete, and mark messages as read/unread
- **Quit Button**: Added dedicated quit button for easier application exit on touch screens

### Fixed
- MessageViewer white window on Pi: Fixed grab_set() timing issue on Linux
- Tkinter cleanup errors: Added proper exception handling and hasattr checks in on_closing()
- Window state management: Improved fullscreen exit behavior

## [1.1.0] - 2025-12-13

### Major UI/UX Refactor
This release represents a significant overhaul of the card display system with improved readability, better layout management, and enhanced user experience.

### Added
- **Dynamic Fullscreen Button**: Button now shows "Fullscreen" when windowed and "Exit Fullscreen" when in fullscreen mode, properly indicating the action it will perform
- **Improved Font Hierarchy**: Implemented two-tier font system for better readability:
  - Labels: 8pt grey text for field names (ICP Batt:, Node Batt:, Ch:, Humidity:, etc.)
  - Values: 11pt bold color-coded text for data values
  - Headers: 14pt bold for node names
- **Battery Current Display Restored**: Ch3 Current now visible in Row 1 Column 2 with:
  - Charge/discharge indicators (↑ for charging, ↓ for discharging)
  - Color coding: Green for charging, Orange for discharging
  - mA units clearly displayed

### Changed
- **Window Geometry**: Default window size increased from 1280x720 to 1400x720 to properly accommodate 3-card-wide layout
- **Card Layout Algorithm**: Fixed calculation to correctly display 3 cards across in windowed mode (was incorrectly showing only 2)
  - Updated from 430px per card to accurate 376px (368px card + 8px padding)
  - Cards now properly utilize available screen space
- **Column Width Rebalancing**: Adjusted internal card column widths for better data display:
  - Row layout: 100px / 105px / 100px (from 100px / 115px / 90px)
  - Provides adequate space for "Node Batt:" label without truncation
  - Maintains balanced appearance across all three columns
- **Humidity Display Format**: Changed from "XX% humidity" to "Humidity: XX%" for consistency with other telemetry fields
- **Pressure Display Spacing**: Added proper space between value and "hPa" unit for improved readability
- **Button Layout in Node Detail Window**: 
  - Row 2 buttons (Close, Forget Node) now left-justified for easier access
  - Consistent left-to-right button flow throughout interface

### Fixed
- **Local Node Flash Color Bug**: Local node cards now correctly restore to dark green background (`bg_local_node`) after flash update instead of grey
- **Short Name Display**: Removed short name from card line 2, which is now reserved exclusively for status messages (motion detected, last heard, etc.)
- **Pressure Display Glitch**: Fixed issue where preloaded pressure values were appearing in the label area during initial card render
- **Card Width Calculation**: Corrected grid layout calculation preventing proper 3-column display in windowed mode
- **Battery Label Clarity**: Added "Batt" suffix to battery labels:
  - "ICP:" → "ICP Batt:"
  - "Node:" → "Node Batt:"

### Technical Details
- **Card Display System**: Complete refactor of telemetry row rendering
- **Font Management**: New `font_card_label` and `font_card_value` definitions in dashboard initialization
- **Color Coding Preserved**: All existing color thresholds maintained (battery levels, SNR, temperature, humidity)
- **Grid Layout**: Fixed `cards_per_row` calculation in both `on_window_resize()` and card display refresh logic

### Performance
- No performance impact - changes are purely visual/layout improvements
- Card flash animation system remains efficient and responsive

### Compatibility
- Fully backward compatible with existing configuration files
- No changes to data logging or CSV format
- No changes to alert system or email notifications
- Python 3.14 compatibility verified with matplotlib 3.10.8

---

## [1.0.0] - Previous Release

Initial stable release with:
- Multi-node monitoring
- Card and table views
- CSV logging
- Alert system
- Node detail windows
- Temperature/humidity/pressure telemetry
- Battery monitoring
- Network statistics (SNR, Channel Util, Air Util)

