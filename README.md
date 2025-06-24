# Window Positioner

## Manage window layouts and apply manual overrides

#### This application provides a GUI to load and apply window layout configurations (position, size, always-on-top, title bar) from '.ini' files.

### Features:
- Load and apply window configurations from 'config_*.ini' files.
- Visual preview of the selected configuration's layout.
- Optional screenshot view mode
   - Screenshots can be automatically downloaded by the application using the "Download images" button
   - You can also add your own screenshots to the image folder
- Toggle Always-on-Top state specifically for windows managed by the *currently applied config*.
- Support for multiple configuration files.
- Config creation through GUI
- Compact GUI mode available

## Main window
<img src="https://i.ibb.co/PX7pNg7/Skjermbilde-2025-06-24-222015.png" alt="Main window">

## Main window screenshot mode
<img src="https://i.ibb.co/yBYNGPj0/Skjermbilde-2025-06-24-222054.png" alt="Main window screenshot mode">

## Main window compact mode
<img src="https://i.ibb.co/S4C17W71/Skjermbilde-2025-06-24-222105.png" alt="Compact mode">

## Config window
<img src="https://i.ibb.co/n8QPQ8cB/Skjermbilde-2025-06-24-222144.png" alt="Create config">


## Usage:
### Create config
1. Click the "Create config" button while your applications are running
2. Select the application windows you would like to manage in the list and click "Confirm selection"
3. Choose the settings you want, type a config name and click "Save config"
   - Choosing an existing file name will overwrite the previous config

#### Auto align
- 1 window:
   - Will expand to entire screen
- 2 windows:
   - Will toggle through 4 predefined layouts for 16/9 and 21/9
- 3 windows:
   - Will toggle through 4 predefined layouts for 16/9 and 21/9
- 4 windows:
   - Will evenly space out all the windows

#### Update drawing
- Will update the screen layout drawing with the current settings

## Apply config
1. Select a configuration from the dropdown menu to preview its layout.
2. Click 'Apply config' to activate the window layout defined in the selected config file.

## Reset config
- Resets currently loaded configuration
## Toggle AOT
- Change the state of windows managed by the *currently applied config*.

## Delete config
1. Select the config from the dropdown
2. Click "Delete config"
3. Click "Yes" in the confirmation window
- You can also manually delete the files from the config folder

## Manually edit settings
1. Click the "Open Config Folder" button
2. Open the config file you want to edit in notepad and adjust values
3. Save the config file and close notepad
- Useful for adding search_title override

## Compact mode
- Click the "Toggle compact" to switch between full and compact mode

## Change theme
- Click the "Change theme" button to toggle between dark and light mode

## Take screenshots
- This button will take a screenshot of all detected windows from the currently selected configuration and use them for the GUI

## Download images
- This button will download screentshots from IGDB and use them for the GUI
- The "Download images" function requires IGDB Client ID and Client Secret to work. These are not included.

## Toggle images
- Switch between basic and screenshot layout

## Configuration Format (***'config_\<name\>.ini'***):
```
[Window Title]
position = x,y              # Window position
size = width,height         # Window size
always_on_top = true/false  # Set always-on-top state
titlebar = true/false       # Enable to keep title bar, disable to remove titlebar
search_title = <title>      # Search title override for screenshot download (must be added manually)
```
### Example:
```
[Microsoft Edge]
position = -7,0
size = 1722,1400
always_on_top = false
titlebar = true

[Final Fantasy XIV]
search_title = Final Fantasy XIV Online
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

## Notes:
- Window titles in config are matched partially and case-insensitively against open windows.

#### This application is made with ultrawide monitors in mind (32:9 / 21:9) and will work best on a single monitor setup

#### *Should* work well with similar monitors in a left to right setup, but not tested:
   ```
   +-----------------------+ +-----------------------+ +-----------------------+
   |                       | |                       | |                       |
   |                       | |                       | |                       |
   | Monitor 1 = 1920x1080 | | Monitor 2 = 1920x1080 | | Monitor 3 = 1920x1080 |
   |                       | |                       | |                       |
   |                       | |                       | |                       |
   +-----------------------+ +-----------------------+ +-----------------------+
   ```
#### It may ***not*** work well with:
- Multi-monitor setups with different resolutions
   ```
   +-----------------------+ 
   |                       | +---------------------+
   |                       | |                     |
   | Monitor 1             | | Monitor 2           |
   | 1920x1080             | | 1280x1024           |
   |                       | |                     |
   +-----------------------+ +---------------------+
   ```

- Multi-monitor setups with vertical positioning
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
