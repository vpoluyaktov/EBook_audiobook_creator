from boto3 import Session
from contextlib import closing
import os
import sys
import re

VOICE_ID = "Matthew"

DICTIONARY_DIR = '../TTSEngines/Dict/AWSPolly'

class AWSPolly:

  def __init__(self, ebook_file_name):
    # Create a client using the credentials and region defined in the [adminuser]
    # section of the AWS credentials file (~/.aws/credentials).
    session = Session(profile_name="default")
    self.engine = session.client("polly")
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

  def fix_pronunciation(self, text):
    for tuple in self.dictionary:
      text = re.sub(tuple[1], tuple[2], text)
    return text  

  def getVoicesList(self):
    None

  def saveTextToMp3(self, text, filename):
    try:
      # Request speech synthesis
      response = self.engine.synthesize_speech(
        Text=text, 
        OutputFormat="mp3",
        VoiceId=VOICE_ID
      )
    except Exception as error:
      # The service returned an error, exit gracefully
      print(error)
      sys.exit(-1)

    # Access the audio stream from the response
    if "AudioStream" in response:
      # Note: Closing the stream is important because the service throttles on the
      # number of parallel connections. Here we are using contextlib.closing to
      # ensure the close method of the stream object will be called automatically
      # at the end of the with statement's scope.
      with closing(response["AudioStream"]) as stream:
        output = filename

      try:
        # Open a file for writing the output as a binary stream
        with open(output, "wb") as file:
          file.write(stream.read())
      except IOError as error:
        # Could not write to file, exit gracefully
        print(error)
        sys.exit(-1)

    else:
      # The response didn't contain audio data, exit gracefully
      print("Could not stream audio")
      sys.exit(-1)
