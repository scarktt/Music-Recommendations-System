import argparse
import json
import math

import pandas as pd
import requests
import spotipy

from cfg_prod import CLIENT_ID, CLIENT_SECRET, SPOTIPY_REDIRECT_URI

scope = "user-library-read,playlist-read-private"
sp = spotipy.Spotify(auth_manager=spotipy.oauth2.SpotifyOAuth(client_id=CLIENT_ID,
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


def get_tracks_features(id_tracks):
    limit=100
    equally_chunks = [id_tracks[i:i+limit] for i in range(0, len(id_tracks), limit)]
    track_features = []
    for ids in equally_chunks:
        track_features += sp.audio_features(tracks=ids)
    return track_features


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
    # print(playlists_df)
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
    # print(tracks_df)
    return tracks_df


def extract(user:str, target_playlist:str):
    playlists_results = get_all_user_playlists()

    user_own_playlists = list(filter(lambda playlist: playlist['owner']['id'] == user, playlists_results))

    playlist_df = map_playlists_to_tabular(user_own_playlists)

    test_playlist = playlist_df.loc[playlist_df['name'] == target_playlist]

    user_tracks, target_tracks = [], []
    for playlist in user_own_playlists:
        print(f'getting songs from {playlist["name"]} playlist...')
        playlist_id = playlist['id']
        if playlist["name"] == target_playlist:
            target_tracks = get_playlist_tracks(playlist_id, {}, 0, [])
        else:
            user_tracks += get_playlist_tracks(playlist_id, {}, 0, [])

    print(f'getting saved songs...')
    user_tracks += get_saved_tracks()

    user_tracks_df = map_tracks_to_tabular(user_tracks)
    target_tracks_df = map_tracks_to_tabular(target_tracks)

    id_tracks = user_tracks_df['id'].tolist()
    id_target_tracks = target_tracks_df['id'].tolist()
    tracks_features = get_tracks_features(id_tracks)
    target_tracks_features = get_tracks_features(id_target_tracks)

    tracks_features_df = pd.DataFrame(tracks_features, columns = ["danceability", "energy", "key", "loudness", "mode", "speechiness", "acousticness", "instrumentalness", "liveness", "valence", "tempo", "type", "id", "uri", "track_href", "analysis_url","duration_ms", "time_signature"])
    target_tracks_features_df = pd.DataFrame(target_tracks_features, columns = ["danceability", "energy", "key", "loudness", "mode", "speechiness", "acousticness", "instrumentalness", "liveness", "valence", "tempo", "type", "id", "uri", "track_href", "analysis_url","duration_ms", "time_signature"])

    df = user_tracks_df.merge(tracks_features_df, on=['id'])
    target_df = target_tracks_df.merge(target_tracks_features_df, on=['id'])
    df.drop(['analysis_url', 'type', 'track_href', 'uri'], axis=1, inplace=True)
    target_df.drop(['analysis_url', 'type', 'track_href', 'uri'], axis=1, inplace=True)
    return df, target_df

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generates music recommendations based on 100% own saved music.')
    parser.add_argument('-u', '--user', required=True, help='Spotify username.')
    parser.add_argument('-p', '--playlist', required=True, help='Spotify playlist name.')
    parser.add_argument('--dev', default=False, action='store_true', help='Uses a dev configuration to connect with spotify (default: False)')
    args = parser.parse_args()
    dev = args.dev
    user = args.user
    playlist = args.playlist

    df, target_df = extract(user, playlist)
    print(f"{df}\n{target_df}")

