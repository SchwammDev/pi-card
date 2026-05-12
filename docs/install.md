# Installing pi-card on a fresh Raspberry Pi

Fresh-Pi runbook — flashed image to headless auto-start. Already provisioned? Use the README quick-start.

## Prerequisites

```bash
sudo apt update
sudo apt install -y git libportaudio2

curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.local/bin/env
which uv
```

## ReSpeaker HAT driver

The [HinTak fork of seeed-voicecard](https://github.com/HinTak/seeed-voicecard) uses one **branch per kernel** (not tags). Pick the branch matching `uname -r`:

```bash
git clone https://github.com/HinTak/seeed-voicecard
cd seeed-voicecard
git checkout v$(uname -r | cut -d. -f1-2)   # e.g. v6.12 for kernel 6.12.x
sudo ./install.sh
sudo reboot
```

`arecord -l` should now list `seeed-4mic-voicecard`.

## ALSA default device

Pi OS Trixie ships without a usable default sink — sounddevice/portaudio (used by pi-card's adapters) needs one. Test:

```bash
speaker-test -t sine -f 440 -l 1 -c 1
```

If it errors "No such device", find your output card index in `aplay -l` (usually `0` for the headphone jack) and write `~/.asoundrc`:

```
pcm.!default {
    type plug
    slave.pcm "hw:0,0"
}

ctl.!default {
    type hw
    card 0
}
```

Re-run `speaker-test` to confirm.

## Hardware roundtrip

Verify mic and speaker via ALSA before involving pi-card. Use the seeed index from `arecord -l`:

```bash
arecord -D plughw:<seeed-card>,0 -f S16_LE -r 16000 -c 2 -d 5 /tmp/mic_test.wav
aplay /tmp/mic_test.wav
```

Speak during the 5 s window — you should hear yourself.

## pi-card install and first run

```bash
cd ~
git clone <pi-card repo URL>
cd pi-card
make install
nano ~/.config/pi-card/config.yaml   # set base_url, api_key, model
make run
```

First run downloads Piper voices, the Whisper model, and openWakeWord models (~1–2 min). Try the wake word.

## Service install and headless boot

```bash
make service
sudo loginctl enable-linger $USER   # without this the user unit only starts after login
sudo reboot
```

After reboot the service should be running unattended (LED + audio cue, wake word works). Check:

```bash
systemctl --user status pi-card.service
journalctl _SYSTEMD_USER_UNIT=pi-card.service -b --no-pager
```

`journalctl --user -u …` returns nothing on default Pi OS — the `_SYSTEMD_USER_UNIT=` field-filter is the working form. Persistent journals are off by default, so check within the same boot.

## Uninstall

```bash
systemctl --user stop pi-card.service   # no sudo — sudo strips the user bus env
make uninstall

ls ~/.config/pi-card ~/.local/state/pi-card ~/.local/share/pi-card 2>&1   # all "No such file"
systemctl --user status pi-card.service 2>&1 | head -3                    # "not-found"
```
