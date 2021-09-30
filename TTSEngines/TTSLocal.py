import pyttsx3

SPEAK_RATE = 180

class TTSLocal:
  def __init__(self):
    self.engine = pyttsx3.init()                      

    self.engine.setProperty('rate', SPEAK_RATE)  
    self.engine.setProperty('volume',1.0)    # setting up volume level  between 0 and 1
    self.voices = self.engine.getProperty('voices') 
    self.engine.setProperty('voice', self.voices[5].id)

  def getVoicesList(self):
    voices = self.engine.getProperty('voices')     
    i = 0
    for voice in voices:
      print("{0}: \t{1} \t {2}".format(i, voice.languages[0], voice.name))
      i += 1 

  def onEnd(self, name, completed):
    self.engine.endLoop()

  def saveTextToMp3(self, text, filename):
    self.engine.connect('finished-utterance', self.onEnd)
    self.engine.save_to_file(text, filename)
    self.engine.startLoop()