
import os
import re
import numpy as np
import nltk
from pydub import AudioSegment
from TTS.utils.manage import ModelManager
from TTS.utils.synthesizer import Synthesizer
from utils.AudioProcessor import AudioProcessor
from utils.ConsoleLogger import ConsoleLogger

DEBUG = False

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
  {'freq': 6150, 'bandwidth': 100,  'gain': -25, 'rolloff': 2},
  {'freq': 3000, 'bandwidth': 2500, 'gain': 0,   'rolloff': 2}, 
]

NOISE_SAMLES_DIR='../TTSEngines/NoiseSamples/TTSDL'

class TTSDL:
  def __init__(self, ebook_file_name):
    self.ebook_file_name = ebook_file_name
    
    self.logger = ConsoleLogger(DEBUG)
    self.audio_processor = AudioProcessor(self.logger)
    self.load_pronunciation_dictionary()

    # Natural language processor
    nltk.download('punkt', quiet=True)

    # TTS DL engine initialization
    with self.logger:
      modelManager = ModelManager(MODELS)
      model_path, config_path, model_item = modelManager.download_model(MODEL_NAME)
      vocoder_path, vocoder_config_path, _ = modelManager.download_model(VOCODER_NAME)

      self.tts_engine =  Synthesizer(
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
    self.narrate = self.logger.output_interceptor(self.tts_engine.tts) # output interceptor

  def getVoicesList(self):
    None

  def saveTextToMp3(self, text, filename):
    audio = None;

    # Split the text onto sentences 
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

        # convert wav to numpy array
        sound_np_array = (np.asarray(wavs) * 32767).astype('int16')
        if NOISE_REDUCTION:
          self.audio_processor.noise_filter(sound_np_array, self.tts_engine.output_sample_rate, NOISE_SAMLES_DIR, VOICE_ID)

        # convert numpy array to AudioSegment
        audio_segment = AudioSegment(
          sound_np_array.tobytes(),
          frame_rate = self.tts_engine.output_sample_rate,
          sample_width = sound_np_array.dtype.itemsize,
          channels=1
        )

        if BANDPASS_FILTER:
          audio_segment = self.audio_processor.band_pass_filter(audio_segment, LOW_CUTOFF_FREQ, HIGH_CUTOFF_FREQ, 10)
        if EQ_FILTER:
          audio_segment = self.audio_processor.eq_filter(audio_segment, EQ_FILTER_PROFILE)
        if NORMALIZE:
          audio_segment = self.audio_processor.normalize(audio_segment)
        # audio_segment = self.audio_processor.apply_gain_stereo()

        if audio == None:
          audio = audio_segment
        else:
          audio += audio_segment

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

  
   