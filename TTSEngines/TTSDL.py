import io
import os
import re
import numpy as np
import noisereduce as nr
import soundfile as sf
import nltk
from contextlib import redirect_stdout
from contextlib import redirect_stderr
from pydub import AudioSegment
from pydub import scipy_effects
from TTS.utils.manage import ModelManager
from TTS.utils.synthesizer import Synthesizer
from utils.SuppressOutput import suppress_output

DEBUG = False
SHOW_ERRORS = True

MODELS = "../TTSEngines/Model/models.json"
DICTIONARY_DIR = '../TTSEngines/Dict/TTSDL'
MODEL_NAME = 'tts_models/en/ljspeech/tacotron2-DDC_ph'
VOCODER_NAME = 'vocoder_models/en/ljspeech/univnet'
VOICE_ID = 'univnet'
USE_CUDA = False

SENTENCE_MAX_LENGTH = 250
LOWER_UPPER_CASE_WORDS = True

NOISE_REDUCTION = True
NORMALIZE = True
BANDPASS_FILTER = True
EQ_FILTER = True
LOW_CUTOFF_FREQ = 20
HIGH_CUTOFF_FREQ = 7000
EQ_FILTER_PROFILE = [
  {'freq': 6000, 'bandwidth': 100, 'gain': -40}, 
  # {'freq': 5000, 'bandwidth': 100, 'gain': 10}
]


NOISE_SAMLES_DIR='../TTSEngines/NoiseSamples/TTSDL'

class TTSDL:
  def __init__(self, ebook_file_name):

    self.ebook_file_name = ebook_file_name
    self.load_pronunciation_dictionary()

    # Natural language processor
    nltk.download('punkt', quiet=True)

    # TTS DL engine initialization
    with suppress_output(suppress_stdout = not DEBUG, suppress_stderr = not SHOW_ERRORS):
      modelManager = ModelManager(MODELS)
      model_path, config_path, model_item = modelManager.download_model(MODEL_NAME)
      vocoder_path, vocoder_config_path, _ = modelManager.download_model(VOCODER_NAME)

      self.engine =  Synthesizer(
        tts_checkpoint = model_path,
        tts_config_path = config_path,
        tts_speakers_file = "",
        tts_languages_file = "",
        vocoder_checkpoint = vocoder_path,
        vocoder_config = vocoder_config_path,
        encoder_checkpoint = "",
        encoder_config = "",
        use_cuda = USE_CUDA
        )
    self.narrate = self.output_interceptor(self.engine.tts) # output interceptor

  def getVoicesList(self):
    None

  def saveTextToMp3(self, text, filename):
    audio = None;
    sentences = nltk.tokenize.sent_tokenize(text)
    for sentence in sentences:
      # TTS Engine crashes on narrating of long sentences, so let's try to split them by a comma
      if len(sentence) > SENTENCE_MAX_LENGTH:
        sentence_chunks = nltk.regexp_tokenize(sentence, pattern=r'[,\.]\s*', gaps=True)
      else:
        sentence_chunks = [sentence] 
      for sentence_chunk in sentence_chunks:
        # TTS DL narrating 
        wavs = self.narrate(sentence_chunk)
        numpy_array = np.asarray(wavs)
        numpy_array = (numpy_array * 32767).astype('int16')
        if NOISE_REDUCTION:
          try:
            noise_sample, rate = sf.read(NOISE_SAMLES_DIR + '/Voice/' + VOICE_ID + '.wav')
            with suppress_output(suppress_stdout = not DEBUG, suppress_stderr = not SHOW_ERRORS):
              numpy_array = nr.reduce_noise(
                y = numpy_array,
                sr = self.engine.output_sample_rate,
                y_noise = noise_sample,
                prop_decrease = 0.8,
                n_fft = 512)
          except Exception:
            None

        sound_clip = AudioSegment(
          numpy_array.tobytes(),
          frame_rate = self.engine.output_sample_rate,
          sample_width = numpy_array.dtype.itemsize,
          channels=1
        )

        if BANDPASS_FILTER:
          sound_clip = sound_clip.band_pass_filter(LOW_CUTOFF_FREQ, HIGH_CUTOFF_FREQ, 10)
        if EQ_FILTER:
          for tune in EQ_FILTER_PROFILE:
            sound_clip = self.eq_filter(sound_clip, tune['freq'], tune['bandwidth'], tune['gain'])  
        if NORMALIZE:
          sound_clip = sound_clip.normalize()
        # sound_clip = sound_clip.apply_gain_stereo()

        if audio == None:
          audio = sound_clip
        else:
          audio += sound_clip

    with open(filename, 'wb') as out_f:
      audio.export(out_f, format='mp3')

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

  def fix_pronunciation(self, text):
    for tuple in self.dictionary:
      text = re.sub(tuple[1], tuple[2], text)
    # convert all upper case words to capitalized 
    if LOWER_UPPER_CASE_WORDS:
      text = re.sub(r'[A-Z]+', lambda m: m.group(0).capitalize(), text)
    return text

  def output_interceptor(self, func):
    # Decorator for stdout and stderr outputs intecept and parsing 
    def wrap(*args, **kwargs):
      stdout = io.StringIO()
      stderr = io.StringIO()
      with redirect_stdout(stdout), redirect_stderr(stderr):
        result = func(*args, **kwargs)
      if SHOW_ERRORS and stderr.getvalue(): print(stderr.getvalue())  
      if DEBUG and stdout.getvalue(): print(stdout.getvalue())
      return result
    return wrap
  
  def eq_filter(self, seg, focus_freq = 1000, bandwidth = 100, gain_dB = 0, order = 2):
    if gain_dB >= 0:
      sec = seg.band_pass_filter(focus_freq - bandwidth/2, focus_freq + bandwidth/2, order)
      seg = seg.overlay(sec + gain_dB)
      return seg

    if gain_dB < 0:
      seg_high = seg.high_pass_filter(focus_freq + bandwidth/2, order)
      seg_low  = seg.low_pass_filter(focus_freq - bandwidth/2, order)
      seg = seg + (gain_dB)
      seg = seg.overlay(seg_high) 
      seg = seg.overlay(seg_low)
      return seg    