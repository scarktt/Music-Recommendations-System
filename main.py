from cfg import CLIENT_ID, CLIENT_SECRET, SPOTIPY_REDIRECT_URI, USER

import json
import math
import requests

import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyOAuth

scope = "playlist-read-private"
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=CLIENT_ID,
                                                client_secret=CLIENT_SECRET,
                                                redirect_uri=SPOTIPY_REDIRECT_URI,
                                                scope=scope))


def get_all_user_playlists(result={}, offset=0, playlists=[]):
    result = sp.current_user_playlists(limit=50, offset=offset)
    if not result.get('items') and offset > 0:
        return playlists
    playlists += result['items']
    return get_all_user_playlists(result, offset+50, playlists)


def get_playlist_tracks(playlist_id, result={}, offset=0, playlist_tracks=[]):
    result = sp.playlist_items(playlist_id, offset=offset)
    if not result.get('items') and offset > 0:
        return playlist_tracks
    playlist_tracks += result['items']
    return get_playlist_tracks(playlist_id, result, offset+100, playlist_tracks)


def get_saved_tracks(result={}, offset=0, saved_tracks=[]):
    result = sp.current_user_saved_tracks(limit=50, offset=offset)
    if not result.get('items') and offset > 0:
        return saved_tracks
    saved_tracks += result['items']
    return get_saved_tracks(result, offset+50, saved_tracks)


def map_playlists_to_tabular(playlists: list):
    ids, names, total_tracks = [], [], []

    for playlist in playlists:
        names.append(playlist['name'])
        ids.append(playlist['id'])
        total_tracks.append(playlist['tracks']['total'])

    user_playlists = {
        'name': names,
        'id': ids,
        'total_tracks': total_tracks
    }

    playlists_df = pd.DataFrame(user_playlists)
    print(playlists_df)
    return playlists_df


def map_tracks_to_tabular(tracks: list):
    ids, names, artists, release_dates = [], [], [], []

    for track in tracks:
        names.append(track['track']['name'])
        ids.append(track['track']['id'])
        release_dates.append(track['track']['album']['release_date'])
        artists.append(track['track']['artists'][0]['name'])

    user_tracks = {
        'name': names,
        'id': ids,
        'artist': artists,
        'release_dates': release_dates
    }

    tracks_df = pd.DataFrame(user_tracks)
    tracks_df.drop_duplicates(subset=['name', 'id', 'artist'], inplace=True)
    print(tracks_df)
    return tracks_df


def main():
    playlists_results = get_all_user_playlists()

    user_own_playlists = list(filter(lambda playlist: playlist['owner']['id'] == USER, playlists_results))

    playlist_df = map_playlists_to_tabular(user_own_playlists)

    user_tracks = []
    for playlist in user_own_playlists:
        print(f'getting songs from {playlist["name"]} playlist...')
        playlist_id = playlist['id']
        user_tracks += get_playlist_tracks(playlist_id)

    print(f'getting saved songs...')
    user_tracks += get_saved_tracks()

    user_tracks_df = map_tracks_to_tabular(user_tracks)

    id_tracks = user_tracks_df['id'].tolist()
    equally_chunks = [id_tracks[i:i+n] for i in range(0, len(id_tracks), 100)]
    audio_features = [sp.audio_features(tracks=ids) for ids in equally_chunks]
    print(audio_features)


if __name__ == "__main__":
    main()

