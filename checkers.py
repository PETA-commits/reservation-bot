class LinkChecker:
    def __init__(self):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    def identify_platform(self, url):
        url = url.strip().lower()

        if 'youtube.com' in url or 'youtu.be' in url:
            return 'youtube'
        elif 'instagram.com' in url:
            return 'instagram'
        elif 't.me' in url or 'telegram.me' in url or url.startswith('@'):
            return 'telegram'

        return None

    async def check_youtube_channel(self, url):
        if '/@' in url:
            username = url.split('/@')[-1].split('/')[0]
        elif '/channel/' in url:
            username = url.split('/channel/')[-1].split('/')[0]
        elif '/c/' in url:
            username = url.split('/c/')[-1].split('/')[0]
        else:
            username = url.rstrip('/').split('/')[-1]

        return True, username

    async def check_instagram_profile(self, url):
        parts = url.rstrip('/').split('/')
        username = parts[-1] if parts[-1] else parts[-2]
        return True, username

    async def check_telegram(self, url):
        username = url.replace('@', '').split('/')[-1].strip()
        username = username.split('?')[0]
        return True, username