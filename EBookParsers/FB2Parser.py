
import xml.etree.ElementTree as ET
import re
import base64

class FB2Parser:
  def __init__(self, filename):
    self._fb2 = ET.parse(filename).getroot()
    for element in self._fb2.iter():
      element.tag = element.tag.partition('}')[-1]

  def parse(self):
    self.book_title = self._fb2.find('./description/title-info/book-title').text
    self.book_author = (self._fb2.find('./description/title-info/author/first-name').text
      + ' ' + self._fb2.find('./description/title-info/author/last-name').text)
    self.book_annotation = self.treeToText(self._fb2.find('./description/title-info/annotation')).strip()

    self.book_bodies = []
    self.book_sections = []
    for body_id, body in enumerate(self._fb2.findall('./body')):
      if 'name' in body.attrib and body.attrib['name'] == "notes":
        section_id = 0
        section_title = re.sub('\n', '. ', self.treeToText(body.find('./title')))
        section_text = self.treeToText(body)
        self.book_sections.append({'section_title':section_title, 'section_id': section_id, 'section_text': section_text})
      elif body.find('./section'):
        for section_id, section in enumerate(body.findall('./section')):
          section_title = re.sub('\n', '. ', self.treeToText(section.find('./title')))
          section_text = self.treeToText(section)
          self.book_sections.append({'section_title':section_title, 'section_id': section_id, 'section_text': section_text})
      else:
        section_title = body.find('./title/p').text
        section_text = self.treeToText(self._fb2)
        section_id = 0
        self.book_sections.append({'section_title':section_title, 'section_id': section_id, 'section_text': section_text})

    # extract cover image if exists
    if self._fb2.find('./binary') != None:
      binary = self._fb2.find('./binary')
      if 'content-type' in binary.attrib and 'id' in binary.attrib \
        and binary.attrib['content-type'] == 'image/jpeg' and binary.attrib['id'] == 'cover.jpg':
          self.cover_image = binary.text
          
  def treeToText(self, ET):
    text = ""
    if ET is not None:
      for child in ET:      
        text += (child.text if child.text else '') + self.treeToText(child) + (child.tail if child.tail else '')
        if child.tag == 'title':
          text = '\n\n' + text.rstrip() +'.\n\n'
    return text  

  def saveTextToFile(self, text, filename):
    file = open(filename, "w")
    file.write(text)
    file.close  

  def saveCoverImageToFile(self, filename):
    file = open(filename, "wb")
    file.write(base64.b64decode(self.cover_image))
    file.close    
