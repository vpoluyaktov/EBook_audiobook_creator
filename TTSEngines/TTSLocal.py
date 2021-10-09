import pyttsx3
import os

SPEAK_RATE = 180
DICTIONARY_NAME = '../TTSEngines/TTSLocal.dict'

class TTSLocal:
  def __init__(self):
    self.engine = pyttsx3.init()                      

    self.engine.setProperty('rate', SPEAK_RATE)  
    self.engine.setProperty('volume',1.0)    # setting up volume level  between 0 and 1
    self.voices = self.engine.getProperty('voices') 
    self.engine.setProperty('voice', self.voices[5].id)

    self.load_pronunciation_dictionary()


  def load_pronunciation_dictionary(self):
    self.dictionary = []
    try:
      print(os.getcwd())
      dict_file = open(DICTIONARY_NAME, 'r')
      line = dict_file.readline()      
      while line:
        tuple = line.split("|")
        self.dictionary.append(tuple)
        line = dict_file.readline()
    finally:
      dict_file.close()

  def getVoicesList(self):
    voices = self.engine.getProperty('voices')     
    i = 0
    for voice in voices:
      print("{0}: \t{1} \t {2}".format(i, voice.languages[0], voice.name))
      i += 1 

  def onEnd(self, name, completed):
    self.engine.endLoop()

  def saveTextToMp3(self, text, filename):
    text = self.fix_pronunciation(text)
    self.engine.connect('finished-utterance', self.onEnd)
    self.engine.save_to_file(text, filename)
    self.engine.startLoop()

  def fix_pronunciation(self, text):
    for tuple in self.dictionary:
      text = text.replace(tuple[0], tuple[1])
    return text  