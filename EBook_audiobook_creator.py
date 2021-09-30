#! /usr/bin/env python3

# On linux make sure that 'espeak' and 'ffmpeg' are installed

import pyttsx3
import time
import xml.etree.ElementTree as ET

SPEAK_RATE = 180

class FB2Parser:
  def __init__(self, filename):
    self._fb2 = ET.parse(filename).getroot()
    for element in self._fb2.iter():
      element.tag = element.tag.partition('}')[-1]

  def parse(self):
    self.book_title = self._fb2.find('./description/title-info/book-title').text
    self.book_author = (self._fb2.find('./description/title-info/author/first-name').text
      + ' ' + self._fb2.find('./description/title-info/author/last-name').text)
    self.book_annotation = self.treeToText(self._fb2.find('./description/title-info/annotation'))

    self.book_sections = []
    if self._fb2.find('./body/section'):
      for section_id, section in enumerate(self._fb2.findall('./body/section')):
        section_title = section.find('./title/p').text
        section_text = self.treeToText(section)
        self.book_sections.append({'section_title':section_title, 'section_id': section_id, 'section_text': section_text})
    else:
      section_title = self._fb2.find('./body/title/p').text
      section_text = self.treeToText(self._fb2)
      section_id = 0
      self.book_sections.append({'section_title':section_title, 'section_id': section_id, 'section_text': section_text})
        
  def treeToText(self, ET):
    text = ""
    for child in ET:      
      text += (child.text if child.text else '') + self.treeToText(child) + (child.tail if child.tail else '')
      if child.tag == 'title':
        text = '\n\n' + text.rstrip() +'.\n\n'
    return text  


class TTS_local:
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
    print(time.ctime(), 'finished', completed)
    self.engine.endLoop()

  def saveTextToMp3(self, text, filename):
    self.engine.connect('finished-utterance', self.onEnd)
    self.engine.save_to_file(text, filename)
    print(time.ctime(), 'started')
    self.engine.startLoop()
    # self.engine.runAndWait()
    # self.engine.stop()


if __name__ == '__main__':
  parser = FB2Parser('test.fb2')
  parser.parse()

  chapter_no = 1

  for section in parser.book_sections:
    filename = './output/chapter_' + str(chapter_no) + '.mp3'
    text = section['section_text']
    tts = TTS_local()
    tts.saveTextToMp3(text, filename)    
    chapter_no += 1