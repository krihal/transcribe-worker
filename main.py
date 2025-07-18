import os
import sys
import logging
import threading

from daemonize import Daemonize
from random import randint
from time import sleep
from utils.log import get_logger, get_fileno
from utils.settings import get_settings
from utils.args import parse_arguments

settings = get_settings()
logger = get_logger()
foreground, pidfile, zap, _, _, _ = parse_arguments()

if not zap:
    from utils.job import TranscriptionJob


def mainloop(worker_id: int) -> None:
    """
    Main function to fetch jobs and process them.
    """

    logger.info(f"Worker thread {worker_id} started")

    api_url = f"{settings.API_BACKEND_URL}/api/{settings.API_VERSION}/job"
    api_token = settings.OIDC_TOKEN

    while True:
        sleep(randint(10, 60))

        with TranscriptionJob(
            logger,
            api_url,
            api_token,
            settings.FILE_STORAGE_DIR,
            hf_whisper=settings.HF_WHISPER,
            hf_token=settings.HF_TOKEN,
        ) as job:
            job.start()


def main() -> None:
    logger.info("Starting transcription service...")

    for i in range(settings.WORKERS):
        thread = threading.Thread(target=mainloop, args=(i,))
        thread.start()


def daemon_kill() -> None:
    try:
        pid = int(open(pidfile, "r").read().strip())
        print(f"Zapping transcription service with PID {pid}...")
        os.kill(pid, 9)
        os.remove(pidfile)
    except FileNotFoundError:
        print("PID file not found, nothing to zap.")


def daemon_running() -> None:
    """
    Check if the daemon is running by checking the PID file.
    """
    if not os.path.exists(pidfile):
        return False

    try:
        with open(pidfile, "r") as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)
    except FileNotFoundError:
        return
    except ProcessLookupError:
        os.remove(pidfile)
        return

    print(f"Daemon is already running with PID {pid}.")
    sys.exit(1)


if __name__ == "__main__":
    if zap:
        daemon_kill()
    elif foreground:
        daemon_running()
        main()
    else:
        daemon_running()
        daemon = Daemonize(
            app="transcription_service",
            pid=pidfile,
            action=main,
            foreground=False,
            verbose=True,
            keep_fds=[get_fileno()],
            auto_close_fds=False,
            chdir=os.getcwd(),
        )
        daemon.start()
