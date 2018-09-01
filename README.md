# SDL2 Joystick Calib

Python script that man-in-the-middles joystick events and applies legacy
`jscal` calibration.

It works by intercepting messages sent to `/dev/input/event*` and publishing
calibrated versions to a virtual device.

## The problem

I wanted to play Freespace 2 using my old Saitek Cyborg 3D Gold joystick.
I had to calibrate it. Using standard tools like `jscal` worked, but not
in game. Turns out, SDL is the culprit.

SDL1.2 defaulted to using event API (`/dev/input/event*`) over `/dev/input/js*`.
You could workaround this by setting environment variable
`export SDL_JOYSTICK_DEVICE=/dev/input/js0`. See
[this answer](https://superuser.com/a/19481) for more info.
Well, it didn't work for me.

Turns out, SDL2 abandonned `/dev/input/js*` input method in favor of
`/dev/input/event*` API completely
([source](https://forums.libsdl.org/viewtopic.php?t=9772)).
And of course Freespace 2 now uses SDL2. Sad thing is, SDL is supposed to handle
calibrating the joystick, but it doesn't work.


## Requirements

* Python3
* jstest, jscal
* Evdev Python3 wrapper, e.g.:

```
sudo dnf install python3-evdev.x86_64 # or your distro equivalent
```


## Usage

1. Use `jstest` to see if the joystick needs recalibration. If moving the
joystick to min/max positions doesn't yield values close to +-32 thousand,
it needs to be recalibrated. (Note: path to device may be different for
you, especially if you have multiple joysticks).
    ```
    jstest /dev/input/js0
    ```

1. If calibration is needed, use `jscal`:
    ```
    jscal -c /dev/input/js0
    ```

1. Verify the calibration. Moving joystick to min/max positions should
yield values close to +-32 thousand.
    ```
    jstest /dev/input/js0
    ```

1. Ensure that SDL2 is the culprit. Use
[sdl-jstest](https://github.com/Grumbel/sdl-jstest). If it seems like it
contradicts `jstest`'s results, then keep reading. Otherwise, you probably
have a different issue.
    ```
    ./sdl2-jstest --list
    ./sdl2-jstest --test 0
    ```

1. Dump calibration data to a file:
    ```
    jscal -p /dev/input/js0 > cal.txt
    ```

1. Use `evtest` to see which `/dev/input/event*` device to intercept:
    ```
    $ sudo evtest
    No device specified, trying to scan all of /dev/input/event*
    Available devices:
    ...
    /dev/input/event28:	SAITEK CYBORG 3D USB
    Select the device event number [0-30]: 30^C
    ```

1. Run the script as root in verbose mode:
    ```
    sudo ./sdl2-joystick-calib.py --calib cal.txt --input "/dev/input/event28" --verbose
    ```

1. Aside from some info logs, you should see different events. If `val`
is different from `Adjusted value`, then the calibration from `jscal`
is being applied.
    ```
    DEBUG:root:event at 1535842389.423851, code 05, type 03, val 85	-> Adjusted value: 468
    ```

1. Are you using the same joystick as me (Saitek Cybork 3D Gold)? If not,
you will probably need to reconfigure the script a little bit. See
[configuring](#configuring).

1. Use `evtest` to verify if our device has come up. Look for 'Calibrated'
prefix:
    ```
    $ sudo evtest
    No device specified, trying to scan all of /dev/input/event*
    Available devices:
    ...
    /dev/input/event28:	SAITEK CYBORG 3D USB
    ...
    /dev/input/event30:	Calibrated SAITEK CYBORG 3D USB
    Select the device event number [0-30]: 30^C
    ```

1. You should be good to go. Enjoy!


## Configuring

I have only one joystick, so I just hard-coded configuration data inside
the script. Sorry, too lazy for now. You may have to modify it. PRs welcome :)

It is likely that you will have to modify `MOVED_EVENT` constant and `MAP_EVENT_CODE_TO_AXIS_IDX` dictionary.

### `MOVED_EVENT`

Your joystick may send many types of messages. Use `evtest` to peek what yours
sends. For me, the interesting output is
```
Event: time 1535842968.567306, -------------- SYN_REPORT ------------
Event: time 1535842968.583313, type 3 (EV_ABS), code 0 (ABS_X), value 93
```
It carries the `value` data, which changes as I move the joystick.
Set `MOVED_EVENT` to value of `type` from these kinds of messages.

### `MAP_EVENT_CODE_TO_AXIS_IDX`

My Joystick has 6 axis. Each one has its own corresponding message code. E.g.
left-right movement is code 0, throttle is 6, etc. We need to associate these
codes with output of `jscal` tool, which doesn't contain such information.

Use `verbose` and `filter_evcode` parameters to try to find correspondence
between the order in which axis appear in `jscal` calibration file and message
codes. Overwrite `MAP_EVENT_CODE_TO_AXIS_IDX` dict with this information.


## References
* https://superuser.com/questions/17959/linux-joystick-seems-mis-calibrated-in-an-sdl-game-freespace-2-open
* https://github.com/Grumbel/sdl-jstest
* https://forums.libsdl.org/viewtopic.php?t=9772
* https://bugs.launchpad.net/ubuntu/+source/libsdl1.2/+bug/410187
* https://askubuntu.com/questions/156017/gamepad-setup-ignored-by-games
* https://www.hard-light.net/forums/index.php?topic=62294.0
* http://manpages.ubuntu.com/manpages/trusty/man1/jscal.1.html
* http://manpages.ubuntu.com/manpages/trusty/man1/jstest.1.html
* https://github.com/flosse/linuxconsole/blob/master/utils/jscal.c
