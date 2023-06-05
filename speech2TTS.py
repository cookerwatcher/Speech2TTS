'''
 # @ Description: Speech Recognition to Text to Speech / Twitch Chat
 # @ Author: Hippy (real_hippyau on twitch.tv)
 # @ Create Time: 2023-06-02 23:36:47
 # @ License: WTFPL
 '''

import os
import numpy as np
import speech_recognition as sr
import tkinter as tk
from tkinter import ttk
from ttkthemes import ThemedTk
import threading
import sounddevice as sd
import tempfile
from elevenlabs import voices, generate, set_api_key
import pygame
import nltk
import re
import time
import socket
import configparser

# load config.ini
config = configparser.ConfigParser()
config.read('config.ini')

# Google speech API key is not required currently, but it might be one day
GOOGLE_SPEECH_API_KEY = None
try:
    GOOGLE_SPEECH_API_KEY = config.get('GOOGLE_SPEECH', 'API_Key', fallback=None)
except:
    GOOGLE_SPEECH_API_KEY = None

# ElevenLabs TTS API 
tts_available = False
try:
    TTS_api_key = config.get('TTS', 'API_Key')
except:
    TTS_api_key = "put_a_valid_key_here" # this will end up in the config.ini as a place holder
    print(f"You need to put a ElevenLabs API key in config.ini for TTS to work")
finally:
    set_api_key(TTS_api_key)    

# twitch chat
twitch_available = False
twitch_connected = False
twitch_nickname = ""
twitch_token = ""
twitch_channel = ""
sock = socket.socket()
server = 'irc.chat.twitch.tv'
port = 6667
try:    
    twitch_nickname = config.get('Twitch', 'Nickname')
    twitch_token = config.get('Twitch', 'Token')
    twitch_channel = config.get('Twitch', 'Channel', fallback=twitch_nickname)
except:
    twitch_available = False
    print(f"Twitch credentials not found in config.ini - twitch integration unavailable.")
finally:
    twitch_available = True

# Save our config.ini file
def config_save():
    if not config.has_section('Twitch'):
        config.add_section('Twitch')
    config.set('Twitch', 'Nickname', twitch_nickname)
    config.set('Twitch', 'Token', twitch_token)
    config.set('Twitch', 'Channel', twitch_channel)

    if not config.has_section('TTS'):
        config.add_section('TTS')
    config.set('TTS', 'API_Key', TTS_api_key)

    if GOOGLE_SPEECH_API_KEY is not None:
        if not config.has_section('GOOGLE_SPEECH'):
            config.add_section('GOOGLE_SPEECH')    
        config.set('GOOGLE_SPEECH', 'API_Key', GOOGLE_SPEECH_API_KEY)

    with open('config.ini', 'w') as configfile:
        config.write(configfile)

def connect_to_twitch():
    global twitch_connected
    if twitch_available == False:
        message_var.set("Twitch integration unavailable.")
        return False
    
    if twitch_connected == True:
        message_var.set("Already connected to Twitch!")
        return True
    
    try:
        # connect to the server
        sock.connect((server, port))
        # authenticate
        sock.send(f"PASS {twitch_token}\n".encode('utf-8'))
        sock.send(f"NICK {twitch_nickname}\n".encode('utf-8'))

        # we are going to just assume this works, if you supply bad credentials
        # it just won't work when you try to chat... meh
        twitch_connected = True
        message_var.set(f"Connected to Twitch as {twitch_nickname}!")
        return True
    except Exception as e:
        print(f"Error connecting to Twitch: {e}")
        message_var.set(f"Error connecting to Twitch. {e}")
        twitch_connected = False
        return False

def change_channel(channel):    
    if twitch_connected == False:
        message_var.set(f"Not connected to Twitch!")
        return        
    twitch_channel = channel_entry.get().strip().replace('#', '')

    try:
        if twitch_channel != "":
            channel = '#' + twitch_channel
            # leave current channel (if any) and join new one
            sock.send(f"PART {channel}\n".encode('utf-8'))
            sock.send(f"JOIN {channel}\n".encode('utf-8'))
        else:            
            message_var.set("Channel name cannot be empty.")
    except Exception as e:        
        message_var.set(f"Error changing channel: {e}")
    finally:
        message_var.set(f"Joined channel '{twitch_channel}'!")

def send_message_to_twitch():
    message = txt_box.get("1.0", "end-1c")
    message = message.strip()
    
    if twitch_connected == False:
        message_var.set(f"Not connected to Twitch!")
        return
    try:
        channel = '#' + channel_entry.get().strip().replace('#', '')
        if not channel or not message:            
            message_var.set("Channel and message cannot be empty.")
            return
        message_temp = f"PRIVMSG {channel} :{message}\n"
        sock.send(message_temp.encode('utf-8'))
    except Exception as e:        
        message_var.set("Error chatting... {e}")

