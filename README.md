# Window Positioner

## Manage window layouts and apply manual overrides

### This script provides a GUI to:
1. Load and apply window layout configurations (position, size, always-on-top, title bar)
   from '.ini' files.
2. Manually select any window to make it always-on-top and remove its title bar.

### Features:
- Load and apply window configurations from 'config_*.ini' files.
- Visual preview of the selected configuration's layout.
- Manually select any window via button click to make it Always-on-Top and remove its title bar.
- Reset all applied settings (config or manual) using the 'Cancel/reset settings' button.
- Toggle Always-on-Top state specifically for windows managed by the *currently applied config*.
- Support for multiple configuration files.
- Config creation through GUI

### Usage:
#### Create config
1. Click the "Create config" button while your applications are running
2. Select the application windows you would like to manage in the list and click "Confirm selection"
3. Choose the settings you want, type a config name and click "Save config"

#### Load config
1. Select a configuration from the dropdown menu to preview its layout.
2. Click 'Apply config' to activate the window layout defined in the selected config file.
- To reset the settings, click "Cancel/reset settings"
- Use 'Toggle Always-on-Top' to change the state of windows managed by the *currently applied config*.

#### Edit settings
1. Click the "Open Config Folder" button
2. Open the config file you want to edit in notepad and adjust values
3. Save the config file and close notepad

#### Delete settings
1. Click the "Open Config Folder" button
2. Delete the config file

#### Single window use
- Click 'Select Window', then click on any target window on your screen.
   - This makes the selected window Always-on-Top and removes its title bar.
   - Entering selection mode stops any active configuration and periodic checks, and resets previously managed windows.
   - Applying a config or selecting a *new* window resets the previously *manually* selected one.

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

[Final Fantasy XIV]
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
- This application is made with ultrawide monitors in mind and may ***not*** work well with:
   - multi-monitor setups with different resolutions
   ```
   +-----------------------+ 
   |                       | +---------------------+
   |                       | |                     |
   | Monitor 1             | | Monitor 2           |
   | 1920x1080             | | 1280x1024           |
   |                       | |                     |
   +-----------------------+ +---------------------+
   ```
   - multi-monitor setups with vertical positioning
   ```
   +-----------------------+ 
   |                       |
   |                       |
   | Monitor 1             |
   | 1920x1080             |
   |                       |
   +-----------------------+
   +-----------------------+ 
   |                       |
   |                       |
   | Monitor 2             |
   | 1920x1080             |
   |                       |
   +-----------------------+
   ```
- *Should* work well with similar monitors in a left to right setup, but not tested:
   ```
   +-----------------------+ +-----------------------+ +-----------------------+
   |                       | |                       | |                       |
   |                       | |                       | |                       |
   | Monitor 1 = 1920x1080 | | Monitor 2 = 1920x1080 | | Monitor 3 = 1920x1080 |
   |                       | |                       | |                       |
   |                       | |                       | |                       |
   +-----------------------+ +-----------------------+ +-----------------------+
   ```
- Windows without position/size in config will be auto-arranged based on screen size.
- Window titles in config are matched partially and case-insensitively against open windows.
