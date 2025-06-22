import os
import requests
from PIL import Image
from client_secrets import CLIENT_ID, CLIENT_SECRET

class AssetManager():
    def __init__(self):
        self.auth_url = 'https://id.twitch.tv/oauth2/token'
        self.params = {
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'grant_type': 'client_credentials'
        }

        try:
            self.access_token = requests.post(self.auth_url, params=self.params).json()['access_token']
            self.headers = {
                'Client-ID': CLIENT_ID,
                'Authorization': f'Bearer {self.access_token}'
            }
        except Exception as e:
            print(f"Failed to get access token: {e}")

    def search(self, query, save_dir='screenshots'):
        try:
            # Try exact match first
            exact_body = f'''
                search "{query}";
                fields name, screenshots;
                limit 10;
            '''
            resp = requests.post('https://api.igdb.com/v4/games', headers=self.headers, data=exact_body)
            games = resp.json()

            if games:
                for game in games:
                    if game.get("name").lower() == query.lower():
                        name = game.get('name')
                        screenshot_ids = game.get("screenshots", [])
                        print(f"Game: {name}")
                        if screenshot_ids:
                            self.get_and_download_screenshots(name, screenshot_ids, save_dir)
                            return True
        except Exception as e:
            print(f"Search query failed: {e}")

    def get_and_download_screenshots(self, game_name, ids, save_dir):
        try:
            id_list = ','.join(str(i) for i in ids)
            body = f'''
                fields url;
                where id = ({id_list});
            '''
            resp = requests.post('https://api.igdb.com/v4/screenshots', headers=self.headers, data=body)
            if resp.status_code == 200:
                urls = resp.json()
                for i, shot in enumerate(urls):
                    url = "https:" + shot['url'].replace('t_thumb', 't_1080p')
                    game_name = game_name.replace(' ', '_').replace(':', '')
                    filename = f"{game_name}.jpg"
                    self.download_image(url, save_dir, filename)
                    return True
            else:
                print("  Failed to fetch screenshots:", resp.status_code, resp.text)
                return False
        except Exception as e:
            print(f"get_and_download failed: {e}")

    def download_image(self, url, folder, filename):
        try:
            os.makedirs(folder, exist_ok=True)
            path = os.path.join(folder, filename)

            r = requests.get(url, stream=True)
            if r.status_code == 200:
                with open(path, 'wb') as f:
                    for chunk in r.iter_content(1024):
                        f.write(chunk)
                try:
                    img = Image.open(path)
                    img.thumbnail((800,450))
                    img.save(path)
                    print(f"  Saved and compressed: {path}")
                except Exception as e:
                    print(f"Failed to compress {path}: {e}")
            else:
                print(f"  Failed to download {url} (status {r.status_code})")
        except Exception as e:
            print(f"Downloading image failed: {e}")



if __name__ == "__main__":
    am = AssetManager()
    search = input("Type search query: ")
    am.search(search, save_dir='assets')
