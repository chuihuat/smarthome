#!/usr/bin/env python3
# Copyright 2017 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Run a recognizer using the Google Assistant Library.

The Google Assistant Library has direct access to the audio API, so this Python
code doesn't need to record audio. Hot word detection "OK, Google" is supported.

It is available for Raspberry Pi 2/3 only; Pi Zero is not supported.
"""

import logging
import platform
import subprocess
import sys
import os

#import aiy.voice.voicehat
from google.assistant.library.event import EventType
from aiy.assistant import auth_helpers
from aiy.assistant.library import Assistant
from aiy.board import Board, Led
from aiy.voice import tts

from aiy.cloudspeech import CloudSpeechClient

import time
import re
import vlc
import youtube_dl
import threading

ydl_opts = {
    'default_search': 'ytsearch1:',
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True
}

vlc_volume = 50
vlc_instance = vlc.get_default_instance()
vlc_player = vlc_instance.media_player_new()
vlc_player.audio_set_volume(vlc_volume)

client = CloudSpeechClient()

def on_button_press():
    state = vlc_player.get_state()
    if state == vlc.State.Playing:
        vlc_player.pause()
        tts.say('Music is paused!')
    elif state == vlc.State.Paused:
        tts.say('Music will be resumed!')
        vlc_player.play()

def power_off_pi():
    tts.say('Good bye!')
    subprocess.call('sudo shutdown now', shell=True)


def reboot_pi():
    tts.say('See you in a bit!')
    subprocess.call('sudo reboot', shell=True)


def say_ip():
    ip_address = subprocess.check_output("hostname -I | cut -d' ' -f1", shell=True)
    tts.say('My IP address is %s' % ip_address.decode('utf-8'))

playshell = None
vlcshell = None

def player_action(cmd):
    global vlc_volume
    if 'up' in cmd or 'louder' in cmd: 
        if vlc_volume >= 100:
            tts.say('Volume already max!')
        else:
            vlc_volume = vlc_volume + 10
    elif 'down' in cmd or 'softer' in cmd:
        if vlc_volume <= 0:
            tts.say('Volume already off!')
        else:
            vlc_volume = vlc_volume - 10

    tts.say('Volume is ' + str(vlc_volume))
    vlc_player.audio_set_volume(vlc_volume)

def change_volume(percentage):
    os.system('amixer sset \'Master\' ' + percentage + '%')
    vlc_player.audio_set_volume(int(percentage))
    tts.say('Volume is ' + percentage + 'percent')

def chinese_input():
    text = client.recognize()
    if not text:
        print('Sorry, I did not hear you.')
    else:
        print(text)
        play_music(text)

def play_music(name):
    if vlc_player.get_state == vlc.State.Playing:
        vlc_player.stop()

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            meta = ydl.extract_info(name, download=False)
    except Exception:
        tts.say('Sorry, Ican\'t find that song.')
        return

    if meta:
        info = meta['entries'][0]
        vlc_player.set_media(vlc_instance.media_new(info['url']))

        print('Now playing ' + re.sub(r'[^\s\w]', '', info['title']))
        vlc_player.play()

def process_event(assistant, event):
    if event.type == EventType.ON_START_FINISHED:
        led.state = Led.BEACON_DARK # Ready.
        print('Say "OK, Google" then speak, or press Ctrl+C to quit...')

    elif event.type == EventType.ON_CONVERSATION_TURN_STARTED:
        led.state = Led.ON # Listening.

    elif event.type == EventType.ON_RECOGNIZING_SPEECH_FINISHED and event.args:
        print('You said:', event.args['text'].lower())
        text = event.args['text'].lower()
        if text.startswith('youtube '):
            assistant.stop_conversation()
            play_music(text[8:])

        if text.startswith('vlc '):
            assistant.stop_conversation()
            player_action(text[4:])

        if text.startswith('change volume to '):
            assistant.stop_conversation()
            change_volume(text.split(' ')[-1])

        if text.startswith('chinese input'):
            assistant.stop_conversation()
            tts.say('you may speak chinese now.')
            chinese_input()

        elif text == 'ip address':
            assistant.stop_conversation()
            say_ip()

    elif event.type == EventType.ON_END_OF_UTTERANCE:
        led.state = Led.PULSE_QUICK # Thinking.

    elif (event.type == EventType.ON_CONVERSATION_TURN_FINISHED
          or event.type == EventType.ON_CONVERSATION_TURN_TIMEOUT
          or event.type == EventType.ON_NO_RESPONSE):
        led.state = Led.BEACON_DARK # Ready.

    elif event.type == EventType.ON_ASSISTANT_ERROR and event.args and event.args['is_fatal']:
        sys.exit(1)


def main():

    logging.basicConfig(level=logging.INFO)

#    button = aiy.voicehat.get_button()
#    button.on_press(on_button_press)

    credentials = auth_helpers.get_assistant_credentials()
    with Board() as board, Assistant(credentials) as assistant:
        for event in assistant.start():
            process_event(assistant, board.led, event)

if __name__ == '__main__':
    main()
