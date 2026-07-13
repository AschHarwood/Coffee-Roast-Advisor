# Artisan settings record — bridge mode vs. standalone mode

Everything changed lives in two Artisan dialogs. Nothing else was touched;
your serial-port settings (Config → Port → ET/BT tab) were **never changed**
and are still: `/dev/cu.SLAB_USBtoUART`, 9600 baud, 8/N/1, timeout 0.7.

## Mode A — Standalone (how it was before; Artisan reads the meter directly)

| Dialog | Setting | Value |
|---|---|---|
| Config → Device, ET/BT tab | Meter | **Mastech MS6514** |

That single dropdown is the master switch. With Mastech selected, Artisan
opens the serial port itself and the WebSocket settings below are ignored —
no need to undo them.

## Mode B — Bridge (roast advisor feeds Artisan; bridge owns the serial port)

| Dialog | Setting | Value |
|---|---|---|
| Config → Device, ET/BT tab | Meter | **WebSocket** |
| Config → Port, WebSocket tab | Host | 127.0.0.1 |
| | Port | **8765** (was 80) |
| | Path | *(empty)* (was `WebSocket`) |
| | Input 1 Node | **BT** (was empty) |
| | Input 2 Node | **ET** (was empty) |
| | everything else on the tab | left at its default (`id`, `command`, `data`, `getData`, `startRoasting`, `endRoasting`, ...) |

Bridge mode only works while `uv run live ...` (or a fakemeter test) is
running — otherwise Artisan shows no readings.

## Switching

- **Back to standalone:** Config → Device → Meter → `Mastech MS6514`. Done.
  (Close the bridge first — two programs can't share the serial port.)
- **Into bridge mode:** start the bridge, then Config → Device → Meter →
  `WebSocket`.

The port/path/node values persist in Artisan either way, so after the first
setup, switching modes is only ever that one Device dropdown.

## Rules of thumb

- Artisan standalone and the bridge (or `uv run capture`) must never run at
  the same time in standalone mode — whoever opens `/dev/cu.SLAB_USBtoUART`
  first wins and the other errors out.
- If Artisan shows flat/no temps in bridge mode: is the bridge terminal
  running? If yes, check Config → Device is on WebSocket and port is 8765.
- If BT and ET ever appear swapped in bridge mode: swap the Input 1/Input 2
  Node values (`BT`/`ET`) in the WebSocket tab.
