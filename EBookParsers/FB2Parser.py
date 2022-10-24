import xml.etree.ElementTree as ET
import re
import base64

# debug and feature-toggles
PARSE_NOTES = False     # parse notes section at the end of the book
PARSE_COMMENTS = False  # parse comments section at the end of the book

class FB2Parser:

  def __init__(self):
    self.TOC_max_depth = 3
    self.book_title = ''
    self.book_author = ''
    self.book_annotation = ''
    self.cover_image = b''
    self.cover_image_name = ''
    self.book_chapters = []

  def parse(self, filename):
    self._fb2 = ET.parse(filename).getroot()
    for element in self._fb2.iter():
      element.tag = element.tag.partition('}')[-1]

    # book metadata
    self.book_title = self._fb2.find('./description/title-info/book-title').text
    self.book_author = (self._fb2.find('./description/title-info/author/first-name').text
      + ' ' + self._fb2.find('./description/title-info/author/last-name').text)
    self.book_annotation = self.tree_to_text(self._fb2.find('./description/title-info/annotation')).strip()

    # book sections
    self.book_chapters = []
    for body_id, body in enumerate(self._fb2.findall('./body')):
      if body.find('./title'): # first title
        chapter_title = self.parse_title(body.find('./title'), 0)
        chapter_text = self.tree_to_text(body.find('./title'))
        chapter_id = 0
        self.book_chapters.append({'chapter_title':chapter_title, 'chapter_id': chapter_id, 'chapter_text': chapter_text})

      if 'name' in body.attrib and body.attrib['name'] == "notes":
        # notes section at the end of a book
        if PARSE_NOTES:
          chapter_id = 0
          chapter_title = self.parse_title(body.find('./title'), 0)
          chapter_text = self.parse_notes(body)
          self.book_chapters.append({'chapter_title':chapter_title, 'chapter_id': chapter_id, 'chapter_text': chapter_text})
        else: 
          continue
      
      elif 'name' in body.attrib and body.attrib['name'] == "comments":
        # notes section at the end of a comment  
        if PARSE_COMMENTS:
          chapter_id = 0
          chapter_title = self.parse_title(body.find('./title'), 0)
          chapter_text = self.parse_comments(body)
          self.book_chapters.append({'chapter_title':chapter_title, 'chapter_id': chapter_id, 'chapter_text': chapter_text})
        else: 
          continue

      elif body.find('./section'):
        TOC_depth = 0
        for chapter_id, section in enumerate(body.findall('./section')):
          self.parse_section(chapter_id, section, TOC_depth)


    # extract cover image if exists
    self._extract_cover_image()
          
  def parse_section(self, chapter_id, section, TOC_depth):
    TOC_depth += 1
    chapter_title = self.parse_title(section.find('./title'), TOC_depth)

    if TOC_depth < self.TOC_max_depth:   
      chapter_text = self.tree_to_text(section)
    else:
      chapter_text = self.tree_to_text(section, False, True)
    self.book_chapters.append({'chapter_title':chapter_title, 'chapter_id': chapter_id, 'chapter_text': chapter_text})

    if TOC_depth < self.TOC_max_depth:  
      for chapter_id, section in enumerate(section.findall('./section')):
        self.parse_section(chapter_id, section, TOC_depth)

  def parse_title(self, title_element, depth):
    text = ""
    TOC = True
    if title_element is not None:
      for child in title_element:      
        text += (child.text if child.text else '') + self.tree_to_text(child, TOC) + (child.tail if child.tail else '').strip()
        if child.tag == 'p':
          text = (text.strip() + '. ').replace('..', '.')
    text = re.sub('\n', ' ', text.rstrip())      
    title = text.rjust(depth * 4 + len(text), '\u00A0')   
    return title

  def tree_to_text(self, ET, TOC = False, combine_child_sections = False):
    text = ""
    if ET is not None:
      for child in ET:     
        if child.tag == 'section' and not combine_child_sections:
          break 
        elif child.tag == 'table' and not TOC:
          text += "\nТАБЛИЦА ОПУЩЕНА.\n\n"
          continue
        elif child.tag == 'image' and not TOC:
          text += "\nИллюстрация.\n\n"
          continue # skip images        
        elif child.tag == 'empty-line':
          text += "\n\n"
        else: 
          if child.tag == 'a':
            child_text = '' # skip footnotes and links
            subchild_text = ''
          else: 
            child_text = child.text.strip() if child.text else ''
            subchild_text = self.tree_to_text(child, TOC)
          tail_text = child.tail.strip() if child.tail else ''

          subtree_text = child_text + ' ' + subchild_text + ' ' + tail_text
          if (child.tag == 'p'):
            subtree_text = '    ' +self.add_period(subtree_text) + '\n\n'
          if (child.tag == 'title' or child.tag == 'subtitle'):
            subtree_text = '\n\n' + self.add_period(subtree_text) +'\n\n'

          text += subtree_text   

          text = self.cleanup_text(text)

    return text  

  def add_period(self, text):
    if text != None and text.strip() != '':
      if text.strip()[-1] != '.' and text.strip()[-1] != '?' and text.strip()[-1] != '?' and text.strip()[-1] != ':' and text.strip()[-3:] != '...':
        text = text.strip() +'. '
    return text    

  def parse_notes(self, ET):
    text = ""
    if ET is not None:
      for child in ET:     
        text += (child.text if child.text else '') + (self.parse_notes(child)) + (child.tail if child.tail else '')
    return text

  def parse_comments(self, ET):
    text = ""
    if ET is not None:
      for child in ET:     
        text += (child.text if child.text else '') + (self.parse_notes(child)) + (child.tail if child.tail else '')
    return text

  # extract cover image if exists
  def _extract_cover_image(self):
    self.cover_image = None    
    cover_page = self._fb2.find('./description/title-info/coverpage/image')
    if cover_page != None:
      cover_image_name = cover_page.attrib['{http://www.w3.org/1999/xlink}href']
      if cover_image_name:
        for binary in self._fb2.findall('./binary'):
          if 'content-type' in binary.attrib and 'id' in binary.attrib \
            and (binary.attrib['content-type'] == 'image/jpeg' or binary.attrib['content-type'] == 'image/jpg' or binary.attrib['content-type'] == 'image/png') \
              and binary.attrib['id'] == cover_image_name.replace('#', ''):
              self.cover_image = base64.b64decode(binary.text)
              self.cover_image_name = cover_image_name.replace('#', '')


  def cleanup_text(self, text):
    cleanup_dictionary = [ ('\u00A0', ' ')]
    for tuple in cleanup_dictionary:
      text = text.replace(tuple[0], tuple[1])
    return text  

  def save_text_to_file(self, text, filename):
    file = open(filename, "w")
    file.write(text)
    file.close  

  def save_cover_image_to_file(self, path):
    cover_file_name = path + self.cover_image_name
    file = open(cover_file_name, "wb")
    file.write(self.cover_image)
    file.close 
    return cover_file_name  
