# Window Positioner

## Manage window layouts and apply manual overrides

### This script provides a GUI to:
1. Load and apply window layout configurations (position, size, always-on-top, title bar)
   from '.ini' files.
2. Manually select any window to make it always-on-top and remove its title bar.

### Features:
- Load and apply window configurations from 'config_*.ini' files.
- Visual preview of the selected configuration's layout.
- Periodic check to maintain the state of configured windows (when a config is applied).
- Manually select any window via button click to make it Always-on-Top and remove its title bar.
- Reset all applied settings (config or manual) using the 'Cancel/reset settings' button.
- Toggle Always-on-Top state specifically for windows managed by the *currently applied config*.
- Support for multiple configuration files.

### Usage:
1. Place configuration files named ***'config_\<name\>.ini'*** in the program directory.
2. Select a configuration from the dropdown menu to preview its layout.
3. Click 'Apply config' to activate the window layout defined in the selected config file.
   - A periodic check starts to maintain the state of these configured windows.
4. Click 'Select Window', then click on any target window on your screen.
   - This makes the selected window Always-on-Top and removes its title bar.
   - Entering selection mode stops any active configuration and periodic checks, and resets previously managed windows.
   - Applying a config or selecting a *new* window resets the previously *manually* selected one.
5. Click 'Cancel/reset settings':
   - If in 'Select Window' mode, it cancels the selection process.
   - It resets *all* windows currently managed (by config or manual selection) to their default state (Always-on-Top removed, title bar restored).
   - It re-enables all buttons.
6. Use 'Toggle Always-on-Top' to change the state of windows managed by the *currently applied config*. (Button is enabled only when a config with always-on-top windows is active).

### Configuration Format (***'config_\<name\>.ini'***):
```
[Window Title]
position = x,y              # Window position (optional)
size = width,height         # Window size (optional)
always_on_top = true/false  # Set always-on-top state (optional, default false)
titlebar = true/false       # Keep title bar (optional, default true)
```
#### Example:
```
[Microsoft Edge]
position = -7,0
size = 1722,1400
always_on_top = true
titlebar = false

[Infinity Nikki]
position = 1708,0
size = 2560,1440
always_on_top = true
titlebar = false

[Discord]
position = 4268,0
size = 852,1392
always_on_top = false
titlebar = true
```

### Notes:
- Windows without position/size in config will be auto-arranged based on screen size.
- Window titles in config are matched partially and case-insensitively against open windows.
