# Release v1.1.0 Summary

## What We Accomplished

This release represents a major UI/UX refactor focused on improving readability, layout management, and overall user experience of the dashboard.

## Key Changes

### 1. **Card Display System Refactor**
- Implemented two-tier font system for better visual hierarchy:
  - **8pt grey labels** for field names (ICP Batt:, Node Batt:, Ch:, Humidity:, etc.)
  - **11pt bold values** with color coding for data
  - **14pt bold** for node name headers
- Result: Data is now much easier to scan at a glance

### 2. **Layout Fixes**
- **Fixed 3-column layout**: Cards now properly display 3 across in windowed mode
  - Corrected calculation from 430px to 376px per card
  - Window width increased from 1280x720 to 1400x720
- **Column rebalancing**: 100px / 105px / 100px (from 100px / 115px / 90px)
  - Provides adequate space for longer labels like "Node Batt:"
  
### 3. **Restored Features**
- **Ch3 Current Display**: Battery current now visible in middle column
  - Shows ±mA with charge/discharge arrows (↑/↓)
  - Color coded: Green (charging), Orange (discharging)

### 4. **UX Improvements**
- **Dynamic Fullscreen Button**: Shows "Fullscreen" when windowed, "Exit Fullscreen" when fullscreen
  - Button text now indicates the action it will perform
- **Humidity Format**: Changed to "Humidity: XX%" for consistency
- **Pressure Spacing**: Added space between value and "hPa" unit
- **Button Layout**: Node detail window buttons now left-justified

### 5. **Bug Fixes**
- Fixed local node flash color (now restores to dark green, not grey)
- Fixed pressure display glitch with preloaded values
- Removed short name from card line 2 (reserved for status messages)
- Added "Batt" to battery labels for clarity

## Files Changed
- `dashboard.py` - Major refactor of card display system
- `node_detail_window.py` - Button layout improvements
- `CHANGELOG.md` - Created comprehensive changelog
- `VERSION` - Updated from 1.0.14 to 1.1.0

## Git Workflow Completed

1. ✅ Committed all changes to `feature/messaging` branch
2. ✅ Merged `feature/messaging` into `main` branch
3. ✅ Created Git tag `v1.1.0` on main branch
4. ✅ Pushed main branch to origin
5. ✅ Pushed v1.1.0 tag to origin
6. ✅ Pushed updated feature/messaging branch
7. ✅ Returned to `feature/messaging` branch for continued development

## Next Steps

Continue messaging feature development on `feature/messaging` branch. The UI/UX improvements from v1.1.0 are now part of main and will be the foundation for the messaging interface.

## Testing Status

- ✅ Dashboard launches successfully
- ✅ 3-column layout displays correctly in windowed mode
- ✅ Fullscreen toggle button works and updates text
- ✅ All telemetry fields display with new font hierarchy
- ✅ Ch3 Current visible with charge/discharge indicators
- ✅ Pressure display shows proper spacing
- ✅ Node detail window buttons accessible
- ✅ Python 3.14 compatibility verified
- ✅ Matplotlib 3.10.8 working

## Backward Compatibility

All changes are fully backward compatible:
- No configuration file changes required
- CSV logging format unchanged
- Alert system unchanged
- All existing features preserved
