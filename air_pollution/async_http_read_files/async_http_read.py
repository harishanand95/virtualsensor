import argparse
import asyncio
import aiohttp
from contextlib import suppress

chunk_size = 1024  # Set to 1 KB chunks

async def download_url(url):
    print('Opening TCP connection to the url: {} \n'.format(url))
    headers = {'apikey': '5cfc255cdb3c47e184d4f2ae08660db8'}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            while True:
                chunk = await response.content.read(chunk_size)
                print(chunk)
                with open("air_pollution/async_http_read_files/output.txt", 'wb') as f:
                    f.write(chunk)
                if not chunk:
                    break
    print('Closing TCP connection to the url: {} \n'.format(url))

def main():
    # get the URL from the command-line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('url', metavar='URL', help='The URL to download')
    arguments = parser.parse_args()
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(download_url(arguments.url))
    except KeyboardInterrupt:  # kills all tasks when SIGTERM is given
        pending = asyncio.Task.all_tasks()
        for task in pending:
            task.cancel()
            with suppress(asyncio.CancelledError):
                loop.run_until_complete(task)


if __name__ == '__main__':
    main()