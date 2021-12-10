from glob import glob
import torch
from pydub import AudioSegment
from pydub.playback import play


language = 'ru'
speaker = 'kseniya_v2'
sample_rate = 16000
device = torch.device('cpu')

model, example_text = torch.hub.load(repo_or_dir='snakers4/silero-models',
                                     model='silero_tts',
                                     language=language,
                                     speaker=speaker)
model.to(device)  # gpu or cpu

example_batch = [ 'Так уж получилось, ',
                  'что наша работа последние двенадцать лет постоянно связана с людьми неординарными: ', 
                  'руководителями альпинистских, ',
                  'полярных, ',
                  'яхтенных, ',
                  'парашютных экспедиций, ',
                  'сильными спортсменами, ',
                  'одиночными путешественниками. ',
                  'Помогая таким людям, ',
                  'невольно становишься соучастником их рискованных проектов. ',
                  'Многие стали нашими друзьями. ',
                  'Статистика восхождений на вершину Эвереста говорит о том, ',
                  'что покорить его всегда было непросто. ', 
                  'С 20-х годов двадцатого века в Непал направлялись экспедиции с тоннами груза, ',
                  'укомплектованные альпинистской командой в два-три десятка человек. ',
                  'Восхождение на гору напоминало осаду средневекового замка, ',
                  'в предместье которого разбивается лагерь и неделя за неделей осаждающие вновь и вновь атакуют стены и отвесы, ',
                  'пробиваясь сквозь туман и пургу. ']

audio_chunks = model.apply_tts(texts=example_batch, sample_rate=sample_rate)
sound = AudioSegment.empty()
for audio_chunk in audio_chunks:
  numpy_array = (audio_chunk * 32767).numpy().astype('int16')
  audio_segment = AudioSegment(
    numpy_array.tobytes(), 
    frame_rate = sample_rate,
    sample_width = numpy_array.dtype.itemsize, 
    channels=1
  )
  sound = sound.append(audio_segment, crossfade=0) 

with open("Audio.mp3", 'wb') as out_f:
    sound.export(out_f, format='mp3')

play(sound)
