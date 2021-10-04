#! /usr/bin/env python3

# On linux make sure that 'espeak' and 'ffmpeg' are installed

import os
import sys
import math
import subprocess
import signal
import humanfriendly
import humanfriendly.prompts
import shutil
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.mp4 import MP4Cover

from EBookParsers.FB2Parser import FB2Parser 
from TTSEngines.TTSLocal import TTSLocal

# debug feature-toggles
PRE_CLEANUP = True
CREATE_DIRS = True
NARRATE_CHAPTERS = False
RE_ENCODE_MP3 = False
CONCATENATE_MP3 = False
CONVERT_TO_MP4 = False
POST_CLEANUP = False

# Experimental features. Use with caution
EDIT_CHAPTER_NAMES = False

BITRATE = "128k"
SAMPLE_RATE = "44100"
BIT_DEPTH = "s16"
OUTPUT_MODE="mono" # mono / stereo
GAP_DURATION = 5 # Duration of a gaps between chapters
part_size_human = "2 GB" # default audiobook part size

# small adjustment (don't ask me why - just noticed mutagen returns slighly incorrect value)
# if you hear the end of previous chapter at the beginning of new one - slightly increase the value of this parameter
# if new chapter sound starts too early - decrease the value
MP3_DURATION_ADJUSTMENT = -50

output_dir = "output"


def signal_handler(sig, frame):
    print('\nCtrl+C has been pressed. Exiting...')
    sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)

def secs_to_hms(seconds):
    h, m, s, ms = 0, 0, 0, 0

    if "." in str(seconds):
        splitted = str(seconds).split(".")
        seconds = int(splitted[0])
        ms = int(splitted[1])

    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)

    ms = str(ms)
    try:
        ms = ms[0:3]
    except:
        pass

    return "%.2i:%.2i:%.2i.%s" % (h, m, s, ms)

def hms_to_sec(hms_string):
    seconds= 0
    for part in str(hms_string).split(':'):
        seconds= seconds*60 + float(part)
    return seconds


def get_mp3_length(file_name):
    try:
        mp3 = MP3(file_name , ID3=EasyID3)
        length = mp3.info.length
    except:
        length = 0
    return length

if __name__ == '__main__':

  print("\n\nAudiobook creator script\n")

  if len(sys.argv) < 2:
    ebook_file_name = input("Enter an ebook file name: ")
  else:  
    ebook_file_name = sys.argv[1];
  parser = FB2Parser(ebook_file_name)
  parser.parse()

  book_author = parser.book_author
  book_title = parser.book_title

  print("\n\nProcessing book:\n{0} - {1}\n".format(book_author, book_title))
  print("Annotation:\n", parser.book_annotation)

  # clean/create output dir
  if PRE_CLEANUP:
      if (os.path.exists(output_dir)):
          shutil.rmtree(output_dir)
  if CREATE_DIRS:
      os.makedirs(os.path.join(output_dir, 'tmp/resampled'))
  os.chdir(output_dir)

  # extract the book cover image
  album_cover = ""
  if parser.cover_image:
    parser.save_cover_image_to_file('tmp/cover.jpg')
  album_cover = 'tmp/cover.jpg'

  tts = TTSLocal()
  chapter_no = 1
  mp3_file_names = []
  chapter_names = []
  for chapter in parser.book_sections:
    print('Narrating chapter {0}'.format(chapter['section_title']))
    filename = 'chapter_' + str(chapter_no)
    text = chapter['section_text']    
    parser.save_text_to_file(text, 'tmp/' + filename + '.txt')
    if NARRATE_CHAPTERS:
      tts.saveTextToMp3(text, 'tmp/' + filename + '.mp3')   
    mp3_file_names.append(filename + '.mp3') 
    chapter_names.append(chapter['section_title'])
    chapter_no += 1

exit()

# generated silence .mp3 to fill gaps between chapters
os.system('ffmpeg -nostdin -f lavfi -i anullsrc=r={}:cl={} -t {} -hide_banner -loglevel fatal -nostats -y -ab {} -ar {} -vn "tmp/resampled/gap.mp3"'.format(SAMPLE_RATE, OUTPUT_MODE, GAP_DURATION, BITRATE, SAMPLE_RATE))
os.system('ffmpeg -nostdin -f lavfi -i anullsrc=r={}:cl={} -t {} -hide_banner -loglevel fatal -nostats -y -ab {} -ar {} -vn "tmp/resampled/half_of_gap.mp3"'.format(SAMPLE_RATE, OUTPUT_MODE, GAP_DURATION / 2, BITRATE, SAMPLE_RATE))

# adjust GAP_DURATION because ffmpeg doesn't produce exact mp3 length
GAP_DURATION = get_mp3_length("tmp/resampled/gap.mp3")

