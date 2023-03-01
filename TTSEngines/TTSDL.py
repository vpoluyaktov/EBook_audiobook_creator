
import os
import re
import numpy as np
import nltk
from pydub import AudioSegment
from TTS.utils.manage import ModelManager
from TTS.utils.synthesizer import Synthesizer
from utils.AudioProcessor import AudioProcessor
from utils.ConsoleLogger import ConsoleLogger
from utils.TestProcessor import TextProcessor

DEBUG = False

MODELS = "../TTSEngines/Model/models.json"
DICTIONARY_DIR = '../TTSEngines/Dict/TTSDL'
MODEL_NAME = 'tts_models/en/ljspeech/tacotron2-DDC_ph'
VOCODER_NAME = 'vocoder_models/en/ljspeech/univnet'
VOICE_ID = 'univnet'
USE_CUDA = False

SENTENCE_MAX_LENGTH = 250

NOISE_REDUCTION = True
EQ_FILTER = True
NORMALIZE = True

EQ_FILTER_PROFILE = [
  {'freq': 6150, 'bandwidth': 100,  'gain': -25, 'rolloff': 2},
  {'freq': 3000, 'bandwidth': 2500, 'gain': 0,   'rolloff': 2}, 
]

NOISE_SAMLES_DIR='../TTSEngines/NoiseSamples/TTSDL'

class TTSDL:
  def __init__(self, ebook_file_name):
    self.ebook_file_name = ebook_file_name
    
    self.logger = ConsoleLogger(DEBUG)
    self.test_processor = TextProcessor(self.logger)
    self.audio_processor = AudioProcessor(self.logger)

    # Natural language processor
    nltk.download('punkt', quiet=True)

    # Load pronunciation dictionary
    self.test_processor.load_pronunciation_dictionary(DICTIONARY_DIR, VOICE_ID, self.ebook_file_name)

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

        if EQ_FILTER:
          audio_segment = self.audio_processor.eq_filter(audio_segment, EQ_FILTER_PROFILE)
        if NORMALIZE:
          audio_segment = self.audio_processor.normalize(audio_segment)

        if audio == None:
          audio = audio_segment
        else:
          audio += audio_segment

    with open(filename, 'wb') as out_f:
      audio.export(out_f, format='mp3')

  def fix_pronunciation(self, text):
    text = self.test_processor.fix_pronunciation(text)
    return text
  
   