auto_do_it = False  # if true, we will auto TTS
auto_chat = False   # if true, we will auto Twitch chat

# main window
window = ThemedTk(theme="equilux")
window.withdraw() # hide the window until we are ready to show it

# splash screen
splash = tk.Toplevel()
splash.title("Loading...")
splash.configure(bg='#141414')
splash.geometry('300x100')
splash_label = tk.Label(splash, text="Initializing system, please wait...", bg='#282828', fg='#ffffff')
splash_label.pack()
splash.update()

# setup the mixer
pygame.mixer.init()
splash.update()

# play the output audio and wait for it to finish
def play_mp3(file_path):
    pygame.mixer.music.load(file_path)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy() == True:
        time.sleep(0.05)
        continue

# download the tokenizer for sentence splitting, part of the natural language toolkit
nltk.download('punkt')
splash.update()

# get the list of voices
try:
    voices = voices()
except:
    voices = None

if not voices:
    voice_names = ['TTS UNAVAILABLE']
    tts_available = False
else:
    voice_names = [voice.name for voice in voices]
    voice_names.insert(0, 'Select voice...')
    tts_available = True

splash.update()

# initialize recognizer
r = sr.Recognizer()

# get list of microphone names
mic_list = sr.Microphone.list_microphone_names()
mic_list.insert(0, 'Select microphone...')

# destroy the splash screen
splash.destroy()

window.deiconify() # Show the main window
window.configure(bg='#282828')
window.title("Voice Recognition for TTS / Twitch Chat")

# Create variables for volume level and UI messages
volume_level = tk.IntVar(window)
volume_level.set(0)

message_var = tk.StringVar(window)
message_var.set("Select a microphone and press listen to get started!")

# some common rules for punctuation
def add_punctuation(text):
    # Add a full stop at the end of each sentence
    text = nltk.tokenize.sent_tokenize(text)
    text = [sentence.strip() + '.' for sentence in text]
    text = ' '.join(text)
    
    # CENSORSHIP - PROFANITY FIXER
    replace_list = {'cont': 'cunt', 'coming': 'cumming', 'come': 'cum',
                    #'word': 'replacement',
                   }
    
    exciting_words = ['amazing', 'incredible',
                      'exciting', 'fantastic', 'astonishing',
                      'fucing', 'fuck', 'cunt', 'cunts', 'cock', 'pussy']

    # replace all words in a replace_list with the alternative 
    for word in replace_list:
        text = re.sub(r'\b' + word + r'\b', replace_list[word], text, flags=re.IGNORECASE)
        
    # Add a comma before a 'but' or 'and' that is not at the start of the sentence
    text = re.sub(r'(?<!^)(\s+)(but|and)(\s+)',
                  r', \2 ', text, flags=re.IGNORECASE)

    # Add a question mark after a phrase that starts with a question word
    text = re.sub(r'\b(who|what|where|when|why|how)\b[\w\s]*',
                  lambda match: match.group(0) + '?', text, flags=re.IGNORECASE)
 
    # Add an exclamation mark to a sentence containing specific words
    for word in exciting_words:        
        text = re.sub(r'\b[\w\s]*\b' + word + r'\b[\w\s]*\.',
                      lambda match: match.group(0)[:-1] + '!', text, flags=re.IGNORECASE)        
    return text

# to show the microphone volume level
def update_audio_level():
    def audio_callback(indata, frames, time, status):
        volume_norm = np.linalg.norm(indata) * 10
        volume_level.set(int(volume_norm))

    stream = sd.InputStream(callback=audio_callback)
    with stream:
        while True:
            sd.sleep(30)

# send to eleven labs and play the result.
def do_it(text):
    if not tts_available:
        message_var.set("TTS is not available. Configure your API key in config.ini")
        return

    voice_name = voice_choice.get()
    if voice_name == 'Select voice...':
        message_var.set("Please select a voice.")
        return
    
    try:
        # Send text to Eleven Labs API
        result = generate(text=text, voice=voice_name)
        if result is not None:
            # Save the returned audio to a temporary file
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as fp:
                fp.write(result)

            # Play the audio
            play_mp3(fp.name)

            # If the checkbox is unchecked, delete the file
            if not keep_mp3s.get():
                os.remove(fp.name)
            else:
                # Save the file in the user's Documents folder
                # Use the first few words of the text for the filename
                filename = f"{voice_name}-{'-'.join(text.split()[:5])}.mp3"
                filename = os.path.join(
                    os.path.expanduser('~'), 'Documents', filename)
                os.rename(fp.name, filename)

    except Exception as e:
                message_var.set(
                    "Error generating audio!\nException type: {}\nException message: {}".format(type(e), e))