print("\nRe-encoding .mp3 files all to the same bitrate...")
file_number = 1
for file_name in mp3_file_names:
    if os.path.dirname(file_name) and not os.path.exists(os.path.join('tmp/resampled', os.path.dirname(file_name))):
        os.makedirs(os.path.join('tmp/resampled', os.path.dirname(file_name))) # create dir structure for complex file names
    print("{:6d}/{}: {:67}".format(file_number, len(mp3_file_names), file_name + '...'), end = " ", flush=True)
    if RE_ENCODE_MP3:
        os.system('ffmpeg -nostdin -i "tmp/{}" -hide_banner -loglevel fatal -nostats -y -ab {} -ar {} -vn "tmp/resampled/{}"'.format(file_name, BITRATE, SAMPLE_RATE, file_name))
    print("OK")
    file_number += 1


# calculate total audiobook size, split the books on parts if needed
total_size = 0
part_size = humanfriendly.parse_size('2Gb')
current_part_size = 0
file_number = 1
part_number = 1
audiobook_parts = {}
part_audio_files = []

for file_name in mp3_file_names:
    part_audio_files.append(file_name)
    file_size = os.stat('tmp/resampled/' + file_name).st_size
    current_part_size += file_size
    total_size += file_size

    if file_number == len(mp3_file_names) or current_part_size >= part_size:
        # we have collected enought files for the audiobook part.
        audiobook_parts[part_number] = {}
        audiobook_parts[part_number]['mp3_file_names'] = part_audio_files
        audiobook_parts[part_number]['part_size'] = current_part_size

        part_number += 1
        current_part_size = 0
        part_audio_files = []
    file_number += 1

number_of_parts = math.ceil(total_size / part_size)
if number_of_parts > 1:
    total_size_human = humanfriendly.format_size(total_size)
    print("\nAudiobook size is {}. The book will be split into {} parts.".format(total_size_human, number_of_parts))

# create a chapter files and audio files list for each part
print("\nCreating audiobook chapters")
part_number = 1
chapter_number = 1
for audiobook_part in audiobook_parts:
    if len(audiobook_parts) > 1:
        print("\n{}. Part {}".format(book_title, part_number))
        print("---------------------------------------------------------")

    mp3_list_file_name = "audio_files.part{:0>3}".format(part_number)
    audiobook_parts[part_number]['mp3_list_file_name'] = mp3_list_file_name
    mp3_list_file = open(mp3_list_file_name, 'w')
    mp3_list_file.write("file 'tmp/resampled/half_of_gap.mp3'\n")

    chapters_file_name = "chapters.part{:0>3}".format(part_number)
    audiobook_parts[part_number]['chapters_file_name'] = chapters_file_name
    chapters_file = open(chapters_file_name, 'w')

    chapters_file.write(";FFMETADATA1\n")
    chapters_file.write("major_brand=isom\n")
    chapters_file.write("minor_version=1\n")
    chapters_file.write("compatible_brands=isom\n")
    chapters_file.write("encoder=Lavf58.20.100\n")

    #chapter_number = 1
    file_number = 1
    chapter_start_time = 0
    chapter_end_time = 0
    chapter_length = 0
    total_part_size = 0
    total_part_length = 0
    part_audio_files = audiobook_parts[part_number]['mp3_file_names']

    # brake files into chapters
    for filename in part_audio_files:
        mp3_title = parser.book_sections[file_number - 1]['section_title']
        length = get_mp3_length('tmp/resampled/' + filename) + (MP3_DURATION_ADJUSTMENT / 1000)
        chapter_end_time = chapter_end_time + length
        file_size = os.stat('tmp/resampled/' + filename).st_size
        mp3_list_file.write("file 'tmp/resampled/{}'\n".format(filename))
        total_part_size += file_size
        chapter_length += length
        total_part_length += length

        # if this is last file in the list or next file title is different from current one - finish the chapter
        if file_number == len(part_audio_files) \
            or mp3_title != parser.book_sections[file_number]['section_title']: # next file title
            # chapter changed
            chapter_title = mp3_title

            if not chapter_title:
                chapter_title = "Chapter {}".format(chapter_number)
            chapter_title = chapter_title.strip();

            mp3_list_file.write("file 'tmp/resampled/gap.mp3'\n")
            chapter_end_time += GAP_DURATION + (MP3_DURATION_ADJUSTMENT / 1000)
            chapters_file.write("[CHAPTER]\n")
            chapters_file.write("TIMEBASE=1/1000\n")
            chapters_file.write("START={}\n".format(int(chapter_start_time * 1000)))
            chapters_file.write("END={}\n".format(int(chapter_end_time * 1000)))
            chapters_file.write("title={}\n".format(chapter_title))
            print("Chapter {:>3} ({}): {}".format(chapter_number, secs_to_hms(chapter_length).split('.')[0], chapter_title))
            chapter_length = 0
            chapter_start_time = chapter_end_time
            chapter_number += 1

        file_number += 1

    chapters_file.close()
    mp3_list_file.write("file 'tmp/resampled/half_of_gap.mp3'\n")
    mp3_list_file.close()
    if len(audiobook_parts) > 1:
        print("---------------------------------------------------------")
        print("Part size: {}. Part length: {}".format( humanfriendly.format_size(total_part_size), secs_to_hms(total_part_length)))
    audiobook_parts[part_number]['chapters_file_name'] = chapters_file_name
    audiobook_parts[part_number]['part_length'] = total_part_length
    part_number += 1

