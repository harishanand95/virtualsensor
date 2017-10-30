import argparse
import asyncio
import aiohttp
from contextlib import suppress

chunk_size = 1024  # Set to 1 KB chunks

async def download_url(url, output, apikey):
    print('\n*********    Opening TCP: {}     *********\n'.format(url))
    headers = {'apikey': apikey}
    try:
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=False)) as session:
            async with session.get(url, headers=headers, timeout=None) as response:
                while True:
                    chunk = await response.content.read(chunk_size)
                    print(chunk)
                    with open("air_pollution/async_http_read_files/files/{0}".format(output), 'wb') as f:
                        f.write(chunk)
                    if not chunk:
                        break
    except Exception as e:
        print("\n*********    Oops: " + url + " " + str(type(e)) + str(e) + "     *********\n")

    print('\n*********    Closing TCP: {}     *********\n'.format(url))

def main():
    # get the URL from the command-line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('url', metavar='URL', help='The URL to download')
    parser.add_argument('writefile', help='The file to write')
    parser.add_argument('apikey', help='api key of the subscriber')
    arguments = parser.parse_args()
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(download_url(arguments.url, arguments.writefile, arguments.apikey))
    except KeyboardInterrupt:  # kills all tasks when SIGTERM is given
        pending = asyncio.Task.all_tasks()
        for task in pending:
            task.cancel()
            with suppress(asyncio.CancelledError):
                loop.run_until_complete(task)


if __name__ == '__main__':
    main()