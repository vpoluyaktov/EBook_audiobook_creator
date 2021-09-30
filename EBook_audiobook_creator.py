#! /usr/bin/env python3

# On linux make sure that 'espeak' and 'ffmpeg' are installed

from EBookParsers.FB2Parser import FB2Parser 
from TTSEngines.TTSLocal import TTSLocal

if __name__ == '__main__':
  parser = FB2Parser('test.fb2')
  parser.parse()

  tts = TTSLocal()
  chapter_no = 1
  for chapter in parser.book_sections:
    print('Processing chapter {0}'.format(chapter['section_title']))
    filename = './output/chapter_' + str(chapter_no) + '.mp3'
    text = chapter['section_text']    
    tts.saveTextToMp3(text, filename)    
    chapter_no += 1