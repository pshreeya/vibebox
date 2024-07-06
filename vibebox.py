from dotenv import load_dotenv
import base64
from requests import post, get
import json
import random
import requests
import time
import streamlit as st
import streamlit.components.v1 as components
from streamlit_lottie import st_lottie
import os
import emoji

load_dotenv('.env')

#SpotifyAPI setup 
client_id = os.getenv('SPOTIFY_CLIENT_ID')
client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')

def get_token():
    auth_string = str(client_id) + ":" + str(client_secret)
    auth_bytes = auth_string.encode("utf-8")
    auth_base64 = str(base64.b64encode(auth_bytes), "utf-8")

    url = "https://accounts.spotify.com/api/token"
    headers = {
        "Authorization": "Basic " + auth_base64, 
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type" : "client_credentials"}
    result = post(url, headers = headers, data = data)
    json_result = json.loads(result.content)
    token = json_result["access_token"]
    return token 

def get_auth_header(token):
    return{"Authorization" : "Bearer " + token}

def search_for_multiple_artists(token, artists, mood, mood_genre_mapping):
    artists_list = [artist.strip() for artist in artists.split(',')]
    artist_info_dict = {}
    
    for artist in artists_list:
        url = "https://api.spotify.com/v1/search"
        headers = get_auth_header(token)
        query = f"?q={artist}&type=artist&limit=1"

        query_url = url + query
        result = get(query_url, headers=headers)
        json_result = json.loads(result.content)["artists"]["items"]
        
        if len(json_result) == 0:
            print(f"No artist with the name '{artist}' exists...")
            artist_info_dict[artist] = None
        else:
            artist_info_dict[artist] = {
                "id": json_result[0]['id'],
                'genres': json_result[0]['genres']
            }
    
    filtered_artists = {}
    
    for artist, info in artist_info_dict.items():
        if info:
            artist_genres = info["genres"]

            match_count = 0
            
            for mood_genre in mood_genre_mapping.get(mood, []):
                for genre in artist_genres:
                    if mood_genre.lower() == genre.lower():
                        match_count += 1
                        break  # Stop checking further genres for this mood_genre
            
            if match_count >= 1:  # Adjust this threshold as needed
                filtered_artists[artist] = {
                    "id": info['id'],
                    'genres': info['genres']
                }

    return filtered_artists

def get_albums_by_artist(token, artist_ids, limit=5):
    artist_albums = {}

    for artist, info in artist_ids.items():
        artist_id = info["id"]  # Assuming artist_ids is a dictionary with artist names as keys and info dictionaries as values
        url = f"https://api.spotify.com/v1/artists/{artist_id}/albums?limit={limit}"
        headers = get_auth_header(token)
        
        try:
            result = requests.get(url, headers=headers)
            result.raise_for_status()  # Raise exception for bad response status
            
            albums = result.json().get('items', [])
            artist_albums[artist] = [album["id"] for album in albums]
        
        except requests.exceptions.RequestException as e:
            print(f"Failed to get albums for artist {artist}: {e}")
            artist_albums[artist] = []  # Handle the error gracefully, e.g., by returning empty list
            continue
        
        except KeyError as e:
            print(f"Failed to parse albums response for artist {artist}: {e}")
            artist_albums[artist] = []  # Handle the error gracefully, e.g., by returning empty list
            continue

    return artist_albums

def get_album_tracks(token, album_ids):
    all_album_tracks = {}

    for artist, albums in album_ids.items():
        artist_tracks = []
        for album_id in albums:
            url = f"https://api.spotify.com/v1/albums/{album_id}/tracks"
            headers = get_auth_header(token)
            result = requests.get(url, headers=headers)

            if result.status_code == 200:
                json_result = result.json()
                if 'items' in json_result:
                     artist_tracks.extend((track["name"], track["id"]) for track in json_result['items']) #appending all track ids
                else:
                    print(f"No tracks found for album ID {album_id}")
            else:
                print(f"Failed to get tracks for album ID {album_id}, status code: {result.status_code}")
        
        all_album_tracks[artist] = artist_tracks

    return all_album_tracks

def get_random_track_play(token, album_ids):
    random_tracks = {}
    tracks_results = get_album_tracks(token, album_ids)

    for artist, tracks in tracks_results.items():
        if tracks:
            random_track = random.choice(tracks)
            random_tracks[artist] = {
                "track_name": random_track [0],
                "track_id": random_track [1]
            }
    random_artist = random.choice(list(random_tracks.keys()))

    # Get the track information for the selected artist
    track_artist = random_tracks[random_artist] #getting key
    track_id = track_artist["track_id"] #getting value

    spotify_embed_url = f'https://open.spotify.com/embed/track/{track_id}'
    st.markdown(f'<iframe src="{spotify_embed_url}" width="300" height="80" frameborder="0" allowtransparency="true" allow="encrypted-media"></iframe>', unsafe_allow_html=True)

def load_lottieurl(url):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

mood_genre_mapping = {
    "Sad": ["R&B", "Indie", "Folk", "Blues", "Pop", "Hip-Hop", "Filmi"],
    "Happy": ["Pop", "Hip-Hop", "Dance", "Electronic", "Filmi"],
    "Angry": ["Rock", "Metal", "Punk", "Rap"],
    "Nervous": ["Electronic", "Ambient", "Classical", "Filmi"],
    "Frustrated": ["Hip-Hop", "Rock", "Alternative"],
    "Bored": ["Electronic", "Chill", "Ambient", "Pop", "Hip-Hop", "Rap", "Filmi"],
    "Depressed": ["Soul", "Blues", "Folk", "Pop", "Hip-Hop", "Filmi"],
    "Motivated": ["Pop", "Hip-Hop", "Rock", "Rap", "Jazz"]
}


st.set_page_config(page_title= "VibeBox", page_icon= "🎶", layout = "wide")
#-----Header Section ------
lottie_music = "https://lottie.host/b407f541-aca1-40e9-bc06-b189dc22074a/82Q4UmD1Ce.json"
st_lottie(lottie_music, height=100)
st.title("Welcome to VibeBox!")
st.subheader("Plays songs based on your mood")
st.divider()

#how are you feeling?
st.subheader("Step 1:")

mood = st.selectbox(
        "Describe how you're feeling",
        list(mood_genre_mapping.keys()),
        index=None,
        placeholder="Select your current mood..."
    )

st.subheader("Step 2:")
artists = st.text_input("Enter at least 3 preferred artists (comma-separated)")

if not artists.strip():
    st.write("Please fill in the above boxes.")
else:
    if st.button("Step 3: Activate VibeBox!"):
        with st.spinner("Loading..."):

            token = get_token()

            st.write("Searching...")
            result = search_for_multiple_artists(token, artists, mood, mood_genre_mapping)

            artist_ids = {}
            for artist, info in result.items():
                if info:
                    artist_id = info["id"]
                    artist_genres = info["genres"]
                    artist_ids[artist]={
                                    "id": artist_id,
                                    "genres": artist_genres
                                } #assigning key to the value to create a dictionary   
            
            albums_result = get_albums_by_artist(token, artist_ids)

            album_ids = {}
            for artist, albums in albums_result.items():
                if albums:
                    album_ids[artist] = albums

            st.write("Generating tracks...")
            tracks_results = get_album_tracks(token, album_ids)

            st.write("Playing soon...")
            get_random_track_play(token, album_ids)
            
            st.button("Try again?")