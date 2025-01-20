import asyncio
import atexit
import multiprocessing

from tasks.check import check
from tasks.notification import notification


async def setup_tasks():
    tasks = [
        check(),
        notification(),
    ]

    await asyncio.gather(*tasks)


def _wrapper():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(setup_tasks())


def run_tasks():
    process = multiprocessing.Process(target=_wrapper)
    process.start()

    def _atexit():
        process.terminate()
        process.kill()

    atexit.register(_atexit)
