import torchaudio
from chatterbox.tts import ChatterboxTTS

def generate(text_path, voice_path, output_path, model=None):
	model=model or ChatterboxTTS.from_pretrained(device="cpu")
	text=open(text_path, encoding="utf-8").read()
	audio=model.generate(text, audio_prompt_path=voice_path)
	torchaudio.save(output_path, audio, model.sr)

if __name__ == '__main__':
	import argparse
	parser=argparse.ArgumentParser(description='Generate speech with the configured voice reference.')
	parser.add_argument('--text', default='text.txt', help='Text file to narrate')
	parser.add_argument('--voice', default='assets/voice.wav', help='Voice reference WAV')
	parser.add_argument('--output', default='output.wav', help='Output WAV path')
	args=parser.parse_args()
	generate(args.text, args.voice, args.output)