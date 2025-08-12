from gpiozero import RotaryEncoder, Button
from signal import pause
import time

# === Your pin mapping ===
ENC_A = 4     # CLK
ENC_B = 27    # DT
BTN   = 17    # SW to GND (internal pull-up)

# Rotary encoder: low debounce (2 ms) for responsiveness
enc = RotaryEncoder(a=ENC_A, b=ENC_B, max_steps=0, bounce_time=0.002)

# Button: longer debounce (100 ms) to prevent multiple triggers
btn = Button(BTN, pull_up=True, bounce_time=0.1)

last_steps = enc.steps
last_t = time.monotonic()

def moved():
    global last_steps, last_t
    s = enc.steps
    d = s - last_steps
    if d != 0:
        now = time.monotonic()
        dt = max(now - last_t, 1e-6)
        cps = d / dt
        direction = "CW" if d > 0 else "CCW"
        print(f"steps={s:6d}  Δ={d:+3d}  {direction}  (~{cps:5.1f} steps/s)")
        last_steps, last_t = s, now

def pressed():
    print("Button: PRESSED")

def released():
    print("Button: released")

enc.when_rotated = moved
btn.when_pressed = pressed
btn.when_released = released

print("Rotary test running…")
pause()
