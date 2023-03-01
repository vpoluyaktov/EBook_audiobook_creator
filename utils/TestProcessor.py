import os
import re

LOWER_UPPER_CASE_WORDS = True

class TextProcessor:
  
  def __init__(self, logger):
    self.logger = logger

  def load_pronunciation_dictionary(self, dictionary_dir, voice_id, ebook_file_name):
    dict_default = dictionary_dir + '/Default.dict'
    dict_voice = dictionary_dir + '/Voice/' + voice_id + '.dict'
    dict_book = dictionary_dir + '/Book/' + os.path.splitext(os.path.basename(ebook_file_name))[0] + '.dict'
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
