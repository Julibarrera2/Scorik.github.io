# Importación de librerías
import librosa
import librosa.display
import numpy as np
import matplotlib.pyplot as plt
import soundfile as sf
import scipy
import os
from pydub import AudioSegment
#Importamos madmom
from madmom.audio.onsets import OnsetPeakPickingProcessor, OnsetDetection
from madmom.features.beats import RNNBeatProcessor, DBNBeatTrackingProcessor

#lolo