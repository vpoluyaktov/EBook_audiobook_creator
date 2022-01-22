import os
import re
import numpy as np
import noisereduce as nr
import soundfile as sf
from pydub import AudioSegment
from pydub import scipy_effects
from TTS.utils.manage import ModelManager
from TTS.utils.synthesizer import Synthesizer
from utils.SuppressOutput import suppress_output

DEBUG = False

MODELS = "../TTSEngines/Model/models.json"
DICTIONARY_DIR = '../TTSEngines/Dict/TTSDL'
MODEL_NAME = 'tts_models/en/ljspeech/tacotron2-DDC_ph'
VOCODER_NAME = 'vocoder_models/en/ljspeech/univnet'
VOICE_ID = 'univnet'
USE_CUDA = False

NOISE_REDUCTION = True
BANDPASS_FILTER = True
LOW_CUTOFF_FREQ = 20
HIGH_CUTOFF_FREQ = 8000
NORMALIZE = True

NOISE_SAMLES_DIR='../TTSEngines/NoiseSamples/TTSDL'

class TTSDL:
  def __init__(self, ebook_file_name):

    modelManager = ModelManager(MODELS)
    model_path, config_path, model_item = modelManager.download_model(MODEL_NAME)
    vocoder_path, vocoder_config_path, _ = modelManager.download_model(VOCODER_NAME)
    speakers_file_path = None
    self.engine =  Synthesizer(model_path, config_path, speakers_file_path, vocoder_path, vocoder_config_path, use_cuda=USE_CUDA)
           
    self.ebook_file_name = ebook_file_name
    self.load_pronunciation_dictionary()


  def load_pronunciation_dictionary(self):

    dict_default = DICTIONARY_DIR + '/Default.dict'
    dict_voice = DICTIONARY_DIR + '/Voice/' + VOICE_ID + '.dict'
    dict_book = DICTIONARY_DIR + '/Book/' + os.path.splitext(os.path.basename(self.ebook_file_name))[0] + '.dict'
    dict_files = [dict_default, dict_voice, dict_book]

    self.dictionary = []
    for dict_file_name in dict_files:
      dict_file = None
      try:
        dict_file = open(dict_file_name, 'r')
        line = dict_file.readline()      
        while line:
          tuple = line.split("~")
          self.dictionary.append(tuple)
          line = dict_file.readline()
      except Exception:
        None
      finally:
        if dict_file:
          dict_file.close()

  def getVoicesList(self):
    None

  def saveTextToMp3(self, text, filename):
    with suppress_output(suppress_stdout = False, suppress_stderr = False):
      wavs = self.engine.tts(text, speaker_idx="", style_wav="")
    numpy_array = np.asarray(wavs) 
    numpy_array = (numpy_array * 32767).astype('int16')
    if NOISE_REDUCTION:
      try: 
        noise_sample, rate = sf.read(NOISE_SAMLES_DIR + '/Voice/' + VOICE_ID + '.wav')
        with suppress_output(suppress_stdout=True, suppress_stderr=True):
          numpy_array = nr.reduce_noise(
            y = numpy_array, 
            sr = self.engine.output_sample_rate, 
            y_noise = noise_sample,           
            prop_decrease = 0.8,
            n_fft = 512)
      except Exception:
        None

    sound = AudioSegment(
      numpy_array.tobytes(), 
      frame_rate = self.engine.output_sample_rate,
      sample_width = numpy_array.dtype.itemsize, 
      channels=1
    )

    if BANDPASS_FILTER:
      sound = sound.band_pass_filter(low_cutoff_freq = LOW_CUTOFF_FREQ, high_cutoff_freq = HIGH_CUTOFF_FREQ)
    if NORMALIZE:  
      sound = sound.normalize()
    # sound = sound.apply_gain_stereo()

    with open(filename, 'wb') as out_f:
      sound.export(out_f, format='mp3')


  def fix_pronunciation(self, text):
    for tuple in self.dictionary:
      text = re.sub(tuple[1], tuple[2], text)
    return text  
