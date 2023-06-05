
* Overview

This application combines real-time voice recognition with TTS generation capabilities. It utilizes the Eleven Labs API to generate audio from recognized text and then plays the audio. It provides a UI to choose the microphone and voice to use. The application also includes capabilities to interact with Twitch chat.

* Requirements

Python 3.7+ is required.

To install the Python dependencies, run:

`pip install -r requirements.txt`

* Configuration

Before starting the application, you need to create a config.ini file in the same directory as the script. This file should contain your ElevenLabs API key, and Twitch credentials.

Before using the twich chat integration, you need to get your OAuth token and put it in the config.ini file. 
You can get it from Twitch's website (https://twitchapps.com/tmi/) by clicking on "Connect" and authorizing the TMI application to use your account. Remember to keep your OAuth token safe, as it allows access to your Twitch account!

Here is an example:

```ini

[Twitch]
nickname = cookedelements
token = oauth:abcdef12345abcdef12345abcdef12
channel = cooker28

[TTS]
api_key = put_a_valid_key_here

```

Replace nickname with your Twitch username and token with your OAuth token.
Replace put_a_valid_key_here with your ElevenLabs API key.

* Running the Application

To run the application, simply execute the script in a terminal:

```python main.py```

* Usage

    Choose a microphone from the dropdown menu at the top of the window.
    Choose a voice from the dropdown menu next to the microphone selection.
    Check the "Keep MP3s" checkbox if you want to keep the generated MP3 files.
    Click the "Listen" button and speak into your chosen microphone.

    The app will display your spoken words. You can edit the words in this box if desired.
    
    "Do It" will generate TTS and playback using your chosen voice.
    "Chat" will post to Twitch chat instead.

    There are check boxes to automatically perform either of those functions.
    
    To change the Twitch channel, type the new channel name in the channel field and click the "Change Channel" button.

* Troubleshooting

If you encounter any problems, first check the Twitch connection status/error message label at the bottom of the application window. If you're having trouble with the voice recognition or generation, try selecting a different microphone or voice.

* Contributing

Please submit a pull request for any bug fixes or feature enhancements. Be sure to include a description of the changes you made and how they improve the application.
License

This project is licensed under the terms of the WTFPL license.

