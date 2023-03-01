import noisereduce as nr
import soundfile as sf
from pydub import AudioSegment
from pydub import scipy_effects

class AudioProcessor:
  def __init__(self, logger):
    self.logger = logger

  def noise_filter(self, sound_np_array, output_sample_rate, noise_samples_dir, voice_id):  
    self.logger.debug('Applying noise filter with noise sample: ' + noise_samples_dir + '/Voice/' + voice_id + '.wav')
    try:
      noise_sample, rate = sf.read(noise_samples_dir + '/Voice/' + voice_id + '.wav')
      with self.logger:
        sound_np_array = nr.reduce_noise(
          y = sound_np_array,
          sr = output_sample_rate,
          y_noise = noise_sample,
          prop_decrease = 0.8,
          n_fft = 512)
    except Exception:
      None
    return sound_np_array    
  

  def band_pass_filter(self, audio_segment, low_cutoff_freq, high_cutoff_freq, rolloff_factor):
    self.logger.debug(f'Applying bandpass filter with low freq: {low_cutoff_freq}, high freq: {high_cutoff_freq}, rolloff factor: {rolloff_factor}')
    audio_segment = audio_segment.band_pass_filter(low_cutoff_freq, high_cutoff_freq, rolloff_factor)
    return audio_segment
    

  def eq_filter(self, audio_segment, eq_filter_profile):                
    for tune in eq_filter_profile:
      focus_freq = tune['freq']
      bandwidth = tune['bandwidth']
      gain_dB = tune['gain']
      rolloff_factor = tune['rolloff']

      self.logger.debug(f'Applying EQ filter with focus freq: {focus_freq}, bandwidth: {bandwidth}, gain: {gain_dB}, rolloff factor: {rolloff_factor}')
            
      if gain_dB >= 0:
        audio_section = audio_segment.band_pass_filter(focus_freq - bandwidth/2, focus_freq + bandwidth/2, rolloff_factor)
        audio_segment = audio_segment.overlay(audio_section + gain_dB)

      if gain_dB < 0:
        audio_segment_high = audio_segment.high_pass_filter(focus_freq + bandwidth/2, rolloff_factor)
        audio_segment_low  = audio_segment.low_pass_filter(focus_freq - bandwidth/2, rolloff_factor)
        audio_segment = audio_segment + (gain_dB)
        audio_segment = audio_segment.overlay(audio_segment_high) 
        audio_segment = audio_segment.overlay(audio_segment_low)  
      
    return audio_segment
  

  def normalize(self, audio_segment):
    audio_segment = audio_segment.normalize()
    return audio_segment
  

  def apply_gain_stereo(self, audio_segment):
    audio_segment = audio_segment.apply_gain_stereo()
    return audio_segment