# listen to the microphone and send the audio to the API
def recognize_and_send_audio(): 
    mic_name = mic_choice.get()
    if mic_name == 'Select microphone...':
        message_var.set("Please select a microphone.")
        return
    
    # Subtract 1 because of the 'Select microphone...' item
    mic_index = mic_list.index(mic_name) - 1
    with sr.Microphone(device_index=mic_index) as source:
        message_var.set("Speak Anything :")
        audio = r.listen(source)
        try:
            text = r.recognize_google(audio, key=GOOGLE_SPEECH_API_KEY)          
        except:
            message_var.set("Sorry could not recognize what you said")

        finally:
            message_var.set("You said : '{}'".format(text))            
            text = add_punctuation(text)

            # Clear text box and add new text
            txt_box.delete('1.0', tk.END)
            txt_box.insert(tk.END, text)

            # Send text to Eleven Labs API and/or Twitch chat
            if auto_do_it == True and tts_available == True:
                do_it(text)
            if auto_chat == True and twitch_connected == True:
                send_message_to_twitch(text)

# audio device selection drop-down
mic_choice = tk.StringVar(window)
mic_choice.set('Select microphone...')
mic_menu = ttk.OptionMenu(window, mic_choice, *mic_list)
mic_menu.grid(row=0, column=0, padx=10, pady=10)

# voice selection drop-down
voice_choice = tk.StringVar(window)
voice_choice.set('Select voice...')
voice_menu = ttk.OptionMenu(window, voice_choice, *voice_names)
voice_menu.grid(row=0, column=1, padx=10, pady=10)  

# 'Keep MP3s' checkbox
keep_mp3s = tk.BooleanVar(window)
keep_mp3s.set(False)
keep_mp3s_checkbutton = ttk.Checkbutton(window, text='Keep MP3s', variable=keep_mp3s)
keep_mp3s_checkbutton.grid(row=0, column=2, padx=10, pady=10)  

# recognition / editing box
txt_box = tk.Text(window, height=10, width=50, bg='black', fg='white')
txt_box.grid(row=1, column=0, padx=5, pady=10, columnspan=4)  

# 'Listen' button
listen_btn = ttk.Button(window, text='Listen', command=recognize_and_send_audio)
listen_btn.grid(row=3, column=0, pady=10)  

# add 'Do It' button
do_it_btn = ttk.Button(window, text='Do-It', command=do_it(text=txt_box.get("1.0", "end-1c")))
do_it_btn.grid(row=3, column=1, pady=10)  

auto_do_it_checkbutton = ttk.Checkbutton(
    window, text='Auto Do-It', variable=auto_do_it)
auto_do_it_checkbutton.grid(row=4, column=1, pady=10)  

auto_chat_checkbutton = ttk.Checkbutton(
    window, text='Auto Chat', variable=auto_chat)
auto_chat_checkbutton.grid(row=4, column=2, pady=10)  

if twitch_available == True:
    # 'Chat' button
    chat_btn = ttk.Button(window, text='Chat', command=lambda: send_message_to_twitch())
    chat_btn.grid(row=3, column=2, pady=10)

    # channel name input
    channel_entry = ttk.Entry(window)
    channel_entry.insert(0, twitch_channel)
    channel_entry.grid(row=5, column=1, pady=10)

    # button to change channel
    change_channel_btn = ttk.Button(window, text='Set Twitch Channel', command=lambda: change_channel(channel_entry.get()))
    change_channel_btn.grid(row=5, column=0, pady=10)

# message label
message_label = ttk.Label(window, textvariable=message_var, wraplength=280)
message_label.grid(row=6, column=0, pady=10, columnspan=4)  

# input level meter
style = ttk.Style(window)
style.layout('LabeledProgressbar',
             [('Horizontal.Progressbar.trough',
               {'children': [('Horizontal.Progressbar.pbar',
                              {'side': 'left', 'sticky': 'ns'}),
                             ('Horizontal.Progressbar.label', {'sticky': ''})],
                'sticky': 'nswe'})])
style.configure('LabeledProgressbar', text='Microphone Level')

volume_bar = ttk.Progressbar(window, style='LabeledProgressbar',
                             length=200, mode="determinate", variable=volume_level)
volume_bar.grid(row=7, column=0, padx=5, pady=10, columnspan=4)  

# start a new thread for the audio level update to avoid blocking the main thread
threading.Thread(target=update_audio_level, daemon=True).start()

# connect to twitch
if twitch_available == True:
    connect_to_twitch()
    if twitch_connected == True and twitch_channel != '':
        change_channel(twitch_channel)

window.mainloop()

# save config at shutdown
config_save()
