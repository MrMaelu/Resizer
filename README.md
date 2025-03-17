# Window Positioner
Resize, move and modify application windows.

## Function
This application lets you define some application window settings.

The following settings are available:
- **Screen position** (x,y)     _(optional)_
- **Window size** (w,h)         _(optional)_
- **Always on top status** (true/false)
- **Titlebar visibility** (true/false)

Settings are defined in **.ini** files.

Filenames starting with **config_** will show up in a dropdown menu with the config name.

If only a **config.ini** is present, and no **config_[config name].ini** the settings will be applied automatically.

## Purpose
The purpose is to help position apllications and imitate "fullscreen windowed" mode for use on an ultrawide monitor (32:9) with custom layout.

This removes the need to use 2 inputs to get fullscreen applications without titlebar and borders as well as adds more possible layouts.

### How application window detection works
If the application window title contains the word defined in **```[ ]```** it will be handled.

### .ini example
```
[Microsoft Edge]
position = -7,0
size = 1722,1400
always_on_top = false
titlebar = true

[Last Epoch]
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
