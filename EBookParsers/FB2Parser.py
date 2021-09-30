
import xml.etree.ElementTree as ET

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
