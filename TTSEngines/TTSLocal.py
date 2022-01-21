import pyttsx3
import os
import re

# VOICE_ID = 5    # 5:      ru_RU    Alyona Infovox iVox HQ
# VOICE_ID = 44     # 44:     ru_RU    Milena
VOICE_ID = 66     # 66:     en_US    Will Infovox iVox HQ
# VOICE_ID = 71     # 71:     ru_RU    Yuri
# VOICE_ID = 24     # 24:     en_US    Heather Infovox iVox HQ

SPEAK_RATE = 180
DICTIONARY_DIR = '../TTSEngines/Dict/TTSLocal'

class TTSLocal:
  def __init__(self, ebook_file_name):
    self.engine = pyttsx3.init()                      

    self.engine.setProperty('rate', SPEAK_RATE)  
    self.engine.setProperty('volume',1.0)    # setting up volume level  between 0 and 1
    self.voices = self.engine.getProperty('voices') 
    self.engine.setProperty('voice', self.voices[VOICE_ID].id)
    self.ebook_file_name = ebook_file_name

    self.load_pronunciation_dictionary()


  def load_pronunciation_dictionary(self):

    dict_default = DICTIONARY_DIR + '/Default.dict'
    dict_voice = DICTIONARY_DIR + '/Voice/' + self.voices[VOICE_ID].name + '.dict'
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
    voices = self.engine.getProperty('voices')     
    i = 0
    for voice in voices:
      print("{0}: \t{1} \t {2}".format(i, voice.languages[0], voice.name))
      i += 1 

  def onEnd(self, name, completed):
    try:
      self.engine.endLoop()
    except:
      None

  def saveTextToMp3(self, text, filename):
    self.engine.connect('finished-utterance', self.onEnd)
    self.engine.save_to_file(text, filename)
    self.engine.startLoop()

  def fix_pronunciation(self, text):
    for tuple in self.dictionary:
      text = re.sub(tuple[1], tuple[2], text)
    return text  