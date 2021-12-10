import os
import re
import numpy as np
import noisereduce as nr
from pydub import AudioSegment
from TTS.utils.manage import ModelManager
from TTS.utils.synthesizer import Synthesizer
from utils.SuppressOutput import suppress_output

MODELS = "../TTSEngines/models.json"
DICTIONARY_DIR = '../TTSEngines/Dict/TTSDL'
MODEL_NAME = 'tts_models/en/ljspeech/tacotron2-DDC_ph'
VOCODER_NAME = 'vocoder_models/en/ljspeech/multiband-melgan'
VOICE_ID = 'tacotron2-DDC_ph'
USE_CUDA = False
NOISE_REDUCTION = False

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
    with suppress_output(suppress_stdout=True, suppress_stderr=False):
      wavs = self.engine.tts(text, speaker_idx="", style_wav="")
    numpy_array = np.asarray(wavs) 
    numpy_array = (numpy_array * 32767).astype('int16')
    if NOISE_REDUCTION:
      numpy_array = nr.reduce_noise(numpy_array, sr = self.engine.output_sample_rate)

    sound = AudioSegment(
      numpy_array.tobytes(), 
      frame_rate = self.engine.output_sample_rate,
      sample_width = numpy_array.dtype.itemsize, 
      channels=1
    )
    with open(filename, 'wb') as out_f:
      sound.export(out_f, format='mp3')


  def fix_pronunciation(self, text):
    for tuple in self.dictionary:
      text = re.sub(tuple[1], tuple[2], text)
    return text  
