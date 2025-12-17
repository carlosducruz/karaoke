import numpy as np
import pyrubberband as rb
import sounddevice as sd

sr = 44100
t = np.linspace(0, 3, sr * 3)
audio = 0.3 * np.sin(2 * np.pi * 220 * t)

shifted = rb.pitch_shift(audio, sr, n_steps=3)

sd.play(shifted, sr)
sd.wait()
