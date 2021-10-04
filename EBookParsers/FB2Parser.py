
import xml.etree.ElementTree as ET
import re
import base64

class FB2Parser:
  def __init__(self, filename):
    self._fb2 = ET.parse(filename).getroot()
    for element in self._fb2.iter():
      element.tag = element.tag.partition('}')[-1]

  def parse(self):
    # book metadata
    self.book_title = self._fb2.find('./description/title-info/book-title').text
    self.book_author = (self._fb2.find('./description/title-info/author/first-name').text
      + ' ' + self._fb2.find('./description/title-info/author/last-name').text)
    self.book_annotation = self.tree_to_text(self._fb2.find('./description/title-info/annotation')).strip()

    # book sections
    self.book_bodies = []
    self.book_sections = []
    for body_id, body in enumerate(self._fb2.findall('./body')):
      # note section at the end of a book
      if 'name' in body.attrib and body.attrib['name'] == "notes":
        section_id = 0
        section_title = self.parse_title(body.find('./title'), 0)
        section_text = self.parse_notes(body)
        self.book_sections.append({'section_title':section_title, 'section_id': section_id, 'section_text': section_text})
      elif body.find('./section'):
        depth = 0
        for section_id, section in enumerate(body.findall('./section')):
          self.parse_section(section_id, section, depth)
      else: # no sections in the book - just plain text
        section_title = body.find('./title/p').text
        section_text = self.tree_to_text(self._fb2)
        section_id = 0
        self.book_sections.append({'section_title':section_title, 'section_id': section_id, 'section_text': section_text})

    # extract cover image if exists
    self._extract_cover_image()
          
  def parse_section(self, section_id, section, depth):
    section_title = self.parse_title(section.find('./title'), depth)
    section_text = self.tree_to_text(section)
    self.book_sections.append({'section_title':section_title, 'section_id': section_id, 'section_text': section_text})
    # print(section_title)
    if section.find('./section'):
      depth += 1
      for section_id, section in enumerate(section.findall('./section')):
        self.parse_section(section_id, section, depth)

  def parse_title(self, title_element, depth):
    text = ""
    if title_element is not None:
      for child in title_element:      
        text += (child.text if child.text else '') + self.tree_to_text(child) + (child.tail if child.tail else '')
        if child.tag == 'p':
          text = (text.rstrip() + '. ').replace('..', '.')
    text = text.rstrip()      
    title = text.rjust(depth * 2 + len(text), ' ')   
    return title

  def tree_to_text(self, ET):
    text = ""
    if ET is not None:
      for child in ET:     
        if child.tag == 'section':
          break 
        elif child.tag == 'table':
          text += "\nТАБЛИЦА ПРОПУЩЕНА.\n\n"
          continue
        else: 
          child_text = child.text if child.text else ''
          subchild_text = self.tree_to_text(child)
          tail_text = child.tail if child.tail else ''
          text += child_text + subchild_text + tail_text   
        if ET.tag == 'p' and child_text != '' and child_text[-1] != '.':
            text = text.strip() +'.'    
        if (ET.tag == 'title' or child.tag == 'subtitle') and child_text != '':
            text = '\n' + text.strip() +'.\n\n'  
    return text  

  def parse_notes(self, ET):
    text = ""
    if ET is not None:
      for child in ET:     
        text += (child.text if child.text else '') + (self.parse_notes(child)) + (child.tail if child.tail else '')     
    return text  

  # extract cover image if exists
  def _extract_cover_image(self):
    self.cover_image = None    
    cover_image_name = self._fb2.find('./description/title-info/coverpage/image').attrib['{http://www.w3.org/1999/xlink}href']
    if cover_image_name:
      for binary in self._fb2.findall('./binary'):
        if 'content-type' in binary.attrib and 'id' in binary.attrib \
          and (binary.attrib['content-type'] == 'image/jpeg' or binary.attrib['content-type'] == 'image/jpg') \
            and binary.attrib['id'] == cover_image_name.replace('#', ''):
            self.cover_image = binary.text

  def save_text_to_file(self, text, filename):
    file = open(filename, "w")
    file.write(text)
    file.close  

  def save_cover_image_to_file(self, filename):
    file = open(filename, "wb")
    file.write(base64.b64decode(self.cover_image))
    file.close    