if EDIT_CHAPTER_NAMES:
    print("\nNow you can edit chapter names. \nOpen the folowing file(s) in any text editor:")
    part_number = 1
    for audiobook_part in audiobook_parts:
        print("\t{}".format(os.path.abspath(audiobook_parts[part_number]['chapters_file_name'])))
        part_number += 1
    input("\nPress <Enter> when you are done...")

# concatenate .mp3 files into big .mp3 and attach chapter meta info
part_number = 1
for audiobook_part in audiobook_parts:
    if len(audiobook_parts) > 1:
        print("\nProcessing Part {} from {}".format(part_number, number_of_parts))
        print("---------------------------------------------------------")
        print("Combining .mp3 files into big one...\nEstimated duration of the part: {}".format(secs_to_hms(audiobook_parts[part_number]['part_length'])))
    else:
        print("\nCombining single .mp3 files into big one...\nEstimated duration of the book: {}".format(secs_to_hms(audiobook_parts[part_number]['part_length'])))
    if CONCATENATE_MP3:
        command = "ffmpeg -nostdin -f concat -safe 0 -loglevel fatal -stats -i {} -y -vn -ab {} -ar {} -acodec aac output.part{:0>3}.aac".format(audiobook_parts[part_number]['mp3_list_file_name'],BITRATE, SAMPLE_RATE, part_number)
        subprocess.call(command.split(" "))

    print("\nConverting .mp3 to audiobook format...")
    if CONVERT_TO_MP4:
        command = "ffmpeg -nostdin -loglevel fatal -stats -i output.part{:0>3}.aac -i {} -map_metadata 1 -y -vn -acodec copy output.part{:0>3}.mp4".format(part_number, audiobook_parts[part_number]['chapters_file_name'], part_number)
        subprocess.call(command.split(" "))

    # create tags, rename file
    audio = MP4("output.part{:0>3}.mp4".format(part_number))
    if len(audiobook_parts) > 1:
        audio["\xa9nam"] = [book_title + ", Part {}".format(part_number)]
        audio["trkn"] = [(part_number, number_of_parts)]
        audio['cpil'] = True
    else:
        audio["\xa9nam"] = [book_title]
    audio["\xa9alb"] = [book_title]
    audio["\xa9ART"] = [book_author]
    audio["desc"] = [parser.book_annotation]
    audio["\xa9gen"] = ["Audiobook"]
    audio['\xa9cmt'] = ""
    audio['\xa9too'] = "This audiobook was created by 'IA Audiobook Creator' https://github.com/vpoluyaktov/IA_audiobook_creator"
    # audio['cprt'] = license_url
    # audio['purl'] = item_url

    print("Adding audiobook cover image")
    if album_cover != "":
      # add album cover to the audiobook
      if ".PNG" in album_cover.upper():
          image_type = 14
      else:
          image_type = 13
      data = open(os.path.join(album_cover), 'rb').read()
      audio["covr"] = [MP4Cover(data, image_type)]

    audio.save()

    if len(audiobook_parts) > 1:
        audiobook_file_name = "{} - {}, Part {}.m4b".format(book_author, book_title, part_number)
    else:
    	audiobook_file_name = "{} - {}.m4b".format(book_author, book_title)

    # replace non-safe characters in the file name
    unsafe_tuples = [('/','_')]
    for tuple in unsafe_tuples:
        audiobook_file_name = audiobook_file_name.replace(tuple[0], tuple[1])

    os.rename("output.part{:0>3}.mp4".format(part_number), "{}".format(audiobook_file_name))

    # clean up
    if POST_CLEANUP:
        os.remove("output.part{:0>3}.aac".format(part_number))
        os.remove("audio_files.part{:0>3}".format(part_number))
        os.remove("chapters.part{:0>3}".format(part_number))

    if len(audiobook_parts) > 1:
      print("\nPart {} created: output/{}\n".format(part_number, audiobook_file_name))
    else:
      print("\nAudiobook created: output/{}\n".format(audiobook_file_name))

    part_number += 1

# clean up
# if POST_CLEANUP:
#     # shutil.rmtree(tmp)
os.chdir("..")