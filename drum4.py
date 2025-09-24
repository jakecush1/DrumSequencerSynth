# drummachine_gui.py
import tkinter as tk
import pygame
import threading
import time
import os

# -------------------------
# Audio / sample loading
# -------------------------
pygame.mixer.init()

SAMPLES = {
    "kick": "kick.wav",
    "snare": "snare.wav",
    "hihat": "hihat.wav",
    "clap": "clap.wav",
}

sounds = {}
for name, fname in SAMPLES.items():
    if os.path.exists(fname):
        try:
            sounds[name] = pygame.mixer.Sound(fname)
        except Exception as e:
            print(f"Could not load {fname}: {e}")
            sounds[name] = None
    else:
        print(f"Warning: sample '{fname}' not found. {name} will be silent.")
        sounds[name] = None

# -------------------------
# Sequencer state
# -------------------------
bpm = 120
beat_duration = 60.0 / bpm / 4  # 16th notes
patterns = {name: [0] * 16 for name in SAMPLES.keys()}  # 0/1 grid
current_step = -1

# thread control
sequencer_thread = None
stop_event = threading.Event()

# -------------------------
# UI helper (main thread only)
# -------------------------
root = tk.Tk()
root.title("808 Drum Machine (Python)")

frame = tk.Frame(root, bg="#222")
frame.pack(padx=12, pady=12)

tempo_label = tk.Label(frame, text=f"Tempo: {bpm} BPM", fg="white", bg="#222", font=("Arial", 14))
tempo_label.grid(row=0, column=0, columnspan=18, pady=(0,6))

def change_tempo(value):
    global bpm, beat_duration
    try:
        bpm = int(value)
        beat_duration = 60.0 / bpm / 4
        tempo_label.config(text=f"Tempo: {bpm} BPM")
    except ValueError:
        pass

tempo_slider = tk.Scale(frame, from_=60, to=200, orient="horizontal", command=change_tempo, bg="#333", fg="white")
tempo_slider.set(bpm)
tempo_slider.grid(row=1, column=0, columnspan=18, sticky="we", pady=(0,8))

# Create the grid of buttons
drum_order = ["kick", "snare", "hihat", "clap"]
buttons = {drum: [] for drum in drum_order}

def update_buttons(step=None):
    """
    Update all button colors according to patterns and current_step.
    Must be called from the main thread (Tkinter).
    """
    global current_step
    if step is not None:
        current_step = step

    for col in range(16):
        for drum in drum_order:
            btn = buttons[drum][col]
            selected = bool(patterns[drum][col])
            if col == current_step:
                # current step highlight
                if selected:
                    btn.config(bg="orange", activebackground="orange")
                else:
                    btn.config(bg="lightgray", activebackground="lightgray")
            else:
                # normal (persisted) state
                if selected:
                    btn.config(bg="red", activebackground="red")
                else:
                    btn.config(bg="gray", activebackground="gray")

def toggle_step(drum, col):
    """
    Toggle pattern state and immediately refresh UI (main thread).
    """
    patterns[drum][col] = 1 - patterns[drum][col]
    # Immediately update UI to reflect selection (keeps it persistent)
    update_buttons()

# Build grid widgets
for row_index, drum in enumerate(drum_order, start=2):
    tk.Label(frame, text=drum.upper(), fg="white", bg="#222").grid(row=row_index, column=0, padx=(4,8))
    for col in range(16):
        # Use tk.Button (bg changes are respected on most platforms).
        btn = tk.Button(frame,
                        width=3,
                        height=2,
                        bg="gray",
                        activebackground="gray",
                        relief="raised",
                        command=lambda d=drum, c=col: toggle_step(d, c))
        btn.grid(row=row_index, column=col + 1, padx=2, pady=2)
        buttons[drum].append(btn)

# -------------------------
# Sequencer loop (worker thread)
# -------------------------
def sequencer_loop():
    """
    Runs in a separate thread. Plays audio, and schedules UI updates on the main thread via root.after.
    """
    step = 0
    next_time = time.time()
    while not stop_event.is_set():
        now = time.time()
        # play any sounds for this step
        for drum in drum_order:
            if patterns[drum][step]:
                snd = sounds.get(drum)
                if snd:
                    try:
                        snd.play()
                    except Exception:
                        pass

        # schedule UI update on main thread
        root.after(0, update_buttons, step)

        # advance and sleep to keep timing
        step = (step + 1) % 16
        next_time += beat_duration
        sleep_time = next_time - time.time()
        if sleep_time > 0:
            time.sleep(sleep_time)
        else:
            # if we fell behind, catch up without sleeping
            next_time = time.time()

# Start/stop control
def start_sequencer():
    global sequencer_thread, stop_event
    if sequencer_thread and sequencer_thread.is_alive():
        return
    stop_event.clear()
    sequencer_thread = threading.Thread(target=sequencer_loop, daemon=True)
    sequencer_thread.start()
    play_button.config(text="Stop")

def stop_sequencer():
    global stop_event, sequencer_thread
    stop_event.set()
    sequencer_thread = None
    # reset current step highlight
    root.after(0, set_current_step_to_none)
    play_button.config(text="Play")

def toggle_play():
    if stop_event.is_set() or sequencer_thread is None:
        start_sequencer()
    else:
        stop_sequencer()

def set_current_step_to_none():
    global current_step
    current_step = -1
    update_buttons()

# -------------------------
# Buttons: Play / Clear
# -------------------------
controls = tk.Frame(root, bg="#222")
controls.pack(pady=(6,12))

play_button = tk.Button(controls, text="Play", width=12, bg="#ff5722", fg="white", font=("Arial", 12), command=toggle_play)
play_button.grid(row=0, column=0, padx=6)

def clear_all():
    for drum in drum_order:
        patterns[drum] = [0] * 16
    update_buttons()

clear_button = tk.Button(controls, text="Clear All", width=12, command=clear_all)
clear_button.grid(row=0, column=1, padx=6)

# Initialize visuals
update_buttons()

# Graceful shutdown to stop thread on close
def on_close():
    stop_event.set()
    # give the thread a moment to stop
    time.sleep(0.05)
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)
root.mainloop()

